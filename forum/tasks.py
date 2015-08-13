from __future__ import absolute_import
from django.utils import timezone
from .models import Subscription, User, Ban, Thread
from djangle.celery import app
from django.core.mail import send_mail
from djangle.settings import EMAIL_SUBJECT_PREFIX
import os


DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"
sep = os.linesep*2


@app.task
def async_mail():
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
                message += 'New messages on thread '+sub.thread.title+':'+sep
                new_posts = sub.thread.post_set.filter(pub_date__range=(sub.last_sync, time)).order_by('pub_date')
                post = ('on '+post.pub_date.strftime("%s %s" % (DATE_FORMAT, TIME_FORMAT))+' ' +
                        post.author.username+' wrote :'+os.linesep +
                        post.message for post in new_posts)
                message += sep.join(post)
                message += sep+80*'_'+sep
                sub.last_sync = time
                sub.save()
        if message is not '':
            message = 'Hi '+subs[0].user.username+', you have some news from djangle:'+sep+80*'_'+sep+message
            mail.delay(EMAIL_SUBJECT_PREFIX+'update from your subscriptions',
                      message,
                      None,
                      [subs[0].user.email],
                      fail_silently=False
                      )


@app.task
def sync_mail(post):
    subs = (sub for sub in post.thread.subscription_set.filter(async=False, active=True))
    message = 'New message on thread '+post.thread.title+':'+sep +\
              'on '+post.pub_date.strftime("%s %s" % (DATE_FORMAT, TIME_FORMAT))+' ' +\
              post.author.username+' wrote :'+os.linesep+post.message
    for sub in subs:
        user_message = 'Hi '+sub.user.username+', you have some news from djangle:'+sep+80*'_'+sep+message
        mail.delay(EMAIL_SUBJECT_PREFIX+'update from thread '+sub.thread.title,
                  user_message,
                  None,
                  [sub.user.email],
                  fail_silently=False
                  )
        sub.last_sync = post.pub_date
        sub.save()


@app.task
def del_mail(post, thread=None):
    if thread != None:
        subject = EMAIL_SUBJECT_PREFIX+'your thread was deleted'
        message = 'Thread: '+thread.title+os.linesep+'in board: '+thread.board.name+os.linesep +\
                  'was deleted'
    else:
        subject = EMAIL_SUBJECT_PREFIX+'your post was deleted'
        message = 'The post:'+os.linesep+post.message+os.linesep+'in thread: '+post.thread.title+os.linesep +\
                  'was deleted'

    mail.delay(subject=subject, message=message, sender=None, reciever=[post.author.email], fail_silently= False)


@app.task
def check_ban():
    for ban in Ban.objects.all():
        if not ban.is_active():
            ban.remove()

@app.task
def mail(subject, message, sender, reciever, fail_silently= False):
    send_mail(subject, message, sender, reciever, fail_silently= False)