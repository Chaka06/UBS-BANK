from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import translation
from django.utils.translation import gettext as _
from .forms import (
    BeneficiaryForm,
    LoginForm,
    LanguagePreferenceForm,
    OTPForm,
    PasswordChangeRequestForm,
    RegistrationForm,
    SupportMessageForm,
    TransferForm,
)
from .models import BankAccount, Beneficiary, Notification, OTP, SupportMessage, Transfer, User
from .pdf_utils import build_rib_pdf, build_transfer_pdf
from .utils import build_email_html, generate_otp, send_email


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'bank/home.html')


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('register_success')
    else:
        form = RegistrationForm()
    return render(request, 'bank/register.html', {'form': form})


def register_success(request):
    return render(request, 'bank/register_success.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            if not user.is_active:
                messages.warning(
                    request,
                    _("Votre compte est en cours de validation. Vous recevrez un email dès activation."),
                )
                return redirect('login')
            otp = generate_otp(user, OTP.PURPOSE_LOGIN)
            request.session['otp_user_id'] = user.id
            request.session['otp_purpose'] = OTP.PURPOSE_LOGIN
            subject = _("Code de connexion UBS")
            body = _("Votre code OTP est : %(code)s. Il est valable 10 minutes.") % {
                "code": otp.code
            }
            html_body = build_email_html(
                _("Connexion sécurisée"),
                _("Bonjour %(first_name)s,") % {"first_name": user.first_name},
                [
                    _("Votre code OTP est : %(code)s") % {"code": otp.code},
                    _("Le code est valable 10 minutes."),
                    _("Ne partagez jamais ce code."),
                ],
                _("Si vous n'êtes pas à l'origine de cette demande, contactez votre gestionnaire."),
            )
            email_sent = send_email(subject, body, user.email, html_body=html_body)
            if not email_sent:
                request.session.pop('otp_user_id', None)
                request.session.pop('otp_purpose', None)
                messages.error(
                    request,
                    _("Impossible d'envoyer l'OTP. Vérifiez la configuration SMTP."),
                )
                return redirect('login')
            return redirect('otp_verify')
    else:
        form = LoginForm()
    return render(request, 'bank/login.html', {'form': form})


def otp_verify(request):
    user_id = request.session.get('otp_user_id')
    purpose = request.session.get('otp_purpose')
    if not user_id or purpose != OTP.PURPOSE_LOGIN:
        return redirect('login')

    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            otp = (
                OTP.objects.filter(user_id=user_id, purpose=purpose, code=code, is_used=False)
                .order_by('-created_at')
                .first()
            )
            if otp and otp.is_valid():
                otp.is_used = True
                otp.save(update_fields=['is_used'])
                user = otp.user
                login(request, user)
                request.session.pop('otp_user_id', None)
                request.session.pop('otp_purpose', None)
                return redirect('dashboard')
            messages.error(request, _('Code OTP invalide ou expiré.'))
    else:
        form = OTPForm()
    return render(request, 'bank/otp_verify.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def dashboard(request):
    bank_account = getattr(request.user, 'bank_account', None)
    transfers = request.user.transfers.order_by('-created_at')[:5]
    notifications = request.user.notifications.order_by('-created_at')[:5]
    return render(
        request,
        'bank/dashboard.html',
        {
            'bank_account': bank_account,
            'transfers': transfers,
            'notifications': notifications,
        },
    )


@login_required
def profile(request):
    bank_account = getattr(request.user, 'bank_account', None)
    form = PasswordChangeRequestForm()
    if request.method == 'POST':
        form = PasswordChangeRequestForm(request.POST)
        if form.is_valid():
            otp = generate_otp(request.user, OTP.PURPOSE_PASSWORD)
            request.session['pending_password_hash'] = make_password(
                form.cleaned_data['new_password1']
            )
            request.session['otp_user_id'] = request.user.id
            request.session['otp_purpose'] = OTP.PURPOSE_PASSWORD
            subject = _("Validation du changement de mot de passe")
            body = _("Votre code OTP est : %(code)s. Il est valable 10 minutes.") % {
                "code": otp.code
            }
            html_body = build_email_html(
                _("Changement de mot de passe"),
                _("Bonjour %(first_name)s,") % {"first_name": request.user.first_name},
                [
                    _("Votre code OTP est : %(code)s") % {"code": otp.code},
                    _("Le code est valable 10 minutes."),
                    _("Ne partagez jamais ce code."),
                ],
                _("Si vous n'êtes pas à l'origine de cette demande, contactez votre gestionnaire."),
            )
            email_sent = send_email(subject, body, request.user.email, html_body=html_body)
            if not email_sent:
                request.session.pop('pending_password_hash', None)
                request.session.pop('otp_user_id', None)
                request.session.pop('otp_purpose', None)
                messages.error(
                    request,
                    _("Impossible d'envoyer l'OTP. Vérifiez la configuration SMTP."),
                )
                return redirect('profile')
            return redirect('password_otp')
    return render(request, 'bank/profile.html', {'form': form, 'bank_account': bank_account})


@login_required
def password_otp(request):
    user_id = request.session.get('otp_user_id')
    purpose = request.session.get('otp_purpose')
    password_hash = request.session.get('pending_password_hash')
    if not user_id or purpose != OTP.PURPOSE_PASSWORD or not password_hash:
        return redirect('profile')
    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            otp = (
                OTP.objects.filter(user_id=user_id, purpose=purpose, code=code, is_used=False)
                .order_by('-created_at')
                .first()
            )
            if otp and otp.is_valid():
                otp.is_used = True
                otp.save(update_fields=['is_used'])
                user = otp.user
                user.password = password_hash
                user.save(update_fields=['password'])
                request.session.pop('pending_password_hash', None)
                request.session.pop('otp_user_id', None)
                request.session.pop('otp_purpose', None)
                messages.success(request, _('Votre mot de passe a été modifié.'))
                return redirect('profile')
            messages.error(request, _('Code OTP invalide ou expiré.'))
    else:
        form = OTPForm()
    return render(request, 'bank/password_otp.html', {'form': form})


@login_required
def beneficiaries(request):
    if request.method == 'POST':
        form = BeneficiaryForm(request.POST)
        if form.is_valid():
            beneficiary = form.save(commit=False)
            beneficiary.user = request.user
            beneficiary.save()
            messages.success(request, _('Bénéficiaire enregistré.'))
            return redirect('beneficiaries')
    else:
        form = BeneficiaryForm()
    items = request.user.beneficiaries.order_by('-created_at')
    return render(request, 'bank/beneficiaries.html', {'form': form, 'beneficiaries': items})


@login_required
def transfer_create(request):
    bank_account = getattr(request.user, 'bank_account', None)
    if not bank_account:
        return HttpResponseForbidden(_('Compte bancaire indisponible.'))
    if bank_account.is_blocked:
        messages.error(request, _('Votre compte est bloqué. Contactez votre gestionnaire.'))
        return redirect('dashboard')
    if bank_account.transfers_suspended:
        messages.error(request, _('Les virements sont suspendus. Contactez votre gestionnaire.'))
        return redirect('dashboard')
    if request.user.beneficiaries.count() == 0:
        messages.warning(request, _('Ajoutez un bénéficiaire avant de faire un virement.'))
        return redirect('beneficiaries')

    if request.method == 'POST':
        form = TransferForm(request.POST)
        form.fields['beneficiary'].queryset = request.user.beneficiaries.all()
        if form.is_valid():
            amount = form.cleaned_data['amount']
            if bank_account.balance < amount:
                form.add_error('amount', _('Solde insuffisant.'))
            else:
                with transaction.atomic():
                    transfer = form.save(commit=False)
                    transfer.user = request.user
                    transfer.currency = bank_account.currency
                    transfer.save()
                    bank_account.balance -= amount
                    bank_account.save(update_fields=['balance'])
                transfer_pdf = build_transfer_pdf(transfer)
                attachments = [
                    (f"virement_{transfer.id}.pdf", transfer_pdf, "application/pdf"),
                ]
                send_email(
                    _('Virement en cours'),
                    (
                        _("Votre virement de %(amount)s %(currency)s vers %(beneficiary)s est en cours de validation.")
                        % {
                            "amount": amount,
                            "currency": bank_account.currency,
                            "beneficiary": transfer.beneficiary.full_name,
                        }
                    ),
                    request.user.email,
                    html_body=build_email_html(
                        _("Virement en cours"),
                        _("Bonjour %(first_name)s,") % {"first_name": request.user.first_name},
                        [
                            _("Montant: %(amount)s %(currency)s")
                            % {"amount": amount, "currency": bank_account.currency},
                            _("Bénéficiaire: %(beneficiary)s")
                            % {"beneficiary": transfer.beneficiary.full_name},
                            _("Statut: en cours de validation"),
                            _("Bordereau en pièce jointe."),
                        ],
                        _("Vous serez informé dès validation."),
                    ),
                    attachments=attachments,
                )
                send_email(
                    _('Virement entrant en cours'),
                    (
                        _("Un virement de %(amount)s %(currency)s est en cours vers votre compte %(account)s.")
                        % {
                            "amount": amount,
                            "currency": bank_account.currency,
                            "account": transfer.beneficiary.account_number,
                        }
                    ),
                    transfer.beneficiary.email,
                    html_body=build_email_html(
                        _("Virement entrant"),
                        _("Bonjour %(full_name)s,") % {"full_name": transfer.beneficiary.full_name},
                        [
                            _("Montant: %(amount)s %(currency)s")
                            % {"amount": amount, "currency": bank_account.currency},
                            _("Statut: en cours de validation"),
                            _("Référence: %(reference)s") % {"reference": transfer.reference or '-'},
                            _("Bordereau en pièce jointe."),
                        ],
                        _("Vous recevrez une confirmation après validation."),
                    ),
                    attachments=attachments,
                )
                messages.success(request, _('Virement enregistré. Statut: en cours.'))
                return redirect('transfers')
    else:
        form = TransferForm()
        form.fields['beneficiary'].queryset = request.user.beneficiaries.all()
    return render(request, 'bank/transfer_create.html', {'form': form, 'bank_account': bank_account})


@login_required
def transfers(request):
    items = request.user.transfers.order_by('-created_at')
    return render(request, 'bank/transfers.html', {'transfers': items})


@login_required
def transfer_detail(request, transfer_id):
    transfer = get_object_or_404(Transfer, pk=transfer_id, user=request.user)
    return render(request, 'bank/transfer_detail.html', {'transfer': transfer})


@login_required
def download_transfer_pdf(request, transfer_id):
    transfer = get_object_or_404(Transfer, pk=transfer_id, user=request.user)
    pdf_bytes = build_transfer_pdf(transfer)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="virement_{transfer.id}.pdf"'
    return response


@login_required
def download_rib_pdf(request):
    bank_account = getattr(request.user, 'bank_account', None)
    if not bank_account:
        return HttpResponseForbidden(_('Compte bancaire indisponible.'))
    pdf_bytes = build_rib_pdf(request.user, bank_account)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="rib_ubs.pdf"'
    return response


@login_required
def notifications(request):
    items = request.user.notifications.order_by('-created_at')
    return render(request, 'bank/notifications.html', {'notifications': items})


@login_required
def notification_delete(request, notification_id):
    if request.method != 'POST':
        return redirect('notifications')
    notification = get_object_or_404(Notification, pk=notification_id, user=request.user)
    notification.delete()
    messages.success(request, _('Notification supprimée.'))
    return redirect('notifications')


@login_required
def notifications_clear(request):
    if request.method != 'POST':
        return redirect('notifications')
    request.user.notifications.all().delete()
    messages.success(request, _('Toutes les notifications ont été supprimées.'))
    return redirect('notifications')


@login_required
def contact(request):
    bank_account = getattr(request.user, 'bank_account', None)
    return render(request, 'bank/contact.html', {'bank_account': bank_account})


@login_required
def parameters(request):
    language_form = LanguagePreferenceForm(instance=request.user)

    if request.method == 'POST':
        if 'save_language' in request.POST:
            language_form = LanguagePreferenceForm(request.POST, instance=request.user)
            if language_form.is_valid():
                user = language_form.save()
                user.save(update_fields=['preferred_language'])
                translation.activate(user.preferred_language)
                request.session['django_language'] = user.preferred_language
                messages.success(request, _('Langue mise à jour.'))
                return redirect('parameters')

    return render(
        request,
        'bank/parameters.html',
        {
            'form': language_form,
        },
    )


@login_required
def support_chat(request):
    message_form = SupportMessageForm()
    if request.method == 'POST':
        if 'send_message' in request.POST:
            message_form = SupportMessageForm(request.POST)
            if message_form.is_valid():
                support_message = message_form.save(commit=False)
                support_message.user = request.user
                support_message.sender_type = SupportMessage.SENDER_USER
                support_message.save()
                messages.success(request, _('Message envoyé au support.'))
                return redirect('support_chat')
        if 'reset_chat' in request.POST:
            request.user.support_messages.all().delete()
            messages.success(request, _('Conversation réinitialisée.'))
            return redirect('support_chat')

    support_messages = request.user.support_messages.order_by('created_at')
    return render(
        request,
        'bank/support_chat.html',
        {'message_form': message_form, 'support_messages': support_messages},
    )
