from django.conf.urls import url
from djangle import views as djangleviews

urlpatterns = [
    url(r'^$', djangleviews.mainpage, name='index'),
]
