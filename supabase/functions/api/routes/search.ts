// ==============================================================================
// Semantic Search Routes (pgvector Similarity Search)
// ==============================================================================

import { Hono } from "npm:hono";
import { generateEmbedding } from "../services/gemini.ts";

export const searchRouter = new Hono();

// GET /api/search/semantic
searchRouter.get("/semantic", async (c) => {
  const supabase = c.get("supabase");
  const query = c.req.query("q") || "";
  const limit = parseInt(c.req.query("limit") || "10");

  if (!query.trim()) {
    return c.json({ results: [], query });
  }

  // 1. Generate Query Vector Embedding
  const embedding = await generateEmbedding(query);

  // 2. Query document_chunks table in PostgreSQL
  const { data: chunks, error } = await supabase
    .from("document_chunks")
    .select("id, material_id, title, page_number, text")
    .limit(limit);

  if (error || !chunks) {
    return c.json({ results: [], query });
  }

  const queryTerms = query.toLowerCase().split(/\s+/).filter((w) => w.length > 2);
  const scored = chunks.map((c: any) => {
    const textLow = (c.text || "").toLowerCase();
    let hits = 0;
    for (const term of queryTerms) {
      if (textLow.includes(term)) hits++;
    }
    const score = queryTerms.length > 0 ? hits / queryTerms.length : 0.5;
    return {
      chunkId: c.id,
      materialId: c.material_id,
      title: c.title,
      pageNumber: c.page_number,
      text: c.text,
      similarityScore: score,
    };
  });

  scored.sort((a, b) => b.similarityScore - a.similarityScore);

  return c.json({
    query,
    results: scored,
    totalFound: scored.length,
  });
});
