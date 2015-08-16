import os
import datetime
from operator import itemgetter

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone

from forum.decorators import user_passes_test_with_403
from forum.models import Board, Thread, Post, Vote, User, Subscription, Moderation, Ban
from forum.forms import PostForm, BoardForm, ThreadForm, UserEditForm, SubscribeForm, AddModeratorForm, AddBanForm, \
    BoardModForm
from forum.tasks import sync_mail, del_mail
from djangle.settings import ELEM_PER_PAGE

# Create your views here.


def index(request):
    board_list = Board.objects.all().order_by('name')
    return render(request, 'forum/index.html', {'boards': board_list})


@login_required
def board_view(request, board_code, page):
    board = get_object_or_404(Board, code=board_code)
    thread_set = board.get_latest()
    st_threads = []
    threads = []
    for thread in thread_set:
        if thread.sticky:
            st_threads.append(thread)
        else:
            threads.append(thread)
    thread_set = st_threads+threads
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
    thread = get_object_or_404(Thread, pk=thread_pk)
    posts = thread.post_set.order_by('pub_date')
    paginator = Paginator(posts, ELEM_PER_PAGE)
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = Post.create(message=form.cleaned_data['message'], thread=thread, author=request.user)
            sync_mail.delay(post)
            return HttpResponseRedirect(reverse('forum:thread',
                                                kwargs={'thread_pk': thread_pk, 'page': paginator.num_pages})+'#bottom')
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
    if request.method == 'POST':
        form = BoardForm(request.POST)
        if form.is_valid():
            Board.create(name=form.cleaned_data['name'], code=form.cleaned_data['code'])
            return redirect('forum:index')
    else:
        form = BoardForm()
    return render(request, 'forum/create.html', {'forms': [form], 'object': 'board'})


@login_required
def vote_view(request, post_pk, vote):
    redirect_to = request.REQUEST.get('next', '')
    post = get_object_or_404(Post, pk=post_pk)
    if vote == 'up':
        Vote.vote(post=post, user=request.user, value=True)
    elif vote == 'down':
        Vote.vote(post=post, user=request.user, value=False)
    return HttpResponseRedirect(redirect_to)


@login_required
def create_thread(request):
    if request.method == 'POST':
        thread_form = ThreadForm(request.POST)
        post_form = PostForm(request.POST)
        if thread_form.is_valid() and post_form.is_valid():
            thread = Thread.create(title=thread_form.cleaned_data['title'],
                                   message=post_form.cleaned_data['message'],
                                   board=thread_form.cleaned_data['board'],
                                   author=request.user,
                                   tag1=thread_form.cleaned_data['tag1'],
                                   tag2=thread_form.cleaned_data['tag2'],
                                   tag3=thread_form.cleaned_data['tag3'])
            return HttpResponseRedirect(reverse('forum:thread',
                                                kwargs={'thread_pk': thread.pk, 'page': ''}))
    else:
        thread_form = ThreadForm()
        post_form = PostForm()
    return render(request, 'forum/create.html', {'forms': [thread_form, post_form], 'object': 'thread'})


@login_required
def profile(request, username):
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
            except:
                check = False
            if check and form.cleaned_data['avatar']:
                image = form.cleaned_data['avatar']
                if image.size > 200 * 1024:
                    return render(request, 'forum/profile_edit.html')
                extension = image.name.rsplit('.', 1)[1]
                if extension in ('jpg', 'jpeg', 'gif', 'png'):
                    image.name = request.user.username+'.'+extension
                    if not request.user.avatar.name.endswith('Djangle_user_default.png'):
                        img_del = request.user.avatar.path
                        try:
                            os.remove(img_del)
                        except:
                            pass
                    request.user.avatar = image
                    request.user.save()
            else:
                form = UserEditForm()
                return render(request, 'forum/profile_edit.html',
                              {'form': form, 'user': request.user, 'error': 'Form not valid'})
    else:
        form = UserEditForm()
    return render(request, 'forum/profile_edit.html', {'form': form, 'user': request.user})


@login_required
def reset_user_field(request, field):
    if field == 'first_name':
        request.user.first_name = ''
        request.user.save()
    elif field == 'last_name':
        request.user.last_name = ''
        request.user.save()
    elif field == 'avatar':
        request.user.reset_avatar()
    return HttpResponseRedirect(reverse('forum:profile', kwargs={'username': request.user.username}))


@login_required
def subscribe(request, thread_pk):
    thread = get_object_or_404(Thread, pk=thread_pk)
    if request.method == 'POST':
        form = SubscribeForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['async']:
                str_int = form.cleaned_data['interval'].split('.')[0]
                interval = datetime.timedelta(seconds=int(str_int))
                sub, created = Subscription.create(thread=thread, user=request.user,
                                                   async=True, sync_interval=interval, active=True)
                if created:
                    sub.save()
            else:
                sub, created = Subscription.create(thread=thread, user=request.user, async=False, active=True)
                if created:
                    sub.save()
        return HttpResponseRedirect(reverse('forum:thread', kwargs={'thread_pk': thread.pk, 'page': ''}))
    else:
        form = SubscribeForm()
        return render(request, 'forum/create.html', {'thread': thread, 'forms': [form], 'object': 'subscription'})


@login_required
def unsubscribe(request, thread_pk):
    thread = get_object_or_404(Thread, pk=thread_pk)
    if Subscription.objects.filter(thread=thread, user=request.user):
        Subscription.objects.get(thread=thread, user=request.user).delete()
    return HttpResponseRedirect(reverse('forum:thread', kwargs={'thread_pk': thread_pk, 'page': ''}))


@login_required
def close_thread(request, thread_pk):
    thread = get_object_or_404(Thread, pk=thread_pk)
    if (thread.first_post.author.username == request.user.username or
            request.user.moderation_set.filter(board=thread.board).exists() or
            request.user.is_supermod()) and not thread.is_closed():
        now = timezone.now()
        thread.close_date = now
        thread.closer = request.user
        thread.save()
    return HttpResponseRedirect(reverse('forum:thread', kwargs={'thread_pk': thread.pk, 'page': ''}))


@login_required
def open_thread(request, thread_pk):
    thread = get_object_or_404(Thread, pk=thread_pk)
    if thread.closer.username == request.user.username == thread.first_post.author or \
            request.user.moderation_set.filter(board=thread.board).exists() or \
            request.user.is_supermod():
        thread.close_date = None
        thread.save()
    return HttpResponseRedirect(reverse('forum:thread', kwargs={'thread_pk': thread.pk, 'page': ''}))


@user_passes_test_with_403(lambda u: u.is_supermod)
def manage_user_mod(request, user_pk):
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
            if ban_old:
                ban_old.delete()
        return HttpResponseRedirect(reverse('forum:profile', kwargs={'username': user.username}))
    else:
        form = AddBanForm()
    return render(request, 'forum/create.html', {'forms': [form]})


@user_passes_test_with_403(lambda u: u.is_mod or u.is_supermod)
def unban_user(request, user_pk):
    user = get_object_or_404(User, pk=user_pk)
    ban = Ban.objects.filter(user=user).last()
    ban.remove()
    return HttpResponseRedirect(reverse('forum:profile', kwargs={'username': user.username}))


@user_passes_test_with_403(lambda u: u.is_superuser)
def manage_supermods(request):
    supermods = []
    for user in User.objects.exclude(username='admin'):
        if user.is_supermod():
            supermods.append(user)
    return render(request, 'forum/supermods.html', {'supermods': supermods})


@user_passes_test_with_403(lambda u: u.is_superuser)
def supermod_toggle(request, user_pk):
    user = get_object_or_404(User, pk=user_pk)
    if user.is_supermod():
        user.set_supermod(False)
    else:
        user.set_supermod(True)
    return HttpResponseRedirect(reverse('forum:supermods'))


@login_required
def stick_thread(request, thread_pk):
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
    moderators = {}
    for board in Board.objects.all():
        moderators[board] = board.moderation_set.all()
    return render(request, 'forum/moderators.html', {'moderators': moderators})


@user_passes_test_with_403(lambda u: u.is_supermod())
def remove_mod(request, user_pk, board_code):
    user = get_object_or_404(User, pk=user_pk)
    board = get_object_or_404(Board, code=board_code)
    mod = get_object_or_404(Moderation, user=user, board=board)
    mod.delete()
    return HttpResponseRedirect(reverse('forum:moderators'))


@user_passes_test_with_403(lambda u: u.is_supermod())
def manage_board_mod(request, board_code):
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
