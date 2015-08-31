from __future__ import absolute_import
from django.utils import timezone
from .models import Subscription, User, Ban
from djangle.celery import app
from django.core.mail import send_mail
from djangle.settings import EMAIL_SUBJECT_PREFIX
import os

DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"
sep = os.linesep * 2


@app.task
def async_mail():
    """
    procedure for asynchronous mail service

    for each active user with active subscriptions, iter through subscribed threads and compose a mail with all new
    posts since last update, then call a deferred procedure to actually send the mail.

    :return: nothing
    """
    # storing current time at beginning of the procedure: this hopefully avoids missing messages being posted during
    # execution time (they will be sent in next iteration)
    time = timezone.now()

    # believe me or not, this iterates over users which have active subscriptions
    users = (User.objects.get(pk=x['user']) for x in Subscription.objects.values('user').distinct())

    # iterator over list of subscriptions grouped by user
    user_subs = (x.subscription_set.filter(async=True, active=True) for x in users if x.is_active)

    for subs in user_subs:
        message = ''
        for sub in subs:
            if sub.is_expired(time):
                message += 'New messages on thread ' + sub.thread.title + ':' + sep
                new_posts = sub.thread.post_set.filter(pub_date__range=(sub.last_sync, time)).order_by('pub_date')
                post = ('on ' + post.pub_date.strftime("%s %s" % (DATE_FORMAT, TIME_FORMAT)) + ' UTC ' +
                        post.author.username + ' wrote :' + os.linesep +
                        post.message for post in new_posts)
                message += sep.join(post)
                message += sep + 20 * '_' + sep
                sub.last_sync = time
                sub.save()
        if message is not '':
            message = 'Hi ' + subs[0].user.username + ', you have some news from djangle:' + sep + 20 * '_' + sep + \
                      message
            mail.delay(EMAIL_SUBJECT_PREFIX + 'update from your subscriptions',
                       message,
                       None,
                       [subs[0].user.email],
                       fail_silently=False
                       )


@app.task
def sync_mail(post):
    """
    procedure for synchronous mail service

    create a message for the update, then iter through users which have subscribed (with synchronous notification)
    the thread containing the post and send a mail to each one through a deferred procedure

    :param post:
    :return: nothing
    """
    subs = (sub for sub in post.thread.subscription_set.filter(async=False, active=True))
    message = 'New message on thread ' + post.thread.title + ':' + sep + \
              'on ' + post.pub_date.strftime("%s %s" % (DATE_FORMAT, TIME_FORMAT)) + ' UTC ' + \
              post.author.username + ' wrote :' + os.linesep + post.message
    for sub in subs:
        user_message = 'Hi ' + sub.user.username + ', you have some news from djangle:' + sep + 20 * '_' + sep + message
        mail.delay(EMAIL_SUBJECT_PREFIX + 'update from thread ' + sub.thread.title,
                   user_message,
                   None,
                   [sub.user.email],
                   fail_silently=False
                   )
        sub.last_sync = post.pub_date
        sub.save()


@app.task
def del_mail(post, thread=None):
    """
    procedure for post deletion notification

    create a message for the deletion and send a notification mail through a deferred procedure

    :param post: the deleted post (first_post if deleting thread)
    :param thread: the deleted thread (only if deleting thread)
    :return: nothing
    """
    if thread is not None:
        subject = EMAIL_SUBJECT_PREFIX + 'your thread was deleted'
        message = 'Thread: ' + thread.title + os.linesep + 'in board: ' + thread.board.name + os.linesep + \
                  'was deleted'
    else:
        subject = EMAIL_SUBJECT_PREFIX + 'your post was deleted'
        message = 'The post:' + os.linesep + post.message + os.linesep + 'in thread: ' + post.thread.title + os.linesep + \
                  'was deleted'

    mail.delay(subject=subject, message=message, sender=None, receiver=[post.author.email], fail_silently=False)


@app.task
def ban_remove_mail(user):
    """
    procedure for ban deletion mail

    create a message for the ban deletion and send a notification mail through a deferred procedure

    :param user: the user to redeem
    :return: nothing
    """
    subject = 'account enabled'
    message = 'your ban is expired: you can now log back into djangle'
    receiver = [user.email]
    mail.delay(subject=subject, message=message, sender=None, receiver=receiver)


@app.task
def ban_create_mail(ban):
    """
    procedure for ban creation mail

    create a message for ban creation and send a notification mail through a deferred procedure

    :param ban: the created ban object
    :return: nothing
    """
    subject = 'account disabled'
    message = 'you have been banned by ' + ban.banner.username + ' for this reason: ' + ban.reason + os.linesep + \
              'we hope you will take your time to think about your behaviour'
    mail.delay(subject=subject, message=message, sender=None, receiver=[ban.user.email])


@app.task
def check_ban():
    """
    check which ban has expired

    asynchronously check in ban list which ban has expired, remove them and send notification mail to users

    :return: nothing
    """
    for ban in Ban.objects.all():
        if not ban.is_active():
            ban.remove()
            ban_remove_mail(ban.user)


@app.task
def mail(subject, message, sender, receiver, fail_silently=False):
    """
    task for sending mail

    this function does nothing different from django.core.mail.send_mail, but is useful for sending deferred emails
    avoiding responsiveness drop

    :param subject: email object
    :param message: email message
    :param sender: email from
    :param receiver: email to
    :param fail_silently: flag for errors
    :return: nothing
    """
    send_mail(subject, message, sender, receiver, fail_silently=fail_silently)
