import re
import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

from app.config import settings

logger = logging.getLogger("campusverse.academic_validator")

# ========================================================
# DOCUMENT TYPE CONSTANTS
# ========================================================
class AcademicDocType:
    # Allowed Academic Categories (Section 3)
    STUDY_NOTES = "STUDY_NOTES"
    LECTURE_NOTES = "LECTURE_NOTES"
    TEXTBOOK = "TEXTBOOK"
    TEXTBOOK_CHAPTER = "TEXTBOOK_CHAPTER"
    QUESTION_PAPER = "QUESTION_PAPER"
    ASSIGNMENT = "ASSIGNMENT"
    ASSIGNMENT_WORKSHEET = "ASSIGNMENT_WORKSHEET"
    LAB_MANUAL = "LAB_MANUAL"
    LAB_MANUAL_RECORD = "LAB_MANUAL_RECORD"
    EDUCATIONAL_PRESENTATION = "EDUCATIONAL_PRESENTATION"
    ACADEMIC_PRESENTATION = "ACADEMIC_PRESENTATION"
    EDUCATIONAL_REFERENCE = "EDUCATIONAL_REFERENCE"
    REFERENCE_MATERIAL = "REFERENCE_MATERIAL"

    # Strictly Prohibited / Non-Academic Categories (Section 1 & 3)
    CERTIFICATE = "CERTIFICATE"
    INTERNSHIP_CERTIFICATE = "INTERNSHIP_CERTIFICATE"
    RESUME = "RESUME"
    RESUME_CV = "RESUME_CV"
    JOB_APPLICATION = "JOB_APPLICATION"
    PLACEMENT_DOCUMENT = "PLACEMENT_DOCUMENT"
    PLACEMENT_RECRUITMENT = "PLACEMENT_RECRUITMENT"
    ID_IDENTITY_DOC = "ID_IDENTITY_DOC"
    
    # Financial Categories (Strictly Prohibited)
    FINANCIAL_DOCUMENT = "FINANCIAL_DOCUMENT"
    FEE_RECEIPT = "FEE_RECEIPT"
    PAYMENT_RECEIPT = "PAYMENT_RECEIPT"
    BANK_STATEMENT = "BANK_STATEMENT"
    INVOICE = "INVOICE"
    INVOICE_BILL = "INVOICE_BILL"

    # Non-Academic Lifestyle, Food, Entertainment & Personal
    COOKING_RECIPE = "COOKING_RECIPE"
    NON_ACADEMIC_LIFESTYLE = "NON_ACADEMIC_LIFESTYLE"
    EVENT_INVITATION = "EVENT_INVITATION"
    PERSONAL_DOCUMENT = "PERSONAL_DOCUMENT"
    PERSONAL_CORRESPONDENCE = "PERSONAL_CORRESPONDENCE"
    BUSINESS_MARKETING = "BUSINESS_MARKETING"
    ADMINISTRATIVE_DOCUMENT = "ADMINISTRATIVE_DOCUMENT"
    NON_ACADEMIC = "NON_ACADEMIC"
    UNRELATED_NON_ACADEMIC = "UNRELATED_NON_ACADEMIC"
    EMPTY_OR_UNREADABLE = "EMPTY_OR_UNREADABLE"
    CORRUPTED_OR_POOR_QUALITY = "CORRUPTED_OR_POOR_QUALITY"
    SUBJECT_MISMATCH = "SUBJECT_MISMATCH"

DOCUMENT_TYPE_LABELS = {
    AcademicDocType.STUDY_NOTES: "Lecture & Study Notes",
    AcademicDocType.LECTURE_NOTES: "Lecture & Study Notes",
    AcademicDocType.TEXTBOOK: "Textbook & Academic Chapter",
    AcademicDocType.TEXTBOOK_CHAPTER: "Textbook & Academic Chapter",
    AcademicDocType.QUESTION_PAPER: "Question Paper & Previous Year Questions",
    AcademicDocType.ASSIGNMENT: "Academic Assignment & Worksheet",
    AcademicDocType.ASSIGNMENT_WORKSHEET: "Academic Assignment & Worksheet",
    AcademicDocType.LAB_MANUAL: "Lab Manual & Practical Record",
    AcademicDocType.LAB_MANUAL_RECORD: "Lab Manual & Practical Record",
    AcademicDocType.EDUCATIONAL_PRESENTATION: "Academic Presentation & Slides",
    AcademicDocType.ACADEMIC_PRESENTATION: "Academic Presentation & Slides",
    AcademicDocType.EDUCATIONAL_REFERENCE: "Subject Reference & Study Guide",
    AcademicDocType.REFERENCE_MATERIAL: "Subject Reference & Study Guide",
    
    AcademicDocType.CERTIFICATE: "Certificate (Course / Participation / Academic)",
    AcademicDocType.INTERNSHIP_CERTIFICATE: "Internship Certificate & Employment Credential",
    AcademicDocType.RESUME: "Personal Resume / Curriculum Vitae",
    AcademicDocType.RESUME_CV: "Personal Resume / Curriculum Vitae",
    AcademicDocType.JOB_APPLICATION: "Job Application & Employment Document",
    AcademicDocType.PLACEMENT_DOCUMENT: "Placement & Recruitment Document",
    AcademicDocType.PLACEMENT_RECRUITMENT: "Placement & Recruitment Document",
    AcademicDocType.ID_IDENTITY_DOC: "Government / Personal ID Document",
    
    AcademicDocType.FINANCIAL_DOCUMENT: "Financial Document & Transaction Record",
    AcademicDocType.FEE_RECEIPT: "College / Tuition Fee Receipt",
    AcademicDocType.PAYMENT_RECEIPT: "Payment Receipt & Confirmation Slip",
    AcademicDocType.BANK_STATEMENT: "Bank Statement & Financial Account",
    AcademicDocType.INVOICE: "Commercial Invoice & Billing Receipt",
    AcademicDocType.INVOICE_BILL: "Commercial Invoice & Billing Receipt",

    AcademicDocType.COOKING_RECIPE: "Cooking Recipe & Food Preparation Guide",
    AcademicDocType.NON_ACADEMIC_LIFESTYLE: "Non-Academic Lifestyle Document (Food Menu / Shopping List / Travel / Diary)",
    AcademicDocType.EVENT_INVITATION: "Event Invitation & Personal Notice",
    AcademicDocType.PERSONAL_DOCUMENT: "Personal Letter / Application",
    AcademicDocType.PERSONAL_CORRESPONDENCE: "Personal Letter / Application",
    AcademicDocType.BUSINESS_MARKETING: "Business Proposal / Marketing Material",
    AcademicDocType.ADMINISTRATIVE_DOCUMENT: "Administrative Form / Confirmation Slip",
    AcademicDocType.NON_ACADEMIC: "Unrelated Non-Academic Document",
    AcademicDocType.UNRELATED_NON_ACADEMIC: "Unrelated Non-Academic Document",
    AcademicDocType.EMPTY_OR_UNREADABLE: "Empty or Unreadable Document",
    AcademicDocType.CORRUPTED_OR_POOR_QUALITY: "Corrupted or Low-Quality Document",
    AcademicDocType.SUBJECT_MISMATCH: "Subject Mismatched Document",
}

DEFAULT_ALLOWED_TYPES = [
    AcademicDocType.STUDY_NOTES,
    AcademicDocType.LECTURE_NOTES,
    AcademicDocType.TEXTBOOK,
    AcademicDocType.TEXTBOOK_CHAPTER,
    AcademicDocType.QUESTION_PAPER,
    AcademicDocType.ASSIGNMENT,
    AcademicDocType.ASSIGNMENT_WORKSHEET,
    AcademicDocType.LAB_MANUAL,
    AcademicDocType.LAB_MANUAL_RECORD,
    AcademicDocType.EDUCATIONAL_PRESENTATION,
    AcademicDocType.ACADEMIC_PRESENTATION,
    AcademicDocType.EDUCATIONAL_REFERENCE,
    AcademicDocType.REFERENCE_MATERIAL,
]

DEFAULT_RESTRICTED_TYPES = [
    AcademicDocType.CERTIFICATE,
    AcademicDocType.INTERNSHIP_CERTIFICATE,
    AcademicDocType.RESUME,
    AcademicDocType.RESUME_CV,
    AcademicDocType.JOB_APPLICATION,
    AcademicDocType.PLACEMENT_DOCUMENT,
    AcademicDocType.PLACEMENT_RECRUITMENT,
    AcademicDocType.ID_IDENTITY_DOC,
    AcademicDocType.FINANCIAL_DOCUMENT,
    AcademicDocType.FEE_RECEIPT,
    AcademicDocType.PAYMENT_RECEIPT,
    AcademicDocType.BANK_STATEMENT,
    AcademicDocType.INVOICE,
    AcademicDocType.INVOICE_BILL,
    AcademicDocType.COOKING_RECIPE,
    AcademicDocType.NON_ACADEMIC_LIFESTYLE,
    AcademicDocType.EVENT_INVITATION,
    AcademicDocType.PERSONAL_DOCUMENT,
    AcademicDocType.PERSONAL_CORRESPONDENCE,
    AcademicDocType.BUSINESS_MARKETING,
    AcademicDocType.ADMINISTRATIVE_DOCUMENT,
    AcademicDocType.NON_ACADEMIC,
    AcademicDocType.UNRELATED_NON_ACADEMIC,
    AcademicDocType.EMPTY_OR_UNREADABLE,
    AcademicDocType.CORRUPTED_OR_POOR_QUALITY,
    AcademicDocType.SUBJECT_MISMATCH,
]

DEFAULT_ADMIN_RULES = {
    "strictValidationEnabled": True,
    "minRelevanceThreshold": 0.40,
    "minConfidenceThreshold": 0.70,
    "minQualityThreshold": 0.50,
    "autoRejectPersonalDocs": True,
    "requireSubjectMatch": True,
    "allowedCategories": DEFAULT_ALLOWED_TYPES,
    "restrictedCategories": DEFAULT_RESTRICTED_TYPES,
}

# ========================================================
# STUDENT-FACING REJECTION TEMPLATES (STRICT FILTER ALIGNED)
# ========================================================
STUDENT_MESSAGES = {
    AcademicDocType.RESUME: (
        "Upload rejected. CampusVerse only accepts academic study materials. This document appears to be a personal resume."
    ),
    AcademicDocType.RESUME_CV: (
        "Upload rejected. CampusVerse only accepts academic study materials. This document appears to be a personal resume."
    ),
    AcademicDocType.COOKING_RECIPE: (
        "Upload rejected. This document contains cooking-related content rather than academic study material."
    ),
    AcademicDocType.INTERNSHIP_CERTIFICATE: (
        "Upload rejected. Internship certificates and employment documents are not accepted as study materials."
    ),
    AcademicDocType.CERTIFICATE: (
        "Upload rejected. Internship certificates and employment documents are not accepted as study materials."
    ),
    AcademicDocType.JOB_APPLICATION: (
        "Upload rejected. Job applications and employment-related documents are not accepted as academic study materials."
    ),
    AcademicDocType.PLACEMENT_DOCUMENT: (
        "Upload rejected. Internship certificates and employment documents are not accepted as study materials."
    ),
    AcademicDocType.PLACEMENT_RECRUITMENT: (
        "Upload rejected. Internship certificates and employment documents are not accepted as study materials."
    ),
    AcademicDocType.FEE_RECEIPT: (
        "Upload rejected. This document has been identified as a college fee receipt or financial payment record, not academic study material. "
        "CampusVerse accepts only relevant academic resources such as study notes, textbooks, question papers, assignments and educational materials. "
        "Please upload a valid study document."
    ),
    AcademicDocType.FINANCIAL_DOCUMENT: (
        "Upload rejected. Financial documents, payment receipts, invoices and bank statements are not permitted in the CampusVerse academic study-material library."
    ),
    AcademicDocType.PAYMENT_RECEIPT: (
        "Upload rejected. Financial documents, payment receipts, invoices and bank statements are not permitted in the CampusVerse academic study-material library."
    ),
    AcademicDocType.BANK_STATEMENT: (
        "Upload rejected. Financial documents, payment receipts, invoices and bank statements are not permitted in the CampusVerse academic study-material library."
    ),
    AcademicDocType.INVOICE: (
        "Upload rejected. Financial documents, payment receipts, invoices and bank statements are not permitted in the CampusVerse academic study-material library."
    ),
    AcademicDocType.INVOICE_BILL: (
        "Upload rejected. Financial documents, payment receipts, invoices and bank statements are not permitted in the CampusVerse academic study-material library."
    ),
    AcademicDocType.NON_ACADEMIC_LIFESTYLE: (
        "Upload rejected. CampusVerse only accepts academic study materials. Non-academic content (menus, shopping lists, travel itineraries, diaries) is not permitted."
    ),
    AcademicDocType.EVENT_INVITATION: (
        "Upload rejected. CampusVerse only accepts academic study materials. Event invitations and personal letters are not accepted."
    ),
    AcademicDocType.ID_IDENTITY_DOC: (
        "Upload rejected. Identity cards and personal identification documents are strictly prohibited on CampusVerse for student privacy and security. Please upload study notes."
    ),
    AcademicDocType.PERSONAL_DOCUMENT: (
        "Upload rejected. CampusVerse only accepts academic study materials. This document appears to be a random personal or unrelated document."
    ),
    AcademicDocType.PERSONAL_CORRESPONDENCE: (
        "Upload rejected. CampusVerse only accepts academic study materials. Personal correspondence and applications are not accepted."
    ),
    AcademicDocType.BUSINESS_MARKETING: (
        "Upload rejected. Business proposals and marketing materials are not academic learning materials. Please upload university notes or course references."
    ),
    AcademicDocType.ADMINISTRATIVE_DOCUMENT: (
        "Upload rejected. Administrative forms, submission confirmations and non-academic documents cannot be published on CampusVerse. Please upload your actual course study materials."
    ),
    AcademicDocType.NON_ACADEMIC: (
        "Upload rejected. CampusVerse only accepts academic study materials. This document appears to be a random personal or unrelated document."
    ),
    AcademicDocType.UNRELATED_NON_ACADEMIC: (
        "Upload rejected. CampusVerse only accepts academic study materials. This document appears to be a random personal or unrelated document."
    ),
    AcademicDocType.SUBJECT_MISMATCH: (
        "Subject Mismatch! The uploaded document does not match the selected subject ({subject}). Please choose the appropriate subject."
    ),
    AcademicDocType.CORRUPTED_OR_POOR_QUALITY: (
        "Upload rejected. The uploaded study material contains excessive errors, corrupted text or unreadable content. Please upload a clear and complete version."
    ),
    AcademicDocType.EMPTY_OR_UNREADABLE: (
        "Upload rejected. The uploaded file is empty or contains unreadable content. Please ensure the document contains clear, readable notes or textbook content and retry."
    ),
    "APPROVED": (
        "Academic Document Verified! The study material has been analyzed and confirmed as genuine academic content."
    ),
    "NEEDS_REVIEW": (
        "Verification Pending! We could not confidently determine whether this document contains sufficient academic material or if it contains mixed personal content. It has been sent for admin review."
    )
}

# ========================================================
# DETECTION PATTERNS & REGEXES
# ========================================================

# 1. Resume / CV indicators
RESUME_KEYWORDS = [
    r"\bcurriculum\s+vitae\b",
    r"\bresum[eé]\b",
    r"\bbio-?data\b",
    r"\bcareer\s+objective\b",
    r"\bprofessional\s+summary\b",
    r"\bwork\s+experience\b",
    r"\bemployment\s+history\b",
    r"\binternship\s+experience\b",
    r"\btechnical\s+skills\b",
    r"\bkey\s+skills\b",
    r"\blanguages\s+known\b",
    r"\bpersonal\s+details\b",
    r"\bdeclaration\s*:\s*i\s+hereby\s+declare\b",
    r"\bgithub\.com/[a-zA-Z0-9_-]+\b",
    r"\blinkedin\.com/in/[a-zA-Z0-9_-]+\b",
    r"\bdate\s+of\s+birth\s*:\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    r"\bphone\s*:\s*(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
]

RESUME_STRUCTURED_HEADINGS = [
    r"\b(career\s+objective|professional\s+summary|profile\s+summary|summary\s+of\s+qualifications)\s*[:\n]",
    r"\b(work\s+experience|professional\s+experience|employment\s+history|internship\s+experience)\s*[:\n]",
    r"\b(educational\s+qualifications?|academic\s+background|education)\s*[:\n]",
    r"\b(technical\s+skills?|key\s+skills?|core\s+competencies|technologies)\s*[:\n]",
    r"\b(academic\s+projects?|personal\s+projects?|projects\s+undertaken|projects)\s*[:\n]",
    r"\b(certifications?|courses\s+and\s+certifications?)\s*[:\n]",
    r"\b(achievements?|honors?\s+and\s+awards?)\s*[:\n]",
    r"\b(personal\s+details?|personal\s+profile)\s*[:\n]",
    r"\bdeclaration\s*:\s*i\s+hereby\s+declare\b"
]

RESUME_SECTION_HEADERS = [
    "education", "experience", "skills", "projects", "certifications",
    "achievements", "interests", "hobbies", "declaration", "objective",
    "personal details", "strengths", "languages"
]

# 2. Certificate Conferral & Award Action Phrases (addressed to an individual recipient)
CONFERRAL_PHRASES = [
    r"\bthis\s+is\s+to\s+certify\s+that\b",
    r"\bis\s+to\s+certify\s+that\b",
    r"\bcertifies\s+that\b",
    r"\bhas\s+successfully\s+completed\b",
    r"\bsuccessfully\s+completed\s+(the\s+)?(course|training|internship|workshop|program|programme|masterclass|bootcamp|summit|symposium|module)\b",
    r"\bhas\s+completed\s+the\s+(course|training|internship|workshop|program|programme)\b",
    r"\bis\s+hereby\s+awarded\b",
    r"\bhereby\s+awarded\b",
    r"\bhereby\s+confer(s)?\s+(upon)?\b",
    r"\bconferred\s+upon\b",
    r"\bthis\s+certificate\s+is\s+presented\s+to\b",
    r"\bproudly\s+presented\s+to\b",
    r"\bpresented\s+to\s*[:\n]\b",
    r"\bawarded\s+to\s*[:\n]\b",
    r"\bin\s+recognition\s+of\s+(his|her|their)?\s*(successful\s+)?(completion|participation|dedication|achievement|excellence|contribution)\b",
    r"\bin\s+appreciation\s+of\s+(his|her|their)?\s*(participation|dedication|service|contribution)\b",
    r"\bhas\s+participated\s+in\b",
    r"\bparticipated\s+in\s+(the|active)\b",
    r"\bhas\s+successfully\s+attended\b",
    r"\bhas\s+attended\s+the\b",
    r"\bawarded\s+for\s+successful\s+completion\b",
    r"\bpresented\s+in\s+appreciation\s+of\b",
    r"\bcompleted\s+the\s+internship\b",
    r"\bcompleted\s+the\s+training\b",
    r"\bcertificate\s+of\s+(completion|participation|appreciation|excellence|achievement|merit|attendance|recognition)\b"
]

# 3. Certificate Issuance Metadata & Identification
ISSUANCE_METADATA_PATTERNS = [
    r"\bcompletion\s+date\s*[:\n]?\b",
    r"\bdate\s+of\s+completion\s*[:\n]?\b",
    r"\bdate\s+of\s+issue\s*[:\n]?\b",
    r"\bissue\s+date\s*[:\n]?\b",
    r"\bdate\s+of\s+achievement\s*[:\n]?\b",
    r"\bawarded\s+on\s*[:\n]?\b",
    r"\bvalid\s+(until|through)\s*[:\n]?\b",
    r"\bvalidity\s+period\b",
    r"\bcertificate\s+(no|number|id)\s*[:#]?\b",
    r"\bcredential\s+(id|identifier|number|verification)\s*[:#]?\b",
    r"\bverification\s+url\s*[:\n]?\b",
    r"\bissued\s+by\s*[:\n]\b",
    r"\blicensed\s+by\b",
    r"\boffered\s+by\b",
    r"\bconducted\s+by\b",
    r"\borganized\s+by\b"
]

# 4. Signatures & Official Seals
SIGNATURE_AND_SEAL_PATTERNS = [
    r"\bauthori[sz]ed\s+signat(ory|ure)\b",
    r"\bdirector('s)?\s+signat(ory|ure)\b",
    r"\bhead\s+of\s+(the\s+)?institution\b",
    r"\bdean\s+of\s+(academic\s+affairs|students|faculty|student\s+affairs)?\b",
    r"\bhead\s+of\s+department\b",
    r"\bconvener\b",
    r"\borganizing\s+secretary\b",
    r"\bco-?ordinator\b",
    r"\binstitutional\s+seal\b",
    r"\bofficial\s+seal\b",
    r"\bseal\s+affixed\b",
    r"\baffix\s+seal\b",
    r"\bvice\s+chancellor\b",
    r"\bchancellor\b",
    r"\bfounder\s+(&|and)\s+ceo\b",
    r"\bchief\s+learning\s+officer\b",
    r"\bmanaging\s+director\b"
]

# 5. Cybersecurity / Scientific "Digital Certificate" Study Concepts (PKI / SSL)
CYBERSECURITY_CERT_STUDY_PATTERNS = [
    r"\bdigital\s+certificate(s)?\b",
    r"\bssl(/tls)?\s+certificate(s)?\b",
    r"\btls\s+certificate(s)?\b",
    r"\bx\.?509(\s+certificate)?\b",
    r"\bpublic\s+key\s+infrastructure\b",
    r"\bpki\b",
    r"\bcertificate\s+authority\b",
    r"\broot\s+ca\b",
    r"\bintermediate\s+ca\b",
    r"\bcertificate\s+revocation\s+list\b",
    r"\bcrl\b",
    r"\bocsp\b",
    r"\bself-signed\s+certificate(s)?\b",
    r"\bwildcard\s+certificate(s)?\b",
    r"\bclient\s+certificate(s)?\b",
    r"\bcertificate\s+signing\s+request\b",
    r"\bcsr\b"
]

# 6. ID and Identity cards
ID_DOC_PATTERNS = [
    r"\bgovernment\s+of\s+india\b",
    r"\bunique\s+identification\s+authority\s+of\s+india\b",
    r"\baadhaar\b",
    r"\buidai\b",
    r"\b\d{4}\s\d{4}\s\d{4}\b",  # Aadhaar format 12 digits
    r"\bincome\s+tax\s+department\b",
    r"\bpermanent\s+account\s+number\b",
    r"\bpan\s+card\b",
    r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",  # PAN format
    r"\belection\s+commission\s+of\s+india\b",
    r"\bvoter\s+(id|identity\s+card)\b",
    r"\bdriving\s+licen[cs]e\b",
    r"\brepublic\s+of\s+india\s+passport\b",
    r"\bstudent\s+identity\s+card\b",
    r"\bemployee\s+id\s+card\b",
    r"\bblood\s+group\s*:\s*[abodeABODE+-]+\b"
]

# 7. Comprehensive Financial Document & Receipt Patterns
COLLEGE_FEE_RECEIPT_PATTERNS = [
    r"\b(fee|fees|tuition|admission|examination|exam|hostel|mess|transport|bus|library|lab|laboratory|semester|term|registration|caution\s+deposit)\s+(receipt|challan|voucher|counterfoil|slip)\b",
    r"\bcollege\s+(fee|fees)\s+receipt\b",
    r"\b(tuition|admission|examination|exam|hostel|mess)\s+fee\b",
    r"\bfee\s+(details|breakdown|particulars|structure|collected)\b",
    r"\bparticulars\s+of\s+fee\b",
    r"\bfee\s+challan\b",
    r"\bfees\s+once\s+paid\b",
    r"\b(student|office|college|bank|parent|counterfoil|institute)\s+copy\b",
    r"\breceived\s+(with\s+thanks\s+from|from)\b",
    r"\breceived\s+a?\s*sum\s+of\b",
    r"\bthe\s+sum\s+of\s+rupees\b",
    r"\b(cashier|accountant|accounts\s+officer|accounts\s+clerk|cashier's)\s+signat(ure|ory)\b",
    r"\bseal\s+(&|and)\s+signature\s+of\s+cashier\b",
    r"\bfee\s+counter\b",
    r"\bcounter\s+signature\b",
    r"\bpaid\s+stamp\b",
    r"\breceived\s+stamp\b"
]

PAYMENT_AND_TRANSACTION_PATTERNS = [
    r"\b(payment|cash|money|donation|refund|acknowledgement|deposit|transaction)\s+receipt\b",
    r"\breceipt\s+(no|number|#|id|code)\s*[:#]?\b",
    r"\brcpt\s+(no|number|#)\s*[:#]?\b",
    r"\btransaction\s+(id|no|number|ref|reference|date)\s*[:#]?\b",
    r"\btxn\s+(id|no|number|ref|reference)\s*[:#]?\b",
    r"\bpayment\s+(id|reference|mode|status|date|successful|completed|confirmation)\b",
    r"\bmode\s+of\s+payment\s*:\b",
    r"\bpayment\s+mode\s*:\s*(cash|cheque|dd|upi|card|online|net\s+banking)\b",
    r"\butr\s*(no|number)?\s*[:#]?\b",
    r"\brrn\s*(no|number)?\s*[:#]?\b",
    r"\bupi\s+ref(erence)?\s+(no|number|id)\b",
    r"\bupi\s+transaction\s+id\b",
    r"\b(google\s+pay|phonepe|paytm|bhim\s+upi|razorpay|stripe\s+receipt|paypal\s+receipt|billdesk|payu)\b",
    r"\bpayment\s+successful\b",
    r"\bpayment\s+completed\b",
    r"\bpaid\s+successfully\b",
    r"\bpaid\s+by\s*[:\n]\b",
    r"\bpaid\s+to\s*[:\n]\b",
    r"\bamount\s+paid\s*[:\n]?\b",
    r"\b(total|net)\s+paid\s*[:\n]?\b",
    r"\bamount\s+due\s*[:\n]?\b",
    r"\bbalance\s+(amount|due)\s*[:\n]?\b",
    r"\boutstanding\s+balance\b",
    r"\bamount\s+in\s+words\s*[:\n]?\b",
    r"\brupees\s+in\s+words\s*[:\n]?\b"
]

LMS_SUBMISSION_RECEIPT_PATTERNS = [
    r"\b(submission|assignment|assessment|project|exam|quiz)\s+(receipt|confirmation|acknowledgement|slip)\b",
    r"\byour\s+submission\s+was\s+successful\b",
    r"\bsubmission\s+was\s+successful\b",
    r"\bsubmission\s+(status\s*:\s*)?successful\b",
    r"\bsuccessfully\s+submitted\b",
    r"\bsubmission\s+(id|no|number|timestamp|details|hash|code)\s*[:#]?\b",
    r"\bconfirmation\s+(number|no|code|id)\s*[:#]?\b",
    r"\bturnitin\s+digital\s+receipt\b",
    r"\bcanvas\s+submission\s+receipt\b",
    r"\bblackboard\s+submission\s+receipt\b",
    r"\bmoodle\s+submission\s+receipt\b"
]

BANK_STATEMENT_AND_SALARY_PATTERNS = [
    r"\b(bank|account)\s+statement\b",
    r"\bstatement\s+of\s+account\b",
    r"\baccount\s+number\s*[:#]?\s*\d+\b",
    r"\ba/c\s+no\s*[:#]?\s*\d+\b",
    r"\b(opening|closing|available|ledger)\s+balance\b",
    r"\b(withdrawal|deposit|debit|credit)\s+amount\b",
    r"\b(salary\s+slip|payslip|pay\s+slip)\b",
    r"\b(gross|net)\s+salary\b",
    r"\b(basic\s+pay|provident\s+fund|pf\s+deduction|hra|esi)\b",
    r"\bform\s+16\b"
]

COMMERCIAL_INVOICE_AND_BILL_PATTERNS = [
    r"\btax\s+invoice\b",
    r"\bretail\s+invoice\b",
    r"\bcommercial\s+invoice\b",
    r"\bproforma\s+invoice\b",
    r"\bbill\s+of\s+supply\b",
    r"\bbill\s+(no|number|date)\s*[:#]?\b",
    r"\binvoice\s+(no|number|date)\s*[:#]?\b",
    r"\bbill\s+to\b",
    r"\bbilled\s+to\b",
    r"\bship\s+to\b",
    r"\bshipped\s+to\b",
    r"\bsold\s+by\s*[:\n]\b",
    r"\bcash\s+memo\b",
    r"\bsales\s+receipt\b",
    r"\bpos\s+receipt\b",
    r"\bstore\s+receipt\b",
    r"\bgstin\s*:\s*[0-9a-z]{15}\b",
    r"\bcgst\b",
    r"\bsgst\b",
    r"\bigst\b",
    r"\b(subtotal|sub\s+total|grand\s+total|total\s+amount|amount\s+payable|net\s+payable|balance\s+due)\b",
    r"\bchange\s+due\b",
    r"\btendered\s*[:\n]?\b",
    r"\bcard\s+ending\s+in\s+\d{4}\b",
    r"\bauth\s+code\s*[:#]?\b",
    r"\bterms\s+and\s+conditions\s+of\s+sale\b",
    r"\belectricity\s+bill\b",
    r"\bwater\s+bill\b",
    r"\bbroadband\s+bill\b",
    r"\btelephone\s+bill\b",
    r"\bgas\s+bill\b",
    r"\brent\s+receipt\b",
    r"\bmaintenance\s+bill\b",
    r"\bbooking\s+receipt\b"
]

ALL_FINANCIAL_PATTERNS = (
    COLLEGE_FEE_RECEIPT_PATTERNS +
    PAYMENT_AND_TRANSACTION_PATTERNS +
    LMS_SUBMISSION_RECEIPT_PATTERNS +
    BANK_STATEMENT_AND_SALARY_PATTERNS +
    COMMERCIAL_INVOICE_AND_BILL_PATTERNS
)

ALL_RECEIPT_AND_INVOICE_PATTERNS = ALL_FINANCIAL_PATTERNS
INVOICE_PATTERNS = ALL_FINANCIAL_PATTERNS
FEE_AND_PAYMENT_RECEIPT_PATTERNS = COLLEGE_FEE_RECEIPT_PATTERNS
TRANSACTION_AND_DIGITAL_PAYMENT_PATTERNS = PAYMENT_AND_TRANSACTION_PATTERNS

def is_academic_discussion_of_finance(text: str, lower_text: str) -> bool:
    """
    Intelligently determines whether the document IS a financial document / receipt
    or merely an academic textbook / study note DISCUSSING accounting, financial receipts,
    or banking protocols as a learning topic (Section 4 compliant).
    """
    # 1. Real personal transaction markers (present in real receipts, NEVER in textbooks)
    has_personal_transaction = bool(re.search(
        r"\b(student\s+copy|office\s+copy|bank\s+copy|cashier\s+signat|counter\s+signat|"
        r"received\s+with\s+thanks\s+from|your\s+submission\s+was\s+successful|"
        r"payment\s+successful|paid\s+to\s*[:\n]|transaction\s+id\s*[:#]|receipt\s+no\s*[:#]|"
        r"utr\s*(no)?\s*[:#]|rrn\s*[:#]|fees\s+once\s+paid|particulars\s+of\s+fee)\b",
        lower_text
    ))
    if has_personal_transaction:
        return False

    # 2. Pedagogical structure of textbooks and study materials
    has_pedagogical_framing = bool(re.search(
        r"\b(chapter|unit|module|lecture|semester|assignment)(\s*[-:]\s*|\s*)(\d+|[ivxlcdm]+|[a-z])\b|"
        r"\b(learning\s+objectives|review\s+questions|exercises\s*:|discussion\s+questions|"
        r"textbook|syllabus|course\s+outline)\b",
        lower_text
    ))

    # 3. Third-person educational exposition
    has_conceptual_exposition = bool(re.search(
        r"\b(definition\s*:|is\s+defined\s+as|refers\s+to\s+the|is\s+an\s+instrument|"
        r"accounting\s+principles|double-entry|ledger\s+accounts|journal\s+entry|"
        r"financial\s+accounting|principles\s+of\s+accounting|payment\s+system\s+architecture|"
        r"cryptographic\s+payment|electronic\s+payment\s+systems|how\s+invoices\s+work|"
        r"difference\s+between\s+(a\s+)?(cash\s+memo|receipt|invoice))\b",
        lower_text
    ))

    words = text.split()
    return (has_pedagogical_framing or has_conceptual_exposition) and len(words) >= 60

# 8. Personal letters & correspondence
LETTER_PATTERNS = [
    r"\bdear\s+(sir|madam|mr\.|mrs\.|ms\.)\b",
    r"\bto\s+whom\s+it\s+may\s+concern\b",
    r"\bsubject\s*:\s*(leave\s+application|application\s+for|resignation\s+letter|request\s+for\s+leave)\b",
    r"\bapplication\s+for\s+the\s+post\s+of\b",
    r"\bi\s+am\s+writing\s+to\s+apply\s+for\b",
    r"\bkindly\s+grant\s+me\s+leave\b",
    r"\brental\s+agreement\b",
    r"\btenancy\s+agreement\b"
]

# 6. Business proposals & Marketing
MARKETING_PATTERNS = [
    r"\bbusiness\s+proposal\b",
    r"\bexecutive\s+summary\s+for\s+investors\b",
    r"\bpitch\s+deck\b",
    r"\bmarketing\s+strategy\s+and\s+plan\b",
    r"\btarget\s+market\s+demographics\b",
    r"\breturn\s+on\s+investment\s*\(roi\)\b",
    r"\bnon-disclosure\s+agreement\b",
    r"\bconfidentiality\s+agreement\b"
]

# 7. Placement / Recruitment / Job Offer Letters
PLACEMENT_OFFER_PATTERNS = [
    r"\boffer\s+of\s+employment\b",
    r"\bemployment\s+offer\b",
    r"\bpleased\s+to\s+offer\s+you\b",
    r"\bappointment\s+letter\b",
    r"\bletter\s+of\s+intent\b",
    r"\bcampus\s+placement\s+selection\b",
    r"\bannual\s+(ctc|package|salary)\b",
    r"\bcost\s+to\s+company\b",
    r"\bfixed\s+pay\s*:\b",
    r"\bvariable\s+pay\s*:\b",
    r"\bstipend\s+(of|per\s+month)\b",
    r"\bdate\s+of\s+joining\b",
    r"\bjoining\s+date\b",
    r"\breporting\s+date\b",
    r"\bprobation\s+period\b",
    r"\bcompensation\s+structure\b",
    r"\bterms\s+and\s+conditions\s+of\s+employment\b"
]

# 8. Cooking Recipes & Food Preparation Patterns
COOKING_RECIPE_PATTERNS = [
    r"\b(recipe|ingredients|cooking\s+time|prep\s+time|servings|serves\s*\d+)\b",
    r"\b(tablespoon[s]?|teaspoon[s]?|tbsp\.?|tsp\.?|cups?\s+of)\b",
    r"\b(preheat\s+(the\s+)?oven|bake\s+for|simmer\s+for|boil\s+for|stir\s+well|season\s+with\s+salt)\b",
    r"\b(pinch\s+of\s+salt|finely\s+chopped|olive\s+oil|garlic\s+cloves?|flour|sugar|butter|baking\s+powder)\b",
    r"\b(cook\s+over\s+medium\s+heat|bring\s+to\s+a\s+boil|garnish\s+with|golden\s+brown)\b",
    r"\b(chocolate\s+cake|pasta\s+sauce|curry\s+powder|chicken\s+breast|pan-fry|saut[eé])\b"
]

# 9. Non-Academic Lifestyle Patterns (Menus, Shopping Lists, Travel Itineraries, Personal Diaries)
LIFESTYLE_NON_ACADEMIC_PATTERNS = [
    r"\b(food\s+menu|restaurant\s+menu|starters|main\s+course|desserts?|beverages|drinks\s+menu)\b",
    r"\b(shopping\s+list|grocery\s+list|to-buy\s+list|items\s+to\s+buy)\b",
    r"\b(travel\s+itinerary|trip\s+itinerary|flight\s+booking|hotel\s+reservation|boarding\s+pass|sightseeing\s+tour)\b",
    r"\bday\s*\d+\s*:\s*(hotel|flight|arrival|tour|sightseeing|checkout)\b",
    r"\b(dear\s+diary|personal\s+diary|today\s+was\s+a\s+(good|bad|busy|wonderful)\s+day|my\s+personal\s+diary)\b",
    r"\b(movie\s+ticket|concert\s+ticket|cinema\s+hall|entertainment\s+show)\b"
]

# 10. Job Applications, Cover Letters, and Experience Letters
JOB_APPLICATION_PATTERNS = [
    r"\b(job\s+application|cover\s+letter|application\s+for\s+the\s+(post|position|role)\s+of)\b",
    r"\b(applying\s+for\s+the\s+(post|position|role|job)|i\s+am\s+writing\s+to\s+apply)\b",
    r"\b(please\s+find\s+my\s+enclosed\s+(resume|cv)|consider\s+my\s+candidature|consider\s+my\s+application)\b",
    r"\b(experience\s+letter|relieving\s+letter|service\s+certificate|internship\s+application)\b"
]

# 11. Event Invitations
EVENT_INVITATION_PATTERNS = [
    r"\b(cordially\s+invites?\s+you|invitation\s+to\s+attend|you\s+are\s+cordially\s+invited)\b",
    r"\b(wedding\s+invitation|birthday\s+party|anniversary\s+celebration|save\s+the\s+date)\b",
    r"\brsvp\s*[:\n]\b"
]

# Common English & academic vocabulary for readability and quality sanity checks
COMMON_ACADEMIC_VOCAB = {
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", "not", "on", "with",
    "he", "as", "you", "do", "at", "this", "but", "his", "by", "from", "they", "we", "say", "her",
    "she", "or", "an", "will", "my", "one", "all", "would", "there", "their", "what", "so", "up",
    "out", "if", "about", "who", "get", "which", "go", "me", "when", "make", "can", "like", "time",
    "no", "just", "him", "know", "take", "people", "into", "year", "your", "good", "some", "could",
    "them", "see", "other", "than", "then", "now", "look", "only", "come", "its", "over", "think",
    "also", "back", "after", "use", "two", "how", "our", "work", "first", "well", "way", "even",
    "new", "want", "because", "any", "these", "give", "day", "most", "us", "is", "are", "was", "were",
    "has", "had", "been", "being", "shall", "should", "may", "might", "must", "each", "every",
    "study", "notes", "lecture", "unit", "module", "chapter", "section", "part", "page", "questions",
    "question", "answer", "answers", "paper", "exam", "examination", "semester", "syllabus",
    "course", "subject", "topic", "department", "university", "college", "faculty", "student",
    "definition", "explain", "describe", "discuss", "analyze", "derive", "prove", "theorem",
    "formula", "algorithm", "method", "process", "system", "structure", "function", "concept",
    "model", "data", "information", "theory", "problem", "solution", "example", "exercise",
    "introduction", "summary", "conclusion", "reference", "diagram", "table", "graph", "figure",
    "marks", "points", "total", "time", "date", "instructions", "following", "given", "find",
    "calculate", "evaluate", "determine", "state", "write", "compare", "differentiate", "between",
    "types", "characteristics", "advantages", "disadvantages", "applications", "importance",
    "step", "steps", "principle", "principles", "law", "rule", "properties", "classification",
    "class", "object", "variable", "code", "program", "output", "input", "loop", "array", "binary",
    "matrix", "vector", "derivative", "integral", "equation", "value", "values", "domain", "range",
    "energy", "force", "mass", "circuit", "current", "voltage", "signal", "power", "network", "cell",
    "species", "organism", "chemical", "reaction", "compound", "physics", "chemistry", "biology", "math"
}

# 8. Academic Study Material Positive Indicators
ACADEMIC_INDICATORS = [
    r"\blecture(\s*[-:]\s*|\s*)(\d+|[ivxlcdm]+|[a-z])?\b",
    r"\blecture\s+(notes|series|outline|summary)\b",
    r"\bmodule(\s*[-:]\s*|\s*)(\d+|[ivxlcdm]+|[a-z])\b",
    r"\bunit(\s*[-:]\s*|\s*)(\d+|[ivxlcdm]+|[a-z])\b",
    r"\bchapter(\s*[-:]\s*|\s*)(\d+|[ivxlcdm]+|[a-z])\b",
    r"\bsyllabus\b",
    r"\btextbook\b",
    r"\bquestion\s+paper\b",
    r"\bexam(ination)?\b",
    r"\bsemester(\s*[-:]\s*|\s*)(\d+|[ivxlcdm]+|[a-z])\b",
    r"\bdefinition\s*:\b",
    r"\btheorem\b",
    r"\balgorithm\b",
    r"\bformula(s)?\b",
    r"\bderivation\b",
    r"\bproof\b",
    r"\bdiagram\b",
    r"\barchitecture\b",
    r"\bobjective\s+questions\b",
    r"\bmultiple\s+choice\s+questions\b",
    r"\bmarks\s*:\s*\d+\b",
    r"\bassignment(\s*[-:]\s*|\s*)(\d+|[ivxlcdm]+|[a-z])?\b",
    r"\blab\s+(manual|experiment|exercise|record)\b",
    r"\bprocedure\s*:\b",
    r"\bobservation\s*:\b",
    r"\bresult\s*:\b",
    r"\bkey\s+concepts\b",
    r"\bapplications\s*:\b",
    r"\badvantages\s*:\b",
    r"\bdisadvantages\s*:\b",
    r"\btime\s+complexity\b",
    r"\bspace\s+complexity\b",
    r"\bcomplexity\s+analysis\b",
    r"\bbest\s+case\b",
    r"\bworst\s+case\b",
    r"\bwe\s+study\b",
    r"\brecap\s*:\b",
    r"\boverview\b",
    r"\bintroduction\s+to\b"
]

# ========================================================
# STAGE 3: DOCUMENT QUALITY & ERROR DETECTION
# ========================================================

def evaluate_document_quality(
    text: str,
    ocr_applied: bool = False
) -> Tuple[float, bool, str, List[str]]:
    """
    STAGE 3: Document Quality and Error Detection.
    Inspects extracted text for:
    1. Short/empty content (< 15 words)
    2. Unprintable or corrupted binary noise characters
    3. Excessive meaningless or random keyboard-mashed text
    4. Vocabulary sanity (proportion of recognizable words)
    5. Excessive repetitive text loops / spam
    Distinguishes minor human spelling errors (< 10% errors) from severe corruption.
    Returns: (quality_score: float [0.0-1.0], is_acceptable: bool, primary_issue: str, issues_list: List[str])
    """
    clean_text = text.strip() if text else ""
    words = clean_text.split()
    total_words = len(words)
    issues = []

    # 1. Empty or nearly empty (< 15 words)
    if total_words < 15:
        return 0.0, False, "Document contains insufficient readable content (< 15 words).", ["insufficient_text_length"]

    # 2. Corrupted / binary non-printable characters check
    non_printable = sum(1 for c in clean_text if ord(c) < 32 and c not in ('\n', '\r', '\t'))
    if len(clean_text) > 0 and (non_printable / len(clean_text)) > 0.05:
        return 0.15, False, "Document contains corrupted binary characters or unreadable encoding.", ["corrupted_binary_characters"]

    # 3. Excessive symbol / non-alphanumeric noise ratio
    alpha_count = sum(1 for c in clean_text if c.isalnum())
    if len(clean_text) > 60 and (alpha_count / len(clean_text)) < 0.30:
        return 0.20, False, "Document contains excessive unreadable symbols or corrupted character noise.", ["excessive_symbol_noise"]

    # 4. Meaningless / Gibberish token analysis
    gibberish_count = 0
    clean_tokens = []
    for w in words:
        clean_w = re.sub(r"[^a-zA-Z]", "", w).lower()
        if not clean_w:
            continue
        clean_tokens.append(clean_w)
        # Check repeated character clusters (e.g. 'aaaaaa', 'zzzzzz')
        if re.search(r"([a-z])\1{4,}", clean_w):
            gibberish_count += 1
        # Check long consonant-only clusters (e.g. 'sdfghjkl', 'bcdfghjk')
        elif len(clean_w) >= 6 and not any(v in clean_w for v in "aeiouy"):
            gibberish_count += 1

    if total_words >= 30 and (gibberish_count / total_words) > 0.25:
        return 0.25, False, "Document contains extensive meaningless or keyboard-mashed text.", ["extensive_gibberish_text"]

    # 5. Vocabulary Sanity Check (English / Academic curriculum words)
    if clean_tokens and len(clean_tokens) >= 30:
        recognized_count = sum(
            1 for t in clean_tokens
            if t in COMMON_ACADEMIC_VOCAB or len(t) <= 2 or t.isdigit()
        )
        recognition_ratio = recognized_count / len(clean_tokens)
        if recognition_ratio < 0.18:
            return 0.25, False, "Document contains mostly meaningless, non-academic or scrambled text.", ["unrecognized_vocabulary_gibberish"]

    # 6. Repetitive Loop / Spam Detection
    lines = [line.strip().lower() for line in clean_text.split("\n") if len(line.strip()) > 15]
    if len(lines) >= 6:
        from collections import Counter
        counts = Counter(lines)
        most_common_line, count = counts.most_common(1)[0]
        if (count / len(lines)) > 0.45:
            return 0.25, False, "Document contains repetitive text spam loops.", ["excessive_repetition_spam"]

    # 7. Minor human spelling errors tolerance:
    # A genuine student document with minor typos will have recognition_ratio >= 0.60
    # and minimal noise, scoring 0.85 - 0.98.
    quality_score = 0.95
    if gibberish_count > 0:
        quality_score -= min(0.30, (gibberish_count / max(total_words, 1)) * 0.5)

    return round(quality_score, 2), True, "Document readability and structure pass quality requirements.", issues

# ========================================================
# CORE DETECTION ENGINE & FEATURE EXTRACTION
# ========================================================

def extract_document_features(text: str) -> Dict[str, Any]:
    """
    Extracts semantic patterns and indicator signals across the full document text:
    - conferral_signals: Action phrases indicating conferral or awarding
    - issuance_signals: Metadata like completion dates, credential IDs, issue dates
    - signature_signals: Authorized signatures, directors, deans, seals
    - resume_signals: Resume headers and keywords
    - placement_signals: Offer letters, CTC, salary, joining date
    - academic_signals: Educational structure (lecture notes, units, chapters, definitions, theorems)
    - cyber_study_signals: Cybersecurity / PKI / SSL concepts (digital certificates as study subject)
    - is_studying_certificates: True if studying digital certificates as an academic topic rather than being a credential
    - is_placement_question_bank: True if practice question bank / MCQs rather than an offer letter
    """
    lower_text = text.lower() if text else ""
    
    conferral_signals = []
    for pat in CONFERRAL_PHRASES:
        m = re.findall(pat, lower_text, re.IGNORECASE)
        if m:
            conferral_signals.append(pat.replace(r"\b", "").replace(r"\s+", " ").strip())
            
    issuance_signals = []
    for pat in ISSUANCE_METADATA_PATTERNS:
        m = re.findall(pat, lower_text, re.IGNORECASE)
        if m:
            issuance_signals.append(pat.replace(r"\b", "").replace(r"\s+", " ").strip())
            
    signature_signals = []
    for pat in SIGNATURE_AND_SEAL_PATTERNS:
        m = re.findall(pat, lower_text, re.IGNORECASE)
        if m:
            signature_signals.append(pat.replace(r"\b", "").replace(r"\s+", " ").strip())
            
    resume_signals = []
    for pat in RESUME_KEYWORDS:
        if re.search(pat, lower_text, re.IGNORECASE):
            resume_signals.append(pat.replace(r"\b", "").replace(r"\s+", " ").strip())
            
    placement_signals = []
    for pat in PLACEMENT_OFFER_PATTERNS:
        if re.search(pat, lower_text, re.IGNORECASE):
            placement_signals.append(pat.replace(r"\b", "").replace(r"\s+", " ").strip())
            
    academic_signals = []
    for pat in ACADEMIC_INDICATORS:
        if re.search(pat, lower_text, re.IGNORECASE):
            academic_signals.append(pat.replace(r"\b", "").replace(r"\s+", " ").strip())
            
    cyber_study_signals = []
    for pat in CYBERSECURITY_CERT_STUDY_PATTERNS:
        if re.search(pat, lower_text, re.IGNORECASE):
            cyber_study_signals.append(pat.replace(r"\b", "").replace(r"\s+", " ").strip())
            
    # Check if this is an academic study of digital certificates (e.g. PKI / SSL notes)
    # Signs: has cyber study signals, academic signals (unit/chapter/definition/review questions),
    # and lacks personal conferral verbs ("is hereby awarded", "certifies that John Doe") or authorized signatures
    has_individual_award = bool(re.search(
        r"\b(this\s+is\s+to\s+certify\s+that|is\s+hereby\s+awarded|presented\s+to\s*[:\n]|awarded\s+to\s*[:\n]|has\s+successfully\s+completed)\b",
        lower_text
    ))
    
    is_studying_certificates = (
        len(cyber_study_signals) >= 1
        and len(academic_signals) >= 1
        and not has_individual_award
        and len(signature_signals) == 0
    )
    
    # Check if placement material is actually a question bank / practice test
    # Signs: questions, multiple choice options (A, B, C, D), marks, solutions
    has_exam_structure = bool(re.search(
        r"\b(question\s*\d+|q\d+\.|mcq|choose\s+the\s+correct|marks\s*:\s*\d+|practice\s+(questions|test|set|problems))\b",
        lower_text
    ))
    is_placement_question_bank = bool(
        has_exam_structure and ("placement" in lower_text or "interview" in lower_text or "aptitude" in lower_text)
    )

    receipt_signals = []
    for pat in ALL_RECEIPT_AND_INVOICE_PATTERNS:
        if re.search(pat, lower_text, re.IGNORECASE):
            receipt_signals.append(pat.replace(r"\b", "").replace(r"\s+", " ").strip())

    recipe_signals = []
    for pat in COOKING_RECIPE_PATTERNS:
        if re.search(pat, lower_text, re.IGNORECASE):
            recipe_signals.append(pat.replace(r"\b", "").replace(r"\s+", " ").strip())

    lifestyle_signals = []
    for pat in LIFESTYLE_NON_ACADEMIC_PATTERNS:
        if re.search(pat, lower_text, re.IGNORECASE):
            lifestyle_signals.append(pat.replace(r"\b", "").replace(r"\s+", " ").strip())

    job_app_signals = []
    for pat in JOB_APPLICATION_PATTERNS:
        if re.search(pat, lower_text, re.IGNORECASE):
            job_app_signals.append(pat.replace(r"\b", "").replace(r"\s+", " ").strip())

    invitation_signals = []
    for pat in EVENT_INVITATION_PATTERNS:
        if re.search(pat, lower_text, re.IGNORECASE):
            invitation_signals.append(pat.replace(r"\b", "").replace(r"\s+", " ").strip())

    return {
        "conferral_signals": conferral_signals,
        "issuance_signals": issuance_signals,
        "signature_signals": signature_signals,
        "resume_signals": resume_signals,
        "placement_signals": placement_signals,
        "academic_signals": academic_signals,
        "cyber_study_signals": cyber_study_signals,
        "receipt_signals": receipt_signals,
        "recipe_signals": recipe_signals,
        "lifestyle_signals": lifestyle_signals,
        "job_app_signals": job_app_signals,
        "invitation_signals": invitation_signals,
        "is_studying_certificates": is_studying_certificates,
        "is_placement_question_bank": is_placement_question_bank
    }

def detect_document_type_from_content(
    text: str,
    title: str = "",
    filename: str = "",
    ocr_applied: bool = False,
    pages_text: Optional[List[str]] = None
) -> Tuple[str, float, List[str], str, Dict[str, Any]]:
    """
    DEEP DOCUMENT CONTENT ANALYSIS & CLASSIFICATION ENGINE
    Examines words, phrases, sentences, structure, purpose, and page context across the entire document.
    Prioritizes actual text content over filename.
    Returns: (document_type, confidence, matched_indicators, primary_reason, semantic_profile)
    """
    clean_text = text.strip() if text else ""
    words = clean_text.split()
    total_words = len(words)
    lower_text = clean_text.lower()
    lower_title = title.lower() if title else ""
    page_count = len(pages_text) if pages_text else (1 if total_words > 0 else 0)

    # 1. Feature Extraction across full document content
    feats = extract_document_features(clean_text)

    # Compile semantic profile dictionary matching Section 6 requirements
    semantic_profile: Dict[str, Any] = {
        "overall_purpose": "",
        "detected_important_phrases": [],
        "certificate_indicators": feats["conferral_signals"] + feats["issuance_signals"] + feats["signature_signals"],
        "resume_indicators": feats["resume_signals"],
        "placement_indicators": feats["placement_signals"],
        "academic_indicators": feats["academic_signals"],
        "receipt_indicators": feats.get("receipt_signals", []),
        "cyber_study_indicators": feats["cyber_study_signals"],
        "is_studying_certificates": feats["is_studying_certificates"],
        "total_words": total_words,
        "page_count": page_count,
        "ocr_applied": ocr_applied
    }

    # Aggregate detected important phrases
    important_phrases = []
    important_phrases.extend(feats["conferral_signals"][:3])
    important_phrases.extend(feats["issuance_signals"][:3])
    important_phrases.extend(feats["signature_signals"][:3])
    important_phrases.extend(feats["academic_signals"][:4])
    important_phrases.extend(feats["cyber_study_signals"][:3])
    important_phrases.extend(feats["placement_signals"][:2])
    semantic_profile["detected_important_phrases"] = list(dict.fromkeys(important_phrases))

    # Check 1: Empty or Unreadable Document (< 15 words)
    if total_words < 15:
        semantic_profile["overall_purpose"] = "Empty or unreadable file containing insufficient text."
        return (
            AcademicDocType.EMPTY_OR_UNREADABLE,
            0.98,
            ["insufficient_text_length", f"words_extracted_{total_words}"],
            "Document contains insufficient readable content (< 15 words).",
            semantic_profile
        )

    # Check 1b: Severe binary/corrupted unprintable characters
    non_printable = sum(1 for c in clean_text if ord(c) < 32 and c not in ('\n', '\r', '\t'))
    if len(clean_text) > 0 and (non_printable / len(clean_text)) > 0.05:
        semantic_profile["overall_purpose"] = "Corrupted file containing raw binary or unreadable character noise."
        return (
            AcademicDocType.CORRUPTED_OR_POOR_QUALITY,
            0.95,
            ["corrupted_binary_characters"],
            "Document contains corrupted binary characters or unreadable encoding.",
            semantic_profile
        )

    # ========================================================
    # STAGE 1: PROHIBITED DOCUMENT TYPES DETECTION
    # ========================================================

    # Check 2: Personal ID Documents (Aadhaar, PAN, Passport, Voter, Student ID)
    id_matches = [p for p in ID_DOC_PATTERNS if re.search(p, lower_text, re.IGNORECASE)]
    if id_matches:
        has_gov_id = any("aadhaar" in p or "pan" in p or "government of india" in p or "unique identification" in p or "\\d{4}" in p for p in id_matches)
        if has_gov_id or len(id_matches) >= 2:
            semantic_profile["overall_purpose"] = "Official government identification document."
            return (
                AcademicDocType.ID_IDENTITY_DOC,
                0.98,
                ["government_id_pattern", *[p[:30] for p in id_matches[:3]]],
                "Detected government identity credentials (Aadhaar / PAN / Identity document) in file content.",
                semantic_profile
            )

    # Check 2b: Cooking Recipes & Culinary Instructions
    recipe_matches = [p for p in COOKING_RECIPE_PATTERNS if re.search(p, lower_text, re.IGNORECASE)]
    has_recipe_terms = any(k in lower_text for k in ["ingredients", "cooking time", "prep time", "tablespoon", "teaspoon", "preheat oven", "servings:", "serves ", "recipe:"])
    if (has_recipe_terms and len(recipe_matches) >= 2) or len(recipe_matches) >= 3 or ("recipe" in lower_text and ("ingredients" in lower_text or "tablespoon" in lower_text or "bake for" in lower_text)):
        semantic_profile["overall_purpose"] = "Culinary cooking recipe containing ingredients, food preparation instructions, and culinary steps."
        return (
            AcademicDocType.COOKING_RECIPE,
            0.98,
            ["cooking_recipe_pattern", *[p[:25] for p in recipe_matches[:3]]],
            "Detected cooking recipe with culinary ingredients and food preparation steps.",
            semantic_profile
        )

    # Check 2c: Non-Academic Lifestyle (Food Menus, Shopping Lists, Travel Itineraries, Personal Diaries)
    lifestyle_matches = [p for p in LIFESTYLE_NON_ACADEMIC_PATTERNS if re.search(p, lower_text, re.IGNORECASE)]
    if lifestyle_matches:
        semantic_profile["overall_purpose"] = "Non-academic lifestyle document (food menu, shopping list, travel itinerary, or personal diary)."
        return (
            AcademicDocType.NON_ACADEMIC_LIFESTYLE,
            0.96,
            ["non_academic_lifestyle_pattern", *[p[:30] for p in lifestyle_matches[:3]]],
            "Detected non-academic lifestyle content (food menu, shopping list, travel itinerary, or personal diary).",
            semantic_profile
        )

    # Check 2d: Job Applications, Cover Letters, Experience Letters
    job_app_matches = [p for p in JOB_APPLICATION_PATTERNS if re.search(p, lower_text, re.IGNORECASE)]
    if job_app_matches:
        semantic_profile["overall_purpose"] = "Job application, cover letter, or employment correspondence."
        return (
            AcademicDocType.JOB_APPLICATION,
            0.96,
            ["job_application_pattern", *[p[:30] for p in job_app_matches[:3]]],
            "Detected formal job application, cover letter, or employment correspondence.",
            semantic_profile
        )

    # Check 2e: Event Invitations & Social Notices
    invitation_matches = [p for p in EVENT_INVITATION_PATTERNS if re.search(p, lower_text, re.IGNORECASE)]
    if invitation_matches:
        semantic_profile["overall_purpose"] = "Personal or social event invitation."
        return (
            AcademicDocType.EVENT_INVITATION,
            0.95,
            ["event_invitation_pattern", *[p[:30] for p in invitation_matches[:2]]],
            "Detected personal or event invitation letter.",
            semantic_profile
        )

    # Check 3: Resume / CV Detection (Examining actual content, not filename)
    has_in_content_academic_heading = bool(re.search(
        r"\b(module|chapter|unit|lecture|semester|assignment)(\s*[-:]\s*|\s*)(\d+|[ivxlcdm]+|[a-z])\b|\b(syllabus|course\s+code|lecture\s+notes|textbook|curriculum)\b",
        lower_text
    ))
    has_pedagogical_content = bool(re.search(
        r"\b(definition\s*:|is\s+defined\s+as|refers\s+to\s+the|concept\s+of|architecture\s+of|principles\s+of|characteristics\s+of|advantages\s+and\s+disadvantages|classification\s+of|properties\s+of|types\s+of|steps\s+involved|complexity|time\s+complexity|space\s+complexity|algorithm|derivation|formula|theorem|we\s+study)\b",
        lower_text
    ))
    academic_keywords_in_doc = sum(1 for p in ACADEMIC_INDICATORS if re.search(p, lower_text, re.IGNORECASE))
    is_strong_academic_doc = has_in_content_academic_heading or (has_pedagogical_content and academic_keywords_in_doc >= 2) or (academic_keywords_in_doc >= 4)

    # Personal contact details specific to a candidate CV / Resume
    has_candidate_contact = bool(re.search(
        r"(\b\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b|"
        r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b|"
        r"\blinkedin\.com/in/[a-zA-Z0-9_-]+\b|"
        r"\bgithub\.com/[a-zA-Z0-9_-]+\b)",
        lower_text
    ))

    # Explicit resume / curriculum vitae / career statement indicators
    has_explicit_resume_phrase = bool(re.search(
        r"\b(curriculum\s+vitae|bio-?data)\b|^\s*resum[eé]\s*$|\bresum[eé]\s*[:\n]|\b(career\s+objective|professional\s+summary|profile\s+summary)\s*[:\n]|\bdeclaration\s*:\s*i\s+hereby\s+declare\b",
        lower_text,
        re.MULTILINE
    ))

    # Structured resume section headers (requiring heading colon or newline, NOT isolated dictionary words in prose)
    matched_structured_headers = [p for p in RESUME_STRUCTURED_HEADINGS if re.search(p, lower_text)]
    structured_header_count = len(matched_structured_headers)

    # Determine genuine resume:
    # 1. Non-academic document with structured resume headings and candidate contact info / explicit resume markers
    # 2. Even if disguised under an academic title, a true resume has candidate contact info + multiple resume sections + zero genuine pedagogy
    is_genuine_resume = False
    if not is_strong_academic_doc:
        if has_explicit_resume_phrase and (structured_header_count >= 1 or has_candidate_contact):
            is_genuine_resume = True
        elif has_candidate_contact and structured_header_count >= 2:
            is_genuine_resume = True
        elif structured_header_count >= 3:
            is_genuine_resume = True
    else:
        # Document has academic headings or pedagogy. It is ONLY classified as a resume if it is
        # unequivocally a candidate CV that merely mentions an academic keyword or course name
        if has_candidate_contact and structured_header_count >= 3 and has_explicit_resume_phrase and not has_pedagogical_content:
            is_genuine_resume = True

    if is_genuine_resume:
        semantic_profile["overall_purpose"] = "Personal curriculum vitae / resume detailing individual career history, education, and technical skills."
        return (
            AcademicDocType.RESUME_CV,
            0.96,
            ["resume_section_headers", f"matched_headers_{structured_header_count}", *[p[:25] for p in matched_structured_headers[:3]]],
            "Detected personal resume / curriculum vitae format with career history and contact details.",
            semantic_profile
        )

    # Check 4: Placement Offer Letters & Recruitment Documents
    if feats["placement_signals"] and not feats["is_placement_question_bank"]:
        if any(k in lower_text for k in ["pleased to offer you", "offer of employment", "appointment letter", "annual ctc", "cost to company", "date of joining"]):
            semantic_profile["overall_purpose"] = "Formal corporate employment offer and compensation package agreement."
            return (
                AcademicDocType.PLACEMENT_RECRUITMENT,
                0.96,
                ["placement_recruitment_offer", *feats["placement_signals"][:3]],
                "Detected campus placement selection offer / employment contract letter.",
                semantic_profile
            )

    # Check 5: Financial Documents, Receipts, Invoices, Fee Slips, and Financial Transactions
    # STRICTLY REJECT ALL RECEIPTS, BILLS, INVOICES, AND PAYMENT SLIPS
    is_finance_study = is_academic_discussion_of_finance(clean_text, lower_text)

    if not is_finance_study:
        lower_fname = (filename or "").lower()
        lower_tname = (title or "").lower()
        has_receipt_in_name = any(k in lower_fname or k in lower_tname for k in ["receipt", "challan", "fee", "invoice", "bill", "salary", "payslip", "statement"])

        has_fee_pattern = any(re.search(p, lower_text, re.IGNORECASE) for p in COLLEGE_FEE_RECEIPT_PATTERNS)
        has_lms_receipt = any(re.search(p, lower_text, re.IGNORECASE) for p in LMS_SUBMISSION_RECEIPT_PATTERNS) or ("your submission was successful" in lower_text)
        has_digital_pattern = any(re.search(p, lower_text, re.IGNORECASE) for p in PAYMENT_AND_TRANSACTION_PATTERNS)
        has_bank_pattern = any(re.search(p, lower_text, re.IGNORECASE) for p in BANK_STATEMENT_AND_SALARY_PATTERNS)
        has_commercial_pattern = any(re.search(p, lower_text, re.IGNORECASE) for p in COMMERCIAL_INVOICE_AND_BILL_PATTERNS)

        # Financial markers: currency symbols, amounts, and settlement status
        has_financial_markers = bool(re.search(
            r"(\b(rs\.?|inr|usd|\$|€|£)\s*[\d,]+|\b[\d,]+\s*(rs|inr)\b|\bamount\s*[:\n]?\s*[\d,]+|\btotal\s*(paid|amount)?\s*[:\n]?\s*[\d,]+|\bpaid\s*[:\n]?\s*[\d,]+|\bbalance\s*[:\n]?\s*[\d,]+)",
            lower_text
        ))
        has_fee_context = any(k in lower_text for k in ["tuition", "hostel", "admission", "examination fee", "exam fee", "mess fee", "college fee", "fee receipt", "fee challan", "accounts branch", "cashier signature"])

        receipt_matches = [p for p in ALL_RECEIPT_AND_INVOICE_PATTERNS if re.search(p, lower_text, re.IGNORECASE)]

        # 5a. College Fee Receipts (Tuition, Admission, Examination, Hostel, Mess, Fee Challan)
        if has_fee_pattern or (has_fee_context and (has_financial_markers or "receipt" in lower_text or "paid" in lower_text or has_receipt_in_name)):
            semantic_profile["overall_purpose"] = "College or institutional fee receipt detailing student tuition, hostel, exam, or admission fee payment."
            return (
                AcademicDocType.FEE_RECEIPT,
                0.98,
                ["college_fee_receipt_pattern", *[p[:30] for p in receipt_matches[:4]]],
                "Detected college fee receipt or student financial payment voucher in file content. CampusVerse accepts only genuine academic study notes.",
                semantic_profile
            )

        # 5b. LMS / Assignment / Course Submission Confirmation Slip
        if has_lms_receipt or (has_receipt_in_name and ("submission" in lower_text or "assessment" in lower_text or "course:" in lower_text or "project" in lower_text)):
            semantic_profile["overall_purpose"] = "Online course LMS assignment or assessment submission receipt confirmation slip."
            return (
                AcademicDocType.PAYMENT_RECEIPT,
                0.98,
                ["submission_confirmation_receipt", *[p[:30] for p in receipt_matches[:4]]],
                "Detected assignment/course submission receipt or confirmation slip in file content. CampusVerse accepts only substantive academic study materials.",
                semantic_profile
            )

        # 5c. Bank Statements & Salary Slips
        if has_bank_pattern or ("bank statement" in lower_text or "statement of account" in lower_text or "salary slip" in lower_text or "payslip" in lower_text):
            semantic_profile["overall_purpose"] = "Personal bank account financial statement or employee salary payslip."
            return (
                AcademicDocType.BANK_STATEMENT,
                0.98,
                ["bank_statement_salary_pattern", *[p[:30] for p in receipt_matches[:4]]],
                "Detected bank statement or salary slip in file content. Financial documents are strictly prohibited.",
                semantic_profile
            )

        # 5d. UPI, Digital Payment, and Transaction Receipts
        if has_digital_pattern and (has_financial_markers or len(receipt_matches) >= 2 or "payment" in lower_text or "paid" in lower_text or "upi" in lower_text):
            semantic_profile["overall_purpose"] = "Digital payment transaction receipt or electronic fund transfer confirmation."
            return (
                AcademicDocType.PAYMENT_RECEIPT,
                0.98,
                ["digital_payment_transaction_markers", *[p[:30] for p in receipt_matches[:4]]],
                "Detected digital payment receipt or online transaction record in file content.",
                semantic_profile
            )

        # 5e. Commercial Invoices, Bills, and Utility Slips
        if has_commercial_pattern and (has_financial_markers or len(receipt_matches) >= 2 or any(k in lower_text for k in ["tax invoice", "bill to", "gstin", "cash memo", "bill no", "invoice no", "total amount", "grand total"])):
            semantic_profile["overall_purpose"] = "Commercial tax invoice, retail purchase bill, or utility payment statement."
            return (
                AcademicDocType.INVOICE,
                0.98,
                ["commercial_invoice_billing_markers", *[p[:30] for p in receipt_matches[:4]]],
                "Detected commercial sales invoice or billing receipt in file content.",
                semantic_profile
            )

        # 5f. General Financial Document or Receipts
        if len(receipt_matches) >= 2 or (has_receipt_in_name and (has_financial_markers or "receipt" in lower_text or "transaction" in lower_text)):
            semantic_profile["overall_purpose"] = "Financial transaction document or payment voucher."
            return (
                AcademicDocType.FINANCIAL_DOCUMENT,
                0.98,
                ["financial_transaction_record", *[p[:30] for p in receipt_matches[:4]]],
                "Detected financial record or payment voucher in file content.",
                semantic_profile
            )

    # Check 6: Certificate Detection (Contextual & Semantic)
    # The AI recognizes certificate-related language even if the word 'certificate' is never used.
    # HOWEVER: If the document is studying digital certificates / PKI / SSL as a computer science topic
    # with definitions and review questions, it is NOT classified as a certificate!
    if not feats["is_studying_certificates"]:
        has_conferral = len(feats["conferral_signals"]) >= 1
        has_recipient_award = bool(re.search(r"\b(awarded\s+to\s*[:\n]|presented\s+to\s*[:\n]|conferred\s+upon\s*[:\n]|certify\s+that\s*[:\n]?)\b", lower_text))
        has_cert_title = bool(re.search(r"\bcertificate\s+of\s+(completion|participation|appreciation|excellence|achievement|merit|attendance|recognition)\b", lower_text))
        has_signatures = len(feats["signature_signals"]) >= 1
        has_issuance = len(feats["issuance_signals"]) >= 1

        is_cert = False
        cert_reason = ""

        if has_conferral or has_cert_title:
            is_cert = True
            cert_reason = "Detected credential conferral statement certifying individual course completion, training, or participation."
        elif has_recipient_award and (has_signatures or has_issuance):
            is_cert = True
            cert_reason = "Detected individual achievement award with issuance metadata and authorized signature."
        elif has_issuance and has_signatures and (total_words < 600 or ocr_applied):
            is_cert = True
            cert_reason = "Detected official certificate issuance details with credential ID, dates, and official signatures."
        elif ocr_applied and (has_conferral or has_cert_title or (has_signatures and "completion" in lower_text)):
            is_cert = True
            cert_reason = "Detected scanned credential document verified via OCR extraction."

        if is_cert:
            is_internship = bool(re.search(r"\b(internship|intern\b|industrial\s+training|summer\s+training|practical\s+training)\b", lower_text))
            doc_type = AcademicDocType.INTERNSHIP_CERTIFICATE if is_internship else AcademicDocType.CERTIFICATE
            semantic_profile["overall_purpose"] = (
                "Official internship credential certifying completion of industrial / practical training."
                if is_internship else
                "Official credential conferral certifying individual course completion, achievement, or event participation."
            )
            return (
                doc_type,
                0.97,
                ["certificate_credential_markers", *(feats["conferral_signals"] + feats["signature_signals"] + feats["issuance_signals"])[:4]],
                cert_reason,
                semantic_profile
            )

    # Check 7: Personal Letters / Leave Applications
    letter_matches = [p for p in LETTER_PATTERNS if re.search(p, lower_text, re.IGNORECASE)]
    if letter_matches and total_words < 500:
        if any(k in lower_text for k in ["leave application", "application for", "dear sir", "dear madam", "resignation letter"]):
            semantic_profile["overall_purpose"] = "Personal correspondence or formal leave/job application letter."
            return (
                AcademicDocType.PERSONAL_CORRESPONDENCE,
                0.92,
                ["personal_correspondence_pattern", *[p[:30] for p in letter_matches[:2]]],
                "Detected personal correspondence / formal leave or job application letter.",
                semantic_profile
            )

    # Check 8: Business Proposals & Marketing Materials
    marketing_matches = [p for p in MARKETING_PATTERNS if re.search(p, lower_text, re.IGNORECASE)]
    if len(marketing_matches) >= 2 or any(k in lower_text for k in ["business proposal", "pitch deck", "non-disclosure agreement"]):
        semantic_profile["overall_purpose"] = "Corporate business proposal or commercial marketing deck."
        return (
            AcademicDocType.BUSINESS_MARKETING,
            0.90,
            ["business_marketing_pattern", *[p[:30] for p in marketing_matches[:2]]],
            "Detected corporate business proposal or commercial marketing document.",
            semantic_profile
        )

    # ========================================================
    # STAGE 3: DOCUMENT QUALITY & ERROR DETECTION (FOR ACADEMIC CANDIDATES)
    # ========================================================
    quality_score, is_acceptable_quality, quality_reason, quality_issues = evaluate_document_quality(
        text=clean_text,
        ocr_applied=ocr_applied
    )

    if not is_acceptable_quality:
        semantic_profile["overall_purpose"] = "Severely degraded, corrupted, or unreadable document content."
        return (
            AcademicDocType.CORRUPTED_OR_POOR_QUALITY,
            0.95,
            quality_issues,
            quality_reason,
            semantic_profile
        )

    # ========================================================
    # STAGE 4: ACADEMIC STUDY MATERIAL IDENTIFICATION & PURPOSE SYNTHESIS
    # ========================================================
    academic_matches = [p for p in ACADEMIC_INDICATORS if re.search(p, lower_text, re.IGNORECASE)]

    # Sub-type classification for academic content
    is_pyq = bool(re.search(r"\b(previous\s+year|pyq|university\s+examination|semester\s+end\s+examination|model\s+question\s+paper|annual\s+examination)\b", lower_text))
    is_question_paper = is_pyq or feats["is_placement_question_bank"] or bool(re.search(r"\bquestion\s+paper\b|\bmaximum\s+marks\b|\btime\s*:\s*\d\s*hours\b|\bpart\s*[-–—]\s*[ab]\b|\banswer\s+all\s+questions\b", lower_text))
    is_lab_manual = bool(re.search(r"\blab\s+manual\b|\bpractical\s+record\b|\bexperiment\s+no\b|\bapparatus\s*:|\bprocedure\s*:", lower_text))
    is_assignment = bool(re.search(r"\bassignment(\s*[-:]\s*|\s*)(\d+|[ivxlcdm]+|[a-z])?\b|\bworksheet\b|\btutorial\s+sheet\b|\bproblem\s+set\b|\bdue\s+date\s*:", lower_text))
    is_textbook_chapter = bool(re.search(r"\bchapter(\s*[-:]\s*|\s*)(\d+|[ivxlcdm]+|[a-z])\b|\bsection\s*\d+\.\d+\b|\blearning\s+objectives\b|\bkey\s+terms\b|\bchapter\s+summary\b|\bexercises\s*:\b|\bdiscussion\s+questions\b", lower_text))
    is_presentation = bool(re.search(r"\bslide\s*\d+\b|\bagenda\b|\bpresentation\s+title\b", lower_text))

    if is_assignment:
        semantic_profile["overall_purpose"] = "Curriculum assignment worksheet containing problem sets and tutorial exercises."
        return (
            AcademicDocType.ASSIGNMENT_WORKSHEET,
            0.92,
            ["assignment_worksheet_markers", "problem_statements", *feats["academic_signals"][:3]],
            "Confirmed academic assignment or tutorial problem worksheet.",
            semantic_profile
        )
    elif is_question_paper:
        semantic_profile["overall_purpose"] = "Academic examination or practice question paper with structured evaluative problems."
        return (
            AcademicDocType.QUESTION_PAPER,
            0.94,
            ["examination_structure", "question_paper_markers", *feats["academic_signals"][:3]],
            "Confirmed academic examination / practice question paper format.",
            semantic_profile
        )
    elif is_lab_manual:
        semantic_profile["overall_purpose"] = "Laboratory manual detailing experimental apparatus, procedure, and observation records."
        return (
            AcademicDocType.LAB_MANUAL_RECORD,
            0.94,
            ["laboratory_manual_structure", "experiment_procedure_markers", *feats["academic_signals"][:3]],
            "Confirmed laboratory manual / practical experiment record.",
            semantic_profile
        )
    elif is_textbook_chapter:
        semantic_profile["overall_purpose"] = "Structured academic textbook chapter with conceptual curriculum sections and pedagogical review questions."
        return (
            AcademicDocType.TEXTBOOK_CHAPTER,
            0.93,
            ["textbook_chapter_structure", "curriculum_sections", *feats["academic_signals"][:3]],
            "Confirmed textbook chapter or structured academic reading material.",
            semantic_profile
        )

    # Special handling for cybersecurity digital certificate study notes
    if feats["is_studying_certificates"]:
        semantic_profile["overall_purpose"] = "Academic lecture notes explaining Public Key Infrastructure (PKI) and digital certificate concepts in network security."
        return (
            AcademicDocType.LECTURE_NOTES,
            0.94,
            ["cybersecurity_digital_certificate_study_concept", *feats["cyber_study_signals"][:3], *feats["academic_signals"][:3]],
            "Confirmed academic study notes explaining Public Key Infrastructure (PKI) and digital certificates.",
            semantic_profile
        )

    # Generic Lecture Notes & Reference Textbooks
    # Guard against short snippets or transaction/submission slips leaking into LECTURE_NOTES
    has_submission_or_trans_markers = bool(re.search(
        r"\b(submission\s+was\s+successful|your\s+submission\s+was|receipt\s*(no|number|#|id)\s*[:#]|"
        r"student\s+copy|office\s+copy|cashier\s+signat|transaction\s+id\s*[:#]|payment\s+successful|"
        r"paid\s+stamp|total\s+amount\s+paid\s*[:\n]?)\b",
        lower_text
    ))
    if has_submission_or_trans_markers:
        semantic_profile["overall_purpose"] = "Administrative submission slip or transaction record."
        return (
            AcademicDocType.ADMINISTRATIVE_DOCUMENT,
            0.95,
            ["administrative_transaction_marker"],
            "Document contains administrative submission confirmation or transaction markers rather than study notes.",
            semantic_profile
        )

    if total_words < 35 and not is_assignment and not is_question_paper:
        semantic_profile["overall_purpose"] = "Short fragment or note snippet lacking curriculum explanations."
        return (
            AcademicDocType.UNRELATED_NON_ACADEMIC,
            0.90,
            ["insufficient_study_content_length"],
            "Document is too brief (< 35 words) to constitute academic study material or lecture notes.",
            semantic_profile
        )

    has_academic_indicators = len(academic_matches) >= 1
    has_pedagogical_structure = bool(re.search(
        r"\b(lecture(\s*[-:]\s*|\s*)(\d+|[ivxlcdm]+|[a-z])?|definition\s*:|is\s+defined\s+as|refers\s+to\s+the|concept\s+of|architecture\s+of|principles\s+of|characteristics\s+of|workflow\s+of|advantages\s+and\s+disadvantages|classification\s+of|properties\s+of|types\s+of|steps\s+involved|complexity|time\s+complexity|space\s+complexity|best\s+case|worst\s+case|we\s+study|sorted\s+array)\b",
        lower_text
    ))
    has_instructional_content = (
        any(v in lower_text for v in ["is defined as", "refers to", "consists of", "is the process of", "algorithm", "formula", "derivation", "theorem", "methodology", "complexity", "time complexity", "space complexity"])
    )

    # Check for Mixed Document (Personal / Non-academic reflections mixed with academic notes)
    # Section 4: "If a document contains both academic and unrelated content:
    # Evaluate the proportion of meaningful academic content.
    # Reject documents primarily containing unrelated material.
    # For ambiguous cases, mark the document as 'Needs Review' rather than automatically approving it."
    has_personal_musings = bool(re.search(
        r"\b(dear\s+diary|today\s+i\s+went|my\s+personal\s+thoughts|today\s+i\s+felt|my\s+daily\s+routine|"
        r"my\s+favorite\s+movies|personal\s+journal|my\s+weekend|my\s+personal\s+life|personal\s+diary|"
        r"woke\s+up\s+and\s+felt|my\s+personal\s+blog|personal\s+reflections?)\b",
        lower_text
    ))
    if has_personal_musings:
        semantic_profile["overall_purpose"] = "Mixed document containing both personal reflections and academic study notes."
        return (
            AcademicDocType.STUDY_NOTES,
            0.50,  # Confidence below threshold (0.70) -> evaluates to NEEDS_REVIEW
            ["mixed_academic_and_personal_content"],
            "Document contains a mix of personal non-academic reflections and academic study notes. Needs review.",
            semantic_profile
        )

    if has_academic_indicators or has_pedagogical_structure or has_instructional_content:
        multi_page_desc = f" ({page_count} pages analyzed)" if page_count > 1 else ""
        semantic_profile["overall_purpose"] = f"Educational lecture study notes explaining academic concepts, definitions, and curriculum topics{multi_page_desc}."
        return (
            AcademicDocType.LECTURE_NOTES,
            0.92,
            ["academic_curriculum_text", *[p[:25] for p in academic_matches[:4]]],
            f"Confirmed genuine academic study notes / educational textbook content{multi_page_desc}.",
            semantic_profile
        )

    # Content lacks recognizable academic study notes or educational material
    semantic_profile["overall_purpose"] = "Document does not contain academic study notes, educational definitions, or curriculum learning material."
    return (
        AcademicDocType.UNRELATED_NON_ACADEMIC,
        0.90,
        ["lack_of_academic_study_notes"],
        "Content lacks recognizable academic study notes, curriculum explanations, or educational materials.",
        semantic_profile
    )

def calculate_subject_relevance(
    text: str,
    selected_subject: str,
    detected_subject: str = ""
) -> Tuple[float, bool, str]:
    """
    Computes subject relevance score between 0.0 and 1.0.
    Checks whether document content aligns with the stated academic subject.
    Detects severe cross-discipline mismatches (e.g. Calculus uploaded as Botany).
    """
    if not selected_subject or selected_subject.lower() in ["general", "all", "engineering"]:
        return 1.0, True, "General subject selection accepted."

    clean_subj = selected_subject.strip().lower()
    lower_text = text.lower()[:15000]

    # Exact or prominent subject name mention
    if clean_subj in lower_text:
        return 0.95, True, f"Document explicitly addresses '{selected_subject}'."

    # Subject token overlap
    subj_tokens = set(re.findall(r"\b[a-zA-Z]{3,}\b", clean_subj))
    subj_tokens -= {"and", "the", "for", "with", "from", "intro", "introduction", "systems", "studies", "science"}

    if not subj_tokens:
        return 0.85, True, "Subject keywords matched academic curriculum."

    matched_tokens = sum(1 for t in subj_tokens if t in lower_text)
    overlap_ratio = matched_tokens / len(subj_tokens)

    # Cross-discipline mismatch check
    # Example: Math terms in Biology subject or Medical terms in Computer Science
    DISCIPLINE_SIGNATURES = {
        "mathematics": ["calculus", "integral", "derivative", "matrix", "eigenvalue", "differential", "theorem", "polynomial", "algebra", "probability"],
        "computer science": ["algorithm", "programming", "database", "data structures", "compiler", "cpu", "python", "software", "binary", "neural network", "class", "object", "inheritance", "function", "code"],
        "biology": ["cell", "mitochondria", "organism", "dna", "genetics", "species", "photosynthesis", "bacteria", "anatomy", "tissue"],
        "chemistry": ["reaction", "molecule", "acid", "base", "compound", "periodic table", "oxidation", "polymer", "organic", "catalyst"],
        "physics": ["thermodynamics", "quantum", "velocity", "acceleration", "optics", "electromagnetism", "kinetic", "gravity", "force", "wavelength"]
    }

    # Find dominant discipline in document
    doc_discipline = None
    max_disc_hits = 0
    for disc, sigs in DISCIPLINE_SIGNATURES.items():
        hits = sum(1 for s in sigs if re.search(r"\b" + re.escape(s), lower_text))
        if hits > max_disc_hits:
            max_disc_hits = hits
            doc_discipline = disc

    # Check if selected subject belongs to a different discipline
    subj_discipline = None
    for disc, sigs in DISCIPLINE_SIGNATURES.items():
        if disc in clean_subj or any(re.search(r"\b" + re.escape(s), clean_subj) for s in sigs):
            subj_discipline = disc
            break

    if doc_discipline and subj_discipline and doc_discipline != subj_discipline and max_disc_hits >= 2:
        # Severe mismatch e.g. Mathematics document uploaded under Biology
        score = 0.15
        return (
            score,
            False,
            f"Subject Mismatch! The document appears to contain {doc_discipline.title()} material, which does not match the selected subject '{selected_subject}'."
        )

    if overlap_ratio >= 0.5:
        score = min(0.90, 0.50 + (overlap_ratio * 0.40))
        return score, True, f"Content aligns with '{selected_subject}' concepts."

    # Detected subject from classifier check
    if detected_subject and detected_subject.lower() != "unable to classify":
        if detected_subject.lower() in clean_subj or clean_subj in detected_subject.lower():
            return 0.85, True, f"Content matched detected subject '{detected_subject}'."

    # Low overlap but not necessarily completely foreign
    return 0.45, True, "Partial relevance to curriculum detected."

# ========================================================
# GEMINI AI ZERO-SHOT VALIDATION (HYBRID AUGMENTATION)
# ========================================================

async def call_gemini_academic_validator(
    text: str,
    title: str = "",
    filename: str = "",
    selected_subject: str = "",
    pages_text: Optional[List[str]] = None,
    ocr_applied: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Calls Gemini API to perform deep semantic document examination across all pages.
    Returns structured JSON with document type, overall purpose, indicators, and validation status.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return None

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        # Multi-page sample strategy: take excerpts from beginning, middle, and end
        page_count = len(pages_text) if pages_text else 1
        if pages_text and len(pages_text) > 1:
            sampled_text = f"--- PAGE 1 ---\n{pages_text[0][:2500]}\n\n"
            if len(pages_text) > 2:
                mid_idx = len(pages_text) // 2
                sampled_text += f"--- PAGE {mid_idx+1} (MIDDLE) ---\n{pages_text[mid_idx][:2500]}\n\n"
            sampled_text += f"--- PAGE {len(pages_text)} (LAST) ---\n{pages_text[-1][:2500]}"
        else:
            sampled_text = text[:8000]

        prompt = f"""You are the Chief Academic Integrity & Document Validation System for CampusVerse, a university study portal.
Your mission is to perform a deep semantic analysis of the entire uploaded document to decide whether it is genuine academic study material.

DOCUMENT METADATA:
Document Title: "{title}"
Filename: "{filename}"
Claimed Subject: "{selected_subject}"
Total Pages: {page_count}
OCR Applied: {ocr_applied}

DOCUMENT EXTRACTED CONTENT:
\"\"\"
{sampled_text}
\"\"\"

CRITICAL CLASSIFICATION RULES:
1. EXAMINE ACTUAL CONTENT & PURPOSE: Do not rely on filename or just the first few lines.
2. DETECT CERTIFICATES CONTEXTUALLY:
   - Identify certificates even if the word "certificate" is missing (e.g. "Awarded to...", "In recognition of successful completion...", dates, signatures, credential IDs).
   - If a certificate mentions "Python", "Machine Learning", or "AI", it is STILL a certificate, NOT study notes -> REJECT!
3. INTELLIGENT CONTEXT AWARENESS:
   - If a textbook or lecture notes discuss "Digital Certificates", "SSL/TLS", or "Public Key Infrastructure (PKI)" as a computer science topic with definitions and review questions, it is ACADEMIC STUDY MATERIAL -> APPROVE!
   - If a history or economics textbook mentions historical dates and government/institutional names, it is ACADEMIC STUDY MATERIAL -> APPROVE!
   - A campus placement aptitude question bank (with questions, MCQs, and marks) is ACADEMIC MATERIAL -> APPROVE!
   - An individual job/placement offer letter (with CTC, salary, joining date) is a PERSONAL EMPLOYMENT DOCUMENT -> REJECT!
4. STRICTLY REJECT ALL RECEIPTS, BILLS, INVOICES, AND PAYMENT SLIPS:
   - Reject college fee receipts, tuition receipts, payment slips, money receipts, cash memos, store receipts, UPI/transaction slips, ATM receipts, utility bills.
   - Even if a receipt mentions an educational institution (e.g. "College of Engineering - Fee Receipt"), it is STILL a financial receipt, NOT study notes -> REJECT as INVOICE_BILL!
5. ONLY NOTES AND CURRICULUM STUDY MATERIALS ARE ALLOWED:
   - Accept only genuine academic study notes, textbooks, question papers, syllabus, worksheets, and lab records.
   - Any document that lacks academic study content must be REJECTED!
6. REJECT RESUMES, IDS, INVOICES, AND MARKETING PROPOSALS.
7. STRICTLY REJECT COOKING RECIPES, MENUS, SHOPPING LISTS, DIARIES, AND TRAVEL ITINERARIES:
   - Recipes, restaurant menus, shopping lists, diaries, and travel itineraries are non-academic content -> REJECT as COOKING_RECIPE or NON_ACADEMIC_LIFESTYLE!
8. STRICTLY REJECT INTERNSHIP CERTIFICATES AND JOB APPLICATIONS:
   - Internship certificates and employment documents are not accepted as study materials -> REJECT as INTERNSHIP_CERTIFICATE or JOB_APPLICATION!
9. HANDLE MIXED DOCUMENTS:
   - If a document contains both academic and unrelated content, evaluate proportion. Ambiguous cases must be marked as NEEDS_REVIEW.
10. QUALITY CHECK: Minor spelling/grammar errors should be tolerated. Severe gibberish or corrupted noise should be rejected.

Respond ONLY with a valid JSON object matching this exact schema:
{{
  "is_academic": boolean,
  "document_type": "LECTURE_NOTES" | "TEXTBOOK_CHAPTER" | "QUESTION_PAPER" | "ASSIGNMENT_WORKSHEET" | "LAB_MANUAL_RECORD" | "ACADEMIC_PRESENTATION" | "REFERENCE_MATERIAL" | "RESUME_CV" | "CERTIFICATE" | "INTERNSHIP_CERTIFICATE" | "JOB_APPLICATION" | "PLACEMENT_RECRUITMENT" | "ID_IDENTITY_DOC" | "INVOICE_BILL" | "FEE_RECEIPT" | "COOKING_RECIPE" | "NON_ACADEMIC_LIFESTYLE" | "EVENT_INVITATION" | "PERSONAL_CORRESPONDENCE" | "BUSINESS_MARKETING" | "UNRELATED_NON_ACADEMIC" | "EMPTY_OR_UNREADABLE" | "CORRUPTED_OR_POOR_QUALITY" | "SUBJECT_MISMATCH",
  "validation_status": "APPROVED" | "REJECTED" | "NEEDS_REVIEW",
  "overall_purpose": "1-2 sentence description explaining the document's fundamental objective",
  "detected_important_phrases": ["phrase 1", "phrase 2"],
  "certificate_indicators": ["indicator 1", "indicator 2"],
  "resume_indicators": [],
  "placement_indicators": [],
  "academic_indicators": ["indicator 1", "indicator 2"],
  "subject_relevance_score": float between 0.0 and 1.0,
  "document_quality_score": float between 0.0 and 1.0,
  "confidence": float between 0.0 and 1.0,
  "detailed_reason": "Clear explanation of why it was approved or rejected",
  "student_message": "Friendly, direct student-facing message explaining the outcome"
}}
"""
        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "temperature": 0.0
                }
            ),
            timeout=4.5
        )

        import json
        res_data = json.loads(response.text.strip())
        return res_data
    except Exception as e:
        logger.warning("Gemini academic validator unavailable or failed: %s", e)
        return None

# ========================================================
# TOP-LEVEL VALIDATION PIPELINE
# ========================================================

def validate_document_relevance_sync(
    text: str,
    title: str = "",
    filename: str = "",
    selected_subject: str = "",
    pages_text: Optional[List[str]] = None,
    ocr_applied: bool = False,
    total_pages: Optional[int] = None,
    admin_rules: Optional[Dict[str, Any]] = None,
    ai_result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Synchronous Core Academic Validation Engine.
    1. Evaluates document content deterministically across all pages.
    2. Extracts semantic signals (conferral, issuance, signatures, cyber PKI study, pedagogy).
    3. Incorporates AI verification results if available.
    4. Checks subject relevance against selected subject.
    5. Applies admin-defined validation rules & thresholds.
    6. Returns structured verdict matching Section 6 requirements.
    """
    rules = {**DEFAULT_ADMIN_RULES, **(admin_rules or {})}
    min_rel = rules.get("minRelevanceThreshold", 0.40)
    min_conf = rules.get("minConfidenceThreshold", 0.70)
    strict_enabled = rules.get("strictValidationEnabled", True)
    page_count = total_pages or (len(pages_text) if pages_text else (1 if text and text.strip() else 0))

    # 1. Quality & Readability Evaluation (Stage 3)
    qual_score, is_qual_acceptable, qual_reason, qual_issues = evaluate_document_quality(
        text=text,
        ocr_applied=ocr_applied
    )

    # 2. Deep Semantic Classification
    det_type, det_conf, det_indicators, det_reason, semantic_profile = detect_document_type_from_content(
        text=text,
        title=title,
        filename=filename,
        ocr_applied=ocr_applied,
        pages_text=pages_text
    )

    # 3. Subject Relevance Check
    subj_score, subj_matches, subj_reason = calculate_subject_relevance(
        text=text,
        selected_subject=selected_subject
    )

    # Synthesize verdict (prioritizing AI result if present and confident)
    if ai_result and ai_result.get("document_type"):
        doc_type = ai_result["document_type"]
        is_academic = ai_result.get("is_academic", False)
        confidence = float(ai_result.get("confidence", det_conf))
        subject_relevance = float(ai_result.get("subject_relevance_score", subj_score))
        overall_purpose = ai_result.get("overall_purpose", semantic_profile.get("overall_purpose", ""))
        gemini_reason = ai_result.get("detailed_reason") or ai_result.get("rejection_reason")
        gemini_student_msg = ai_result.get("student_message")
    else:
        doc_type = det_type
        is_academic = doc_type in DEFAULT_ALLOWED_TYPES
        confidence = det_conf
        subject_relevance = subj_score
        overall_purpose = semantic_profile.get("overall_purpose", "")
        gemini_reason = None
        gemini_student_msg = None

    # Check if subject mismatch should trigger rejection
    if is_academic and not subj_matches and rules.get("requireSubjectMatch", True):
        doc_type = AcademicDocType.SUBJECT_MISMATCH
        is_academic = False
        det_reason = subj_reason
        overall_purpose = f"Academic study notes with subject mismatch: content does not align with '{selected_subject}'."

    # Apply Admin Rules & Final Decision
    is_restricted = doc_type in rules.get("restrictedCategories", DEFAULT_RESTRICTED_TYPES)
    is_allowed = doc_type in rules.get("allowedCategories", DEFAULT_ALLOWED_TYPES)

    if not strict_enabled:
        decision = "APPROVED"
        rejection_reason = None
        student_message = STUDENT_MESSAGES["APPROVED"]
    elif is_restricted or not is_academic:
        decision = "REJECTED"
        rejection_reason = gemini_reason or det_reason or f"Document classified as restricted type: {DOCUMENT_TYPE_LABELS.get(doc_type, doc_type)}"
        student_message = gemini_student_msg or STUDENT_MESSAGES.get(doc_type, STUDENT_MESSAGES[AcademicDocType.UNRELATED_NON_ACADEMIC]).format(subject=selected_subject)
    elif confidence < min_conf or subject_relevance < min_rel:
        decision = "NEEDS_REVIEW"
        rejection_reason = f"Verification confidence ({confidence:.2f}) or subject relevance ({subject_relevance:.2f}) below threshold."
        student_message = STUDENT_MESSAGES["NEEDS_REVIEW"]
    elif is_allowed and is_academic:
        decision = "APPROVED"
        rejection_reason = None
        student_message = STUDENT_MESSAGES["APPROVED"]
    else:
        decision = "NEEDS_REVIEW"
        rejection_reason = "Ambiguous academic relevance."
        student_message = STUDENT_MESSAGES["NEEDS_REVIEW"]

    return {
        # Section 6 Structured Output Requirements
        "document_type": doc_type,
        "document_type_label": DOCUMENT_TYPE_LABELS.get(doc_type, doc_type),
        "overall_purpose": overall_purpose,
        "detected_important_phrases": semantic_profile.get("detected_important_phrases", []),
        "certificate_indicators": semantic_profile.get("certificate_indicators", []),
        "resume_indicators": semantic_profile.get("resume_indicators", []),
        "placement_indicators": semantic_profile.get("placement_indicators", []),
        "academic_indicators": semantic_profile.get("academic_indicators", []),
        "subject_relevance": round(subject_relevance, 2),
        "subject_relevance_score": round(subject_relevance, 2),
        "document_quality": round(qual_score, 2),
        "quality_score": round(qual_score, 2),
        "confidence_score": round(confidence, 2),
        "confidence": round(confidence, 2),
        "validation_status": decision,
        "decision": decision,
        "is_academic": is_academic,
        "detailed_reason": rejection_reason or "Document verified as genuine academic learning material.",
        "rejection_reason": rejection_reason,
        "student_message": student_message,
        "matched_indicators": det_indicators,
        "total_pages_analyzed": page_count,
        "is_acceptable_quality": is_qual_acceptable,
        "selected_subject": selected_subject,
        "strict_validation_enabled": strict_enabled,
        "verified_at": datetime.utcnow().isoformat()
    }

async def validate_document_relevance(
    text: str,
    title: str = "",
    filename: str = "",
    selected_subject: str = "",
    pages_text: Optional[List[str]] = None,
    ocr_applied: bool = False,
    total_pages: Optional[int] = None,
    admin_rules: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Main Async Academic Validation Pipeline.
    Calls Gemini API if available, then delegates to validate_document_relevance_sync.
    """
    ai_result = None
    if settings.GEMINI_API_KEY:
        ai_result = await call_gemini_academic_validator(
            text=text,
            title=title,
            filename=filename,
            selected_subject=selected_subject,
            pages_text=pages_text,
            ocr_applied=ocr_applied
        )

    return validate_document_relevance_sync(
        text=text,
        title=title,
        filename=filename,
        selected_subject=selected_subject,
        pages_text=pages_text,
        ocr_applied=ocr_applied,
        total_pages=total_pages,
        admin_rules=admin_rules,
        ai_result=ai_result
    )
