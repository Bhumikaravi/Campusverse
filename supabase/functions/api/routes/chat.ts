// ==============================================================================
// Chat With Notes (RAG) Routes
// ==============================================================================

import { Hono } from "npm:hono";
import { executeRAG } from "../services/ragEngine.ts";
import { getBearerToken } from "./auth.ts";

export const chatRouter = new Hono();

// GET /api/chat/materials
chatRouter.get("/materials", async (c) => {
  const supabase = c.get("supabase");

  const { data: docs } = await supabase
    .from("study_materials")
    .select("id, document_id, title, subject, department, page_count, extension, status")
    .in("status", ["AI_APPROVED", "ADMIN_APPROVED", "QUALITY_CHECK_PASSED"])
    .order("created_at", { ascending: false })
    .limit(100);

  const materials = (docs || []).map((d: any) => ({
    id: d.id,
    documentId: d.document_id || d.id,
    title: d.title || "Untitled Note",
    subject: d.subject || "",
    department: d.department || "",
    pageCount: d.page_count || 1,
    fileType: (d.extension || "pdf").replace(".", "").toUpperCase(),
    status: d.status || "Available",
  }));

  return c.json({ materials });
});

// POST /api/chat/sessions
chatRouter.post("/sessions", async (c) => {
  const supabase = c.get("supabase");
  const token = getBearerToken(c.req.raw);
  const body = await c.req.json();
  const { materialIds, title } = body;

  let userId = "00000000-0000-0000-0000-000000000000";
  if (token) {
    const { data: { user } } = await supabase.auth.getUser(token);
    if (user) userId = user.id;
  }

  const sessionTitle = title || "Study Session";

  const { data: session, error } = await supabase
    .from("chat_sessions")
    .insert({
      user_id: userId,
      title: sessionTitle,
      material_ids: materialIds || [],
    })
    .select()
    .single();

  if (error) {
    // If foreign key constraint on dummy user ID, return ephemeral session
    const ephemeralId = `session-${Date.now()}`;
    return c.json({
      id: ephemeralId,
      sessionId: ephemeralId,
      title: sessionTitle,
      materialIds,
      createdAt: new Date().toISOString(),
    }, 201);
  }

  return c.json({
    id: session.id,
    sessionId: session.id,
    title: session.title,
    materialIds: session.material_ids,
    createdAt: session.created_at,
  }, 201);
});

// GET /api/chat/sessions
chatRouter.get("/sessions", async (c) => {
  const supabase = c.get("supabase");
  const token = getBearerToken(c.req.raw);

  if (!token) return c.json({ sessions: [] });
  const { data: { user } } = await supabase.auth.getUser(token);
  if (!user) return c.json({ sessions: [] });

  const { data: sessions } = await supabase
    .from("chat_sessions")
    .select("*")
    .eq("user_id", user.id)
    .order("updated_at", { ascending: false });

  return c.json({ sessions: sessions || [] });
});

// GET /api/chat/sessions/:id
chatRouter.get("/sessions/:id", async (c) => {
  const supabase = c.get("supabase");
  const id = c.req.param("id");

  const { data: session } = await supabase
    .from("chat_sessions")
    .select("*")
    .eq("id", id)
    .single();

  const { data: messages } = await supabase
    .from("chat_messages")
    .select("*")
    .eq("session_id", id)
    .order("created_at", { ascending: true });

  return c.json({
    session: session || { id, title: "Study Session" },
    messages: messages || [],
  });
});

// POST /api/chat/sessions/:id/message
chatRouter.post("/sessions/:id/message", async (c) => {
  const supabase = c.get("supabase");
  const id = c.req.param("id");
  const body = await c.req.json();
  const { question } = body;

  const { data: session } = await supabase
    .from("chat_sessions")
    .select("*")
    .eq("id", id)
    .single();

  const materialIds = session?.material_ids || [];

  // Fetch recent history
  const { data: pastMsgs } = await supabase
    .from("chat_messages")
    .select("role, content")
    .eq("session_id", id)
    .order("created_at", { ascending: true })
    .limit(6);

  const history = (pastMsgs || []).map((m: any) => ({ role: m.role, content: m.content }));

  // Run Grounded RAG Pipeline
  const ragResult = await executeRAG(question, materialIds, supabase, history);

  // Record user and assistant messages
  if (session) {
    await supabase.from("chat_messages").insert([
      { session_id: id, role: "user", content: question },
      { session_id: id, role: "assistant", content: ragResult.answer, sources: ragResult.sources },
    ]).catch(() => {});

    await supabase.from("chat_sessions").update({ updated_at: new Date().toISOString() }).eq("id", id).catch(() => {});
  }

  return c.json({
    answer: ragResult.answer,
    sources: ragResult.sources,
    message: {
      role: "assistant",
      content: ragResult.answer,
      sources: ragResult.sources,
      createdAt: new Date().toISOString(),
    },
  });
});

// DELETE /api/chat/sessions/:id
chatRouter.delete("/sessions/:id", async (c) => {
  const supabase = c.get("supabase");
  const id = c.req.param("id");

  await supabase.from("chat_sessions").delete().eq("id", id);
  return c.json({ success: true });
});
