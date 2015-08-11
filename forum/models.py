from operator import attrgetter
import os
from django.core.validators import RegexValidator
from django.db import models
from django.contrib.auth.models import AbstractUser, Group
from django.utils import timezone
from xdg.Exceptions import ValidationError
from djangle.settings import ELEM_PER_PAGE

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
            latest_threads.append(post.thread)
        return latest_threads

    def get_new(self, num=5):
        return self.get_latest(num)

    def __str__(self):
        return self.name


class User(AbstractUser):

    def validate_image(fieldfile_obj):
        filesize = fieldfile_obj.file.size
        kilobyte_limit = 200
        if filesize > kilobyte_limit*1024:
            raise ValidationError("Max file size is %sKB" % str(kilobyte_limit))

    models.EmailField.unique = True
    rep = models.IntegerField(default=0)
    avatar = models.ImageField(upload_to='prof_pic', default='prof_pic/Djangle_user_default.png', validators=[validate_image])
    posts = models.PositiveIntegerField(default=0)
    threads = models.PositiveIntegerField(default=0)

    def num_threads(self):
        count = 0
        for post in self.post_set.all():
            if post == post.thread.first_post:
                count += 1
        return count

    def reset_avatar(self):
        if not self.avatar.name.endswith('Djangle_user_default.png'):
            img = self.avatar.path
            try:
                os.remove(img)
            except:
                pass
            self.avatar = 'prof_pic/Djangle_user_default.png'
            self.save()

    def subscribed_threads(self):
        threads = []
        for subscription in self.subscription_set.all():
            threads.append(subscription.thread)
        return threads

    def modded_boards(self):
        boards = []
        for mod in self.moderation_set.all():
            boards.append(mod.board)
        return boards

    def set_supermod(self, set=True):
        group = Group.objects.get_or_create(name='supermod')[0]
        if set:
            if not self.groups.filter(name='supermod').exists():
                group.user_set.add(self)
                self.save()
        else:
            if self.groups.filter(name='supermod').exists():
                self.groups.filter(name='supermod').delete()
                self.save()

    def is_supermod(self):
        if self.groups.filter(name='supermod').exists():
            return True
        else:
            return False


class Post(models.Model):
    message = models.CharField(max_length=5000)
    pub_date = models.DateTimeField('publication date')
    thread = models.ForeignKey('Thread')
    author = models.ForeignKey(User)
    pos_votes = models.PositiveIntegerField(default=0)
    neg_votes = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.message[:50]

    class Meta:
        get_latest_by = 'pub_date'

    @classmethod
    def create(cls, message, thread, author):
        pub_date = timezone.now()
        post = cls(message=message, pub_date=pub_date, thread=thread, author=author)
        post.save()
        if post.thread.first_post is None:
            post.thread.first_post = post
        post.thread.save()
        author.posts += 1
        author.save()
        return post

    def remove(self, send_mail=False):
        self.author.posts -= 1
        self.author.save()
        if send_mail:
            pass
        self.delete()
        return

    def get_page(self):
        older = self.thread.post_set.filter(pub_date__lte=self.pub_date).count()
        pages = older // ELEM_PER_PAGE
        if older % ELEM_PER_PAGE == 0:
            return pages
        return pages + 1


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

    @classmethod
    def create(cls, title, message, board, author, tag1=None, tag2=None, tag3=None):
        thread = cls(title=title, board=board, tag1=tag1, tag2=tag2, tag3=tag3)
        thread.save()
        post = Post.create(message=message, thread=thread, author=author)
        post.save()
        return thread

    def remove(self):
        for post in self.post_set.all():
            post.remove()
        self.delete()
        return

    def sub_users(self):
        users=[]
        for sub in self.subscription_set.all():
            users.append(sub.user)
        return users


class Subscription(models.Model):
    thread = models.ForeignKey(Thread)
    user = models.ForeignKey(User)
    async = models.BooleanField(default=True)
    sync_interval = models.DurationField('sync interval', blank=True, null=True, default=None)
    last_sync = models.DateTimeField('last synchronization', blank=True, null=True, default=None)
    active = models.BooleanField(default=True)

    def is_expired(self, time=timezone.now()):
        return ((self.last_sync + self.sync_interval < time) and
                (self.thread.post_set.latest().pub_date > self.last_sync))

    class Meta:
        unique_together = (('thread', 'user'),)

    @classmethod
    def create(cls, thread, user, async, sync_interval=None, last_sync='default'):
        if Subscription.objects.filter(thread=thread, user=user).exists():
            created = False
            subscr = Subscription.objects.get(thread=thread, user=user)
        else:
            now = timezone.now()
            if last_sync == 'default':
                last_sync = now
            subscr = cls(thread=thread, user=user, async=async, sync_interval=sync_interval, last_sync=last_sync)
            created = True
        return subscr,created


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


class Moderation(models.Model):
    user = models.ForeignKey(User)
    board = models.ForeignKey(Board)

    class Meta:
        unique_together = (('user', 'board'),)
