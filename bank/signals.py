from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext as _

from .models import BankAccount, Notification, Transfer, User, generate_account_number, generate_bic, generate_iban
from .pdf_utils import build_rib_pdf, build_transfer_pdf
from .utils import build_email_html, send_email


@receiver(pre_save, sender=User)
def user_previous_state(sender, instance, **kwargs):
    if instance.pk:
        instance._previous_is_active = sender.objects.filter(pk=instance.pk).values_list(
            'is_active', flat=True
        ).first()
    else:
        instance._previous_is_active = False


@receiver(post_save, sender=User)
def create_bank_account_on_activation(sender, instance, created, **kwargs):
    previous = getattr(instance, '_previous_is_active', False)
    if instance.is_active and not previous:
        if not hasattr(instance, 'bank_account'):
            BankAccount.objects.create(
                user=instance,
                country=instance.country,
                iban=generate_iban(instance.country),
                bic=generate_bic(instance.country),
                account_number=generate_account_number(),
            )
        bank_account = instance.bank_account
        rib_pdf = build_rib_pdf(instance, bank_account)
        login_url = f"{settings.SITE_URL.rstrip('/')}{reverse('login')}"
        send_email(
            _("Compte UBS activé"),
            _(
                "Votre compte est maintenant actif. Vous pouvez vous connecter "
                "avec votre adresse mail et votre mot de passe."
            ),
            instance.email,
            html_body=build_email_html(
                _("Compte activé"),
                _("Bonjour %(first_name)s,") % {"first_name": instance.first_name},
                [
                    _("Votre compte est maintenant actif."),
                    _("Vous pouvez vous connecter avec votre adresse mail et votre mot de passe."),
                    _("Votre RIB est joint à cet email."),
                ],
                _("Bienvenue chez UBS Banque en ligne."),
                button_text=_("Se connecter"),
                button_url=login_url,
            ),
            attachments=[("rib_ubs.pdf", rib_pdf, "application/pdf")],
        )


@receiver(pre_save, sender=BankAccount)
def bankaccount_previous_state(sender, instance, **kwargs):
    if instance.pk:
        previous = sender.objects.filter(pk=instance.pk).values(
            'is_blocked',
            'block_reason',
            'block_fee',
            'transfers_suspended',
            'suspend_reason',
        ).first()
        instance._previous_state = previous
    else:
        instance._previous_state = None


@receiver(post_save, sender=BankAccount)
def notify_bankaccount_status(sender, instance, created, **kwargs):
    previous = getattr(instance, '_previous_state', None)
    if not previous:
        return

    if previous['is_blocked'] != instance.is_blocked:
        if instance.is_blocked:
            send_email(
                _("Votre compte UBS est bloqué"),
                _(
                    "Votre compte a été bloqué. Motif: %(reason)s. Frais: %(fee)s %(currency)s."
                )
                % {
                    "reason": instance.block_reason or _("Non précisé"),
                    "fee": instance.block_fee,
                    "currency": instance.currency,
                },
                instance.user.email,
                html_body=build_email_html(
                    _("Compte bloqué"),
                    _("Bonjour %(first_name)s,") % {"first_name": instance.user.first_name},
                    [
                        _("Motif: %(reason)s") % {"reason": instance.block_reason or _("Non précisé")},
                        _("Frais: %(fee)s %(currency)s")
                        % {"fee": instance.block_fee, "currency": instance.currency},
                        _("Veuillez contacter votre gestionnaire."),
                    ],
                    _("UBS Banque en ligne."),
                ),
            )
        else:
            send_email(
                _("Votre compte UBS est débloqué"),
                _("Votre compte a été débloqué. Vous pouvez utiliser vos services."),
                instance.user.email,
                html_body=build_email_html(
                    _("Compte débloqué"),
                    _("Bonjour %(first_name)s,") % {"first_name": instance.user.first_name},
                    [
                        _("Votre compte a été débloqué."),
                        _("Vous pouvez utiliser vos services."),
                    ],
                    _("UBS Banque en ligne."),
                ),
            )

    if previous['transfers_suspended'] != instance.transfers_suspended:
        if instance.transfers_suspended:
            send_email(
                _("Virements suspendus"),
                _(
                    "Les virements sont suspendus sur votre compte. Motif: %(reason)s."
                )
                % {"reason": instance.suspend_reason or _("Non précisé")},
                instance.user.email,
                html_body=build_email_html(
                    _("Virements suspendus"),
                    _("Bonjour %(first_name)s,") % {"first_name": instance.user.first_name},
                    [
                        _("Motif: %(reason)s") % {"reason": instance.suspend_reason or _("Non précisé")},
                        _("Veuillez contacter votre gestionnaire."),
                    ],
                    _("UBS Banque en ligne."),
                ),
            )
        else:
            send_email(
                _("Virements rétablis"),
                _("Les virements sont à nouveau disponibles sur votre compte."),
                instance.user.email,
                html_body=build_email_html(
                    _("Virements rétablis"),
                    _("Bonjour %(first_name)s,") % {"first_name": instance.user.first_name},
                    [
                        _("Les virements sont à nouveau disponibles."),
                    ],
                    _("UBS Banque en ligne."),
                ),
            )


@receiver(post_save, sender=Notification)
def notify_notification(sender, instance, created, **kwargs):
    if created:
        send_email(
            _("Notification UBS: %(title)s") % {"title": instance.title},
            instance.message,
            instance.user.email,
            html_body=build_email_html(
                instance.title,
                _("Bonjour %(first_name)s,") % {"first_name": instance.user.first_name},
                [instance.message],
                _("UBS Banque en ligne."),
            ),
        )


@receiver(pre_save, sender=Transfer)
def transfer_previous_state(sender, instance, **kwargs):
    if instance.pk:
        instance._previous_status = sender.objects.filter(pk=instance.pk).values_list(
            'status', flat=True
        ).first()
    else:
        instance._previous_status = None


@receiver(post_save, sender=Transfer)
def transfer_status_updates(sender, instance, created, **kwargs):
    if created:
        return
    previous = getattr(instance, '_previous_status', None)
    if previous == instance.status:
        return

    bank_account = instance.user.bank_account
    transfer_pdf = build_transfer_pdf(instance)
    attachments = [(f"virement_{instance.id}.pdf", transfer_pdf, "application/pdf")]
    if previous == Transfer.STATUS_PENDING and instance.status == Transfer.STATUS_REJECTED:
        with transaction.atomic():
            bank_account.balance += instance.amount
            bank_account.save(update_fields=['balance'])
        send_email(
            _("Virement rejeté"),
            _(
                "Votre virement vers %(beneficiary)s a été rejeté. Motif: %(reason)s."
            )
            % {
                "beneficiary": instance.beneficiary.full_name,
                "reason": instance.rejection_reason or _("Non précisé"),
            },
            instance.user.email,
            html_body=build_email_html(
                _("Virement rejeté"),
                _("Bonjour %(first_name)s,") % {"first_name": instance.user.first_name},
                [
                    _("Bénéficiaire: %(beneficiary)s")
                    % {"beneficiary": instance.beneficiary.full_name},
                    _("Motif: %(reason)s")
                    % {"reason": instance.rejection_reason or _("Non précisé")},
                    _("Bordereau en pièce jointe."),
                ],
                _("UBS Banque en ligne."),
            ),
            attachments=attachments,
        )
        send_email(
            _("Virement rejeté"),
            _(
                "Le virement en provenance de %(first_name)s %(last_name)s a été rejeté. Statut: Rejeté."
            )
            % {
                "first_name": instance.user.first_name,
                "last_name": instance.user.last_name,
            },
            instance.beneficiary.email,
            html_body=build_email_html(
                _("Virement rejeté"),
                _("Bonjour %(full_name)s,") % {"full_name": instance.beneficiary.full_name},
                [
                    _("Emetteur: %(first_name)s %(last_name)s")
                    % {
                        "first_name": instance.user.first_name,
                        "last_name": instance.user.last_name,
                    },
                    _("Statut: Rejeté"),
                    _("Bordereau en pièce jointe."),
                ],
                _("UBS Banque en ligne."),
            ),
            attachments=attachments,
        )
    elif previous == Transfer.STATUS_PENDING and instance.status == Transfer.STATUS_APPROVED:
        send_email(
            _("Virement traité"),
            _("Votre virement vers %(beneficiary)s a été traité avec succès.")
            % {"beneficiary": instance.beneficiary.full_name},
            instance.user.email,
            html_body=build_email_html(
                _("Virement traité"),
                _("Bonjour %(first_name)s,") % {"first_name": instance.user.first_name},
                [
                    _("Bénéficiaire: %(beneficiary)s")
                    % {"beneficiary": instance.beneficiary.full_name},
                    _("Statut: Traitée"),
                    _("Bordereau en pièce jointe."),
                ],
                _("UBS Banque en ligne."),
            ),
            attachments=attachments,
        )
        send_email(
            _("Virement reçu"),
            _(
                "Le virement en provenance de %(first_name)s %(last_name)s est maintenant traité. Statut: Traitée."
            )
            % {
                "first_name": instance.user.first_name,
                "last_name": instance.user.last_name,
            },
            instance.beneficiary.email,
            html_body=build_email_html(
                _("Virement reçu"),
                _("Bonjour %(full_name)s,") % {"full_name": instance.beneficiary.full_name},
                [
                    _("Emetteur: %(first_name)s %(last_name)s")
                    % {
                        "first_name": instance.user.first_name,
                        "last_name": instance.user.last_name,
                    },
                    _("Statut: Traitée"),
                    _("Bordereau en pièce jointe."),
                ],
                _("UBS Banque en ligne."),
            ),
            attachments=attachments,
        )
