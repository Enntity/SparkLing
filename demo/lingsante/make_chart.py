# SPDX-License-Identifier: AGPL-3.0-only
"""Write a fully synthetic six-year outpatient chart for one fictional patient.

Routine visits, vitals, labs and reports surround four problems that a
reviewer should catch:
  1. An incidental 9 mm right-upper-lobe nodule (CT 2021-03-18) whose
     recommended follow-up CT never happened.
  2. Lisinopril + spironolactone (2023-08) + ibuprofen 600 mg TID (2024-11):
     the "triple whammy" for acute kidney injury and hyperkalemia.
  3. Creatinine rising from 0.9 to 2.0 mg/dL, eGFR falling to 27, potassium
     climbing to 5.8 mmol/L.
  4. Metformin 1000 mg twice daily continued at eGFR 27.
No real person, clinic or record is depicted.
usage: make_chart.py OUT.txt"""
import random
import sys

rng = random.Random(20261125)
PATIENT = "Synthetic Patient 0417 (fictional), female, born 1957-04-02"


def vitals(year):
    sbp = rng.randint(128, 146) + (year - 2019)
    return (f"BP {sbp}/{rng.randint(74, 88)} mmHg, HR {rng.randint(66, 84)}, RR {rng.randint(14, 18)}, "
            f"T {rng.choice(['36.6', '36.7', '36.8', '36.9'])} C, SpO2 {rng.randint(95, 98)}% RA, "
            f"weight {rng.randint(81, 86)} kg")


# Kidney trajectory and potassium by date (creatinine mg/dL, eGFR, K mmol/L).
RENAL = {
    "2019-05-14": (0.9, 68, 4.2), "2019-11-20": (0.9, 68, 4.3), "2020-06-02": (0.95, 64, 4.3),
    "2020-12-09": (1.0, 60, 4.4), "2021-06-15": (1.0, 60, 4.4), "2021-12-07": (1.05, 57, 4.5),
    "2022-06-21": (1.1, 54, 4.5), "2022-12-13": (1.1, 54, 4.6), "2023-06-20": (1.2, 49, 4.7),
    "2023-10-03": (1.3, 44, 5.0), "2024-03-12": (1.4, 40, 5.1), "2024-09-24": (1.5, 37, 5.2),
    "2025-01-28": (1.8, 30, 5.6), "2025-04-15": (2.0, 27, 5.8),
}

MEDS_BASE = ["metformin 1000 mg PO twice daily", "lisinopril 20 mg PO daily", "atorvastatin 40 mg PO nightly",
             "aspirin 81 mg PO daily", "omeprazole 20 mg PO daily"]

FILLER_HPI = [
    "Reports good adherence to medications. Walking 20 minutes most days. Diet reviewed; trying to reduce portion sizes.",
    "Mild bilateral knee stiffness in the mornings, improves after 15 minutes. No falls. Sleeping 6-7 hours.",
    "No chest pain, no syncope. Occasional heartburn after large meals, controlled on omeprazole.",
    "Feels well. Daughter visiting from out of state. Asked about shingles vaccine.",
    "Home glucose readings mostly 120-160 fasting. No hypoglycemia symptoms reported.",
    "Some fatigue in the afternoons, attributes to poor sleep. No orthopnea. No PND.",
]
FILLER_ROS = ("Constitutional: no fever, no weight loss. Eyes: no vision change. ENT: no sore throat. "
              "Cardiovascular: no chest pain, no palpitations. Respiratory: no cough, no hemoptysis. "
              "GI: no nausea, no melena. GU: no dysuria. MSK: knee stiffness as above. "
              "Skin: no rash. Neuro: no focal weakness. Psych: mood good.")
FILLER_EXAM = ("General: well appearing, no distress. HEENT: normocephalic, oropharynx clear. Neck: supple, no JVD. "
               "Lungs: clear to auscultation bilaterally. Heart: regular rate and rhythm, no murmur. "
               "Abdomen: soft, non-tender. Extremities: trace bilateral ankle edema. Neuro: alert, oriented.")


ROUTINE = [
    lambda d, m: (f"\n--- PORTAL MESSAGE {d} ---\nPatient asks about refill timing and parking validation. Refills sent "
                  f"for {rng.choice(m)}. Reminder sent for annual eye exam and foot exam.\n"),
    lambda d, m: (f"\n--- NURSE TELEPHONE NOTE {d} ---\nCalled to review home glucose log: fasting {rng.randint(112, 158)}, "
                  f"post-prandial {rng.randint(150, 210)}. No hypoglycemia. Reinforced carbohydrate counting and foot care. "
                  f"Patient verbalized understanding.\n"),
    lambda d, m: (f"\n--- PHYSICAL THERAPY NOTE {d} ---\nKnee program session {rng.randint(2, 11)} of 12. Quadriceps "
                  f"strengthening, gait training, stationary bike {rng.randint(8, 15)} minutes. Pain {rng.randint(2, 5)}/10 "
                  f"after session. Home exercise program updated. Tolerated well.\n"),
    lambda d, m: (f"\n--- MEDICATION RECONCILIATION {d} ---\nReviewed with patient at pharmacy counter:\n" +
                  "\n".join(f"  - {x}: taking as prescribed" for x in m) + "\nNo changes made.\n"),
    lambda d, m: (f"\n--- PREVENTIVE CARE {d} ---\nMammogram {rng.choice(['up to date', 'ordered'])}. Colonoscopy 2018 "
                  f"normal, repeat 2028. Diabetic eye exam: no retinopathy. Monofilament exam normal. Pneumococcal and "
                  f"shingles vaccines documented. Depression screen PHQ-2 negative.\n"),
    lambda d, m: (f"\n--- DIETITIAN NOTE {d} ---\nThirty-minute session on plate method, sodium under 2 g per day and "
                  f"label reading. Typical day reviewed: oatmeal, sandwiches, rice and chicken, fruit. Goal: "
                  f"{rng.choice(['two vegetable servings at dinner', 'replace soda with water', 'walk after dinner'])}.\n"),
    lambda d, m: (f"\n--- SOCIAL WORK NOTE {d} ---\nLives with husband in a two-story home; drives; volunteers at the "
                  f"library twice weekly. Medicare with supplemental plan. No financial barriers to medications reported. "
                  f"Advance directive on file; healthcare proxy is her daughter.\n"),
]


def routine(d, meds):
    return rng.choice(ROUTINE)(d, meds)


def labs(date, extra=True):
    cr, egfr, k = RENAL[date]
    rows = [f"  Sodium {rng.randint(136, 141)} mmol/L (135-145)", f"  Potassium {k} mmol/L (3.5-5.1)",
            f"  Chloride {rng.randint(99, 106)} mmol/L", f"  CO2 {rng.randint(22, 27)} mmol/L",
            f"  BUN {int(12 + (cr - 0.9) * 25)} mg/dL (7-20)", f"  Creatinine {cr} mg/dL (0.5-1.1)",
            f"  eGFR {egfr} mL/min/1.73m2 (>60)", f"  Glucose {rng.randint(118, 168)} mg/dL",
            f"  Calcium {rng.choice(['9.1', '9.3', '9.4'])} mg/dL"]
    if extra:
        rows += [f"  HbA1c {rng.choice(['7.1', '7.3', '7.4', '7.6'])} %", f"  WBC {rng.choice(['6.2', '6.8', '7.1'])} K/uL",
                 f"  Hemoglobin {rng.choice(['12.6', '12.9', '13.1'])} g/dL", f"  Platelets {rng.randint(210, 290)} K/uL",
                 f"  LDL {rng.randint(62, 88)} mg/dL", f"  ALT {rng.randint(14, 28)} U/L", f"  TSH {rng.choice(['1.8', '2.1', '2.4'])} mIU/L"]
    return f"LAB RESULTS {date}\n" + "\n".join(rows)


def visit(date, clinician, specialty, meds, assessment, extra_text=""):
    year = int(date[:4])
    return (f"\n=== OFFICE VISIT {date} | {specialty} | {clinician} ===\nPatient: {PATIENT}\n"
            f"HPI: {rng.choice(FILLER_HPI)} {rng.choice(FILLER_HPI)}\n{extra_text}"
            f"Review of systems: {FILLER_ROS}\nVitals: {vitals(year)}\nExam: {FILLER_EXAM}\n"
            f"Current medications:\n" + "\n".join(f"  - {m}" for m in meds) +
            f"\nAllergies: see allergy list\nAssessment and plan:\n{assessment}\n")


def main():
    out = []
    out.append(f"OUTPATIENT RECORD EXPORT (SYNTHETIC - FOR SOFTWARE DEMONSTRATION ONLY)\n{PATIENT}\n"
               "Problem list: type 2 diabetes mellitus; essential hypertension; hyperlipidemia; GERD; "
               "osteoarthritis of both knees; heart failure with reduced ejection fraction (added 2023).\n")
    out.append("\n=== ALLERGY LIST (entered 2019-05-14) ===\n  - PENICILLIN: anaphylaxis (throat swelling, hypotension) "
               "after IM penicillin G in 1984. Avoid all penicillins.\n  - Sulfa: rash (mild).\n")
    meds = list(MEDS_BASE)
    dates = sorted(RENAL)
    for i, d in enumerate(dates):
        if d == "2023-10-03":
            meds = meds + ["carvedilol 12.5 mg PO twice daily", "spironolactone 25 mg PO daily", "furosemide 20 mg PO daily"]
        if d == "2025-01-28" and "ibuprofen 600 mg PO three times daily" not in meds:
            meds = meds + ["ibuprofen 600 mg PO three times daily"]
        out.append(visit(d, rng.choice(["Dr. A. Rivera (PCP)", "N. Patel, NP (PCP)"]), "Primary care", meds,
                         "1. Type 2 diabetes: continue metformin 1000 mg twice daily. Recheck HbA1c in 6 months.\n"
                         "2. Hypertension: continue current regimen. Home BP log encouraged.\n"
                         "3. Hyperlipidemia: continue atorvastatin.\n4. Knee osteoarthritis: activity as tolerated.\n"
                         "Follow up in 6 months with labs."))
        out.append(labs(d, extra=i % 2 == 0))
        for _ in range(40):  # routine documentation that pads the chart
            out.append(routine(d, meds))
        if d == "2020-12-09":
            out.append("\n=== EMERGENCY DEPARTMENT NOTE 2020-12-29 ===\nChest pain after lifting boxes, reproducible on "
                       "palpation. Troponin negative x2. ECG sinus rhythm, no ischemic changes. Discharged with "
                       "acetaminophen. Musculoskeletal chest wall strain.\n")
        if d == "2021-06-15":
            out.append("\n=== RADIOLOGY REPORT: CT CHEST WITHOUT CONTRAST 2021-03-18 ===\nIndication: persistent cough "
                       "after viral illness.\nFindings: No consolidation. No effusion. Incidental 9 mm solid nodule in "
                       "the right upper lobe (series 3, image 47), smooth margins. Mild coronary calcification. "
                       "Small hiatal hernia.\nImpression: 1. No acute process. 2. 9 mm solid right upper lobe "
                       "pulmonary nodule. Per Fleischner guidance for a solid nodule of this size, recommend "
                       "follow-up CT chest in 3 months, then PET/CT or tissue sampling as indicated.\n")
            out.append("\n--- RESULT NOTE 2021-03-22 ---\nCT reviewed with patient by phone: no pneumonia, cough "
                       "likely post-viral. Continue supportive care.\n")
        if d == "2023-06-20":
            out.append("\n=== CARDIOLOGY CONSULT 2023-08-29 ===\nDyspnea on exertion. Echocardiogram: LVEF 35%, "
                       "global hypokinesis. Diagnosis: heart failure with reduced ejection fraction. Plan: start "
                       "carvedilol 12.5 mg twice daily, spironolactone 25 mg daily, furosemide 20 mg daily; continue "
                       "lisinopril. Recheck BMP in 1 week.\n")
        if d == "2024-09-24":
            out.append("\n=== ORTHOPEDICS VISIT 2024-11-12 ===\nBilateral knee osteoarthritis, worse on the right. "
                       "X-ray: moderate medial compartment narrowing. Plan: start ibuprofen 600 mg three times daily "
                       "with food, physical therapy referral, consider steroid injection if no improvement.\n")
    text = "".join(out)
    open(sys.argv[1], "w").write(text)
    print(len(text), "characters")


if __name__ == "__main__":
    main()
