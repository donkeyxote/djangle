from django import forms
from .models import Post, Board, Thread, User
from datetime import timedelta


class PostForm(forms.ModelForm):

    class Meta:
        model = Post
        widgets = {
            'message': forms.Textarea
        }
        fields = ['message']


class BoardForm(forms.ModelForm):

    class Meta:
        model = Board
        fields = ['name', 'code']


class ThreadForm(forms.ModelForm):

    board = forms.ModelChoiceField(queryset=Board.objects.order_by('name'))
    post = PostForm()

    class Meta:

        model = Thread
        fields = ['title', 'board', 'tag1', 'tag2', 'tag3']


class UserEditForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'avatar']


class SubscribeForm(forms.Form):
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
    boards = []
    for board in Board.objects.all():
        boards.append(forms.BooleanField(label=board.name, required=False))

    def __init__(self, user, *args, **kwargs):
        super(AddModeratorForm, self).__init__(*args, **kwargs)
        for board in Board.objects.all():
            value = user.moderation_set.filter(board=board).exists()
            self.fields['%s' % board.name] = forms.BooleanField(label=board.name, required=False, initial=value)


class BoardModForm(forms.Form):
    users = []
    for user in User.objects.all():
        users.append(forms.BooleanField(label=user.username, required=False))

    def __init__(self, board, *args, **kwargs):
        super(BoardModForm, self).__init__(*args, **kwargs)
        for user in User.objects.all():
            value = board.moderation_set.filter(user=user).exists()
            self.fields[user.username] = forms.BooleanField(label=user.username, required=False, initial=value)