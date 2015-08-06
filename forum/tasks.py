from __future__ import absolute_import
from djangle.celery import app
from django.core.mail import send_mail
from djangle.settings import EMAIL_SUBJECT_PREFIX


@app.task
def mail():
    send_mail(EMAIL_SUBJECT_PREFIX+'update from your subscriptions',
              'Here is the message.',
              None,
              ['test@gmail.com'],
              fail_silently=False
              )
