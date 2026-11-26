# SPDX-License-Identifier: AGPL-3.0-only
"""Render a fabricated laboratory report as a PNG (fictional lab and patient).
usage: make_labs.py OUT.png"""
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1100, 1400
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)


def font(size, bold=False):
    names = ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    for base in ("/usr/share/fonts/truetype/dejavu/", ""):
        for n in names:
            try:
                return ImageFont.truetype(base + n, size)
            except OSError:
                pass
    return ImageFont.load_default()


d.rectangle((0, 0, W, 120), fill="#1f3b63")
d.text((40, 28), "DEMO CLINICAL LABORATORY", fill="white", font=font(38, True))
d.text((40, 78), "Fictional laboratory - synthetic data for software demonstration", fill="#cfd8e6", font=font(20))
y = 150
for label, value in [("Patient", "Synthetic Patient 1182 (fictional)"), ("Sex / Age", "Male / 71"),
                     ("Collected", "2026-11-25 07:42 (Emergency Department)"), ("Ordering", "ED attending (demo)"),
                     ("Clinical note", "Cough, fever 39.1 C, dyspnea for 3 days")]:
    d.text((40, y), f"{label}:", fill="#333", font=font(22, True))
    d.text((260, y), value, fill="#111", font=font(22))
    y += 36
y += 16
rows = [("COMPLETE BLOOD COUNT", None, None, None),
        ("WBC", "18.4", "4.0-10.5 K/uL", "H"), ("Neutrophils", "89", "40-75 %", "H"), ("Lymphocytes", "6", "20-45 %", "L"),
        ("Hemoglobin", "12.1", "13.5-17.5 g/dL", "L"), ("Platelets", "412", "150-400 K/uL", "H"),
        ("BASIC METABOLIC PANEL", None, None, None),
        ("Sodium", "131", "135-145 mmol/L", "L"), ("Potassium", "4.6", "3.5-5.1 mmol/L", ""),
        ("BUN", "34", "7-20 mg/dL", "H"), ("Creatinine", "1.6", "0.7-1.3 mg/dL", "H"), ("Glucose", "164", "70-99 mg/dL", "H"),
        ("INFLAMMATION / SEPSIS", None, None, None),
        ("C-reactive protein", "214", "<10 mg/L", "H"), ("Procalcitonin", "3.8", "<0.5 ng/mL", "H"),
        ("Lactate", "2.9", "0.5-2.0 mmol/L", "H"),
        ("ARTERIAL BLOOD GAS (room air)", None, None, None),
        ("pH", "7.46", "7.35-7.45", "H"), ("pO2", "58", "80-100 mmHg", "L"), ("SpO2", "89", "95-100 %", "L")]
d.line((40, y, W - 40, y), fill="#1f3b63", width=2)
y += 10
for name, value, ref, flag in rows:
    if value is None:
        y += 10
        d.text((40, y), name, fill="#1f3b63", font=font(22, True))
        y += 36
        continue
    color = "#b00020" if flag else "#111"
    d.text((60, y), name, fill="#111", font=font(22))
    d.text((480, y), value, fill=color, font=font(22, True))
    d.text((600, y), flag, fill="#b00020", font=font(22, True))
    d.text((680, y), ref, fill="#555", font=font(20))
    y += 34
d.line((40, H - 80, W - 40, H - 80), fill="#999", width=1)
d.text((40, H - 64), "H = high, L = low. Values outside the reference range are shown in red.", fill="#555", font=font(18))
img.save(sys.argv[1])
print(sys.argv[1])
