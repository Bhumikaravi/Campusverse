// ==============================================================================
// AI Safety & Guardrails Engine for Supabase Edge Functions
// ==============================================================================

export interface GuardrailResult {
  allowed: boolean;
  blockedPolicy?: string;
  reason?: string;
  sanitizedText?: string;
}

const INJECTION_PATTERNS = [
  /\bignore\s+(all\s+)?(previous|prior)\s+instructions\b/i,
  /\bdisregard\s+(all\s+)?rules\b/i,
  /\byou\s+are\s+now\s+in\s+developer\s+mode\b/i,
  /\bjailbreak\b/i,
  /\bsystem\s+prompt\b/i,
  /\breveal\s+(your\s+)?instructions\b/i,
];

const HARMFUL_PATTERNS = [
  /\bhow\s+to\s+(make|build|synthesize)\s+(a\s+)?(bomb|explosive|weapon)\b/i,
  /\bhack\s+(into\s+)?(the\s+)?(university|exam|system)\b/i,
];

const PII_PATTERNS = [
  { pattern: /\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b/g, replacement: "[REDACTED CARD]" },
  { pattern: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g, replacement: "[REDACTED EMAIL]" },
  { pattern: /\b(?:\+?\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}\b/g, replacement: "[REDACTED PHONE]" },
];

export function evaluateInputGuardrails(text: string): GuardrailResult {
  for (const pattern of INJECTION_PATTERNS) {
    if (pattern.test(text)) {
      return {
        allowed: false,
        blockedPolicy: "PROMPT_INJECTION",
        reason: "Prompt injection or system override attempt detected.",
      };
    }
  }

  for (const pattern of HARMFUL_PATTERNS) {
    if (pattern.test(text)) {
      return {
        allowed: false,
        blockedPolicy: "HARMFUL_CONTENT",
        reason: "Content flagged under harmful content policy.",
      };
    }
  }

  let sanitized = text;
  for (const pii of PII_PATTERNS) {
    sanitized = sanitized.replace(pii.pattern, pii.replacement);
  }

  return {
    allowed: true,
    sanitizedText: sanitized,
  };
}

export function evaluateOutputGuardrails(text: string): string {
  let clean = text;
  for (const pii of PII_PATTERNS) {
    clean = clean.replace(pii.pattern, pii.replacement);
  }
  return clean;
}
