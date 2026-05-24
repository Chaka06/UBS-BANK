from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .admin_forms import UserChangeForm, UserCreationForm
from .models import AccountManager, BankAccount, Beneficiary, Notification, SupportMessage, Transfer, User


class BankAccountInline(admin.StackedInline):
    model = BankAccount
    extra = 0
    readonly_fields = ('iban', 'bic', 'account_number', 'balance', 'currency', 'country')
    fields = (
        'manager',
        'country',
        'iban',
        'bic',
        'account_number',
        'balance',
        'currency',
        'is_blocked',
        'block_reason',
        'block_fee',
        'transfers_suspended',
        'suspend_reason',
    )


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    list_display = ('email', 'first_name', 'last_name', 'is_active', 'is_staff')
    list_filter = ('is_active', 'is_staff', 'country')
    ordering = ('email',)
    search_fields = ('email', 'first_name', 'last_name')
    fieldsets = (
        ('Identité', {'fields': ('email', 'password', 'first_name', 'last_name')}),
        ('Informations', {'fields': ('date_of_birth', 'phone_number', 'address', 'country')}),
        ("Documents", {'fields': ('id_doc_front', 'id_doc_back')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'first_name',
                    'last_name',
                    'date_of_birth',
                    'phone_number',
                    'address',
                    'country',
                    'id_doc_front',
                    'id_doc_back',
                    'password1',
                    'password2',
                    'is_active',
                    'is_staff',
                ),
            },
        ),
    )
    inlines = [BankAccountInline]


@admin.register(AccountManager)
class AccountManagerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone_number')
    search_fields = ('full_name', 'email')


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'iban', 'balance', 'currency', 'is_blocked', 'transfers_suspended')
    list_filter = ('is_blocked', 'transfers_suspended', 'currency', 'country')
    search_fields = ('user__email', 'iban')


@admin.register(Beneficiary)
class BeneficiaryAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'user')
    search_fields = ('full_name', 'email', 'user__email')


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'beneficiary', 'amount', 'status', 'created_at')
    list_filter = ('status', 'currency')
    search_fields = ('user__email', 'beneficiary__full_name', 'beneficiary__email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created_at', 'is_read')
    search_fields = ('title', 'user__email')


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'sender_type', 'created_at')
    list_filter = ('sender_type',)
    search_fields = ('user__email', 'message')
