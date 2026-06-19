from django.contrib import admin

from .admin_forms import UserChangeForm, UserCreationForm
from .models import AccountManager, BankAccount, Beneficiary, Notification, SupportMessage, Transfer, User


@admin.action(description='Lever le DI (autoriser les transactions)')
def lever_di(modeladmin, request, queryset):
    updated = 0
    for account in queryset.filter(is_di=True):
        account.is_di = False
        account.save(update_fields=['is_di'])
        updated += 1
    if updated:
        modeladmin.message_user(request, f"{updated} compte(s) : DI levé avec succès.")
    else:
        modeladmin.message_user(request, "Aucun DI à lever dans la sélection.")


class BankAccountInline(admin.StackedInline):
    model = BankAccount
    extra = 0
    can_delete = False
    readonly_fields = ('iban', 'bic', 'account_number', 'created_at')
    fields = (
        'manager',
        'country',
        'iban',
        'bic',
        'account_number',
        'balance',
        'currency',
        'is_di',
        'di_note',
        'is_blocked',
        'block_reason',
        'block_fee',
        'transfers_suspended',
        'suspend_reason',
    )

    def get_queryset(self, request):
        return super().get_queryset(request)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ('email', 'first_name', 'last_name', 'is_active', 'is_staff')
    list_filter = ('is_active', 'is_staff', 'country')
    ordering = ('email',)
    search_fields = ('email', 'first_name', 'last_name')

    # Formulaire de MODIFICATION (utilisateur existant)
    fieldsets = (
        ('Identité',     {'fields': ('email', 'password', 'first_name', 'last_name')}),
        ('Informations', {'fields': ('date_of_birth', 'phone_number', 'address', 'country', 'preferred_language')}),
        ('Documents ID', {'fields': ('id_doc_front', 'id_doc_back'),
                          'description': 'Documents uploadés par l\'utilisateur lors de son inscription.'}),
        ('Permissions',  {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Dates',        {'fields': ('last_login', 'date_joined')}),
    )

    # Formulaire de CRÉATION — sans uploads de fichiers (limite Vercel 4.5MB)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'first_name', 'last_name',
                'date_of_birth', 'phone_number', 'address', 'country',
                'password1', 'password2',
                'is_active', 'is_staff',
            ),
        }),
    )

    readonly_fields = ('id_doc_front', 'id_doc_back', 'last_login', 'date_joined')
    inlines = [BankAccountInline]

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            kwargs['form'] = self.add_form
        else:
            kwargs['form'] = self.form
        return super().get_form(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        return self.fieldsets

    def get_inlines(self, request, obj):
        if obj is None:
            return []
        return self.inlines

    def save_model(self, request, obj, form, change):
        if not change and 'password1' in form.cleaned_data:
            obj.set_password(form.cleaned_data['password1'])
        super().save_model(request, obj, form, change)


@admin.register(AccountManager)
class AccountManagerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone_number')
    search_fields = ('full_name', 'email')


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'iban', 'balance', 'currency', 'is_di', 'is_blocked', 'transfers_suspended')
    list_filter = ('is_di', 'is_blocked', 'transfers_suspended', 'currency', 'country')
    search_fields = ('user__email', 'iban')
    actions = [lever_di]


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

    def save_model(self, request, obj, form, change):
        if not change:
            obj.sender_type = SupportMessage.SENDER_ADMIN
        super().save_model(request, obj, form, change)
