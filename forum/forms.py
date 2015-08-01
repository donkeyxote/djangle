from django import forms
from .models import Post, Board, Thread


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
