// ==============================================================================
// Hybrid Grounded Syllabus RAG Engine
// Fulfills Cases 1, 2, 3, Short Questions, Abbreviations & Follow-Up Resolution
// ==============================================================================

import { generateGeminiContent } from "./gemini.ts";
import { evaluateInputGuardrails, evaluateOutputGuardrails } from "./guardrails.ts";

export interface RAGSource {
  materialId: string;
  title: string;
  pageNumber: number;
  text: string;
  score: number;
  heading?: string;
}

export interface RAGResponse {
  answer: string;
  sources: RAGSource[];
  caseType: "CASE_1_GROUNDED" | "CASE_2_NOT_IN_SYLLABUS" | "CASE_3_OUT_OF_SYLLABUS" | "GREETING";
}

// ------------------------------------------------------------------------------
// ACRONYM & ABBREVIATION DICTIONARY
// ------------------------------------------------------------------------------
const ACRONYMS: Record<string, string[]> = {
  vae: ["variational autoencoder", "autoencoder", "latent space", "probabilistic", "encoder", "decoder", "kl divergence", "reparameterization", "blurry", "reconstruction"],
  ae: ["autoencoder", "encoder", "decoder", "compression", "latent representation", "reconstruction loss"],
  gan: ["generative adversarial network", "generator", "discriminator", "adversarial"],
  fid: ["frechet inception distance", "evaluation metric", "image quality", "synthetic"],
  encoder: ["encoder", "compress", "input image", "latent space", "feature extraction", "representation"],
  decoder: ["decoder", "reconstruction", "reconstruct", "generate", "latent vector", "output"],
  latent: ["latent space", "manifold", "representation", "distribution", "lower-dimensional"],
  aov: ["average order value", "revenue per order", "metric", "sales"],
  "power bi": ["power bi", "business analytics", "data model", "dimensions", "measures", "dax"],
  campusverse: ["campusverse", "knowledge exchange", "student-led", "peer-to-peer", "notes", "rating", "upload"],
  dbms: ["database management system", "sql", "normalization", "tables", "relational"],
  os: ["operating system", "cpu scheduling", "deadlock", "process", "memory management"],
  dsa: ["data structures and algorithms", "trees", "graphs", "sorting", "time complexity"],
  ml: ["machine learning", "supervised", "unsupervised", "model", "training"],
  dl: ["deep learning", "neural networks", "backpropagation", "weights", "layers"],
  cnn: ["convolutional neural network", "filters", "feature maps", "pooling", "conv"],
  rnn: ["recurrent neural network", "sequence", "hidden state", "time steps"],
  lstm: ["long short-term memory", "gates", "cell state", "forget gate"],
  nlp: ["natural language processing", "tokenization", "transformer", "embeddings"],
  bert: ["bidirectional encoder representations", "transformer", "attention"],
  svm: ["support vector machine", "hyperplane", "margin", "kernel"],
  pca: ["principal component analysis", "dimensionality reduction", "eigenvectors"],
  api: ["application programming interface", "endpoints", "rest", "http"],
  ui: ["user interface", "frontend", "design", "components"],
};

// ------------------------------------------------------------------------------
// CONCEPTUAL SYNONYMS
// ------------------------------------------------------------------------------
const SYNONYMS: Record<string, string[]> = {
  advantage: ["benefit", "advantages", "benefits", "merit", "merits", "strength", "strengths", "pro", "pros"],
  advantages: ["benefit", "advantage", "benefits", "merit", "merits", "strength", "strengths", "pro", "pros"],
  disadvantage: ["limitation", "limitations", "drawback", "drawbacks", "weakness", "weaknesses", "con", "cons"],
  limitations: ["limitation", "disadvantage", "disadvantages", "drawback", "drawbacks", "weakness", "weaknesses"],
  limitation: ["limitations", "disadvantage", "disadvantages", "drawback", "drawbacks", "weakness"],
  objective: ["objectives", "goal", "goals", "aim", "aims", "purpose", "target"],
  objectives: ["objective", "goal", "goals", "aim", "aims", "purpose", "target"],
  purpose: ["objective", "objectives", "goal", "aim", "role", "need"],
  architecture: ["structure", "design", "framework", "components", "layers", "system", "workflow"],
  difference: ["differences", "compare", "comparison", "contrast", "distinction", "vs", "versus"],
  differences: ["difference", "compare", "comparison", "contrast", "distinction", "vs", "versus"],
  blurry: ["blur", "fuzzy", "smoothing", "smooth", "indistinct", "reconstruction error", "mse"],
  why: ["reason", "cause", "factors", "leads to", "because"],
  future: ["scope", "roadmap", "upcoming", "enhancements", "expansion"],
  methodology: ["approach", "process", "steps", "workflow", "lifecycle"],
  features: ["functionalities", "capabilities", "modules", "tools"],
};

// ------------------------------------------------------------------------------
// OUT-OF-SYLLABUS TOPICS (SPORTS, ENTERTAINMENT, DATING, WEATHER, POLITICS)
// ------------------------------------------------------------------------------
const OUT_OF_SYLLABUS_PATTERNS = [
  /\b(ipl|cricket|fifa|world\s*cup|football|messi|ronaldo|match|score)\b/i,
  /\b(romantic\s+story|love\s+story|dating|boyfriend|girlfriend|romance)\b/i,
  /\b(weather|temperature|forecast|climate\s+today|rain\s+today)\b/i,
  /\b(restaurant|food\s+delivery|recipe|pizza|burger|delicious)\b/i,
  /\b(movie|cinema|actor|actress|bollywood|hollywood|song|lyrics)\b/i,
  /\b(joke|funny|horoscope|zodiac|lottery|gambling)\b/i,
  /\b(election|political\s+party|vote\s+for|president\s+election)\b/i,
];

const GREETING_PATTERNS = [
  /^(hi|hello|hey|greetings|good\s+(morning|afternoon|evening)|yo|hola)[\s!.]*$/i,
  /^(who\s+are\s+you|what\s+can\s+you\s+do|help|how\s+are\s+you)[\s!.]*$/i,
];

/**
 * Checks if a query is a casual greeting.
 */
function isGreeting(q: string): boolean {
  return GREETING_PATTERNS.some((p) => p.test(q.trim()));
}

/**
 * Checks if a query is completely unrelated to academic study.
 */
function isOutOfSyllabusTopic(q: string): boolean {
  return OUT_OF_SYLLABUS_PATTERNS.some((p) => p.test(q));
}

/**
 * Rewrites follow-up questions by resolving entities from past conversation.
 */
function resolveFollowUpQuery(query: string, history: Array<{ role: string; content: string }>): string {
  const qLower = query.toLowerCase().trim();
  const isFollowUpPattern =
    /\b(second\s+point|first\s+point|third\s+point|last\s+point|why\s+blurry|why\s+does\s+this|how\s+does\s+it|advantages?|limitations?|give\s+an?\s+example|difference\s+between\s+them|explain\s+that)\b/i.test(
      qLower
    ) || qLower.split(/\s+/).length <= 3;

  if (!isFollowUpPattern || history.length === 0) {
    return query;
  }

  // Extract key topic from last conversation turns
  const lastTurns = history.slice(-3);
  let contextTopic = "";

  for (const turn of lastTurns) {
    const text = turn.content;
    for (const acr of Object.keys(ACRONYMS)) {
      const re = new RegExp(`\\b${acr}\\b`, "i");
      if (re.test(text)) {
        contextTopic = acr.toUpperCase();
        break;
      }
    }
    if (contextTopic) break;

    // Check for prominent capitalized terms
    const caps = text.match(/\b[A-Z][a-zA-Z]{3,}\b/g) || [];
    const validCaps = caps.filter((w) => !["This", "Based", "Here", "There", "What", "When", "Your"].includes(w));
    if (validCaps.length > 0) {
      contextTopic = validCaps[0];
      break;
    }
  }

  if (contextTopic && !qLower.includes(contextTopic.toLowerCase())) {
    return `${contextTopic} ${query}`;
  }

  return query;
}

const STOP_WORDS = new Set([
  "what", "is", "are", "the", "a", "an", "in", "on", "for", "of", "to", "and", "or",
  "it", "its", "do", "does", "can", "how", "why", "with", "by", "from", "as", "at",
  "about", "into", "through", "during", "before", "after", "above", "below", "these",
  "those", "then", "there", "this", "that", "explain", "describe", "tell", "me", "give",
  "show", "please", "point", "points", "first", "second", "third", "last"
]);

/**
 * Expands a query with synonyms and acronym expansions.
 */
function expandQuery(query: string): string[] {
  const clean = query.toLowerCase().replace(/[^a-z0-9\s]/g, " ");
  const rawWords = clean.split(/\s+/).filter((w) => w.length > 1 && !STOP_WORDS.has(w));
  const terms = new Set<string>(rawWords);

  for (const w of rawWords) {
    if (ACRONYMS[w]) {
      ACRONYMS[w].forEach((t) => terms.add(t));
    }
    for (const [acr, expansions] of Object.entries(ACRONYMS)) {
      if (expansions.includes(w)) {
        terms.add(acr);
        expansions.forEach((t) => terms.add(t));
      }
    }
    if (SYNONYMS[w]) {
      SYNONYMS[w].forEach((t) => terms.add(t));
    }
  }

  return Array.from(terms);
}

/**
 * Core Hybrid RAG Execution Engine.
 */
export async function executeRAG(
  query: string,
  materialIds: string[],
  supabaseClient: any,
  conversationHistory: Array<{ role: string; content: string }> = []
): Promise<RAGResponse> {
  const cleanQ = query.trim();

  // 1. Guardrail Validation
  const guard = evaluateInputGuardrails(cleanQ);
  if (!guard.allowed) {
    return {
      answer: `Safety Alert: ${guard.reason}`,
      sources: [],
      caseType: "CASE_3_OUT_OF_SYLLABUS",
    };
  }

  // 2. Greeting Handling
  if (isGreeting(cleanQ)) {
    return {
      answer:
        "Hello! I'm CampusVerse's AI study assistant. Ask me any question grounded in your uploaded study materials (such as definitions, architectures, key concepts, formulas, or exam review topics)!",
      sources: [],
      caseType: "GREETING",
    };
  }

  // 3. Case C Check: Unrelated Non-Academic Topics
  if (isOutOfSyllabusTopic(cleanQ)) {
    return {
      answer:
        "Out of syllabus! I'm CampusVerse's study assistant. Please ask a question related to your uploaded study materials.",
      sources: [],
      caseType: "CASE_3_OUT_OF_SYLLABUS",
    };
  }

  // 4. Follow-Up Entity Resolution
  const contextualQuery = resolveFollowUpQuery(cleanQ, conversationHistory);
  const expandedTerms = expandQuery(contextualQuery);

  // 5. Query Chunks from Supabase
  let sources: RAGSource[] = [];
  try {
    let dbQuery = supabaseClient
      .from("document_chunks")
      .select("id, material_id, title, page_number, heading, text")
      .limit(100);

    if (materialIds && materialIds.length > 0) {
      dbQuery = dbQuery.in("material_id", materialIds);
    }

    const { data: chunks, error } = await dbQuery;

    if (!error && chunks && chunks.length > 0) {
      // Score each chunk
      const scoredChunks: RAGSource[] = [];

      // Find meaningful content words from query
      const contentWords = cleanQ.toLowerCase().split(/\s+/).filter((w) => !STOP_WORDS.has(w) && w.length > 1);

      for (const chunk of chunks) {
        const textLow = (chunk.text || "").toLowerCase();
        const headingLow = (chunk.heading || "").toLowerCase();
        let score = 0;

        // Exact phrase bonus (only if query contains real content words)
        if (contentWords.length > 0) {
          if (textLow.includes(cleanQ.toLowerCase())) score += 5.0;
          if (headingLow.includes(cleanQ.toLowerCase())) score += 4.0;
        }

        // Expanded terms match
        for (const term of expandedTerms) {
          if (STOP_WORDS.has(term)) continue;
          if (term.includes(" ")) {
            if (textLow.includes(term)) score += 3.0;
            if (headingLow.includes(term)) score += 4.0;
          } else {
            const regex = new RegExp(`\\b${term}\\b`, "i");
            if (regex.test(textLow)) score += 2.0;
            if (regex.test(headingLow)) score += 3.0;
          }
        }

        if (score >= 2.0) {
          scoredChunks.push({
            materialId: chunk.material_id,
            title: chunk.title || "Study Material",
            pageNumber: chunk.page_number || 1,
            text: chunk.text,
            score,
            heading: chunk.heading,
          });
        }
      }

      scoredChunks.sort((a, b) => b.score - a.score);
      sources = scoredChunks.slice(0, 5);
    }
  } catch (err) {
    console.warn("Chunk search notice:", err);
  }

  // 6. Strict Syllabus Decision
  // If no chunks scored sufficiently (no relevant content found):
  if (sources.length === 0 || sources[0].score < 2.0) {
    // Case 2: Information is not present in uploaded notes
    return {
      answer:
        "This information is not available in your uploaded study materials. Please upload the relevant study material.",
      sources: [],
      caseType: "CASE_2_NOT_IN_SYLLABUS",
    };
  }

  // 7. Case 1: Information EXISTS in uploaded materials!
  // Assemble context snippets with exact page/slide citations
  const contextSnippet = sources
    .map(
      (s) =>
        `[Document: ${s.title} | Slide/Page ${s.pageNumber} | Section: ${s.heading || "Notes"}]\n${s.text}`
    )
    .join("\n\n---\n\n");

  const topDocTitle = sources[0].title;
  const topPageNum = sources[0].pageNumber;

  // Attempt Gemini AI Synthesis with strict teacher persona
  const teacherPrompt = `You are a helpful, clear, and friendly college professor assisting a student with their syllabus notes.
Answer the student's question accurately using ONLY the uploaded study material excerpts provided below.

STUDY MATERIAL EXCERPTS:
${contextSnippet}

STUDENT QUESTION:
${cleanQ} (Context: ${contextualQuery})

RULES:
1. Explain in simple, student-friendly English.
2. Direct explanations without fluff or introductory filler.
3. Organize important points in bullet points.
4. Expand technical abbreviations and explain concepts clearly.
5. Ground the answer completely in the excerpts. Cite the specific slide or page (e.g. "[Slide ${topPageNum}]" or "[Page ${topPageNum}]").
6. Do NOT invent facts or cite external knowledge not in the notes.`;

  try {
    const rawAnswer = await generateGeminiContent(teacherPrompt);
    const cleanAnswer = evaluateOutputGuardrails(rawAnswer);
    if (cleanAnswer && cleanAnswer.length > 30) {
      return {
        answer: cleanAnswer,
        sources,
        caseType: "CASE_1_GROUNDED",
      };
    }
  } catch {
    // If Gemini key is unconfigured, format direct grounded response from retrieved text
  }

  // Built-in Teacher Grounded Synthesis (Exact excerpts from the matched slides/pages)
  const bestExcerpt = sources[0].text;
  const points = bestExcerpt
    .split(/(?<=[.!?])\s+/)
    .filter((s) => s.trim().length > 15)
    .slice(0, 4);

  const bulletList =
    points.length > 0
      ? points.map((p) => `* ${p.trim()}`).join("\n")
      : `* ${bestExcerpt.slice(0, 300)}...`;

  const fallbackAnswer = `Based on your uploaded study notes in **${topDocTitle}** (Slide/Page ${topPageNum}):

${bulletList}

*(Citation: ${topDocTitle}, Slide/Page ${topPageNum})*`;

  return {
    answer: fallbackAnswer,
    sources,
    caseType: "CASE_1_GROUNDED",
  };
}
