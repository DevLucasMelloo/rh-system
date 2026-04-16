"""
Geração de holerite em PDF com ReportLab.
Layout: cabeçalho da empresa, dados do funcionário, tabela de itens, rodapé.
"""
import os
from decimal import Decimal
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


# ── Constantes de layout ──────────────────────────────────────────────────────

MARGIN = 15 * mm
PAGE_W, PAGE_H = A4

# Paleta de cores
COLOR_HEADER = colors.HexColor("#1a3c5e")
COLOR_SUBHEADER = colors.HexColor("#2c6fad")
COLOR_CREDIT_BG = colors.HexColor("#e8f4f8")
COLOR_DEBIT_BG = colors.HexColor("#fdf0f0")
COLOR_TABLE_HEADER = colors.HexColor("#34495e")
COLOR_TOTAL_BG = colors.HexColor("#ecf0f1")
COLOR_NET_BG = colors.HexColor("#27ae60")

MONTHS_PT = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def _fmt_brl(value: Decimal | float | None) -> str:
    if value is None:
        return "R$ 0,00"
    v = Decimal(str(value))
    sign = "-" if v < 0 else ""
    abs_v = abs(v)
    inteiro = int(abs_v)
    centavos = int(round((abs_v - inteiro) * 100))
    return f"{sign}R$ {inteiro:,d},{centavos:02d}".replace(",", "X").replace(".", ",").replace("X", ".")


def generate_payslip_pdf(payroll, employee, output_dir: str = "pdfs") -> str:
    """
    Gera o PDF do holerite e retorna o caminho do arquivo.

    :param payroll: objeto Payroll (SQLAlchemy model)
    :param employee: objeto Employee (SQLAlchemy model)
    :param output_dir: diretório onde salvar o PDF
    :return: caminho relativo do PDF gerado
    """
    os.makedirs(output_dir, exist_ok=True)

    filename = (
        f"holerite_{employee.id}_{payroll.competence_year}"
        f"_{payroll.competence_month:02d}.pdf"
    )
    filepath = os.path.join(output_dir, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )

    styles = getSampleStyleSheet()
    story = []

    # ── Estilos personalizados ────────────────────────────────────────────────
    title_style = ParagraphStyle(
        "Title", parent=styles["Heading1"],
        fontSize=16, textColor=colors.white,
        spaceAfter=2, alignment=TA_CENTER,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontSize=10, textColor=colors.white,
        alignment=TA_CENTER,
    )
    label_style = ParagraphStyle(
        "Label", parent=styles["Normal"],
        fontSize=8, textColor=colors.HexColor("#7f8c8d"),
    )
    value_style = ParagraphStyle(
        "Value", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#2c3e50"),
        fontName="Helvetica-Bold",
    )
    section_style = ParagraphStyle(
        "Section", parent=styles["Normal"],
        fontSize=9, textColor=colors.white,
        fontName="Helvetica-Bold",
        alignment=TA_LEFT,
    )

    # ── Cabeçalho ─────────────────────────────────────────────────────────────
    competence_str = f"{MONTHS_PT[payroll.competence_month]} / {payroll.competence_year}"
    header_data = [[
        Paragraph("HOLERITE DE PAGAMENTO", title_style),
        Paragraph(f"Competência: {competence_str}", subtitle_style),
    ]]
    header_table = Table(header_data, colWidths=["60%", "40%"])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_HEADER),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (0, 0), 10),
        ("RIGHTPADDING", (-1, -1), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4 * mm))

    # ── Dados do funcionário ──────────────────────────────────────────────────
    emp_data = [
        [
            _info_cell("Funcionário", employee.name, label_style, value_style),
            _info_cell("Cargo", employee.role, label_style, value_style),
            _info_cell("Admissão", str(employee.admission_date), label_style, value_style),
        ],
        [
            _info_cell("Salário Base", _fmt_brl(employee.salary), label_style, value_style),
            _info_cell("Dias Trabalhados", str(payroll.worked_days), label_style, value_style),
            _info_cell(
                "Horas Extras",
                f"{payroll.total_overtime_hours:.2f}h" if payroll.total_overtime_hours else "0,00h",
                label_style, value_style,
            ),
        ],
    ]
    emp_table = Table(emp_data, colWidths=["34%", "33%", "33%"])
    emp_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8f9fa")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dee2e6")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(emp_table)
    story.append(Spacer(1, 4 * mm))

    # ── Separar itens em créditos e débitos ───────────────────────────────────
    visible_items = [i for i in payroll.items if i.show_on_payslip]
    credits = [i for i in visible_items if i.is_credit]
    debits = [i for i in visible_items if not i.is_credit]

    # ── Tabela de benefícios ──────────────────────────────────────────────────
    if credits:
        story.append(_section_header("PROVENTOS / BENEFÍCIOS", COLOR_SUBHEADER, section_style))
        story.append(Spacer(1, 1 * mm))
        credit_rows = [["Descrição", "Tipo", "Valor"]]
        for item in credits:
            credit_rows.append([
                item.description,
                _fmt_item_type(item.item_type),
                _fmt_brl(item.amount),
            ])
        credit_table = Table(credit_rows, colWidths=["50%", "30%", "20%"])
        credit_table.setStyle(_item_table_style(COLOR_CREDIT_BG))
        story.append(credit_table)
        story.append(Spacer(1, 3 * mm))

    # ── Tabela de descontos ───────────────────────────────────────────────────
    if debits:
        story.append(_section_header("DESCONTOS", colors.HexColor("#c0392b"), section_style))
        story.append(Spacer(1, 1 * mm))
        debit_rows = [["Descrição", "Tipo", "Valor"]]
        for item in debits:
            debit_rows.append([
                item.description,
                _fmt_item_type(item.item_type),
                _fmt_brl(item.amount),
            ])
        debit_table = Table(debit_rows, colWidths=["50%", "30%", "20%"])
        debit_table.setStyle(_item_table_style(COLOR_DEBIT_BG))
        story.append(debit_table)
        story.append(Spacer(1, 3 * mm))

    # ── Totalizadores ─────────────────────────────────────────────────────────
    totals_style = ParagraphStyle(
        "Totals", parent=styles["Normal"],
        fontSize=9, fontName="Helvetica-Bold",
    )
    totals_net_style = ParagraphStyle(
        "TotalsNet", parent=styles["Normal"],
        fontSize=11, fontName="Helvetica-Bold",
        textColor=colors.white,
    )
    totals_data = [
        ["Salário Bruto", _fmt_brl(payroll.gross_salary)],
        ["Total Benefícios", _fmt_brl(payroll.total_benefits)],
        ["Total Descontos", f"- {_fmt_brl(payroll.total_discounts)}"],
    ]
    totals_table = Table(totals_data, colWidths=["70%", "30%"])
    totals_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_TOTAL_BG),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (0, 0), 8),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("RIGHTPADDING", (1, 0), (1, -1), 8),
    ]))
    story.append(totals_table)

    net_data = [["SALÁRIO LÍQUIDO", _fmt_brl(payroll.net_salary)]]
    net_table = Table(net_data, colWidths=["70%", "30%"])
    net_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_NET_BG),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (0, 0), 8),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("RIGHTPADDING", (1, 0), (1, -1), 8),
    ]))
    story.append(net_table)

    # ── Linha de assinatura ───────────────────────────────────────────────────
    story.append(Spacer(1, 12 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 2 * mm))

    payment_info = ""
    if payroll.payment_date:
        payment_info = f"Data de pagamento: {payroll.payment_date}"
    closed_info = ""
    if payroll.closed_at:
        closed_info = f"Fechado em: {payroll.closed_at.strftime('%d/%m/%Y %H:%M')}"

    footer_data = [
        [
            Paragraph(payment_info, label_style),
            Paragraph(closed_info, label_style),
        ],
        [
            Paragraph("_________________________\nAssinatura do Funcionário", label_style),
            Paragraph("_________________________\nAssinatura do Empregador", label_style),
        ],
    ]
    footer_table = Table(footer_data, colWidths=["50%", "50%"])
    footer_table.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    story.append(footer_table)

    doc.build(story)
    return filepath


# ── Helpers de layout ─────────────────────────────────────────────────────────

def _info_cell(label: str, value: str, label_style, value_style) -> Table:
    data = [[Paragraph(label, label_style)], [Paragraph(str(value or "—"), value_style)]]
    t = Table(data)
    t.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def _section_header(text: str, bg_color, style) -> Table:
    t = Table([[Paragraph(text, style)]], colWidths=["100%"])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_color),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def _item_table_style(row_bg):
    return TableStyle([
        # Cabeçalho
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_TABLE_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        # Linhas de dados
        ("BACKGROUND", (0, 1), (-1, -1), row_bg),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [row_bg, colors.white]),
        # Grid
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#bdc3c7")),
        # Alinhamento
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (0, -1), 8),
        ("RIGHTPADDING", (2, 0), (2, -1), 8),
    ])


def _fmt_item_type(item_type) -> str:
    labels = {
        "salario": "Salário",
        "vale_transporte": "VT",
        "auxilio": "Auxílio",
        "auxilio_familia": "Aux. Família",
        "bonificacao": "Bônus",
        "hora_extra": "H. Extra",
        "adicional": "Adicional",
        "decimo_terceiro_primeira": "13º (1ª)",
        "decimo_terceiro_segunda": "13º (2ª)",
        "ferias": "Férias",
        "inss": "INSS",
        "vale_desconto": "Vale",
        "falta": "Falta",
        "dsr": "DSR",
        "imposto_renda": "IR",
        "outros_desconto": "Outro Desc.",
        "outros_credito": "Outro Cred.",
    }
    val = item_type.value if hasattr(item_type, "value") else str(item_type)
    return labels.get(val, val)
