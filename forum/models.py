import datetime
from operator import attrgetter
import os
from django.contrib.contenttypes.models import ContentType
from django.core.validators import RegexValidator
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone, six
from django.core.exceptions import ValidationError
from djangle.settings import ELEM_PER_PAGE

# Create your models here.

alphanumeric = RegexValidator(r'^\w*$', 'Only alphanumeric characters are allowed.')


class Board(models.Model):
    """
    list of thread

    a board is a container of threads. it is usually meant to group threads by category.
    """
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=10, unique=True, validators=[alphanumeric])

    @classmethod
    def create(cls, name, code):
        """
        method for board creation

        :param name: name for the new board
        :param code: code for the new board
        :return: the new board
        """
        if not isinstance(name, six.string_types):
            raise TypeError('name is not a string')
        if not isinstance(code, six.string_types):
            raise TypeError('code is not a string')
        if len(name) > 50:
            raise ValueError('name too long (max length: 50)')
        if len(code) > 10:
            raise ValueError('code too long (max length: 10)')
        try:
            alphanumeric.__call__(code)
        except ValidationError as error:
            raise error
        else:
            board = cls(name=name, code=code)
            board.save()
            return board

    def get_latest(self, num=None):
        """
        get board's thread ordered by last post publish date

        :param num: number of threads to return (optional: default all)
        :return: list of threads
        """
        latest_posts = []
        if (num is not None) and (not isinstance(num, six.integer_types)):
            num = None
        for thread in self.thread_set.all():
            if thread.last_post() is not None:
                latest_posts.append(thread.last_post())
        latest_posts = sorted(latest_posts, key=attrgetter('pub_date'), reverse=True)
        latest_threads = []
        for post in latest_posts[:num]:
            latest_threads.append(post.thread)
        return latest_threads

    def get_new(self, num=5):
        """
        get board's thread ordered by last post publish date (alias of get_latest for templates)

        :param num: number of threads to return (optional: default 5)
        :return: list of threads
        """
        if not isinstance(num, six.integer_types):
            num = 5
        return self.get_latest(num)

    def __str__(self):
        """
        redefine id field to be name

        :return: board name
        """
        return self.name


class User(AbstractUser):
    """
    abstraction of forum's user

    class user is used to collect information of forum's users like avatar, reputation, number of posts, number of
    threads, email, username, password (hash is used for storage). this is also used for django authentication system.
    """
    def validate_image(self):
        """
        validator for avatar field, check that file loaded is not bigger than kilobyte_limit

        :return: raise validation error if file is too big
        """
        file_size = self.file.size
        kilobyte_limit = 200
        if file_size > kilobyte_limit * 1024:
            raise ValidationError("Max file size is %sKB" % str(kilobyte_limit), self.file)

    models.EmailField.unique = True
    rep = models.IntegerField(default=0, verbose_name='reputation')
    avatar = models.ImageField(upload_to='prof_pic',
                               default=os.path.join('prof_pic', 'Djangle_user_default.png'),
                               validators=[validate_image])
    posts = models.PositiveIntegerField(default=0)
    threads = models.PositiveIntegerField(default=0)

    def num_threads(self):
        """
        return the number of threads

        :return: number of threads
        """
        return Thread.objects.filter(first_post__author=self).count()

    def reset_avatar(self):
        """
        set profile picture to default

        :return: nothing
        """
        if not self.avatar.name.endswith('Djangle_user_default.png'):
            img = self.avatar.path
            try:
                os.remove(img)
            except:
                pass
            self.avatar = os.path.join('prof_pic', 'Djangle_user_default.png')
            self.save()

    def subscribed_threads(self):
        """
        return a list of thread subscribed by user

        :return: subscribed threads list
        """
        threads = []
        for subscription in self.subscription_set.all():
            threads.append(subscription.thread)
        return threads

    def modded_boards(self):
        """
        return a list of board modded by the user

        :return: list of modded board
        """
        boards = []
        for mod in self.moderation_set.all():
            boards.append(mod.board)
        return boards

    def set_supermod(self, do_set=True):
        """
        toggle supermod status

        insert or remove user from supermod group

        :param do_set: True to insert, False to remove (default True)
        :return: nothing
        """
        group, created = Group.objects.get_or_create(name='supermod')
        if created:
            content_type = ContentType.objects.get_or_create(model='board')[0]
            permission1 = Permission.objects.get(codename='add_board', content_type=content_type)
            content_type = ContentType.objects.get_or_create(model='moderation')[0]
            permission2 = Permission.objects.get(codename='add_moderation', content_type=content_type)
            permission3 = Permission.objects.get(codename='delete_moderation', content_type=content_type)
            group.permissions.add(permission1, permission2, permission3)
        if do_set:
            if not self.groups.filter(name='supermod').exists():
                group.user_set.add(self)
                self.save()
        else:
            if self.groups.filter(name='supermod').exists():
                group.user_set.remove(self)
                self.save()

    def is_supermod(self):
        """
        return whether user is supermod

        :return: True if user is supermod, else False
        """
        if self.groups.filter(name='supermod').exists() or self.is_superuser:
            return True
        else:
            return False

    def is_mod(self):
        """
        return whether user is moderator

        :return: True if user is moderator, else False
        """
        if self.moderation_set.all().exists():
            return True
        else:
            return False

    def is_banned(self):
        """
        return whether user is banned

        :return: True if user is banned, else False
        """
        for ban in Ban.objects.filter(user=self):
            if ban.is_active():
                return True
        return False


class GenericPost(models.Model):
    """
    Generic class for messages

    a generic message instance. it has a message content, a publish date, number of votes (positive and negative),
    an author.
    """
    message = models.CharField(max_length=5000)
    pub_date = models.DateTimeField('publication date')
    author = models.ForeignKey(User)
    pos_votes = models.PositiveIntegerField(default=0)
    neg_votes = models.PositiveIntegerField(default=0)

    def __str__(self):
        """
        redefine id field to return first 50 characters of message

        :return: string containing first 50 characters of message
        """
        return self.message[:50]


class Post(GenericPost):
    """
    a message in a thread

    post is the building block of a thread. each registered and active user can write a post in a thread. inherits all
    fields from GenericPost, moreover it has a related thread
    """
    thread = models.ForeignKey('Thread')

    class Meta:
        get_latest_by = 'pub_date'

    @classmethod
    def create(cls, message, thread, author):
        """
        method for post creation

        :param message: the actual post's message
        :param thread: the thread associated with the post
        :param author: the post's author
        :return: the created post
        """
        if not (isinstance(message, six.string_types)):
            raise TypeError("message is not a string instance")
        if not (isinstance(thread, Thread)):
            raise TypeError("thread is not a Thread instance")
        if not (isinstance(author, User)):
            raise TypeError("author is not an User instance")
        if not author.is_active:
            raise ValueError("author is not an active user")
        if not len(message) <= 5000:
            raise ValueError("message too long")

        pub_date = timezone.now()
        try:
            post = cls(message=message, pub_date=pub_date, thread=thread, author=author)
            post.save()
        except Exception as e:
            raise e
        if post.thread.first_post is None:
            post.thread.first_post = post
            post.thread.save()
        author.posts += 1
        author.save()
        return post

    def remove(self):
        """
        method for removing a post

        :return:nothing
        """
        self.author.posts -= 1
        self.author.save()
        self.delete()
        return

    def get_page(self):
        """
        method for getting post's page number in thread's posts list

        :return: page number
        """
        older = self.thread.post_set.filter(pub_date__lte=self.pub_date).count()
        pages = older // ELEM_PER_PAGE
        if older % ELEM_PER_PAGE == 0:
            return pages
        return pages + 1


class Comment(GenericPost):
    """
    a comment to a post

    reply to a post. inherits all fields from GenericPost, moreover it has a related post
    """
    post = models.ForeignKey(Post, related_name='reply')

    @classmethod
    def create(cls, message, post, author):
        """
        method for comment creation

        :param message: the actual comment's message
        :param post: the post associated with the comment
        :param author: the comment's author
        :return: the created comment
        """
        if not (isinstance(message, six.string_types)):
            raise TypeError("message is not a string instance")
        if not (isinstance(post, Post)):
            raise TypeError("post is not a Post instance")
        if not (isinstance(author, User)):
            raise TypeError("author is not an User instance")
        if not author.is_active:
            raise ValueError("author is not an active user")
        if not len(message) <= 5000:
            raise ValueError("message too long")

        pub_date = timezone.now()
        try:
            comment = cls(message=message, pub_date=pub_date, post=post, author=author)
            comment.save()
        except Exception as e:
            raise e
        return comment


class Thread(models.Model):
    """
    a thread in a board

    thread is composed by posts and represents a discussion. a thread as a title, a first_post (the author's opening
    message), a close_date if post has been marked as closed, a closer field (the user who closed the thread), three
    tags (not used yet, meant to simplify search), an associated board and a sticky flag, which determines whether the
    thread must be on top of board's threads' list or not.
    """
    title = models.CharField(max_length=200)
    first_post = models.ForeignKey(Post, related_name='thread_message', blank=True, null=True, default=None)
    close_date = models.DateTimeField('closed on', blank=True, null=True, default=None)
    closer = models.ForeignKey(User, blank=True, null=True, default=None)
    tag1 = models.CharField(max_length=50, blank=True, null=True, default=None)
    tag2 = models.CharField(max_length=50, blank=True, null=True, default=None)
    tag3 = models.CharField(max_length=50, blank=True, null=True, default=None)
    board = models.ForeignKey(Board)
    sticky = models.BooleanField(default=False)

    def __str__(self):
        """
        redefine id field to return first 50 characters of title

        :return: first 50 characters of title
        """
        return self.title[:50]

    def last_post(self):
        """
        return lats post added to thread

        :return: last post added
        """
        return self.post_set.last()

    @classmethod
    def create(cls, title, message, board, author, tag1=None, tag2=None, tag3=None):
        """
        method for new threads creation

        :param title: thread title
        :param message: first post's message
        :param board: board associated with thread
        :param author: author of thread
        :param tag1: string tag for indexing threads
        :param tag2: string tag for indexing threads
        :param tag3: string tag for indexing threads
        :return: the new thread
        """
        if not (isinstance(title, six.string_types)):
            raise TypeError("title is not a string instance")
        if not len(title) <= 200:
            raise ValueError("title too long")
        if not (isinstance(message, six.string_types)):
            raise TypeError("message is not a string instance")
        if not len(message) <= 5000:
            raise ValueError("message too long")
        if not (isinstance(author, User)):
            raise TypeError("author is not an User instance")
        if not (isinstance(board, Board)):
            raise TypeError("board is not a Board instance")
        if not (isinstance(author, User)):
            raise TypeError("author is not an User instance")
        if not author.is_active:
            raise ValueError("author is not an active user")
        for tag in (tag1, tag2, tag3):
            if not (isinstance(tag, six.string_types)) and tag is not None:
                raise TypeError("tag is not a string instance")
            if tag is not None and not len(tag) <= 50:
                raise ValueError("tag too long")

        thread = cls(title=title, board=board, tag1=tag1, tag2=tag2, tag3=tag3)
        thread.save()
        try:
            post = Post.create(message=message, thread=thread, author=author)
            post.save()
        except Exception as e:
            raise e

        return thread

    def remove(self):
        """
        method for thread deletion

        :return: nothing
        """
        for post in self.post_set.all():
            post.remove()
        self.delete()
        return

    def sub_users(self):
        """
        return a list of user who subscribed the thread

        :return: list of subscribers
        """
        users = []
        for sub in self.subscription_set.all():
            users.append(sub.user)
        return users

    def is_closed(self):
        """
        return whether close date is previous to timezone.now()

        :return: True if close_date < now, else False
        """
        now = timezone.now()
        if self.close_date and (self.close_date < now):
            return True
        return False

    def get_tags(self):
        """
        returns threads' tags list

        :return: list of tags
        """
        tags = []
        if self.tag1:
            tags.append(self.tag1)
        if self.tag2:
            tags.append(self.tag2)
        if self.tag3:
            tags.append(self.tag3)
        return tags


class Subscription(models.Model):
    """
    class for managing subscriptions

    a subscription is a relation between an user and a thread: it means that the user cares about receiving mail
    notifications when thread is updated. subscription's fields are: thread to subscribe, subscriber user, async flag to
    determinate if notification should be sent periodically or every time thread is updated, sync_interval time between
    asynchronous notification, last_sync datetime field to determinate which posts are to be notified, active flag (not
    used yet, it will give the user the possibility to disable subscription for some time without deleting it).
    """
    thread = models.ForeignKey(Thread)
    user = models.ForeignKey(User)
    async = models.BooleanField(default=True)
    sync_interval = models.DurationField('sync interval', blank=True, null=True, default=None)
    last_sync = models.DateTimeField('last synchronization', blank=True, null=True, default=None)
    active = models.BooleanField(default=True)

    def is_expired(self, time=timezone.now()):
        """
        method to know if sync_interval has passed since last mail notification and there are new posts

        :param time: date to check (optional, default now)
        :return: True if subscription is expired, else False
        """
        return ((self.last_sync + self.sync_interval < time) and
                (self.thread.post_set.latest().pub_date > self.last_sync))

    class Meta:
        unique_together = (('thread', 'user'),)

    @classmethod
    def create(cls, thread, user, async, sync_interval=None, last_sync='default', active=True):
        """
        method for new subscriptions creation

        :param thread: the thread to subscribe
        :param user: the subscriber user
        :param async: True for asynchronous notification, else False
        :param sync_interval: period that must pass between two notifications
        :param last_sync: last sync time (default now)
        :param active: whether subscription is active
        :return: the new subscription
        """
        if not (isinstance(thread, Thread)):
            raise TypeError("thread is not a Thread instance")
        if not (isinstance(user, User)):
            raise TypeError("user is not an User instance")
        if not user.is_active:
            raise ValueError("user is not an active user")

        if Subscription.objects.filter(thread=thread, user=user).exists():
            created = False
            subscr = Subscription.objects.get(thread=thread, user=user, active=active)
        else:
            if not (isinstance(async, bool)):
                raise TypeError("async is not a bool instance")
            if not (isinstance(sync_interval, datetime.timedelta)) and sync_interval is not None:
                raise TypeError("sync_interval is not a valid interval instance")
            if last_sync is not None and not (isinstance(last_sync, datetime.datetime)) and not last_sync == 'default':
                raise TypeError("last_sync is not a valid datetime instance")
            if not (isinstance(active, bool)):
                raise TypeError("active is not a bool instance")

            now = timezone.now()
            if last_sync == 'default':
                last_sync = now
            subscr = cls(thread=thread, user=user, async=async, sync_interval=sync_interval,
                         last_sync=last_sync, active=active)
            created = True
            subscr.save()
        return subscr, created


class Vote(models.Model):
    """
    a vote for a message/thread

    vote class is used to store user's preferences about messages and to make sure an user can't vote two times for the
    same message. it has three fields: the voting user, the voted message and the value of the vote (positive or
    negative)
    """
    post = models.ForeignKey(GenericPost)
    user = models.ForeignKey(User)
    value = models.BooleanField()

    class Meta:
        unique_together = (('post', 'user'),)

    @classmethod
    def vote(cls, post, user, value):
        """
        method for new votes creation

        this ensures posts' and users' static attributes to be updated whenever a vote is created or changed

        :param post: voted message
        :param user: voting user
        :param value: vote value (True for positive, False for negative)
        :return: the new vote
        """
        if user == post.author:
            return
        vote = Vote.objects.filter(post=post, user=user).first()
        if vote is None:
            vote = cls(post=post, user=user, value=value)
            vote.save()
            if value:
                post.pos_votes += 1
                post.save()
                post.author.rep += 1
                post.author.save()
            else:
                post.neg_votes += 1
                post.save()
                post.author.rep -= 1
                post.author.save()
        else:
            if value:
                if not vote.value:
                    vote.value = value
                    vote.save()
                    post.pos_votes += 1
                    post.neg_votes -= 1
                    post.save()
                    post.author.rep += 2
                    post.author.save()
                else:
                    post.pos_votes -= 1
                    post.save()
                    post.author.rep -= 1
                    post.author.save()
                    vote.delete()
                    return
            else:
                if vote.value:
                    vote.value = value
                    vote.save()
                    post.pos_votes -= 1
                    post.neg_votes += 1
                    post.save()
                    post.author.rep -= 2
                    post.author.save()
                else:
                    post.neg_votes -= 1
                    post.save()
                    post.author.rep += 1
                    post.author.save()
                    vote.delete()
                    return
        return vote


class Ban(models.Model):
    """
    representation of ban

    ban class is used to store information about user's ban, such as banned user, date of ban, duration, banner user,
    reason of ban.
    """
    user = models.ForeignKey(User)
    start = models.DateTimeField('start on', default=timezone.now)
    duration = models.DurationField('duration', blank=True, null=True, default=None)
    banner = models.ForeignKey(User, related_name='banner')
    reason = models.CharField(max_length=50)

    def is_active(self):
        """
        method to know if ban is valid or expired

        :return: True if ban is active, else False
        """
        if self.duration is None or self.start + self.duration >= timezone.now():
            return True
        else:
            return False

    def remove(self):
        """
        method for removing bans

        :return: nothing
        """
        self.user.is_active = True
        self.user.save()
        self.delete()


class Moderation(models.Model):
    """
    moderation relation between an user and a board

    moderation class is used to express that an user has particular permissions over a board, like closing threads,
    deleting messages or banning users (globally)
    """
    user = models.ForeignKey(User)
    board = models.ForeignKey(Board)

    class Meta:
        unique_together = (('user', 'board'),)
