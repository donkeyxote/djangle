"""djangle forum URL Configuration

The `urlpatterns` list routes URLs to views.
"""
from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^create/board/$', views.create_board, name='create_board'),
    url(r'^create/moderation/(?P<user_pk>\d*)/?$', views.manage_user_mod, name='edit_mod'),
    url(r'^create/boardmoderation/(?P<board_code>\w+)/?$', views.manage_board_mod, name='board_mod'),
    url(r'^create/thread/$', views.create_thread, name='create_thread'),
    url(r'^board/(?P<board_code>\w+)/(?P<page>\d*)/?$', views.board_view, name='board'),
    url(r'^thread/(?P<thread_pk>\d+)/(?P<page>\d*)/?$', views.thread_view, name='thread'),
    url(r'^post/(?P<post_pk>\d+)/(?P<vote>up)/?$', views.vote_view, name='pos_vote'),
    url(r'^post/(?P<post_pk>\d+)/(?P<vote>down)/?$', views.vote_view, name='neg_vote'),
    url(r'^profile/(?P<username>[\w\+\-@_\.]+)/$', views.profile, name='profile'),
    url(r'^edit/profile/$', views.edit_profile, name='edit_profile'),
    url(r'^edit/profile/(?P<field>first_name)/$', views.reset_user_field, name='reset_first_name'),
    url(r'^edit/profile/(?P<field>last_name)/$', views.reset_user_field, name='reset_last_name'),
    url(r'^edit/profile/(?P<field>avatar)/$', views.reset_user_field, name='reset_avatar'),
    url(r'^post/(?P<post_pk>\d+)/delete/$', views.del_post, name='del_post'),
    url(r'^comment/post/(?P<post_pk>\d+)/$', views.comment, name='comment'),
    url(r'^comment/(?P<comment_pk>\d+)/delete/$', views.del_comment, name='del_comment'),
    url(r'^thread/(?P<thread_pk>\d+)/subscribe/$', views.subscribe, name='subscribe'),
    url(r'^thread/(?P<thread_pk>\d+)/unsubscribe/$', views.unsubscribe, name='unsubscribe'),
    url(r'^thread/(?P<thread_pk>\d+)/close/$', views.toggle_close_thread, name='toggle_close_thread'),
    url(r'^thread/(?P<thread_pk>\d+)/stick/$', views.stick_thread, name='stick_thread'),
    url(r'^tag/(?P<tag>\w+)/(?P<page>\d*)/?$', views.tag_view, name='tag'),
    url(r'^manage/supermods/$', views.manage_supermods, name='supermods'),
    url(r'^manage/supermods/toggle/(?P<user_pk>\d+)/$', views.supermod_toggle, name='supermod_toggle'),
    url(r'^manage/moderators/$', views.moderators_view, name='moderators'),
    url(r'^remove/moderation/(?P<user_pk>\d+)/(?P<board_code>\w+)', views.remove_mod, name='remove_mod'),
    url(r'^manage/ban/(?P<user_pk>\d+)/$', views.ban_user, name='ban_user'),
    url(r'^manage/unban/(?P<user_pk>\d+)/$', views.unban_user, name='unban_user'),
    url(r'^search/(?P<page>\d*)/?$', views.search, name='search'),
    url(r'^search/new/$', views.new_search, name='new_search')
]
