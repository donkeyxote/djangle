from django import forms
from .models import Post, Board, Thread, User, Ban
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


class AddBanForm(forms.ModelForm):
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
