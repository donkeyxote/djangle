from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Board, Thread, Post, Vote
from .forms import PostForm, BoardForm

# Create your views here.

ELEM_PER_PAGE = 20


def index(request):
    board_list = Board.objects.all().order_by('name')
    return render(request, 'forum/index.html', {'boards': board_list})


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


def thread_view(request, thread_pk, page):
    thread = get_object_or_404(Thread, pk=thread_pk)
    posts = thread.post_set.order_by('pub_date')
    paginator = Paginator(posts, ELEM_PER_PAGE)
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            Post.create(message=form.cleaned_data['message'], thread=thread, author=request.user)
            return HttpResponseRedirect(reverse('forum:thread',
                                                kwargs={'thread_pk': thread_pk, 'page': paginator.num_pages}),'#bottom')
    else:
        form = PostForm()
    try:
        post_list = paginator.page(page)
    except PageNotAnInteger:
        post_list = paginator.page(1)
    except EmptyPage:
        post_list = paginator.page(paginator.num_pages)
    return render(request, 'forum/thread.html', {'thread': thread, 'posts': post_list, 'form': form})


def create_board(request):
    if request.method == 'POST':
        form = BoardForm(request.POST)
        if form.is_valid():
            Board.create(name=form.cleaned_data['name'], code=form.cleaned_data['code'])
            return redirect('forum:index')
    else:
        form = BoardForm()
    return render(request, 'forum/create_board.html', {'form': form})


def vote_view(request, post_pk, vote):
    redirect_to = request.REQUEST.get('next', '')
    post = get_object_or_404(Post, pk=post_pk)
    if vote == 'up':
        Vote.vote(post=post, user=request.user, value=True)
    elif vote == 'down':
        Vote.vote(post=post, user=request.user, value=False)
    return HttpResponseRedirect(redirect_to)
