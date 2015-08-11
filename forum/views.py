import os
import datetime
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Board, Thread, Post, Vote, User, Subscription
from .forms import PostForm, BoardForm, ThreadForm, UserEditForm, SubscribeForm
from operator import itemgetter
from djangle.settings import ELEM_PER_PAGE
from forum.tasks import sync_mail, del_mail
from djangle.settings import EMAIL_SUBJECT_PREFIX
from django.utils import timezone

# Create your views here.


def index(request):
    board_list = Board.objects.all().order_by('name')
    return render(request, 'forum/index.html', {'boards': board_list})


@login_required
def board_view(request, board_code, page):
    board = get_object_or_404(Board, code=board_code)
    thread_set = board.get_latest()
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


@login_required
def create_board(request):
    if request.method == 'POST':
        form = BoardForm(request.POST)
        if form.is_valid():
            Board.create(name=form.cleaned_data['name'], code=form.cleaned_data['code'])
            return redirect('forum:index')
    else:
        form = BoardForm()
    return render(request, 'forum/create.html', {'forms': [form]})


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
    return render(request, 'forum/create.html', {'forms': [thread_form, post_form]})


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
    redirect_to = request.GET.get('next', '')
    post = get_object_or_404(Post, pk=post_pk)
    if (request.user.username == post.author.username) or\
            request.user.moderation_set.filter(board=post.thread.board).exists() or\
            request.user.is_supermod():
        sub = EMAIL_SUBJECT_PREFIX+'your post was deleted'
        mex = 'The post:'+os.linesep+post.message+os.linesep+'in thread: '+post.thread.title+os.linesep+'was deleted'
        rec = post.author.email
        del_mail.delay(sub=sub, mex=mex, rec=rec)
        post.remove()
    return HttpResponseRedirect(redirect_to)


@login_required
def del_thread(request, thread_pk):
    thread = get_object_or_404(Thread, pk=thread_pk)
    board = thread.board
    if (request.user.username == thread.first_post.author.username) or\
            request.user.moderation_set.filter(board=thread.board).exists() or\
            request.user.is_supermod():
        sub = EMAIL_SUBJECT_PREFIX+'your thread was deleted'
        mex = 'Thread: '+thread.title+os.linesep+'in board: '+thread.board.name+os.linesep+'was deleted'
        rec = thread.first_post.author.email
        del_mail.delay(sub=sub, mex=mex, rec=rec)
        thread.remove()
        return HttpResponseRedirect(reverse('forum:board', kwargs={'board_code': board.code, 'page': ''}))
    else:
        return HttpResponseRedirect(reverse('forum:thread', kwargs={'thread_pk': thread_pk, 'page': ''}))


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
                sub, created = Subscription.create(thread=thread, user=request.user, async=True, sync_interval=interval, active=True)
                if created:
                    sub.save()
            else:
                sub, created = Subscription.create(thread=thread, user=request.user, async=False, active=True)
                if created:
                    sub.save()
        return HttpResponseRedirect(reverse('forum:thread', kwargs={'thread_pk': thread.pk, 'page': ''}))
    else:
        form = SubscribeForm()
        return render(request, 'forum/subscribe.html', {'thread': thread, 'form': form})


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
