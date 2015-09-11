"""
module for site's views
"""

from django.contrib.auth import logout
from django.contrib.auth.views import login
from djangle.forms import UserCreationForm, LoginForm
from django.shortcuts import render_to_response, redirect, render


def mainpage(request):
    """
    view for main page's rendering

    :param request: the user's request
    :return: the mainpage
    """
    return render_to_response('index.html', {'request': request})


def login_view(request):
    """
    view for user's login

    :param request: the user's request
    :return: render login view or, if user is authenticated, redirect to main page
    """
    if request.user.is_authenticated():
        return redirect('main_page')
    else:
        return login(request, authentication_form=LoginForm)


def logout_view(request):
    """
    view for user's logout

    :param request: the user's request
    :return: redirect to main page
    """
    logout(request)
    return redirect('main_page')


def register(request):
    """
    view for user registration

    :param request: the user's request
    :return: render registration page or, if user is authenticated, redirect to main page
    """
    if request.user.is_authenticated():
        return redirect('main_page')
    elif request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('main_page')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})
