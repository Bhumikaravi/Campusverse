// ==============================================================================
// Bookmarks and Downloads Routes
// ==============================================================================

import { Hono } from "npm:hono";
import { getBearerToken } from "./auth.ts";

export const bookmarksRouter = new Hono();
export const downloadsRouter = new Hono();

// GET /api/bookmarks
bookmarksRouter.get("/", async (c) => {
  const supabase = c.get("supabase");
  const token = getBearerToken(c.req.raw);
  if (!token) return c.json({ materials: [] });

  const { data: { user } } = await supabase.auth.getUser(token);
  if (!user) return c.json({ materials: [] });

  const { data: bookmarks } = await supabase
    .from("bookmarks")
    .select("material_id")
    .eq("user_id", user.id);

  if (!bookmarks || bookmarks.length === 0) return c.json({ materials: [] });

  const ids = bookmarks.map((b: any) => b.material_id);
  const { data: materials } = await supabase
    .from("study_materials")
    .select("*")
    .in("id", ids);

  const formatted = (materials || []).map((m: any) => ({
    id: m.id,
    documentId: m.document_id || m.id,
    title: m.title,
    description: m.description,
    department: m.department,
    semester: m.semester,
    subject: m.subject,
    fileUrl: m.file_url,
    bookmarked: true,
  }));

  return c.json({ materials: formatted });
});

// POST /api/bookmarks/:materialId
bookmarksRouter.post("/:materialId", async (c) => {
  const supabase = c.get("supabase");
  const materialId = c.req.param("materialId");
  const token = getBearerToken(c.req.raw);

  if (!token) return c.json({ detail: "Unauthorized" }, 401);
  const { data: { user } } = await supabase.auth.getUser(token);
  if (!user) return c.json({ detail: "Unauthorized" }, 401);

  // Check existing
  const { data: existing } = await supabase
    .from("bookmarks")
    .select("id")
    .eq("user_id", user.id)
    .eq("material_id", materialId)
    .single();

  if (existing) {
    await supabase.from("bookmarks").delete().eq("id", existing.id);
    return c.json({ success: true, bookmarked: false });
  } else {
    await supabase.from("bookmarks").insert({ user_id: user.id, material_id: materialId });
    return c.json({ success: true, bookmarked: true });
  }
});

// GET /api/downloads/history
downloadsRouter.get("/history", async (c) => {
  const supabase = c.get("supabase");
  const token = getBearerToken(c.req.raw);
  if (!token) return c.json({ history: [] });

  const { data: { user } } = await supabase.auth.getUser(token);
  if (!user) return c.json({ history: [] });

  const { data: history } = await supabase
    .from("downloads")
    .select("id, material_id, downloaded_at")
    .eq("user_id", user.id)
    .order("downloaded_at", { ascending: false });

  return c.json({ history: history || [] });
});
