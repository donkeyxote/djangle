from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.


class Board(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=10)

    def __str__(self):
        return self.code


class User(AbstractUser):
    models.EmailField.unique = True
    rep = models.IntegerField(default=0)
    avatar = models.ImageField(default='static/djangle/images/Djangle_logo.png')
    posts = models.PositiveIntegerField(default=0)
    threads = models.PositiveIntegerField(default=0)


class Post(models.Model):
    message = models.CharField(max_length=5000)
    pub_date = models.DateTimeField('publication date')
    in_thread = models.ForeignKey('Thread')
    author = models.ForeignKey(User)
    pos_votes = models.PositiveIntegerField()
    neg_votes = models.PositiveIntegerField()

    def __str__(self):
        return self.message[:50]


class Thread(models.Model):
    title = models.CharField(max_length=200)
    first_post = models.ForeignKey(Post, related_name='thread_message')
    open = models.BooleanField
    close_date = models.DateTimeField('closed on')
    closer = models.ForeignKey(User)
    tag1 = models.CharField(max_length=50)
    tag2 = models.CharField(max_length=50)
    tag3 = models.CharField(max_length=50)
    last_post = models.ForeignKey(Post)
    board = models.ForeignKey(Board)

    def __str__(self):
        return self.title[:50]


class Subscription(models.Model):
    thread = models.ForeignKey(Thread)
    user = models.ForeignKey(User)
    async = models.BooleanField()
    sync_interval = models.DurationField('sync interval')
    last_sync = models.DateTimeField('last syncronization')
    active = models.BooleanField()


class Vote(models.Model):
    post = models.ForeignKey(Post)
    user = models.ForeignKey(User)
    value = models.BooleanField()


class Ban(models.Model):
    user = models.ForeignKey(User)
    start = models.DateTimeField('start on')
    duration = models.DurationField('duration')
    banner = models.ForeignKey(User, related_name='banner')
    reason = models.CharField(max_length=50)
