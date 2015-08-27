"""
module for site's forms
"""
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from forum.models import User


class LoginForm(AuthenticationForm):
    """
    form for user authentication
    """
    username = forms.CharField(max_length=254, widget=forms.TextInput(attrs={'autofocus': 'autofocus'}))

    error_messages = {
        'invalid_login': "Please enter a correct %(username)s and password. "
                         "Note that password field is case-sensitive.",
        'inactive': "This account is inactive.",
    }


class UserCreationForm(DjangoUserCreationForm):
    """
    form for user creation
    """
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super(UserCreationForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user
