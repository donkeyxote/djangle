from django import forms
from .models import Post, Board


class PostForm(forms.ModelForm):

    message = forms.CharField(widget=forms.Textarea)

    class Meta:
        model = Post
        fields = ['message']


class BoardForm(forms.ModelForm):

    class Meta:
        model = Board
        fields = ['name', 'code']
