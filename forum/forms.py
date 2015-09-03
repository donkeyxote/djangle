"""
module for forum's forms
"""
import os
from django import forms
from django.core.exceptions import ValidationError
from .models import Post, Board, Thread, User, Ban, Comment
from datetime import timedelta


class PostForm(forms.ModelForm):
    """
    form for post creation
    """

    class Meta:
        model = Post
        widgets = {
            'message': forms.Textarea
        }
        fields = ['message']

class CommentForm(forms.ModelForm):
    """
    form for comment creation
    """

    class Meta:
        model = Comment
        widgets = {
            'message': forms.Textarea
        }
        fields = ['message']


class BoardForm(forms.ModelForm):
    """
    form for board creation
    """

    class Meta:
        model = Board
        fields = ['name', 'code']


class ThreadForm(forms.ModelForm):
    """
    form for thread creation
    """

    board = forms.ModelChoiceField(queryset=Board.objects.order_by('name'))
    post = PostForm()

    class Meta:
        model = Thread
        fields = ['title', 'board', 'tag1', 'tag2', 'tag3']


class UserEditForm(forms.ModelForm):
    """
    form for user's field modification
    """

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'avatar']

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar', None)
        if avatar:  # this is not working, if image field is blank
            try:
                if avatar.size:
                    if avatar:
                        if avatar.size > 200 * 1024:
                            self._errors['avatar'] = 'file too big: max size is 200 kb'
                            raise ValidationError(
                                self.fields['avatar'].error_messages['file too big: max size is 200 kb'])

                        return avatar
                    else:
                        self._errors['avatar'] = "Couldn't read uploaded image"
                        raise ValidationError("Couldn't read uploaded image")
                else:
                    self._errors['avatar'] = "image format not supported"
                    raise ValidationError("image format not supported")
            except AttributeError:
                if avatar != os.path.join('prof_pic', 'Djangle_user_default.png'):
                    self._errors['avatar'] = "image format not supported"
                    raise ValidationError("image format not supported")


class SubscribeForm(forms.Form):
    """
    form for subscription creation
    """
    async = forms.BooleanField(label='asynchronous', required=False)
    int_choices = (
        (timedelta(minutes=15).total_seconds(), '15 min'),
        (timedelta(minutes=30).total_seconds(), '30 min'),
        (timedelta(hours=1).total_seconds(), '1 hour'),
        (timedelta(hours=3).total_seconds(), '3 hours'),
        (timedelta(hours=6).total_seconds(), '6 hours'),
        (timedelta(hours=12).total_seconds(), '12 hours'),
        (timedelta(days=1).total_seconds(), 'once a day'),
        (timedelta(weeks=1).total_seconds(), 'once a week'),
        (timedelta(weeks=4).total_seconds(), 'once every 4 weeks')
    )
    interval = forms.ChoiceField(choices=int_choices, required=False)

    class Meta:
        fields = ['async', 'interval']


class AddModeratorForm(forms.Form):
    """
    form for managing user's moderations
    """
    boards = []
    for board in Board.objects.all():
        boards.append(forms.BooleanField(label=board.name, required=False))

    def __init__(self, user, *args, **kwargs):
        super(AddModeratorForm, self).__init__(*args, **kwargs)
        for board in Board.objects.all():
            value = user.moderation_set.filter(board=board).exists()
            self.fields['%s' % board.name] = forms.BooleanField(label=board.name, required=False, initial=value)


class AddBanForm(forms.ModelForm):
    """
    form for adding a new ban
    """
    ban_choices = (
        (timedelta(days=1).total_seconds(), 'one day'),
        (timedelta(days=3).total_seconds(), 'three days'),
        (timedelta(weeks=1).total_seconds(), 'one week'),
        (timedelta(weeks=2).total_seconds(), 'two weeks'),
        (timedelta(weeks=3).total_seconds(), 'three weeks'),
        (timedelta(weeks=4).total_seconds(), 'one month'),
        (timedelta(weeks=12).total_seconds(), 'three months'),
        (timedelta(weeks=24).total_seconds(), 'six months'),
        (timedelta(weeks=52).total_seconds(), 'one year'),
        (None, 'permaban'),

    )
    duration = forms.ChoiceField(choices=ban_choices, required=False)

    class Meta:
        model = Ban
        fields = ['duration', 'reason']


class BoardModForm(forms.Form):
    """
    form for adding a new board
    """
    users = []
    for user in User.objects.all():
        users.append(forms.BooleanField(label=user.username, required=False))

    def __init__(self, board, *args, **kwargs):
        super(BoardModForm, self).__init__(*args, **kwargs)
        for user in User.objects.all().order_by('username'):
            value = board.moderation_set.filter(user=user).exists()
            self.fields[user.username] = forms.BooleanField(label=user.username, required=False, initial=value)


class SearchForm(forms.Form):
    """
    form for advanced search
    """
    search_item = forms.ChoiceField(choices=(
        ('thread', 'thread'),
        ('user', 'user')
    ), required=False)
    title = forms.CharField(max_length=50, required=False)
    tags = forms.CharField(max_length=50, required=False)
    username = forms.CharField(max_length=50, required=False)

    def clean(self):
        cleaned_data = super(SearchForm, self).clean()
        if 'query' in self.data:
            title = self.data.get("query")
            cleaned_data['title'] = title
        else:
            item = cleaned_data.get('search_item')
            if item == 'thread':
                title = cleaned_data.get('title')
                tags = cleaned_data.get('tags')
                username = cleaned_data.get('username')
                if not title and not tags and not username:
                    raise forms.ValidationError('empty form')
            elif item == 'user':
                username = cleaned_data.get('username')
                if not username:
                    raise forms.ValidationError('username is a required field')
            else:
                raise forms.ValidationError('item field error')
        return cleaned_data
