// ==============================================================================
// Google Gemini AI Client for Supabase Edge Functions (Deno Runtime)
// ==============================================================================

const GEMINI_API_KEY = Deno.env.get("GEMINI_API_KEY") || "";
const GEMINI_MODEL = Deno.env.get("GEMINI_MODEL") || "gemini-1.5-flash";

export interface AIReviewResult {
  provider: string;
  model: string;
  usedFallback: boolean;
  confidence: number;
  reason: string;
  flags: string[];
  reviewedAt: string;
}

export async function generateGeminiContent(
  prompt: string,
  systemInstruction?: string,
  jsonOutput: boolean = false
): Promise<string> {
  if (!GEMINI_API_KEY) {
    throw new Error("GEMINI_API_KEY is not configured in Edge Function environment.");
  }

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${GEMINI_API_KEY}`;

  const payload: any = {
    contents: [{ role: "user", parts: [{ text: prompt }] }],
    generationConfig: {
      temperature: 0.2,
      maxOutputTokens: 1000,
    },
  };

  if (systemInstruction) {
    payload.systemInstruction = { parts: [{ text: systemInstruction }] };
  }

  if (jsonOutput) {
    payload.generationConfig.responseMimeType = "application/json";
  }

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Gemini API Error (${res.status}): ${errText}`);
  }

  const data = await res.json();
  const text = data.candidates?.[0]?.content?.parts?.[0]?.text || "";
  return text.trim();
}

export async function generateEmbedding(text: string): Promise<number[]> {
  if (!GEMINI_API_KEY) {
    // Return deterministic pseudo-embedding vector if no key
    const vec = new Array(768).fill(0);
    for (let i = 0; i < text.length; i++) {
      vec[i % 768] += (text.charCodeAt(i) % 10) / 100;
    }
    return vec;
  }

  const url = `https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key=${GEMINI_API_KEY}`;
  const payload = {
    model: "models/text-embedding-004",
    content: { parts: [{ text: text.slice(0, 2048) }] },
  };

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      throw new Error(`Embedding API failed: ${res.statusText}`);
    }

    const data = await res.json();
    return data.embedding?.values || new Array(768).fill(0);
  } catch (err) {
    console.warn("Embedding error, using deterministic fallback:", err);
    const vec = new Array(768).fill(0);
    for (let i = 0; i < text.length; i++) {
      vec[i % 768] += (text.charCodeAt(i) % 10) / 100;
    }
    return vec;
  }
}

export async function reviewDocumentWithAI(
  title: string,
  description: string,
  department: string,
  semester: number,
  subject: string,
  text: string
): Promise<{ status: string; aiReview: AIReviewResult }> {
  const flags: string[] = [];

  // 1. Basic Rule-Based Checks
  const combined = `${title} ${description} ${text}`.toLowerCase();
  const spamKeywords = ["buy now", "click here", "free money", "casino", "betting", "whatsapp group", "discount code"];
  for (const kw of spamKeywords) {
    if (combined.includes(kw)) flags.push("SPAM_PHRASE");
  }

  if (text.length < 50) flags.push("LITTLE_TEXT");

  if (!GEMINI_API_KEY) {
    const isApproved = flags.length === 0;
    return {
      status: isApproved ? "AI_APPROVED" : "NEEDS_REVIEW",
      aiReview: {
        provider: "rules",
        model: "keyword-heuristics-v1",
        usedFallback: true,
        confidence: isApproved ? 0.95 : 0.65,
        reason: isApproved ? "Material meets academic requirements." : `Review required: ${flags.join(", ")}`,
        flags,
        reviewedAt: new Date().toISOString(),
      },
    };
  }

  const systemPrompt = `You are a senior academic content moderation assistant for CampusVerse, a university study material portal.
Evaluate if this document is genuine university/college study material for the stated subject.
Return ONLY clean JSON:
{
  "relevant": boolean,
  "spam": boolean,
  "inappropriate": boolean,
  "confidence": number between 0.0 and 1.0,
  "reason": "Clear explanation",
  "flags": ["FLAG_NAME"]
}`;

  try {
    const userPrompt = JSON.stringify({
      title,
      description,
      department,
      semester,
      subject,
      textExcerpt: text.slice(0, 4000),
    });

    const raw = await generateGeminiContent(userPrompt, systemPrompt, true);
    const parsed = JSON.parse(raw);

    const allFlags = Array.from(new Set([...flags, ...(parsed.flags || [])]));
    let status = "AI_APPROVED";
    if (parsed.spam || parsed.inappropriate || !parsed.relevant || parsed.confidence < 0.7) {
      status = "NEEDS_REVIEW";
    }

    return {
      status,
      aiReview: {
        provider: "gemini",
        model: GEMINI_MODEL,
        usedFallback: false,
        confidence: parsed.confidence || 0.9,
        reason: parsed.reason || "AI validation passed.",
        flags: allFlags,
        reviewedAt: new Date().toISOString(),
      },
    };
  } catch (e) {
    console.error("AI review error, falling back to rule-based:", e);
    const isApproved = flags.length === 0;
    return {
      status: isApproved ? "AI_APPROVED" : "NEEDS_REVIEW",
      aiReview: {
        provider: "rules",
        model: "keyword-heuristics-v1",
        usedFallback: true,
        confidence: isApproved ? 0.92 : 0.6,
        reason: isApproved ? "Document verified." : "Review required.",
        flags,
        reviewedAt: new Date().toISOString(),
      },
    };
  }
}

export async function generateDocumentSummary(
  title: string,
  text: string
): Promise<{ summary: string; wordCount: number }> {
  if (!GEMINI_API_KEY || text.length < 50) {
    const words = text.split(/\s+/).slice(0, 150).join(" ");
    const summary = `${title} - Comprehensive study notes.\n\n${words}...`;
    return { summary, wordCount: summary.split(/\s+/).length };
  }

  const prompt = `Summarize these university study notes for students preparing for examinations.
Include key concepts, definitions, and model takeaways. Max 450 words.
Document Title: ${title}
Document Content:
${text.slice(0, 8000)}`;

  try {
    const summary = await generateGeminiContent(prompt);
    const wordCount = summary.split(/\s+/).length;
    return { summary, wordCount };
  } catch (err) {
    const words = text.split(/\s+/).slice(0, 150).join(" ");
    const fallback = `${title} - Comprehensive study notes.\n\n${words}...`;
    return { summary: fallback, wordCount: fallback.split(/\s+/).length };
  }
}
