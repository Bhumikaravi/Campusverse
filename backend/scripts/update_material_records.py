import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

UPDATES = [
    {
        "filter": {"fileName": "med_cardio_hypertension_clinical_guide.pdf"},
        "set": {
            "mainCategory": "General Medicine",
            "subcategory": "Cardiology",
            "topic": "Hypertension",
            "department": "General Medicine"
        }
    },
    {
        "filter": {"fileName": "med_cardio_ecg_interpretation_handbook.pdf"},
        "set": {
            "mainCategory": "General Medicine",
            "subcategory": "Cardiology",
            "topic": "ECG interpretation",
            "department": "General Medicine"
        }
    },
    {
        "filter": {"fileName": "med_clinical_history_taking_framework.docx"},
        "set": {
            "mainCategory": "General Medicine",
            "subcategory": "General Medicine and Clinical Practice",
            "topic": "Patient history taking",
            "department": "General Medicine"
        }
    },
    {
        "filter": {"fileName": "med_respiratory_asthma_copd_guidelines.pdf"},
        "set": {
            "mainCategory": "General Medicine",
            "subcategory": "Respiratory Medicine",
            "topic": "Asthma",
            "department": "General Medicine"
        }
    },
    {
        "filter": {"fileName": "med_endocrine_diabetes_clinical_protocol.pdf"},
        "set": {
            "mainCategory": "General Medicine",
            "subcategory": "Endocrinology",
            "topic": "Diabetes mellitus",
            "department": "General Medicine"
        }
    },
    {
        "filter": {"fileName": "mgmt_corporate_finance_capital_budgeting.pdf"},
        "set": {
            "mainCategory": "Business and Management",
            "subcategory": "Financial Management",
            "topic": "Corporate Finance & Capital Budgeting",
            "department": "Business and Management"
        }
    },
    {
        "filter": {"fileName": "law_constitutional_fundamental_rights.pdf"},
        "set": {
            "mainCategory": "Law",
            "subcategory": "Constitutional Law",
            "topic": "Fundamental Rights & Constitutional Remedies",
            "department": "Law"
        }
    },
    {
        "filter": {"fileName": "sci_physics_newton_mechanics.pdf"},
        "set": {
            "mainCategory": "Science",
            "subcategory": "Physics",
            "topic": "Classical Mechanics & Newton's Laws",
            "department": "Science"
        }
    },
    {
        "filter": {"fileName": "comm_accounting_financial_reporting.pdf"},
        "set": {
            "mainCategory": "Commerce",
            "subcategory": "Accounting",
            "topic": "Corporate Financial Reporting Standards",
            "department": "Commerce"
        }
    },
    {
        "filter": {"fileName": "arts_psychology_cognitive_memory.pdf"},
        "set": {
            "mainCategory": "Arts and Humanities",
            "subcategory": "Psychology",
            "topic": "Cognitive Psychology & Memory",
            "department": "Arts and Humanities"
        }
    }
]

async def main():
    c = AsyncIOMotorClient("mongodb://localhost:27017/campusverse")
    db = c["campusverse"]
    for u in UPDATES:
        res = await db["materials"].update_one(
            {"originalName": u["filter"]["fileName"]},
            {"$set": u["set"]}
        )
        print(f"Updated {u['filter']['fileName']}: matched {res.matched_count}")

asyncio.run(main())
