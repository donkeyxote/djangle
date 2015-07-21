from django.contrib.auth import logout
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response


def mainpage(request):
    return render_to_response('index.html', {'request': request})


def logout_view(request):
    logout(request)
    return HttpResponseRedirect('/')
