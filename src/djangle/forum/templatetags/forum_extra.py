"""
module for custom templates' tags
"""


import os
from djangle.settings import MEDIA_ROOT, MEDIA_URL
from django import template

register = template.Library()


@register.filter(name='file_exists')
def file_exists(filepath):
    """
    check if profile picture exists and return profile picture path
    :param filepath: path to check
    :return: return filepath if exists, else return default profile picture's path
    """
    try:
        path = os.path.join(MEDIA_ROOT, filepath[len(MEDIA_URL):])
        open(path)
        return filepath
    except Exception:
        return os.path.join(MEDIA_URL, 'prof_pic', 'Djangle_user_default.png')
