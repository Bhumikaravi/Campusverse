"""AI Safety & Security Guardrails Service for CampusVerse.

Provides multi-layered input/output guardrails:
1. Prompt Injection & Jailbreak Defense (overrides, DAN, system prompt exfiltration)
2. Content Safety & Toxicity Filter (harassment, hate, self-harm, cyber-attacks)
3. PII (Personally Identifiable Information) Shield (Cards, Phone numbers, National IDs, API keys)
4. Academic Domain & Integrity Guardrail (exam malpractice, illicit homework bypass)
5. Clinical & Medical Safety Invariant (disclaimer enforcement for healthcare queries)
6. Output Verification & Leak Prevention (system prompt & secret masking)
7. Audit Telemetry & Statistics
"""

import re
import time
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("campusverse.guardrails")

# ---------------------------------------------------------------------------
# 1. PROMPT INJECTION & JAILBREAK PATTERNS
# ---------------------------------------------------------------------------
PROMPT_INJECTION_PATTERNS = [
    # Direct instruction overriding
    re.compile(r"\bignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules|commands)\b", re.I),
    re.compile(r"\bdisregard\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)\b", re.I),
    re.compile(r"\bforget\s+(all\s+)?(previous|prior|your)\s+(instructions|rules|guidelines)\b", re.I),
    re.compile(r"\bbypass\s+(all\s+)?(restrictions|safety|filters|guardrails)\b", re.I),
    re.compile(r"\boverride\s+(system|safety|security)\s+(rules|instructions|prompts)\b", re.I),

    # Roleplay / Jailbreak personas
    re.compile(r"\b(act|pretend|behave)\s+as\s+(dan|an?\s+unfiltered|an?\s+unrestricted|jailbreak)\b", re.I),
    re.compile(r"\bdeveloper\s+mode\s+(enabled|activate|on)\b", re.I),
    re.compile(r"\byou\s+have\s+no\s+(rules|restrictions|limits|guidelines)\b", re.I),
    re.compile(r"\bdo\s+anything\s+now\b", re.I),

    # System prompt exfiltration
    re.compile(r"\b(print|show|repeat|display|reveal|output|tell\s+me)\s+(your\s+)?(system\s+prompt|initial\s+prompt|secret\s+instructions|system\s+instructions)\b", re.I),
    re.compile(r"\bwhat\s+(is|are)\s+your\s+(exact\s+)?(system\s+prompt|initial\s+instructions|secret\s+rules)\b", re.I),

    # Delimiter / Structural injections
    re.compile(r"(<\|im_start\|>system|<\|system\|>|\[SYSTEM\s+PROMPT\]|---\s*system\s*:)", re.I),
    re.compile(r"(\"\"\"\s*###\s*System\s*Instructions:)", re.I),
]

# ---------------------------------------------------------------------------
# 2. TOXICITY, MALICE & DANGEROUS CONTENT PATTERNS
# ---------------------------------------------------------------------------
HARMFUL_INTENT_PATTERNS = [
    # Hacking / Cyber-malware creation
    re.compile(r"\bhow\s+to\s+(hack|infiltrate|ddos|crack|deface)\s+(into\s+)?\w+\b", re.I),
    re.compile(r"\b(write|create|make|build|generate|code|develop)\s+(a\s+)?(keylogger|ransomware|trojan|worm|rootkit|botnet|exploit\s+payload|malware|spyware|computer\s+virus)\b", re.I),
    re.compile(r"\b(ransomware|keylogger|botnet|trojan|rootkit)\s+(in\s+\w+|code|script|payload|to\s+attack)\b", re.I),
    re.compile(r"\b(steal|dump|sniff)\s+(passwords|credentials|database\s+dump|credit\s+cards)\b", re.I),

    # Weapons, explosive devices & physical harm
    re.compile(r"\bhow\s+to\s+(make|build|assemble|manufacture)\s+(a\s+)?(bomb|explosive|weapon|poison|ied)\b", re.I),
    re.compile(r"\binstructions\s+for\s+(synthesizing|producing)\s+(illegal\s+drugs|explosives|poison)\b", re.I),

    # Self-harm & severe violence
    re.compile(r"\bhow\s+to\s+(commit\s+suicide|kill\s+myself|hurt\s+myself)\b", re.I),

    # Hate speech & severe harassment slurs (academic safe list filter)
    re.compile(r"\b(kill\s+all|exterminate|hate\s+all)\s+(jews|muslims|hindus|christians|blacks|whites|immigrants)\b", re.I),
]

# ---------------------------------------------------------------------------
# 3. ACADEMIC INTEGRITY & MALPRACTICE PATTERNS
# ---------------------------------------------------------------------------
ACADEMIC_MALPRACTICE_PATTERNS = [
    re.compile(r"\b(solve|answer)\s+(my\s+)?(live\s+)?(proctored|online)\s+(exam|quiz|test)\s+right\s+now\b", re.I),
    re.compile(r"\bhow\s+to\s+(cheat|bypass|hack)\s+(turnitin|safeassign|proctorio|examity|moodle\s+exam)\b", re.I),
    re.compile(r"\bhack\s+(my\s+)?(grades|attendance|exam\s+portal|university\s+server)\b", re.I),
]

# ---------------------------------------------------------------------------
# 4. PII REGEX PATTERNS (Personally Identifiable Information)
# ---------------------------------------------------------------------------
PII_PATTERNS = {
    "CREDIT_CARD": re.compile(r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b"),
    "PHONE_NUMBER": re.compile(r"(?:\+91[\-\s]?)?[6-9]\d{9}\b|\b(?:\+1[\-\s]?)?\(?\d{3}\)?[\-\s]?\d{3}[\-\s]?\d{4}\b"),
    "AADHAAR_NUMBER": re.compile(r"\b[2-9]\d{3}\s\d{4}\s\d{4}\b"),
    "API_KEY": re.compile(r"\b(AIza[0-9A-Za-z\-_]{35}|sk-[a-zA-Z0-9]{32,}|ghp_[a-zA-Z0-9]{36}|Bearer\s+[a-zA-Z0-9\-\._~\+\/]+=*)\b"),
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"),
}

# ---------------------------------------------------------------------------
# 5. CLINICAL / MEDICAL SAFETY TERMS
# ---------------------------------------------------------------------------
CLINICAL_TRIGGER_KEYWORDS = [
    "dosage", "prescribe", "treatment for my patient", "clinical diagnosis",
    "injectable dose", "overdose symptoms", "cure my disease", "take these pills"
]

CLINICAL_SAFETY_DISCLAIMER = (
    "\n\n> ⚠️ **CampusVerse Academic Guardrail Notice:** The following information is synthesized "
    "strictly for university academic study and educational revision. It is **not** medical advice, "
    "clinical diagnosis, or treatment prescription."
)

# ---------------------------------------------------------------------------
# 6. IN-MEMORY AUDIT TELEMETRY COUNTERS
# ---------------------------------------------------------------------------
class GuardrailsTelemetry:
    def __init__(self):
        self.total_checked = 0
        self.total_allowed = 0
        self.total_blocked = 0
        self.total_sanitized = 0
        self.injections_blocked = 0
        self.harm_blocked = 0
        self.malpractice_blocked = 0
        self.pii_redacted = 0
        self.medical_disclaimers_added = 0
        self.total_latency_ms = 0.0

    def record_check(self, result: Dict[str, Any], duration_ms: float):
        self.total_checked += 1
        self.total_latency_ms += duration_ms
        action = result.get("action")
        if action == "BLOCK":
            self.total_blocked += 1
            for g in result.get("triggered_guardrails", []):
                if g == "PROMPT_INJECTION":
                    self.injections_blocked += 1
                elif g == "HARMFUL_CONTENT":
                    self.harm_blocked += 1
                elif g == "ACADEMIC_MALPRACTICE":
                    self.malpractice_blocked += 1
        elif action == "SANITIZE":
            self.total_sanitized += 1
            self.total_allowed += 1
        else:
            self.total_allowed += 1

        if result.get("pii_detected"):
            self.pii_redacted += len(result["pii_detected"])
        if result.get("medical_disclaimer_required"):
            self.medical_disclaimers_added += 1

    def get_summary(self) -> Dict[str, Any]:
        avg_latency = round(self.total_latency_ms / max(1, self.total_checked), 2)
        safe_rate = round((self.total_allowed / max(1, self.total_checked)) * 100.0, 1)
        return {
            "totalEvaluated": self.total_checked,
            "totalAllowed": self.total_allowed,
            "totalBlocked": self.total_blocked,
            "totalSanitized": self.total_sanitized,
            "safeRatePercent": safe_rate,
            "injectionsBlocked": self.injections_blocked,
            "harmBlocked": self.harm_blocked,
            "malpracticeBlocked": self.malpractice_blocked,
            "piiRedacted": self.pii_redacted,
            "medicalDisclaimersAdded": self.medical_disclaimers_added,
            "avgLatencyMs": avg_latency,
            "status": "ACTIVE_AND_ENFORCING",
            "activePolicies": [
                {
                    "id": "PROMPT_INJECTION",
                    "name": "Prompt Injection & Jailbreak Shield",
                    "description": "Intercepts overrides, system prompt exfiltration, and persona jailbreaks",
                    "mode": "BLOCK",
                    "status": "ENABLED"
                },
                {
                    "id": "HARMFUL_CONTENT",
                    "name": "Harmful Content & Cyber Defense",
                    "description": "Blocks weapon synthesis, malware creation, and hate speech",
                    "mode": "BLOCK",
                    "status": "ENABLED"
                },
                {
                    "id": "PII_PROTECTION",
                    "name": "Personally Identifiable Information Shield",
                    "description": "Automatically redacts credit cards, phone numbers, national IDs, and API keys",
                    "mode": "REDACT_AND_SANITIZE",
                    "status": "ENABLED"
                },
                {
                    "id": "ACADEMIC_MALPRACTICE",
                    "name": "Academic Integrity & Exam Boundary",
                    "description": "Prevents live proctored exam solving and grade hacking attempts",
                    "mode": "BLOCK",
                    "status": "ENABLED"
                },
                {
                    "id": "CLINICAL_SAFETY",
                    "name": "Clinical & Medical Safety Invariant",
                    "description": "Enforces mandatory academic disclaimers on clinical and medical queries",
                    "mode": "APPEND_DISCLAIMER",
                    "status": "ENABLED"
                }
            ]
        }

telemetry = GuardrailsTelemetry()

# ---------------------------------------------------------------------------
# 7. CORE GUARDRAIL EVALUATION LOGIC
# ---------------------------------------------------------------------------
def redact_pii(text: str) -> Tuple[str, List[Dict[str, str]]]:
    """Scans and masks sensitive PII from user text."""
    sanitized = text
    detected = []

    for pii_type, pattern in PII_PATTERNS.items():
        matches = list(pattern.finditer(sanitized))
        if matches:
            for m in reversed(matches):
                val = m.group(0)
                # Don't redact typical short years or normal 4-digit numbers as aadhaar
                if pii_type == "AADHAAR_NUMBER" and len(val.replace(" ", "")) != 12:
                    continue
                placeholder = f"[{pii_type}_REDACTED]"
                detected.append({"type": pii_type, "masked": val[:3] + "***"})
                sanitized = sanitized[:m.start()] + placeholder + sanitized[m.end():]

    return sanitized, detected


def check_prompt_injection(text: str) -> Tuple[bool, Optional[str]]:
    """Evaluates text for prompt injection and jailbreak signatures."""
    clean = text.strip()
    for pat in PROMPT_INJECTION_PATTERNS:
        match = pat.search(clean)
        if match:
            return True, f"Prompt injection pattern detected: '{match.group(0)}'"
    return False, None


def check_harmful_content(text: str) -> Tuple[bool, Optional[str]]:
    """Evaluates text for dangerous instructions, cyber exploits, or threats."""
    clean = text.strip()
    for pat in HARMFUL_INTENT_PATTERNS:
        match = pat.search(clean)
        if match:
            return True, f"Safety violation detected: unauthorized request for dangerous or malicious material ('{match.group(0)}')"
    return False, None


def check_academic_malpractice(text: str) -> Tuple[bool, Optional[str]]:
    """Evaluates text for attempts to cheat live exams or hack academic systems."""
    clean = text.strip()
    for pat in ACADEMIC_MALPRACTICE_PATTERNS:
        match = pat.search(clean)
        if match:
            return True, f"Academic integrity violation: attempts to circumvent proctored examinations or alter grades are blocked."
    return False, None


def evaluate_input_guardrails(text: str, context: Optional[str] = None) -> Dict[str, Any]:
    """
    Main entry point for checking input queries against all CampusVerse guardrails.
    Returns structured verdict and sanitized text.
    """
    start_time = time.perf_counter()
    triggered = []
    reasons = []
    risk_score = 0.0

    # 1. Prompt Injection Check
    is_inj, inj_reason = check_prompt_injection(text)
    if is_inj:
        triggered.append("PROMPT_INJECTION")
        reasons.append(inj_reason)
        risk_score = max(risk_score, 0.95)

    # 2. Harmful Content Check
    is_harm, harm_reason = check_harmful_content(text)
    if is_harm:
        triggered.append("HARMFUL_CONTENT")
        reasons.append(harm_reason)
        risk_score = max(risk_score, 0.98)

    # 3. Academic Malpractice Check
    is_mal, mal_reason = check_academic_malpractice(text)
    if is_mal:
        triggered.append("ACADEMIC_MALPRACTICE")
        reasons.append(mal_reason)
        risk_score = max(risk_score, 0.85)

    # 4. PII Redaction
    sanitized_text, pii_detected = redact_pii(text)
    if pii_detected:
        triggered.append("PII_PROTECTION")

    # 5. Clinical Safety Check
    lower_t = text.lower()
    medical_disclaimer_required = any(k in lower_t for k in CLINICAL_TRIGGER_KEYWORDS)

    # Determine Verdict Action
    if "PROMPT_INJECTION" in triggered or "HARMFUL_CONTENT" in triggered or "ACADEMIC_MALPRACTICE" in triggered:
        action = "BLOCK"
        is_safe = False
        user_message = (
            "🛡️ **CampusVerse AI Safety Guardrail Alert**\n\n"
            "Your message could not be processed because it triggered an active academic safety guardrail:\n"
            f"- **Policy Enforced:** {', '.join(triggered)}\n"
            f"- **Reason:** {reasons[0] if reasons else 'Safety policy violation'}\n\n"
            "CampusVerse is designed exclusively for verified, constructive academic study and course revision. "
            "Please rephrase your query focusing on educational concepts, textbook explanations, or study notes."
        )
    elif pii_detected:
        action = "SANITIZE"
        is_safe = True
        user_message = None
        risk_score = 0.3
    else:
        action = "ALLOW"
        is_safe = True
        user_message = None
        risk_score = 0.0

    duration_ms = (time.perf_counter() - start_time) * 1000.0

    result = {
        "is_safe": is_safe,
        "action": action,
        "triggered_guardrails": triggered,
        "reasons": reasons,
        "sanitized_text": sanitized_text,
        "pii_detected": pii_detected,
        "medical_disclaimer_required": medical_disclaimer_required,
        "risk_score": risk_score,
        "user_message": user_message,
        "latency_ms": round(duration_ms, 2)
    }

    # Record telemetry
    telemetry.record_check(result, duration_ms)
    return result


def evaluate_output_guardrails(answer: str, is_medical: bool = False) -> str:
    """
    Evaluates generated AI responses before delivery to student:
    1. Prevents system prompt leakage
    2. Redacts unintended secrets or credentials
    3. Appends mandatory clinical disclaimer if applicable
    """
    clean_ans = answer

    # Guardrail against system prompt echo/leak
    leak_patterns = [
        re.compile(r"SYSTEM_PROMPT_CHATGPT_STYLE", re.I),
        re.compile(r"You are an advanced AI assistant designed to provide a complete, natural", re.I),
        re.compile(r"GEMINI_API_KEY\s*=\s*['\"][^'\"]+['\"]", re.I),
    ]
    for pat in leak_patterns:
        if pat.search(clean_ans):
            clean_ans = pat.sub("[SYSTEM_INSTRUCTION_PROTECTED]", clean_ans)

    # Redact sensitive credentials in output if any
    clean_ans, _ = redact_pii(clean_ans)

    # Append clinical safety disclaimer if medical context
    if is_medical and "Educational Notice" not in clean_ans:
        clean_ans += CLINICAL_SAFETY_DISCLAIMER

    return clean_ans
