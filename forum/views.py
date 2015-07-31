from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Board, Thread

# Create your views here.

ELEM_PER_PAGE = 2


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
    td = get_object_or_404(Thread, pk=thread_pk)
    posts = td.post_set.order_by('pub_date')
    paginator = Paginator(posts, ELEM_PER_PAGE)
    try:
        post_list = paginator.page(page)
    except PageNotAnInteger:
        post_list = paginator.page(1)
    except EmptyPage:
        post_list = paginator.page(paginator.num_pages)
    return render(request, 'forum/thread.html', {'thread': td, 'posts': post_list})
