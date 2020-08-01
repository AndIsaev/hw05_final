from .models import *
from django import forms



class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["group", "text", "image"]
        help_texts = {
            "text": ("Напишите текст"),
            "group": ("Выберите группу")
        }



class CommentForm(forms.ModelForm):
    text = forms.CharField(widget=forms.Textarea)
    class Meta:
        model = Comment
        fields = ("text",)
        labels = {
            "text": "Текст вашего комментария",
        }


class FollowForm(forms.ModelForm):
    class Meta:
        model = Follow
        labels = {
            'user': ('Пользователь подписывается на:'),
            'author': ('Автор даной записи'),
        }
        help_texts = {
           'user': ('Вы подписываетесь на:'),
          'author': ('Автор данной записи'),
        }
        fields = ['user']
