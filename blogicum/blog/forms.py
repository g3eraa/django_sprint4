from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Category, Comment, Location, Post

User = get_user_model()


class PostForm(forms.ModelForm):

    class Meta:
        model = Post
        fields = (
            'title', 'text', 'image', 'pub_date', 'category', 'location',
        )
        widgets = {
            'pub_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Скрытые админом категории и места не предлагаем в списке выбора.
        self.fields['category'].queryset = Category.objects.filter(
            is_published=True
        )
        self.fields['location'].queryset = Location.objects.filter(
            is_published=True
        )


class CommentForm(forms.ModelForm):

    class Meta:
        model = Comment
        fields = ('text',)
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3}),
        }


class ProfileForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email')


class RegistrationForm(UserCreationForm):

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
