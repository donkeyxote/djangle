from operator import attrgetter
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
# Create your models here.


class Board(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=10)

    def get_latest(self, num=5):
        latest_posts = []
        for thread in self.thread_set.all():
            if thread.last_post() is not None:
                latest_posts.append(thread.last_post())
        latest_posts = sorted(latest_posts, key=attrgetter('pub_date'), reverse=True)
        latest_threads = []
        for post in latest_posts[:num]:
            latest_threads.append(post.in_thread)
        return latest_threads

    def __str__(self):
        return self.code


class User(AbstractUser):
    models.EmailField.unique = True
    rep = models.IntegerField(default=0)
    avatar = models.ImageField(default='/static/djangle/images/Djangle_logo.png')
    posts = models.PositiveIntegerField(default=0)
    threads = models.PositiveIntegerField(default=0)


class Post(models.Model):
    message = models.CharField(max_length=5000)
    pub_date = models.DateTimeField('publication date')
    in_thread = models.ForeignKey('Thread')
    author = models.ForeignKey(User)
    pos_votes = models.PositiveIntegerField(default=0)
    neg_votes = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.message[:50]

    @classmethod
    def create(cls, message, thread, author):
        pub_date = timezone.now()
        post = cls(message=message, pub_date=pub_date, in_thread=thread, author=author)
        post.save()
        if post.in_thread.first_post is None:
            post.in_thread.first_post = post
        post.in_thread.save()
        return post


class Thread(models.Model):
    title = models.CharField(max_length=200)
    first_post = models.ForeignKey(Post, related_name='thread_message', blank=True, null=True, default=None)
    open = models.BooleanField
    close_date = models.DateTimeField('closed on', blank=True, null=True, default=None)
    closer = models.ForeignKey(User, blank=True, null=True, default=None)
    tag1 = models.CharField(max_length=50, blank=True, null=True, default=None)
    tag2 = models.CharField(max_length=50, blank=True, null=True, default=None)
    tag3 = models.CharField(max_length=50, blank=True, null=True, default=None)
    board = models.ForeignKey(Board)

    def __str__(self):
        return self.title[:50]

    def last_post(self):
        return self.post_set.last()


class Subscription(models.Model):
    thread = models.ForeignKey(Thread)
    user = models.ForeignKey(User)
    async = models.BooleanField(default=True)
    sync_interval = models.DurationField('sync interval', blank=True, null=True, default=None)
    last_sync = models.DateTimeField('last syncronization', blank=True, null=True, default=None)
    active = models.BooleanField(default=True)


class Vote(models.Model):
    post = models.ForeignKey(Post)
    user = models.ForeignKey(User)
    value = models.BooleanField()


class Ban(models.Model):
    user = models.ForeignKey(User)
    start = models.DateTimeField('start on', default=timezone.now)
    duration = models.DurationField('duration')
    banner = models.ForeignKey(User, related_name='banner')
    reason = models.CharField(max_length=50)
