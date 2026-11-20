// ==============================================================================
// AI Safety & Academic Document Guardrails Engine
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

// ==============================================================================
// STRICT ACADEMIC STUDY MATERIAL VALIDATION
// Rejects resumes, cooking recipes, job descriptions, invoices, shopping lists
// ==============================================================================

export interface DocumentValidationResult {
  isAcademic: boolean;
  category: "ACADEMIC_STUDY_MATERIAL" | "RESUME_CV" | "JOB_DESCRIPTION" | "COOKING_RECIPE" | "FINANCIAL_INVOICE" | "NON_ACADEMIC";
  reason?: string;
}

export function validateAcademicDocument(text: string, fileName: string): DocumentValidationResult {
  const content = text.toLowerCase();
  const name = fileName.toLowerCase();

  // 1. Resume / CV Detection
  const resumeSignals = [
    /\b(curriculum\s+vitae|resume|cv)\b/i,
    /\b(career\s+objective|professional\s+summary|work\s+experience)\b/i,
    /\b(technical\s+skills|core\s+competencies|employment\s+history)\b/i,
    /\b(hobbies|declaration|references\s+available)\b/i,
    /\b(internship\s+experience|projects\s+undertaken|educational\s+qualifications)\b/i,
  ];

  let resumeCount = 0;
  for (const sig of resumeSignals) {
    if (sig.test(content) || sig.test(name)) resumeCount++;
  }

  if (resumeCount >= 3 || (name.includes("resume") || name.includes("cv"))) {
    return {
      isAcademic: false,
      category: "RESUME_CV",
      reason: "Document identified as a personal resume or CV. Only syllabus-based academic study materials are allowed.",
    };
  }

  // 2. Cooking Recipe Detection
  const recipeSignals = [
    /\b(ingredients|prep\s+time|cook\s+time|cooking\s+time|servings?)\b/i,
    /\b(tablespoons?|teaspoons?|tbsp|tsp|cups?\s+of)\b/i,
    /\b(preheat\s+oven|simmer|boil|bake|chop|stir\s+well|garnish)\b/i,
    /\b(delicious|recipe|marinade|batter|dough)\b/i,
  ];

  let recipeCount = 0;
  for (const sig of recipeSignals) {
    if (sig.test(content) || sig.test(name)) recipeCount++;
  }

  if (recipeCount >= 3 || name.includes("recipe")) {
    return {
      isAcademic: false,
      category: "COOKING_RECIPE",
      reason: "Document identified as a food recipe. Only academic curriculum study materials are allowed.",
    };
  }

  // 3. Job Description / Recruitment Detection
  const jobSignals = [
    /\b(job\s+description|job\s+title|job\s+summary|we\s+are\s+hiring)\b/i,
    /\b(roles?\s+and\s+responsibilities|job\s+requirements|qualifications?\s+required)\b/i,
    /\b(compensation|salary\s+range|ctc|benefits\s+include|apply\s+now)\b/i,
    /\b(equal\s+opportunity\s+employer|reporting\s+to|full[- ]time\s+position)\b/i,
  ];

  let jobCount = 0;
  for (const sig of jobSignals) {
    if (sig.test(content) || sig.test(name)) jobCount++;
  }

  if (jobCount >= 3) {
    return {
      isAcademic: false,
      category: "JOB_DESCRIPTION",
      reason: "Document identified as a recruitment/job description. Only academic study materials are allowed.",
    };
  }

  // 4. Financial Documents / Invoices / Receipts
  const invoiceSignals = [
    /\b(invoice\s+no|tax\s+invoice|bill\s+to|ship\s+to)\b/i,
    /\b(payment\s+receipt|subtotal|amount\s+due|grand\s+total|transaction\s+id)\b/i,
    /\b(bank\s+statement|account\s+number|account\s+balance|credit\s+card\s+statement)\b/i,
  ];

  let invoiceCount = 0;
  for (const sig of invoiceSignals) {
    if (sig.test(content) || sig.test(name)) invoiceCount++;
  }

  if (invoiceCount >= 2) {
    return {
      isAcademic: false,
      category: "FINANCIAL_INVOICE",
      reason: "Document identified as an invoice/financial receipt. Only academic materials are permitted.",
    };
  }

  // All non-academic categories passed $\rightarrow$ legitimate academic material
  return {
    isAcademic: true,
    category: "ACADEMIC_STUDY_MATERIAL",
  };
}
