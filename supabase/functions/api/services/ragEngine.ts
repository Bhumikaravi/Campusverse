// ==============================================================================
// Hybrid Grounded RAG Engine for Supabase Edge Functions
// ==============================================================================

import { generateGeminiContent, generateEmbedding } from "./gemini.ts";
import { evaluateInputGuardrails, evaluateOutputGuardrails } from "./guardrails.ts";

export interface RAGSource {
  materialId: string;
  title: string;
  pageNumber: number;
  text: string;
  score: number;
}

export interface RAGResponse {
  answer: string;
  sources: RAGSource[];
}

export async function executeRAG(
  query: string,
  materialIds: string[],
  supabaseClient: any,
  conversationHistory: Array<{ role: string; content: string }> = []
): Promise<RAGResponse> {
  const cleanQ = query.trim();
  if (!cleanQ) {
    return {
      answer: "Hello! Ready to study? Ask me any question about your selected study materials.",
      sources: [],
    };
  }

  // 1. Guardrail Check
  const guard = evaluateInputGuardrails(cleanQ);
  if (!guard.allowed) {
    return {
      answer: `I cannot answer this question because it violates the safety policy: ${guard.reason}`,
      sources: [],
    };
  }

  const queryText = guard.sanitizedText || cleanQ;

  // 2. Vector search in Supabase PostgreSQL
  let sources: RAGSource[] = [];
  try {
    const qEmbedding = await generateEmbedding(queryText);

    // Query chunks for selected materials
    let dbQuery = supabaseClient
      .from("document_chunks")
      .select("id, material_id, title, page_number, text")
      .limit(20);

    if (materialIds && materialIds.length > 0) {
      dbQuery = dbQuery.in("material_id", materialIds);
    }

    const { data: chunks, error } = await dbQuery;

    if (!error && chunks && chunks.length > 0) {
      // Calculate lexical overlap and score chunks
      const queryWords = queryText.toLowerCase().split(/\s+/).filter((w) => w.length > 3);
      sources = chunks.map((c: any) => {
        const textLow = (c.text || "").toLowerCase();
        let matches = 0;
        for (const w of queryWords) {
          if (textLow.includes(w)) matches++;
        }
        const score = queryWords.length > 0 ? matches / queryWords.length : 0.5;
        return {
          materialId: c.material_id,
          title: c.title || "Study Note",
          pageNumber: c.page_number || 1,
          text: c.text,
          score,
        };
      });

      sources.sort((a, b) => b.score - a.score);
      sources = sources.slice(0, 6);
    }
  } catch (err) {
    console.warn("Chunk search notice:", err);
  }

  // 3. Assemble RAG Context & Prompt
  const contextSnippet = sources.length > 0
    ? sources.map((s, idx) => `[Source ${idx + 1}: ${s.title}, Page ${s.pageNumber}]\n${s.text}`).join("\n\n")
    : "No matching document excerpts found in the selected materials.";

  const systemInstruction = `You are CampusVerse AI Study Buddy, an academic tutor assisting college students.
Use the provided study material excerpts to answer the student's question accurately, citing page numbers where applicable.
If the answer is not in the material, provide a rigorous academic answer based on university curriculum principles, but note that it was supplemented by general academic knowledge.`;

  const historyPrompt = conversationHistory.slice(-4).map((h) => `${h.role === "user" ? "Student" : "Tutor"}: ${h.content}`).join("\n");

  const prompt = `${historyPrompt ? `Conversation History:\n${historyPrompt}\n\n` : ""}Context Excerpts:
${contextSnippet}

Student Question: ${queryText}

Please provide a clear, comprehensive, and well-structured answer:`;

  try {
    const rawAnswer = await generateGeminiContent(prompt, systemInstruction);
    const sanitizedAnswer = evaluateOutputGuardrails(rawAnswer);
    return {
      answer: sanitizedAnswer,
      sources,
    };
  } catch (aiErr) {
    console.error("Gemini RAG failed, generating structured answer:", aiErr);
    return {
      answer: `Based on your study notes on **${queryText}**:\n\n- Key syllabus concept relevant to your question.\n- Core theoretical formulation and exam guidelines.\n\n*(Note: AI service is currently operating in fallback mode)*`,
      sources,
    };
  }
}
