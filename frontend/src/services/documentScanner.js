// src/services/documentScanner.js
/**
 * Client-side document pre-validator for CampusVerse.
 * Validates supported file formats, enforces strict 150-page limit,
 * suggests academic categories, and delegates authoritative multi-page
 * extraction & OCR to the backend pipeline.
 */

export const MAX_ALLOWED_PAGES = 150;

export const ACADEMIC_CATEGORIES = [
  "Engineering",
  "Computer Science",
  "Civil Engineering",
  "Mechanical Engineering",
  "Electrical Engineering",
  "Electronics & Communication",
  "General Medicine",
  "Medical Sciences",
  "Cardiology",
  "Anatomy",
  "Pharmacology",
  "Artificial Intelligence",
  "Machine Learning",
  "Data Science",
  "Web Development",
  "Cloud Computing",
  "Cybersecurity",
  "Business and Management",
  "Finance",
  "Marketing",
  "Human Resources",
  "Science",
  "Physics",
  "Chemistry",
  "Mathematics",
  "Law",
  "Commerce",
  "Arts and Humanities",
];

/**
 * Validates document format and estimates initial page count before backend extraction.
 * Returns { pageCount, isExceeded, error }
 */
export async function inspectDocumentFile(file) {
  if (!file) {
    throw new Error("No file provided.");
  }

  const name = file.name.toLowerCase();
  const ext = name.includes(".") ? `.${name.split(".").pop()}` : "";

  const allowed = [".pdf", ".ppt", ".pptx", ".doc", ".docx", ".txt", ".md"];
  if (!allowed.includes(ext)) {
    throw new Error(`Unsupported format '${ext}'. Please upload a PDF, DOCX, DOC, PPTX, or PPT document.`);
  }

  if (file.size <= 0) {
    throw new Error("The uploaded file is empty (0 bytes).");
  }

  let estimatedPages = 1;

  try {
    const arrayBuffer = await file.arrayBuffer();
    const uint8 = new Uint8Array(arrayBuffer);

    if (ext === ".pdf") {
      estimatedPages = estimatePdfPages(uint8);
    } else if (ext === ".docx") {
      estimatedPages = estimateDocxPages(uint8, file.size);
    } else if (ext === ".pptx") {
      estimatedPages = estimatePptxSlides(uint8, file.size);
    } else if (ext === ".doc" || ext === ".ppt") {
      estimatedPages = Math.max(1, Math.min(150, Math.round(file.size / (35 * 1024))));
    } else if (ext === ".txt" || ext === ".md") {
      const text = new TextDecoder("utf-8").decode(uint8);
      estimatedPages = Math.max(1, Math.ceil(text.split("\n").length / 45));
    }
  } catch (e) {
    // Non-fatal estimation issue; backend will perform authoritative validation
    estimatedPages = 1;
  }

  if (estimatedPages > MAX_ALLOWED_PAGES) {
    return {
      pageCount: estimatedPages,
      isExceeded: true,
      error: `Upload failed: Documents must contain no more than ${MAX_ALLOWED_PAGES} pages. Uploaded document has approximately ${estimatedPages} pages.`,
    };
  }

  return {
    pageCount: estimatedPages,
    isExceeded: false,
    error: null,
  };
}

/**
 * Counts PDF pages by checking Linearized /N, PDF page-tree /Type /Pages /Count, and /Type /Page objects.
 */
function estimatePdfPages(uint8) {
  // Decode the binary string using latin1 to safely examine raw PDF structure
  const binaryString = new TextDecoder("latin1").decode(uint8);

  // 1. Linearized PDF header: /Linearized ... /N <pageCount>
  const linMatch = binaryString.match(/\/Linearized\b[\s\S]{1,400}?\/N\s+(\d+)/);
  if (linMatch && parseInt(linMatch[1], 10) > 0) {
    return parseInt(linMatch[1], 10);
  }

  // 2. /Type /Pages dictionary with /Count N (the authoritative page-tree root in PDF catalog)
  const pagesMatches = [
    ...binaryString.matchAll(/\/Type\s*\/Pages[\s\S]{0,250}?\/Count\s*(\d+)/g),
    ...binaryString.matchAll(/\/Count\s*(\d+)[\s\S]{0,250}?\/Type\s*\/Pages/g),
  ];
  if (pagesMatches.length > 0) {
    const counts = pagesMatches.map((m) => parseInt(m[1], 10)).filter((n) => n > 0 && n <= 5000);
    if (counts.length > 0) {
      return Math.max(...counts);
    }
  }

  // 3. Count all /Type /Page occurrences (excluding /Pages)
  const pageRegex = /\/Type\s*\/Page(?![a-zA-Z])/g;
  const pageMatches = binaryString.match(pageRegex);
  if (pageMatches && pageMatches.length > 0) {
    return pageMatches.length;
  }

  // 4. Any positive /Count N in the document
  const countMatches = [...binaryString.matchAll(/\/Count\s+(\d+)/g)];
  if (countMatches.length > 0) {
    const counts = countMatches.map((m) => parseInt(m[1], 10)).filter((n) => n > 0 && n <= 5000);
    if (counts.length > 0) {
      return Math.max(...counts);
    }
  }

  return 1;
}

/**
 * Estimates DOCX page count from ZIP directory and size without blocking compressed streams.
 */
function estimateDocxPages(uint8, sizeBytes) {
  // Check PK zip header
  if (uint8.length >= 4 && uint8[0] === 0x50 && uint8[1] === 0x4b) {
    try {
      const text = new TextDecoder("latin1").decode(uint8);
      const pageMatch = text.match(/<Pages>(\d+)<\/Pages>/);
      if (pageMatch && parseInt(pageMatch[1], 10) > 0) {
        return parseInt(pageMatch[1], 10);
      }
      const pageBreaks = (text.match(/w:type="page"/g) || []).length;
      if (pageBreaks > 0) {
        return pageBreaks + 1;
      }
    } catch {
      // fallback
    }
    return Math.max(1, Math.min(150, Math.round(sizeBytes / (80 * 1024))));
  }
  return 1;
}

/**
 * Estimates PPTX slide count from slide entries in ZIP container.
 */
function estimatePptxSlides(uint8, sizeBytes) {
  if (uint8.length >= 4 && uint8[0] === 0x50 && uint8[1] === 0x4b) {
    const latin1 = new TextDecoder("latin1").decode(uint8.subarray(Math.max(0, uint8.length - 100000)));
    const slideMatches = latin1.match(/ppt\/slides\/slide\d+\.xml/g) || [];
    const count = new Set(slideMatches).size;
    if (count > 0) return count;
    return Math.max(1, Math.round(sizeBytes / (45 * 1024)));
  }
  return 1;
}

/**
 * Classifies document filename/content into recommended Academic Category.
 */
export function classifyAcademicContent(text = "", fileName = "") {
  const lower = `${fileName} ${text}`.toLowerCase();

  if (lower.includes("machine learning") || lower.includes("deep learning") || lower.includes("neural net") || lower.includes("supervised")) {
    return "Machine Learning";
  }
  if (lower.includes("artificial intelligence") || lower.includes("heuristic search") || lower.includes("nlp")) {
    return "Artificial Intelligence";
  }
  if (lower.includes("data science") || lower.includes("big data") || lower.includes("pandas")) {
    return "Data Science";
  }
  if (lower.includes("web development") || lower.includes("react") || lower.includes("javascript")) {
    return "Web Development";
  }
  if (lower.includes("cloud computing") || lower.includes("aws") || lower.includes("docker") || lower.includes("kubernetes")) {
    return "Cloud Computing";
  }
  if (lower.includes("cybersecurity") || lower.includes("cryptography") || lower.includes("firewall")) {
    return "Cybersecurity";
  }
  if (
    lower.includes("cpu scheduling") ||
    lower.includes("operating system") ||
    lower.includes("deadlock") ||
    lower.includes("database") ||
    lower.includes("sql") ||
    lower.includes("data structure") ||
    lower.includes("algorithm") ||
    lower.includes("binary search")
  ) {
    return "Computer Science";
  }

  if (lower.includes("concrete") || lower.includes("beam") || lower.includes("structural") || lower.includes("civil") || lower.includes("soil mechanics")) {
    return "Civil Engineering";
  }
  if (lower.includes("thermodynamics") || lower.includes("fluid mechanics") || lower.includes("rankine") || lower.includes("heat transfer") || lower.includes("mechanical")) {
    return "Mechanical Engineering";
  }
  if (lower.includes("power system") || lower.includes("induction motor") || lower.includes("transformer") || lower.includes("circuit") || lower.includes("electrical")) {
    return "Electrical Engineering";
  }
  if (lower.includes("signal") || lower.includes("microcontroller") || lower.includes("semiconductor") || lower.includes("vlsi") || lower.includes("electronics")) {
    return "Electronics & Communication";
  }

  if (lower.includes("cardio") || lower.includes("hypertension") || lower.includes("ecg") || lower.includes("blood pressure")) {
    return "Cardiology";
  }
  if (lower.includes("anatomy") || lower.includes("skeletal") || lower.includes("muscular") || lower.includes("histology")) {
    return "Anatomy";
  }
  if (lower.includes("pharmacology") || lower.includes("drug") || lower.includes("pharmacokinetics")) {
    return "Pharmacology";
  }
  if (lower.includes("medicine") || lower.includes("clinical") || lower.includes("patient") || lower.includes("diagnosis")) {
    return "General Medicine";
  }

  if (lower.includes("finance") || lower.includes("capital budgeting") || lower.includes("investment")) {
    return "Finance";
  }
  if (lower.includes("marketing") || lower.includes("branding")) {
    return "Marketing";
  }
  if (lower.includes("accounting") || lower.includes("taxation") || lower.includes("auditing")) {
    return "Commerce";
  }
  if (lower.includes("management") || lower.includes("business")) {
    return "Business and Management";
  }

  if (lower.includes("physics") || lower.includes("quantum")) return "Physics";
  if (lower.includes("chemistry") || lower.includes("organic")) return "Chemistry";
  if (lower.includes("calculus") || lower.includes("differential") || lower.includes("mathematics")) return "Mathematics";
  if (lower.includes("law") || lower.includes("constitution")) return "Law";
  if (lower.includes("literature") || lower.includes("humanities")) return "Arts and Humanities";

  return "Engineering";
}

/**
 * Fallback client-side summary generator (strictly grounded in extracted text).
 */
export function generateContentBasedSummary(extractedText, title = "", academicCategory = "Engineering", maxWords = 500) {
  const cleanRaw = extractedText.replace(/\s+/g, " ").trim();
  const sentences = cleanRaw
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter((s) => {
      const words = s.split(/\s+/);
      return words.length >= 5 && words.length <= 45;
    });

  if (sentences.length === 0) {
    return {
      summary: `Academic study notes for ${title} in ${academicCategory}.`,
      wordCount: 8,
    };
  }

  const selected = [];
  const seen = new Set();

  function addSentence(s) {
    if (!s) return;
    const sig = s.toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 40);
    if (!seen.has(sig)) {
      seen.add(sig);
      let formatted = s.trim();
      if (!formatted.endsWith(".") && !formatted.endsWith("!") && !formatted.endsWith("?")) {
        formatted += ".";
      }
      selected.push(formatted);
    }
  }

  // Cover beginning, middle, and end of document
  addSentence(sentences[0]);
  if (sentences[1]) addSentence(sentences[1]);

  const step = Math.max(2, Math.floor(sentences.length / 5));
  for (let i = 2; i < sentences.length - 1; i += step) {
    addSentence(sentences[i]);
  }

  if (sentences.length > 2) {
    addSentence(sentences[sentences.length - 1]);
  }

  let combined = selected.join(" ");
  let words = combined.split(/\s+/).filter(Boolean);

  if (words.length > maxWords) {
    words = words.slice(0, maxWords);
    combined = words.join(" ") + ".";
  }

  return {
    summary: combined,
    wordCount: combined.split(/\s+/).filter(Boolean).length,
  };
}
