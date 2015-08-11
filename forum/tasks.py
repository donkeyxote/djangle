from __future__ import absolute_import
from django.utils import timezone
from .models import Subscription, User
from djangle.celery import app
from django.core.mail import send_mail
from djangle.settings import EMAIL_SUBJECT_PREFIX
import os


DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"
sep = os.linesep*2


@app.task
def mail():
    # storing current time at beginning of the procedure: this hopefully avoids missing messages being posted during
    # execution time (they will be sent in next iteration)
    time = timezone.now()
    # believe me or not, this iterates over users which have active subscriptions
    users = (User.objects.get(pk=x['user']) for x in Subscription.objects.values('user').distinct())
    # iterator over list of subscriptions grouped by user
    user_subs = (x.subscription_set.filter(async=True, active=True) for x in users)

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
            send_mail(EMAIL_SUBJECT_PREFIX+'update from your subscriptions',
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
        send_mail(EMAIL_SUBJECT_PREFIX+'update from thread '+sub.thread.title,
                  user_message,
                  None,
                  [sub.user.email],
                  fail_silently=False
                  )
        sub.last_sync = post.pub_date
        sub.save()


@app.task
def del_mail(sub=None, mex=None, rec=None):
    if type(sub) is str and type(mex) is str and type(rec) is str:
        send_mail(sub,
                  mex,
                  None,
                  [rec],
                  fail_silently=False
                  )
