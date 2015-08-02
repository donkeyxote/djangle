from operator import attrgetter
from django.core.validators import RegexValidator
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# Create your models here.

alphanumeric = RegexValidator(r'^\w*$', 'Only alphanumeric characters are allowed.')


class Board(models.Model):
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=10, unique=True, validators=[alphanumeric])

    @classmethod
    def create(cls, name, code):
        board = cls(name=name, code=code)
        board.save()

    def get_latest(self, num=None):
        latest_posts = []
        for thread in self.thread_set.all():
            if thread.last_post() is not None:
                latest_posts.append(thread.last_post())
        latest_posts = sorted(latest_posts, key=attrgetter('pub_date'), reverse=True)
        latest_threads = []
        for post in latest_posts[:num]:
            latest_threads.append(post.in_thread)
        return latest_threads

    def get_new(self, num=5):
        return self.get_latest(num)

    def __str__(self):
        return self.code


class User(AbstractUser):
    models.EmailField.unique = True
    rep = models.IntegerField(default=0)
    avatar = models.ImageField(default='/static/djangle/images/Djangle_logo.png')
    posts = models.PositiveIntegerField(default=0)
    threads = models.PositiveIntegerField(default=0)

    def num_threads(self):
        count = 0
        for post in self.post_set.all():
            if post == post.in_thread.first_post:
                count += 1
        return count


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
        author.posts += 1
        author.save()
        return post

    def get_page(self, num):
        older = self.in_thread.post_set.filter(pub_date__lte=self.pub_date).count()
        pages = older//num
        if older % num == 0:
            return pages
        return pages+1


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

    class Meta:
        unique_together = (('post', 'user'),)

    @classmethod
    def vote(cls, post, user, value):
        if user == post.author:
            return
        vote = Vote.objects.filter(post=post, user=user).first()
        if vote is None:
            vote = cls(post=post, user=user, value=value)
            vote.save()
            if value:
                post.pos_votes += 1
                post.author.rep += 1
                post.save()
                post.author.save()
            else:
                post.neg_votes += 1
                post.author.rep -= 1
                post.save()
                post.author.save()
            return vote
        else:
            if value:
                if not vote.value:
                    vote.value = value
                    post.pos_votes += 1
                    post.neg_votes -= 1
                    post.author.rep += 2
                    vote.save()
                    post.save()
                    post.author.save()
                else:
                    post.pos_votes -= 1
                    post.author.rep -= 1
                    vote.delete()
                    post.save()
                    post.author.save()
                    return
            else:
                if vote.value:
                    vote.value = value
                    post.pos_votes -= 1
                    post.neg_votes += 1
                    post.author.rep -= 2
                    vote.save()
                    post.save()
                    post.author.save()
                else:
                    post.neg_votes -= 1
                    post.author.rep += 1
                    vote.delete()
                    post.save()
                    post.author.save()
                    return vote
        return


class Ban(models.Model):
    user = models.ForeignKey(User)
    start = models.DateTimeField('start on', default=timezone.now)
    duration = models.DurationField('duration')
    banner = models.ForeignKey(User, related_name='banner')
    reason = models.CharField(max_length=50)
