from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^create/board/$', views.create_board, name='create_board'),
    url(r'^create/thread/$', views.create_thread, name='create_thread'),
    url(r'^board/(?P<board_code>\w+)/(?P<page>\d*)/?$', views.board_view, name='board'),
    url(r'^thread/(?P<thread_pk>\d+)/(?P<page>\d*)/?$', views.thread_view, name='thread'),
    url(r'^post/(?P<post_pk>\d+)/(?P<vote>up)/?$', views.vote_view, name='pos_vote'),
    url(r'^post/(?P<post_pk>\d+)/(?P<vote>down)/?$', views.vote_view, name='neg_vote'),
    url(r'^profile/(?P<username>\w+)/$', views.profile, name='profile'),
]
