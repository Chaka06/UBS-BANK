import logging
import random
import smtplib
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from .models import OTP


logger = logging.getLogger(__name__)

LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/3/34/UBS_Logo.png"


def build_email_html(
    title: str,
    greeting: str,
    lines: list[str],
    footer: str,
    button_text: str | None = None,
    button_url: str | None = None,
) -> str:
    items = "".join(f"<li>{line}</li>" for line in lines)
    button_block = ""
    if button_text and button_url:
        button_block = (
            f'<div style="margin:16px 0 8px;">'
            f'<a href="{button_url}" '
            f'style="background:#cc0000;color:#ffffff;text-decoration:none;'
            f'padding:10px 16px;border-radius:8px;display:inline-block;'
            f'font-weight:600;font-size:14px;">{button_text}</a>'
            f"</div>"
        )
    return f"""
    <html>
      <body style="margin:0;background:#f5f6f8;font-family:Arial,sans-serif;color:#1c1f24;">
        <div style="max-width:600px;margin:0 auto;padding:24px;">
          <div style="background:#ffffff;border-radius:14px;padding:24px;border:1px solid #e6e8ec;">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
              <img src="{LOGO_URL}" alt="UBS" style="height:32px;">
              <div style="font-size:14px;color:#6c737f;">Banque en ligne</div>
            </div>
            <h2 style="margin:0 0 8px;font-size:20px;">{title}</h2>
            <p style="margin:0 0 16px;">{greeting}</p>
            <ul style="padding-left:18px;margin:0 0 16px;">{items}</ul>
            {button_block}
            <p style="margin:0;font-size:13px;color:#6c737f;">{footer}</p>
          </div>
          <p style="text-align:center;font-size:12px;color:#9aa0a6;margin-top:12px;">
            UBS Banque en ligne • Message automatique
          </p>
        </div>
      </body>
    </html>
    """.strip()


def send_email(
    subject: str,
    body: str,
    to_email: str,
    html_body: str | None = None,
    attachments: list[tuple[str, bytes, str]] | None = None,
) -> bool:
    message = EmailMultiAlternatives(subject, body, settings.DEFAULT_FROM_EMAIL, [to_email])
    if html_body:
        message.attach_alternative(html_body, "text/html")
    if attachments:
        for filename, content, mimetype in attachments:
            message.attach(filename, content, mimetype)
    try:
        message.send(fail_silently=False)
        return True
    except (smtplib.SMTPException, OSError) as exc:
        logger.exception('Echec envoi email: %s', exc)
        return False


def generate_otp(user, purpose: str) -> OTP:
    code = ''.join(str(random.randint(0, 9)) for _ in range(6))
    otp = OTP.objects.create(
        user=user,
        code=code,
        purpose=purpose,
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    return otp
