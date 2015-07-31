from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^board/(?P<board_code>\w+)/(?P<page>\d*)$', views.board_view, name='board')
]
