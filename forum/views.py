from django.shortcuts import render
from .models import Board

# Create your views here.


def index(request):
    board_list = Board.objects.all().order_by('name')
    return render(request, 'forum/index.html', {'boards': board_list})
