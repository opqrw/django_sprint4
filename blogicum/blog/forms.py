from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Comment, Post


User = get_user_model()


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')


class PostForm(forms.ModelForm):
    pub_date = forms.DateTimeField(
        input_formats=('%Y-%m-%dT%H:%M',),
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local'},
            format='%Y-%m-%dT%H:%M',
        ),
    )

    class Meta:
        model = Post
        exclude = ('author', 'created_at', 'is_published')
        widgets = {
            'text': forms.Textarea(attrs={'rows': 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                continue
            css_class = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f'{css_class} form-control'.strip()
        if not self.instance.pk:
            self.initial.setdefault(
                'pub_date',
                timezone.localtime().strftime('%Y-%m-%dT%H:%M')
            )


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'].widget.attrs['class'] = 'form-control'
