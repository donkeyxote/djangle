from django.contrib.auth import logout
from django.contrib.auth.views import login
from djangle.forms import UserCreationForm
from django.shortcuts import render_to_response, redirect, render


def mainpage(request):
    return render_to_response('index.html', {'request': request})


def login_view(request):
    if request.user.is_authenticated():
        return redirect('main_page')
    else:
        return login(request)


def logout_view(request):
    logout(request)
    return redirect('main_page')


def register(request):
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
