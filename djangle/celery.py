"""
module for instantiation of celery app

this module contains all the information for retrieving celery's configuration
"""
from __future__ import absolute_import
import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangle.settings')
"""
set the default settings module for django
"""

app = Celery()
"""
create a new celery app
"""

app.config_from_object('django.conf:settings')
"""
configure the celery app automatically
"""

app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
"""
add tasks from all tasks.py files in settings.INSTALLED_APPS automatically
"""