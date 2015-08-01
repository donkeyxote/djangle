from django import forms
from .models import Post


class PostForm(forms.ModelForm):

    message = forms.CharField(widget=forms.Textarea)

    class Meta:
        model = Post
        fields = ['message']
