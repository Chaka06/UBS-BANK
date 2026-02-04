from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from .models import User


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Mot de passe', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirmer', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = (
            'email',
            'first_name',
            'last_name',
            'date_of_birth',
            'phone_number',
            'address',
            'country',
            'id_doc_front',
            'id_doc_back',
            'is_active',
            'is_staff',
        )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password1') != cleaned_data.get('password2'):
            raise forms.ValidationError('Les mots de passe ne correspondent pas.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = (
            'email',
            'password',
            'first_name',
            'last_name',
            'date_of_birth',
            'phone_number',
            'address',
            'country',
            'id_doc_front',
            'id_doc_back',
            'is_active',
            'is_staff',
            'is_superuser',
            'groups',
            'user_permissions',
        )
