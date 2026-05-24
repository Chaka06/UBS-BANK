from io import BytesIO

from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def build_transfer_pdf(transfer) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle(f'Bordereau virement {transfer.id}')
    width, height = A4
    left = 18 * mm
    right = width - 18 * mm
    top = height - 18 * mm

    logo_path = settings.BASE_DIR / "bank" / "static" / "bank" / "ubs-logo.png"
    if logo_path.exists():
        pdf.drawImage(ImageReader(str(logo_path)), left, top - 28, width=45, height=18, mask="auto")
    else:
        pdf.setFillColor(colors.HexColor("#CC0000"))
        pdf.rect(left, top - 20, 60, 12, fill=1, stroke=0)
        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(left + 6, top - 17, "UBS")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(left, top - 40, "Bordereau de virement")
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(colors.HexColor("#6c737f"))
    pdf.drawString(left, top - 56, "Document bancaire - usage client")

    pdf.setStrokeColor(colors.HexColor("#e6e8ec"))
    pdf.line(left, top - 64, right, top - 64)

    y = top - 85
    pdf.setFont("Helvetica-Bold", 11)
    pdf.setFillColor(colors.black)
    pdf.drawString(left, y, "Informations principales")
    y -= 16

    pdf.setFont("Helvetica", 10)

    def row(label, value, y_pos):
        pdf.setFillColor(colors.HexColor("#6c737f"))
        pdf.drawString(left, y_pos, label)
        pdf.setFillColor(colors.black)
        pdf.drawRightString(right, y_pos, value)
        return y_pos - 14

    y = row("Identifiant", f"{transfer.id}", y)
    y = row("Statut", transfer.get_status_display(), y)
    y = row("Montant", f"{transfer.amount} {transfer.currency}", y)
    y = row("Date", timezone.localtime(transfer.created_at).strftime("%d/%m/%Y %H:%M"), y)

    y -= 8
    pdf.setFont("Helvetica-Bold", 11)
    pdf.setFillColor(colors.black)
    pdf.drawString(left, y, "Bénéficiaire")
    y -= 16
    pdf.setFont("Helvetica", 10)
    y = row("Nom", transfer.beneficiary.full_name, y)
    y = row("Compte", transfer.beneficiary.account_number, y)
    y = row("BIC/SWIFT", transfer.beneficiary.bic_swift, y)
    if transfer.reference:
        y = row("Référence", transfer.reference, y)
    if transfer.rejection_reason:
        y -= 6
        pdf.setFillColor(colors.HexColor("#b42318"))
        pdf.drawString(left, y, f"Motif de rejet: {transfer.rejection_reason}")

    pdf.setFillColor(colors.HexColor("#9aa0a6"))
    pdf.setFont("Helvetica", 8)
    pdf.drawString(left, 28, settings.UBS_LEGAL_SIEGE)
    pdf.drawString(left, 18, settings.UBS_LEGAL_CAPITAL)
    pdf.drawString(left, 8, "UBS Banque en ligne • Document généré automatiquement")
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.read()


def build_rib_pdf(user, bank_account) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle('RIB UBS')
    width, height = A4
    left = 18 * mm
    right = width - 18 * mm
    top = height - 18 * mm

    logo_path = settings.BASE_DIR / "bank" / "static" / "bank" / "ubs-logo.png"
    if logo_path.exists():
        pdf.drawImage(ImageReader(str(logo_path)), left, top - 28, width=45, height=18, mask="auto")
    else:
        pdf.setFillColor(colors.HexColor("#CC0000"))
        pdf.rect(left, top - 20, 60, 12, fill=1, stroke=0)
        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(left + 6, top - 17, "UBS")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(left, top - 40, "Relevé d'identité bancaire")
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(colors.HexColor("#6c737f"))
    pdf.drawString(left, top - 56, "Document bancaire - usage client")

    pdf.setStrokeColor(colors.HexColor("#e6e8ec"))
    pdf.line(left, top - 64, right, top - 64)

    y = top - 85
    pdf.setFont("Helvetica-Bold", 11)
    pdf.setFillColor(colors.black)
    pdf.drawString(left, y, "Titulaire")
    y -= 16

    pdf.setFont("Helvetica", 10)

    def row(label, value, y_pos):
        pdf.setFillColor(colors.HexColor("#6c737f"))
        pdf.drawString(left, y_pos, label)
        pdf.setFillColor(colors.black)
        pdf.drawRightString(right, y_pos, value)
        return y_pos - 14

    y = row("Nom", f"{user.first_name} {user.last_name}", y)
    y = row("Adresse", user.address, y)
    y = row("Pays", user.get_country_display(), y)

    y -= 8
    pdf.setFont("Helvetica-Bold", 11)
    pdf.setFillColor(colors.black)
    pdf.drawString(left, y, "Coordonnées bancaires")
    y -= 16
    pdf.setFont("Helvetica", 10)
    y = row("IBAN", bank_account.iban, y)
    y = row("BIC", bank_account.bic, y)
    y = row("Numéro de compte", bank_account.account_number, y)
    y = row("Devise", bank_account.currency, y)

    if bank_account.manager:
        y -= 8
        pdf.setFont("Helvetica-Bold", 11)
        pdf.setFillColor(colors.black)
        pdf.drawString(left, y, "Gestionnaire")
        y -= 16
        pdf.setFont("Helvetica", 10)
        y = row("Nom", bank_account.manager.full_name, y)
        y = row("Email", bank_account.manager.email, y)
        if bank_account.manager.phone_number:
            y = row("Téléphone", bank_account.manager.phone_number, y)

    pdf.setFillColor(colors.HexColor("#9aa0a6"))
    pdf.setFont("Helvetica", 8)
    pdf.drawString(left, 28, settings.UBS_LEGAL_SIEGE)
    pdf.drawString(left, 18, settings.UBS_LEGAL_CAPITAL)
    pdf.drawString(left, 8, "UBS Banque en ligne • Document généré automatiquement")
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.read()
