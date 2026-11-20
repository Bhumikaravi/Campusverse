// ==============================================================================
// Chat With Notes (RAG) Routes
// ==============================================================================

import { Hono } from "npm:hono";
import { executeRAG } from "../services/ragEngine.ts";
import { getBearerToken } from "./auth.ts";

export const chatRouter = new Hono();

function isUuid(str: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(str);
}

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

  let userId: string | null = null;
  if (token) {
    const { data: { user } } = await supabase.auth.getUser(token);
    if (user) {
      userId = user.id;
      // Guarantee profile exists for foreign key
      await supabase.from("profiles").upsert({
        id: user.id,
        name: user.user_metadata?.name || user.user_metadata?.full_name || user.email?.split("@")[0] || "Student",
        email: user.email,
        role: user.user_metadata?.role || "student",
      }, { onConflict: "id" }).catch(() => {});
    }
  }

  const sessionTitle = title || "Study Session";
  const newUuid = crypto.randomUUID();

  if (userId) {
    const { data: session, error } = await supabase
      .from("chat_sessions")
      .insert({
        id: newUuid,
        user_id: userId,
        title: sessionTitle,
        material_ids: materialIds || [],
      })
      .select()
      .single();

    if (!error && session) {
      return c.json({
        id: session.id,
        sessionId: session.id,
        title: session.title,
        materialIds: session.material_ids,
        createdAt: session.created_at,
      }, 201);
    }
  }

  // Ephemeral or guest session with valid UUID
  return c.json({
    id: newUuid,
    sessionId: newUuid,
    title: sessionTitle,
    materialIds: materialIds || [],
    createdAt: new Date().toISOString(),
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

  const formatted = (sessions || []).map((s: any) => ({
    id: s.id,
    sessionId: s.id,
    title: s.title,
    materialIds: s.material_ids || [],
    createdAt: s.created_at,
    updatedAt: s.updated_at,
  }));

  return c.json({ sessions: formatted });
});

// GET /api/chat/sessions/:id
chatRouter.get("/sessions/:id", async (c) => {
  const supabase = c.get("supabase");
  const id = c.req.param("id");

  let session: any = null;
  let messages: any[] = [];

  if (isUuid(id)) {
    try {
      const { data: s } = await supabase
        .from("chat_sessions")
        .select("*")
        .eq("id", id)
        .single();
      session = s;

      const { data: m } = await supabase
        .from("chat_messages")
        .select("*")
        .eq("session_id", id)
        .order("created_at", { ascending: true });
      messages = m || [];
    } catch {
      // Ignore database notice
    }
  }

  return c.json({
    session: session || { id, sessionId: id, title: "Study Session" },
    messages,
  });
});

// POST /api/chat/sessions/:id/message
chatRouter.post("/sessions/:id/message", async (c) => {
  const supabase = c.get("supabase");
  const id = c.req.param("id");
  const body = await c.req.json();
  const { question } = body;

  let session: any = null;
  let materialIds: string[] = [];
  let history: Array<{ role: string; content: string }> = [];

  if (isUuid(id)) {
    try {
      const { data: s } = await supabase
        .from("chat_sessions")
        .select("*")
        .eq("id", id)
        .single();
      session = s;
      materialIds = session?.material_ids || [];

      // Fetch recent history
      const { data: pastMsgs } = await supabase
        .from("chat_messages")
        .select("role, content")
        .eq("session_id", id)
        .order("created_at", { ascending: true })
        .limit(6);

      history = (pastMsgs || []).map((m: any) => ({ role: m.role, content: m.content }));
    } catch {
      // Continue to RAG execution
    }
  }

  // Run Grounded RAG Pipeline
  const ragResult = await executeRAG(question, materialIds, supabase, history);

  // Record user and assistant messages if persistent session exists
  if (session && isUuid(id)) {
    try {
      await supabase.from("chat_messages").insert([
        { session_id: id, role: "user", content: question },
        { session_id: id, role: "assistant", content: ragResult.answer, sources: ragResult.sources },
      ]);

      await supabase
        .from("chat_sessions")
        .update({ updated_at: new Date().toISOString() })
        .eq("id", id);
    } catch {
      // Continue
    }
  }

  return c.json({
    role: "assistant",
    content: ragResult.answer,
    answer: ragResult.answer,
    sources: ragResult.sources,
    message: {
      role: "assistant",
      content: ragResult.answer,
      sources: ragResult.sources,
      createdAt: new Date().toISOString(),
    },
    createdAt: new Date().toISOString(),
  });
});

// DELETE /api/chat/sessions/:id
chatRouter.delete("/sessions/:id", async (c) => {
  const supabase = c.get("supabase");
  const id = c.req.param("id");

  if (isUuid(id)) {
    await supabase.from("chat_sessions").delete().eq("id", id).catch(() => {});
  }
  return c.json({ success: true });
});
