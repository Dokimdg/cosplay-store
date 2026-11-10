"""Генерація PDF-рахунку (reportlab). Шрифт DejaVu лежить у orders/assets — він підтримує кирилицю."""
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.fonts import addMapping
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ASSETS = Path(__file__).resolve().parent / 'assets'
FONT, FONT_BOLD = 'DejaVuSans', 'DejaVuSans-Bold'

_fonts_ready = False


def _register_fonts():
    global _fonts_ready
    if not _fonts_ready:
        pdfmetrics.registerFont(TTFont(FONT, str(ASSETS / 'DejaVuSans.ttf')))
        pdfmetrics.registerFont(TTFont(FONT_BOLD, str(ASSETS / 'DejaVuSans-Bold.ttf')))
        addMapping(FONT, 0, 0, FONT)
        addMapping(FONT, 1, 0, FONT_BOLD)
        addMapping(FONT, 0, 1, FONT)
        addMapping(FONT, 1, 1, FONT_BOLD)
        _fonts_ready = True


def _money(value):
    return f'{Decimal(value):,.2f}'.replace(',', ' ') + ' грн'


def build_invoice_pdf(order, company=None):
    """Повертає байти PDF для замовлення. company — словник реквізитів (за замовчуванням з settings)."""
    _register_fonts()
    company = company or settings.COMPANY_DETAILS

    normal = ParagraphStyle('n', fontName=FONT, fontSize=9.5, leading=13)
    small = ParagraphStyle('s', parent=normal, fontSize=8.5, leading=12, textColor=colors.HexColor('#495057'))
    h1 = ParagraphStyle('h1', parent=normal, fontName=FONT_BOLD, fontSize=17, leading=22, spaceAfter=4)
    h2 = ParagraphStyle('h2', parent=normal, fontName=FONT_BOLD, fontSize=11, leading=15, spaceBefore=8, spaceAfter=3)
    right = ParagraphStyle('r', parent=normal, alignment=2)

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
        title=f'Рахунок №{order.id}', author=company['name'],
    )
    story = []

    # --- шапка: логотип + реквізити компанії ---
    requisites = (
        f'<b>{escape(company["name"])}</b><br/>'
        f'ЄДРПОУ: {escape(company["edrpou"])}<br/>'
        f'IBAN: {escape(company["iban"])}<br/>'
        f'Банк: {escape(company["bank"])}<br/>'
        f'{escape(company["address"])}<br/>'
        f'{escape(company["phone"])} · {escape(company["email"])}'
    )
    header = Table(
        [[Image(str(ASSETS / 'logo.png'), width=24 * mm, height=24 * mm), Paragraph(requisites, small)]],
        colWidths=[30 * mm, None],
    )
    header.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LEFTPADDING', (0, 0), (0, 0), 0)]))
    story += [header, Spacer(1, 6 * mm)]

    created = order.created.strftime('%d.%m.%Y')
    story.append(Paragraph(f'Рахунок на оплату №{order.id} від {created}', h1))
    story.append(Paragraph(f'Статус замовлення: {order.get_status_display()}', normal))

    # --- покупець ---
    addr = order.shipping_address
    story.append(Paragraph('Платник / одержувач', h2))
    customer = (
        f'{escape(addr.full_name)}, тел. {escape(addr.phone)}<br/>'
        f'{escape(addr.city)}, {escape(addr.address)}'
    )
    if addr.postal_code:
        customer += f', {escape(addr.postal_code)}'
    story.append(Paragraph(customer, normal))
    story.append(Spacer(1, 5 * mm))

    # --- позиції ---
    rows = [[Paragraph(f'<b>{h}</b>', normal) for h in ('№', 'Товар', 'К-сть', 'Ціна', 'Сума')]]
    total = Decimal('0')
    for i, item in enumerate(order.items.all(), start=1):
        cost = item.get_cost()
        total += cost
        rows.append([
            Paragraph(str(i), normal), Paragraph(escape(item.product_name), normal),
            Paragraph(str(item.quantity), right), Paragraph(_money(item.price), right), Paragraph(_money(cost), right),
        ])
    rows.append([Paragraph(f'<b>Разом до сплати: {_money(total)}</b>', right), '', '', '', ''])

    table = Table(rows, colWidths=[10 * mm, None, 16 * mm, 30 * mm, 32 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9ecef')),
        ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#adb5bd')),
        ('SPAN', (0, -1), (-1, -1)),
        ('LINEABOVE', (0, -1), (-1, -1), 0.8, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    story.append(Spacer(1, 6 * mm))

    if order.estimated_delivery_date:
        story.append(Paragraph(
            f'Орієнтовна дата доставки: {order.estimated_delivery_date.strftime("%d.%m.%Y")}', normal))
    story.append(Paragraph(
        f'Призначення платежу: оплата замовлення №{order.id}. Дякуємо, що обрали {escape(company["name"])}!', small))

    doc.build(story)
    return buf.getvalue()
