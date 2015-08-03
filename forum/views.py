from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Board, Thread, Post, Vote, User
from .forms import PostForm, BoardForm, ThreadForm
from operator import itemgetter

# Create your views here.

ELEM_PER_PAGE = 20


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
            Post.create(message=form.cleaned_data['message'], thread=thread, author=request.user)
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
            if post.pk == post.in_thread.first_post.pk:
                threads.append((post.in_thread, votes))
            else:
                posts.append((post, votes, post.get_page(ELEM_PER_PAGE)))
        posts.sort(key=itemgetter(1), reverse=True)
        top_posts = posts[:5]
        threads.sort(key=itemgetter(1), reverse=True)
        top_threads = threads[:5]
    return render(request, 'forum/profile.html', {'user': user, 'top_threads': top_threads, 'top_posts': top_posts})
