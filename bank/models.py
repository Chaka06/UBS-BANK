import random
import string
from decimal import Decimal

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


COUNTRY_CHOICES = [
    ('FR', _('France')),
    ('IT', _('Italie')),
    ('DE', _('Allemagne')),
    ('ES', _('Espagne')),
    ('CH', _('Suisse')),
    ('BE', _('Belgique')),
    ('LU', _('Luxembourg')),
    ('NL', _('Pays-Bas')),
    ('GB', _('Royaume-Uni')),
]


IBAN_LENGTHS = {
    'FR': 27,
    'IT': 27,
    'DE': 22,
    'ES': 24,
    'CH': 21,
    'BE': 16,
    'LU': 20,
    'NL': 18,
    'GB': 22,
}


def _random_digits(count: int) -> str:
    return ''.join(random.choice(string.digits) for _ in range(count))


def generate_iban(country_code: str) -> str:
    length = IBAN_LENGTHS.get(country_code, 27)
    check_digits = _random_digits(2)
    body = _random_digits(length - 4)
    return f'{country_code}{check_digits}{body}'


def generate_account_number() -> str:
    return _random_digits(12)


def generate_bic(country_code: str) -> str:
    return f'UBS{country_code}XXX'


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Un email est obligatoire.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    phone_number = models.CharField(max_length=30)
    address = models.CharField(max_length=255)
    country = models.CharField(max_length=2, choices=COUNTRY_CHOICES)
    id_doc_front = models.ImageField(upload_to='ids/front/')
    id_doc_back = models.ImageField(upload_to='ids/back/')
    preferred_language = models.CharField(
        max_length=2,
        choices=(
            ('fr', _('Français')),
            ('en', _('English')),
            ('de', _('Deutsch')),
            ('es', _('Español')),
        ),
        default='fr',
    )

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'date_of_birth', 'phone_number', 'address', 'country']

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.email})'


class AccountManager(models.Model):
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone_number = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return self.full_name


class BankAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='bank_account')
    manager = models.ForeignKey(AccountManager, on_delete=models.SET_NULL, null=True, blank=True)
    country = models.CharField(max_length=2, choices=COUNTRY_CHOICES)
    iban = models.CharField(max_length=34)
    bic = models.CharField(max_length=11)
    account_number = models.CharField(max_length=20)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=3, default='EUR')

    is_blocked = models.BooleanField(default=False)
    block_reason = models.TextField(blank=True)
    block_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    transfers_suspended = models.BooleanField(default=False)
    suspend_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Compte UBS - {self.user.email}'


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=150)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f'Notification {self.title} - {self.user.email}'


class SupportMessage(models.Model):
    SENDER_USER = 'user'
    SENDER_ADMIN = 'admin'

    SENDER_CHOICES = [
        (SENDER_USER, _('Client')),
        (SENDER_ADMIN, _('Support')),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_messages')
    sender_type = models.CharField(max_length=10, choices=SENDER_CHOICES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Support {self.sender_type} - {self.user.email}'


class OTP(models.Model):
    PURPOSE_LOGIN = 'login'
    PURPOSE_PASSWORD = 'password_change'

    PURPOSE_CHOICES = [
        (PURPOSE_LOGIN, _('Connexion')),
        (PURPOSE_PASSWORD, _('Changement de mot de passe')),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self) -> bool:
        return not self.is_used and timezone.now() <= self.expires_at

    def __str__(self):
        return f'OTP {self.purpose} - {self.user.email}'


class Beneficiary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='beneficiaries')
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    account_number = models.CharField(max_length=34)
    bic_swift = models.CharField(max_length=11)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.full_name} ({self.user.email})'


class Transfer(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING, _('En cours')),
        (STATUS_APPROVED, _('Traitée')),
        (STATUS_REJECTED, _('Rejetée')),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transfers')
    beneficiary = models.ForeignKey(Beneficiary, on_delete=models.CASCADE, related_name='transfers')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='EUR')
    reference = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Virement {self.id} - {self.user.email}'
