from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^thread/(?P<thread_pk>[0-9]+)/(?P<page>.*)$', views.thread_view, name='thread'),
]
