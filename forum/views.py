"""
module for form views
"""

import os
import datetime
from operator import itemgetter, attrgetter

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone

from .decorators import user_passes_test_with_403
from .models import Board, Thread, Post, Vote, User, Subscription, Moderation, Ban
from .tasks import sync_mail, del_mail, ban_create_mail, ban_remove_mail
from .forms import PostForm, BoardForm, ThreadForm, UserEditForm, SubscribeForm, AddModeratorForm, AddBanForm, \
    BoardModForm, SearchForm

from djangle.settings import ELEM_PER_PAGE


# Create your views here.


def index(request):
    """
    view for forum index

    return a list of recently commented threads grouped by board. you can set maximum number of posts to show
    for each board in function forum.models.get_new

    :param request: the user's request
    :return: render the list of threads
    """
    board_list = Board.objects.all().order_by('name')
    return render(request, 'forum/index.html', {'boards': board_list})


@login_required
def board_view(request, board_code, page):
    """
    view for board

    render the threads' list associated with the board. first threads shown are sticky ones, then recently commented
    follow. if threads' number exceeds ELEM_PER_PAGE (set in djangle.settings) they will be paginated as appropriate.

    :param request: the user's request
    :param board_code: code of the board
    :param page: page of threads' list to show
    :return: render the list of threads in selected page
    """
    board = get_object_or_404(Board, code=board_code)
    thread_set = board.get_latest()
    st_threads = []
    threads = []
    for thread in thread_set:
        if thread.sticky:
            st_threads.append(thread)
        else:
            threads.append(thread)
    thread_set = st_threads + threads
    paginator = Paginator(thread_set, ELEM_PER_PAGE)
    try:
        thread_set = paginator.page(page)
    except PageNotAnInteger:
        thread_set = paginator.page(1)
    except EmptyPage:
        thread_set = paginator.page(paginator.num_pages)
    return render(request, 'forum/board.html', {'board': board, 'thread_set': thread_set})


@login_required
def thread_view(request, thread_pk, page):
    """
    view for thread

    render the post's list in selected thread, ordered from older to newer. if posts' number exceeds ELEM_PER_PAGE
    (set in djangle.settings) they will be paginated as appropriate.

    :param request: the user's request
    :param thread_pk: primary key of thread
    :param page: page of posts' list to show
    :return: render the list of posts in selected page
    """
    errors = []
    thread = get_object_or_404(Thread, pk=thread_pk)
    posts = thread.post_set.order_by('pub_date')
    paginator = Paginator(posts, ELEM_PER_PAGE)
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            try:
                post = Post.create(message=form.cleaned_data['message'], thread=thread, author=request.user)
                sync_mail.delay(post)
            except (TypeError, ValueError) as error:
                errors.append(str(error))
                return render(request, 'errors.html', {'errors': errors})
            return HttpResponseRedirect(reverse('forum:thread',
                                                kwargs={'thread_pk': thread_pk, 'page': paginator.num_pages}) +
                                        '#bottom')
    else:
        form = PostForm()
    try:
        post_list = paginator.page(page)
    except PageNotAnInteger:
        post_list = paginator.page(1)
    except EmptyPage:
        post_list = paginator.page(paginator.num_pages)
    return render(request, 'forum/thread.html', {'thread': thread, 'posts': post_list, 'form': form})


@user_passes_test_with_403(lambda u: u.is_supermod())
def create_board(request):
    """
    view for boards' creation

    display the form for new boards' creation

    :param request: the user's request
    :return: render form or redirect to new board view if board is created
    """
    errors = []
    if request.method == 'POST':
        form = BoardForm(request.POST)
        if form.is_valid():
            try:
                board = Board.create(name=form.cleaned_data['name'], code=form.cleaned_data['code'])
            except (TypeError, ValueError) as error:
                errors.append(str(error))
                return render(request, 'errors.html', {'errors': errors})
            return HttpResponseRedirect(reverse('forum:board', kwargs={'board_code': board.code, 'page': ''}))
    else:
        form = BoardForm()
    return render(request, 'forum/create.html', {'forms': [form], 'object': 'board'})


@login_required
def vote_view(request, post_pk, vote):
    """
    view for voting post

    a simple interface for templates to function forum.models.Vote.vote

    :param request: the user's request
    :param post_pk: primary key of post to vote
    :param vote: vote value. use "up" for positive vote, "down" for negative
    :return: redirect to updated post.
    """
    redirect_to = request.REQUEST.get('next', '')
    post = get_object_or_404(Post, pk=post_pk)
    if vote == 'up':
        Vote.vote(post=post, user=request.user, value=True)
    elif vote == 'down':
        Vote.vote(post=post, user=request.user, value=False)
    return HttpResponseRedirect(redirect_to)


@login_required
def create_thread(request):
    """
    view for threads' creation

    display the form for new threads' creation

    :param request: the user's request
    :return: render form or redirect to new thread if thread is created
    """
    errors = []
    if request.method == 'POST':
        thread_form = ThreadForm(request.POST)
        post_form = PostForm(request.POST)
        if thread_form.is_valid() and post_form.is_valid():
            try:
                thread = Thread.create(title=thread_form.cleaned_data['title'],
                                       message=post_form.cleaned_data['message'],
                                       board=thread_form.cleaned_data['board'],
                                       author=request.user,
                                       tag1=thread_form.cleaned_data['tag1'],
                                       tag2=thread_form.cleaned_data['tag2'],
                                       tag3=thread_form.cleaned_data['tag3'])
            except (TypeError, ValueError) as error:
                errors.append(str(error))
                return render(request, 'errors.html', {'errors': errors})

            return HttpResponseRedirect(reverse('forum:thread',
                                                kwargs={'thread_pk': thread.pk, 'page': ''}))
    else:
        thread_form = ThreadForm()
        post_form = PostForm()
    return render(request, 'forum/create.html', {'forms': [thread_form, post_form], 'object': 'thread'})


@login_required
def profile(request, username):
    """
    view for user's info

    render information about selected user like: first and last name (only if set), post and thread number, reputation,
    top threads, top posts, avatar, join date, last login, role

    :param request: the user's request
    :param username: username of the user to show
    :return: render user's profile info
    """
    user = get_object_or_404(User, username=username)
    threads = []
    top_threads = []
    posts = []
    top_posts = []
    if user.post_set.exists():
        for post in user.post_set.all():
            votes = post.pos_votes - post.neg_votes
            if post.pk == post.thread.first_post.pk:
                threads.append((post.thread, votes))
            else:
                posts.append((post, votes, post.get_page))
        posts.sort(key=itemgetter(1), reverse=True)
        top_posts = posts[:5]
        threads.sort(key=itemgetter(1), reverse=True)
        top_threads = threads[:5]
    return render(request, 'forum/profile.html', {'user': user, 'top_threads': top_threads, 'top_posts': top_posts})


@login_required
def del_post(request, post_pk):
    """
    view for deleting posts or threads

    delete post or thread of you are author, moderator or supermoderator and send mail to author

    :param request: the user's request
    :param post_pk: primary key of post (or first_post if deleting thread)
    :return: render to thread on current page (or first page of board if deleting thread)
    """
    post = get_object_or_404(Post, pk=post_pk)
    if (request.user.username == post.author.username) or\
            request.user.moderation_set.filter(board=post.thread.board).exists() or\
            request.user.is_supermod():
        if post.thread.first_post == post:
            thread = post.thread
            del_mail(thread.first_post, thread)
            thread.remove()
            return HttpResponseRedirect(reverse('forum:board', kwargs={'board_code': thread.board.code, 'page': ''}))
        else:
            redirect_to = request.GET.get('next', '')
            del_mail(post)
            post.remove()
            return HttpResponseRedirect(redirect_to)
    raise PermissionError


@login_required
def edit_profile(request):
    """
    view for change user's info

    change some user's info like: first and last name, avatar

    :param request: the user's request
    :return: render info's updating page
    """
    errors = []
    if request.method == 'POST':
        if not request.FILES:
            form = UserEditForm(request.POST)
            if form.is_valid():
                if form.cleaned_data['first_name']:
                    request.user.first_name = form.cleaned_data['first_name']
                    request.user.save()
                if form.cleaned_data['last_name']:
                    request.user.last_name = form.cleaned_data['last_name']
                    request.user.save()
        else:
            form = UserEditForm(request.POST, request.FILES)
            try:
                check = form.is_valid()
            except KeyError as error:
                check = False
                errors.append(str(error))
            if check and form.cleaned_data['avatar']:
                image = form.cleaned_data['avatar']
                extension = image.name.rsplit('.', 1)[1]
                if extension in ('jpg', 'jpeg', 'gif', 'png'):
                    image.name = request.user.username + '.' + extension
                    image.name = request.user.username + '.' + extension
                    if not request.user.avatar.name.endswith('Djangle_user_default.png'):
                        img_del = request.user.avatar.path
                        try:
                            os.remove(img_del)
                        except FileNotFoundError:
                            pass
                        except Exception as error:
                            errors.append(str(error))
                            return render(request, 'errors.html', {'errors': errors})
                    request.user.avatar = image
                    request.user.save()
                else:
                    errors.append('image must end with .jpg, .jpeg, .gif or .png')

    form = UserEditForm()
    return render(request, 'forum/profile_edit.html', {'form': form, 'user': request.user, 'errors': errors})


@login_required
def reset_user_field(request, field):
    """
    view for clearing fields

    interface for templates to clear user's editable fields

    :param request: the user's request
    :param field: name of field to clear. use "first_name" for first name, "last_name" for last name and "avatar"
    for profile picture
    :return: redirect to profile edit view
    """
    if field == 'first_name':
        request.user.first_name = ''
        request.user.save()
    elif field == 'last_name':
        request.user.last_name = ''
        request.user.save()
    elif field == 'avatar':
        request.user.reset_avatar()
    form = UserEditForm()
    return render(request, 'forum/profile_edit.html', {'form': form, 'user': request.user})


@login_required
def subscribe(request, thread_pk):
    """
    view for creating subscriptions

    render form for subscriptions' creation

    :param request: the user's request
    :param thread_pk: primary key of thread to subscribe
    :return: render form for subscriptions' creation or redirect to thread if subscription is created
    """
    errors = []
    thread = get_object_or_404(Thread, pk=thread_pk)
    if request.method == 'POST':
        form = SubscribeForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['async']:
                str_int = form.cleaned_data['interval'].split('.')[0]
                sync_interval = datetime.timedelta(seconds=int(str_int))
                async = True
            else:
                async = False
                sync_interval = None
            try:
                Subscription.create(thread=thread, user=request.user,
                                    async=async, sync_interval=sync_interval, active=True)
            except (TypeError, ValueError) as error:
                errors.append(str(error))
                return render(request, 'errors.html', {'errors': errors})
        return HttpResponseRedirect(reverse('forum:thread', kwargs={'thread_pk': thread.pk, 'page': ''}))
    else:
        form = SubscribeForm()
        return render(request, 'forum/create.html', {'thread': thread, 'forms': [form], 'object': 'subscription'})


@login_required
def unsubscribe(request, thread_pk):
    """
    view for subscription deletion

    delete user's subscription to thread

    :param request: the user's request
    :param thread_pk: primary key of thread to unsubscribe
    :return: redirect to selected thread
    """
    thread = get_object_or_404(Thread, pk=thread_pk)
    if Subscription.objects.filter(thread=thread, user=request.user):
        Subscription.objects.get(thread=thread, user=request.user).delete()
    return HttpResponseRedirect(reverse('forum:thread', kwargs={'thread_pk': thread_pk, 'page': ''}))


@login_required
def toggle_close_thread(request, thread_pk):
    """
    view for closing/opening threads

    mark thread as closed/open if user is author, moderator or supermoderator and disable new posts

    :param request: the user's request
    :param thread_pk: primary key of thread to close
    :return: redirect to thread view
    """
    thread = get_object_or_404(Thread, pk=thread_pk)
    if (thread.first_post.author.username == request.user.username or
            request.user.moderation_set.filter(board=thread.board).exists() or
            request.user.is_supermod()):
        if thread.is_closed():
            thread.close_date = None
        else:
            thread.close_date = timezone.now()
            thread.closer = request.user
        thread.save()
    return HttpResponseRedirect(reverse('forum:thread', kwargs={'thread_pk': thread.pk, 'page': ''}))


@user_passes_test_with_403(lambda u: u.is_supermod)
def manage_user_mod(request, user_pk):
    """
    view for managing moderation for user

    display form for selecting which boards user can moderate

    :param request: the user's request
    :param user_pk: primary key of user to manage
    :return: render form for moderation management or redirect to target user's profile if management is over
    """
    user = get_object_or_404(User, pk=user_pk)
    if request.method == 'POST':
        form = AddModeratorForm(user, request.POST)
        if form.is_valid():
            for board in Board.objects.all():
                if form.cleaned_data[board.name] and board not in user.modded_boards():
                    mod = Moderation(user=user, board=board)
                    mod.save()
                elif board in user.modded_boards() and not form.cleaned_data[board.name]:
                    mod = get_object_or_404(Moderation, user=user, board=board)
                    mod.delete()
            return HttpResponseRedirect(reverse('forum:profile', kwargs={'username': user.username}))
    else:
        form = AddModeratorForm(user=user)
    return render(request, 'forum/create.html', {'forms': [form]})


@user_passes_test_with_403(lambda u: u.is_mod or u.is_supermod)
def ban_user(request, user_pk):
    """
    view for banning users

    ban an user and send a mail as notification. if user is banned already, the selected duration will be added to
    previous one

    :param request: the user's request
    :param user_pk: primary key of user to ban
    :return: render ban form or redirect to target user's profile if ban is created
    """
    user = get_object_or_404(User, pk=user_pk)
    if request.method == 'POST':
        ban_old = Ban.objects.filter(user=user).last()
        form = AddBanForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['duration'] is not '':
                str_int = form.cleaned_data['duration'].split('.')[0]
                interval = datetime.timedelta(seconds=int(str_int))
                if ban_old:
                    if ban_old.duration is None:
                        interval = None
                    else:
                        interval += ban_old.duration
            else:
                interval = None
            ban = Ban(user=user,
                      start=timezone.now(),
                      duration=interval,
                      banner=request.user,
                      reason=form.cleaned_data['reason'])
            ban.save()
            user.is_active = False
            user.save()
            ban_create_mail.delay(ban)
            if ban_old:
                ban_old.delete()
            return HttpResponseRedirect(reverse('forum:profile', kwargs={'username': user.username}))
    else:
        form = AddBanForm()
    return render(request, 'forum/create.html', {'forms': [form]})


@user_passes_test_with_403(lambda u: u.is_mod or u.is_supermod)
def unban_user(request, user_pk):
    """
    view for removing ban

    remove ban for selected user and send notification mail

    :param request: the user's request
    :param user_pk: primary key of user to redeem
    :return: redirect to target user's profile
    """
    user = get_object_or_404(User, pk=user_pk)
    ban = Ban.objects.filter(user=user).last()
    ban.remove()
    ban_remove_mail.delay(user)
    return HttpResponseRedirect(reverse('forum:profile', kwargs={'username': user.username}))


@user_passes_test_with_403(lambda u: u.is_superuser)
def manage_supermods(request):
    """
    view for supermoderator overview

    show supermoderators' list

    :param request: the user's request
    :return: render supermoderators' list
    """
    supermods = []
    for user in User.objects.exclude(username='admin'):
        if user.is_supermod():
            supermods.append(user)
    return render(request, 'forum/supermods.html', {'supermods': supermods})


@user_passes_test_with_403(lambda u: u.is_superuser)
def supermod_toggle(request, user_pk):
    """
    view for supermoderators management

    set if user is supermoderator

    :param request: the user's request
    :param user_pk: primary key of user to toggle
    :return: redirect to supermoderators view
    """
    user = get_object_or_404(User, pk=user_pk)
    if user.is_supermod():
        user.set_supermod(False)
    else:
        user.set_supermod(True)
    return HttpResponseRedirect(reverse('forum:supermods'))


@login_required
def stick_thread(request, thread_pk):
    """
    view to stick thread

    set if thread is sticky (to keep it on top of thread list in board)

    :param request: the user's request
    :param thread_pk: primary key of thread to stick
    :return: redirect to thread's view
    """
    thread = get_object_or_404(Thread, pk=thread_pk)
    if thread.sticky:
        thread.sticky = False
        thread.save()
    else:
        thread.sticky = True
        thread.save()
    return HttpResponseRedirect(reverse('forum:thread', kwargs={'thread_pk': thread.pk, 'page': ''}))


@user_passes_test_with_403(lambda u: u.is_supermod())
def moderators_view(request):
    """
    view for moderations' overview

    show a list of board in which each element has a list of moderators

    :param request: the user's request
    :return: render the list of moderators for each board
    """
    moderators = {}
    for board in Board.objects.all():
        moderators[board] = board.moderation_set.all()
    return render(request, 'forum/moderators.html', {'moderators': moderators})


@user_passes_test_with_403(lambda u: u.is_supermod())
def remove_mod(request, user_pk, board_code):
    """
    view for removing moderators from a board

    remove moderator from selected board and redirect to moderations' overview

    :param request: the user's request
    :param user_pk: primary key of user to remove from moderators
    :param board_code: code of board from which remove moderation
    :return: redirect to moderations' overview
    """
    user = get_object_or_404(User, pk=user_pk)
    board = get_object_or_404(Board, code=board_code)
    mod = get_object_or_404(Moderation, user=user, board=board)
    mod.delete()
    return HttpResponseRedirect(reverse('forum:moderators'))


@user_passes_test_with_403(lambda u: u.is_supermod())
def manage_board_mod(request, board_code):
    """
    view for managing board's moderators

    show form to update the list of moderator in a board. all users will be shown and selected ones will be moderators
    after post

    :param request: the user's request
    :param board_code: code of board to manage
    :return: render moderations' overview
    """
    board = get_object_or_404(Board, code=board_code)
    if request.method == 'POST':
        form = BoardModForm(board, request.POST)
        if form.is_valid():
            for user in User.objects.all():
                if form.cleaned_data[user.username] and board not in user.modded_boards():
                    mod = Moderation(user=user, board=board)
                    mod.save()
                elif board in user.modded_boards() and not form.cleaned_data[user.username]:
                    mod = get_object_or_404(Moderation, user=user, board=board)
                    mod.delete()
            return HttpResponseRedirect(reverse('forum:moderators'))
    else:
        form = BoardModForm(board=board)
    return render(request, 'forum/create.html', {'forms': [form], 'object': 'board moderation'})


@login_required
def tag_view(request, tag, page):
    """
    view for grouping thread by tag

    render a list of threads related to the same topic (tag), if threads' number exceeds ELEM_PER_PAGE
    (set in djangle.settings) they will be paginated as appropriate.

    :param request: the user's request
    :param tag: string representing the tag
    :param page: page of threads' list to show
    :return: render the list of threads in selected page
    """
    threads = Thread.objects.filter(Q(tag1=tag) | Q(tag2=tag) | Q(tag3=tag))
    posts = []
    for thread in threads:
        if thread.last_post() is not None:
            posts.append(thread.last_post())
    posts = sorted(posts, key=attrgetter('pub_date'), reverse=True)
    threads = []
    for post in posts:
        threads.append(post.thread)
    paginator = Paginator(threads, ELEM_PER_PAGE)
    try:
        threads = paginator.page(page)
    except PageNotAnInteger:
        threads = paginator.page(1)
    except EmptyPage:
        threads = paginator.page(paginator.num_pages)
    return render(request, 'forum/search_threads.html', {'search': 'Tag = ' + tag, 'threads': threads})


@login_required
def search(request, page):
    """
    view for search results

    render a list of threads selected by title, tags and username or a list of users selected by username,
    if objects' number exceeds ELEM_PER_PAGE (set in djangle.settings) they will be paginated as appropriate

    :param request: the user's request
    :param page: page to show
    :return: render the list of threads/users
    """
    if not request.method == 'POST':
        if 'search-form' in request.session:
            request.POST = request.session['search-form']
            request.method = 'POST'
    form = SearchForm(request.POST)
    request.session['search-form'] = request.POST
    threads = []
    search_message = ''
    if form.is_valid():
        if form.cleaned_data['search_item'] == 'user':
            if form.cleaned_data['username']:
                username = form.cleaned_data['username']
                users = User.objects.filter(username__icontains=username)
                paginator = Paginator(users, ELEM_PER_PAGE)
                try:
                    users = paginator.page(page)
                except PageNotAnInteger:
                    users = paginator.page(1)
                except EmptyPage:
                    users = paginator.page(paginator.num_pages)
                return render(request,
                              'forum/search_users.html',
                              {'search': 'Username = ' + username, 'users': users, 'page': page})
        else:
            if not (form.cleaned_data['title'] or form.cleaned_data['tags'] or form.cleaned_data['username']):
                return render(request, 'forum/search_threads.html', {'search': search_message,
                                                                     'threads': threads,
                                                                     'page': page,
                                                                     'errors': ['empty form']})
            threads = Thread.objects.all()
            if form.cleaned_data['title']:
                title = form.cleaned_data['title']
                threads = threads.filter(title__icontains=title)
                search_message = 'Title = ' + title
            if form.cleaned_data['tags']:
                tags = form.cleaned_data['tags']
                threads = threads.filter(Q(tag1__icontains=tags) | Q(tag2__icontains=tags) | Q(tag3__icontains=tags))
                search_message += ' Tag = ' + tags
            if form.cleaned_data['username']:
                username = form.cleaned_data['username']
                threads = threads.filter(first_post__author__username__icontains=username)
                search_message += ' Author = ' + username
            posts = []
            for thread in threads:
                if thread.last_post() is not None:
                    posts.append(thread.last_post())
            posts = sorted(posts, key=attrgetter('pub_date'), reverse=True)
            threads = [post.thread for post in posts]
            paginator = Paginator(threads, ELEM_PER_PAGE)
            try:
                threads = paginator.page(page)
            except PageNotAnInteger:
                threads = paginator.page(1)
            except EmptyPage:
                threads = paginator.page(paginator.num_pages)
        return render(request, 'forum/search_threads.html',
                      {'search': search_message, 'threads': threads, 'page': page})
    return render(request, 'forum/create.html', {'forms': [form], 'object': 'search'})


@login_required
def new_search(request):
    """
    view for a new search

    display the form for new search

    :param request: the user's request
    :return: render the search form or redirect to search results
    """
    if request.method == 'POST':
        request.session['search-form'] = request.POST
        return HttpResponseRedirect(reverse('forum:search', kwargs={'page': ''}))
    form = SearchForm()
    return render(request, 'forum/create.html', {'forms': [form], 'object': 'search'})
