import pandas as pd
import pdfplumber
import re
from collections import defaultdict

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT


# -------------------------
# 🔹 CLEAN TEXT
# -------------------------
def clean_text(text):
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9]', '', text)

    # 🔥 remove ending numbers
    text = re.sub(r'\d+$', '', text)

    return text


# -------------------------
# 🔹 TRAIN FROM EXCEL
# -------------------------
def train_from_excel(file_path):
    df = pd.read_excel(file_path, header=None)

    main_row = df.iloc[0]
    sub_row = df.iloc[1]

    mapping = []

    for col in df.columns:
        main = str(main_row[col]).strip()
        sub = str(sub_row[col]).strip()

        if main == 'nan' or sub == 'nan':
            continue

        variants = df.iloc[2:, col].dropna().tolist()
        clean_variants = [clean_text(v) for v in variants]

        mapping.append({
            "main": main.upper(),
            "sub": sub.upper(),
            "variants": clean_variants
        })

    return mapping


# -------------------------
# 🔹 EXTRACT FROM PDF
# -------------------------
def extract_from_pdf(pdf_path):
    data = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            lines = text.split("\n")

            for line in lines:
                match = re.search(r'([A-Za-z0-9.\- ]+)\s+(\d+)$', line.strip())
                if match:
                    sku = match.group(1).strip()
                    qty = int(match.group(2))
                    data.append((sku, qty))

    return data


# -------------------------
# 🔹 MATCH & GROUP
# -------------------------
def match_and_group(mapping, manifest_data):
    result = defaultdict(lambda: defaultdict(int))

    for raw_sku, qty in manifest_data:
        cleaned_sku = clean_text(raw_sku)

        matched = False

        for item in mapping:
            for variant in item["variants"]:

                if cleaned_sku.startswith(variant) or variant in cleaned_sku:

                    main = item["main"]
                    sub = item["sub"]

                    if main == sub:
                        result[main][main] += qty
                    else:
                        result[main][sub] += qty

                    matched = True
                    break

            if matched:
                break

    return result


# -------------------------
# 🔹 GENERATE PDF (FINAL FIX)
# -------------------------
def generate_pdf(result, output_path):
    doc = SimpleDocTemplate(output_path)
    styles = getSampleStyleSheet()

    left_title = ParagraphStyle(
        name="LeftTitle",
        parent=styles["Title"],
        alignment=TA_LEFT,
        fontSize=18,
        leading=24,
        fontName="Helvetica-Bold"
    )

    left_normal = ParagraphStyle(
        name="LeftNormal",
        parent=styles["Normal"],
        alignment=TA_LEFT,
        fontSize=15,
        leading=22,
        fontName="Helvetica"
    )

    elements = []
    total_qty = 0

    for main, subs in result.items():

        if len(subs) == 1 and list(subs.keys())[0] == main:
            qty = list(subs.values())[0]
            elements.append(Paragraph(f"<b>{main} → {qty}</b>", left_title))
            total_qty += qty
        else:
            elements.append(Paragraph(f"<b>{main}</b>", left_title))

            for sub, qty in subs.items():
                clean_sub = sub.replace(main, "").strip()
                if clean_sub == "":
                    clean_sub = sub

                elements.append(Paragraph(
                    f"&nbsp;&nbsp;&nbsp;{clean_sub} → {qty}",
                    left_normal
                ))
                total_qty += qty

        elements.append(Spacer(1, 22))

    # Footer
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("------------------------------", left_normal))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>Total Quantity: {total_qty}</b>", left_title))

    doc.build(elements)


# -------------------------
# 🔹 MAIN RUN (TEST)
# -------------------------
if __name__ == "__main__":
    excel_file = "mapping.xlsx"
    pdf_file = "input.pdf"
    output_file = "output.pdf"

    mapping = train_from_excel(excel_file)
    manifest_data = extract_from_pdf(pdf_file)
    result = match_and_group(mapping, manifest_data)

    generate_pdf(result, output_file)

    print("✅ PDF Generated Successfully!")