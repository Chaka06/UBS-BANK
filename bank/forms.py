from decimal import Decimal

from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import Beneficiary, SupportMessage, Transfer, User


class RegistrationForm(forms.ModelForm):
    password1 = forms.CharField(
        label=_('Mot de passe'),
        widget=forms.PasswordInput(attrs={'class': 'password-input'}),
    )
    password2 = forms.CharField(
        label=_('Confirmer le mot de passe'),
        widget=forms.PasswordInput(attrs={'class': 'password-input'}),
    )

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'date_of_birth',
            'phone_number',
            'address',
            'country',
            'id_doc_front',
            'id_doc_back',
        ]
        labels = {
            'first_name': _('Prénom'),
            'last_name': _('Nom'),
            'email': _('Adresse mail'),
            'date_of_birth': _('Date de naissance'),
            'phone_number': _('Numéro de téléphone'),
            'address': _('Adresse de résidence'),
            'country': _('Pays'),
            'id_doc_front': _("Pièce d'identité (recto)"),
            'id_doc_back': _("Pièce d'identité (verso)"),
        }
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password1') != cleaned_data.get('password2'):
            raise ValidationError(_('Les mots de passe ne correspondent pas.'))
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.is_active = False
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(label=_('Adresse mail'))
    password = forms.CharField(
        label=_('Mot de passe'),
        widget=forms.PasswordInput(attrs={'class': 'password-input'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise ValidationError(_('Identifiants invalides.'))
            cleaned_data['user'] = user
        return cleaned_data


class OTPForm(forms.Form):
    code = forms.CharField(label=_('Code OTP'), max_length=6)


class BeneficiaryForm(forms.ModelForm):
    class Meta:
        model = Beneficiary
        fields = ['full_name', 'email', 'account_number', 'bic_swift']
        labels = {
            'full_name': _('Nom et prénom'),
            'email': _('Adresse mail'),
            'account_number': _('Numéro de compte'),
            'bic_swift': _('Code BIC / SWIFT'),
        }


class TransferForm(forms.ModelForm):
    class Meta:
        model = Transfer
        fields = ['beneficiary', 'amount', 'reference']
        labels = {
            'beneficiary': _('Bénéficiaire / gestionnaire'),
            'amount': _('Montant'),
            'reference': _('Référence'),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None or amount <= Decimal('0.00'):
            raise ValidationError(_('Le montant doit être supérieur à 0.'))
        return amount


class PasswordChangeRequestForm(forms.Form):
    new_password1 = forms.CharField(
        label=_('Nouveau mot de passe'),
        widget=forms.PasswordInput(attrs={'class': 'password-input'}),
    )
    new_password2 = forms.CharField(
        label=_('Confirmer le mot de passe'),
        widget=forms.PasswordInput(attrs={'class': 'password-input'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('new_password1') != cleaned_data.get('new_password2'):
            raise ValidationError(_('Les mots de passe ne correspondent pas.'))
        return cleaned_data


class LanguagePreferenceForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['preferred_language']
        labels = {'preferred_language': _('Langue du système')}


class SupportMessageForm(forms.ModelForm):
    class Meta:
        model = SupportMessage
        fields = ['message']
        labels = {'message': _('Votre message')}
        widgets = {'message': forms.Textarea(attrs={'rows': 4})}
