from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^board/(?P<board_code>\w+)/(?P<page>\d*)/?$', views.board_view, name='board'),
    url(r'^thread/(?P<thread_pk>\d+)/(?P<page>\d*)/?$', views.thread_view, name='thread'),
    url(r'^post/(?P<post_pk>\d+)/(?P<vote>up)/?$', views.vote, name='pos_vote' ),
    url(r'^post/(?P<post_pk>\d+)/(?P<vote>down)/?$', views.vote, name='neg_vote' ),
]
