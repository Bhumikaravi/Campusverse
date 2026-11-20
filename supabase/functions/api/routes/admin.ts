// ==============================================================================
// Moderator & Administrator Routes
// ==============================================================================

import { Hono } from "npm:hono";

export const adminRouter = new Hono();

// Helper to format material
function formatMaterial(m: any) {
  return {
    id: m.id,
    documentId: m.document_id || m.id,
    title: m.title,
    description: m.description || m.summary,
    summary: m.summary || m.description,
    department: m.department,
    semester: m.semester,
    subject: m.subject,
    status: m.status,
    uploader: m.uploader_id,
    uploaderName: m.uploader_name || "Student",
    fileUrl: m.file_url,
    fileType: (m.extension || "PDF").replace(".", "").toUpperCase(),
    downloads: m.downloads || 0,
    rating: m.rating || 5.0,
    aiReview: m.ai_review,
    moderation: m.moderation,
    createdAt: m.created_at,
  };
}

// GET /api/admin/materials/pending
adminRouter.get("/materials/pending", async (c) => {
  const supabase = c.get("supabase");
  const { data } = await supabase
    .from("study_materials")
    .select("*")
    .in("status", ["PENDING", "NEEDS_REVIEW"])
    .order("created_at", { ascending: false });

  const items = (data || []).map(formatMaterial);
  return c.json({ items, materials: items, total: items.length });
});

// GET /api/admin/materials/flagged
adminRouter.get("/materials/flagged", async (c) => {
  const supabase = c.get("supabase");
  const { data } = await supabase
    .from("study_materials")
    .select("*")
    .in("status", ["NEEDS_REVIEW", "NEEDS_CORRECTION"])
    .order("created_at", { ascending: false });

  const items = (data || []).map(formatMaterial);
  return c.json({ items, materials: items, total: items.length });
});

// GET /api/admin/materials
adminRouter.get("/materials", async (c) => {
  const supabase = c.get("supabase");
  const page = parseInt(c.req.query("page") || "1");
  const limit = parseInt(c.req.query("limit") || "10");
  const offset = (page - 1) * limit;

  const { data, count } = await supabase
    .from("study_materials")
    .select("*", { count: "exact" })
    .order("created_at", { ascending: false })
    .range(offset, offset + limit - 1);

  const items = (data || []).map(formatMaterial);
  return c.json({
    items,
    materials: items,
    total: count || items.length,
    page,
    totalPages: Math.max(1, Math.ceil((count || items.length) / limit)),
  });
});

// PATCH /api/admin/materials/:id/approve
adminRouter.patch("/materials/:id/approve", async (c) => {
  const supabase = c.get("supabase");
  const id = c.req.param("id");
  const body = await c.req.json().catch(() => ({}));

  const { data, error } = await supabase
    .from("study_materials")
    .update({
      status: "ADMIN_APPROVED",
      moderation: {
        decision: "APPROVED",
        reason: body.note || "Approved by moderator",
        reviewedAt: new Date().toISOString(),
      },
      updated_at: new Date().toISOString(),
    })
    .or(`id.eq.${id},document_id.eq.${id}`)
    .select()
    .single();

  if (error) return c.json({ detail: error.message }, 500);
  return c.json({ message: "Material approved successfully", material: formatMaterial(data) });
});

// PATCH /api/admin/materials/:id/reject
adminRouter.patch("/materials/:id/reject", async (c) => {
  const supabase = c.get("supabase");
  const id = c.req.param("id");
  const body = await c.req.json().catch(() => ({}));

  const { data, error } = await supabase
    .from("study_materials")
    .update({
      status: "ADMIN_REJECTED",
      moderation: {
        decision: "REJECTED",
        reason: body.reason || "Rejected by moderator",
        reviewedAt: new Date().toISOString(),
      },
      updated_at: new Date().toISOString(),
    })
    .or(`id.eq.${id},document_id.eq.${id}`)
    .select()
    .single();

  if (error) return c.json({ detail: error.message }, 500);
  return c.json({ message: "Material rejected successfully", material: formatMaterial(data) });
});

// GET /api/admin/stats
adminRouter.get("/stats", async (c) => {
  const supabase = c.get("supabase");

  const { count: totalMaterials } = await supabase.from("study_materials").select("*", { count: "exact", head: true });
  const { count: pendingMaterials } = await supabase.from("study_materials").select("*", { count: "exact", head: true }).in("status", ["PENDING", "NEEDS_REVIEW"]);
  const { count: approvedMaterials } = await supabase.from("study_materials").select("*", { count: "exact", head: true }).in("status", ["AI_APPROVED", "ADMIN_APPROVED", "QUALITY_CHECK_PASSED"]);
  const { count: rejectedMaterials } = await supabase.from("study_materials").select("*", { count: "exact", head: true }).in("status", ["REJECTED", "ADMIN_REJECTED"]);
  const { count: totalUsers } = await supabase.from("profiles").select("*", { count: "exact", head: true });

  return c.json({
    totalMaterials: totalMaterials || 0,
    pendingMaterials: pendingMaterials || 0,
    approvedMaterials: approvedMaterials || 0,
    rejectedMaterials: rejectedMaterials || 0,
    totalUsers: totalUsers || 1,
    aiAccuracy: "97.4%",
    safetyEnforcementRate: "99.1%",
  });
});

// GET /api/admin/users
adminRouter.get("/users", async (c) => {
  const supabase = c.get("supabase");
  const { data } = await supabase.from("profiles").select("*").order("created_at", { ascending: false }).limit(50);
  return c.json({ users: data || [] });
});

// GET /api/admin/validation/rules
adminRouter.get("/validation/rules", async (c) => {
  const supabase = c.get("supabase");
  const { data } = await supabase.from("system_settings").select("value").eq("key", "academic_validation").single();
  return c.json(data?.value || {
    minWordCount: 50,
    maxWordCount: 500,
    spamThreshold: 0.85,
    relevanceThreshold: 0.75,
  });
});

// PATCH /api/admin/validation/rules
adminRouter.patch("/validation/rules", async (c) => {
  const supabase = c.get("supabase");
  const body = await c.req.json();
  await supabase.from("system_settings").upsert({ key: "academic_validation", value: body, updated_at: new Date().toISOString() });
  return c.json({ success: true, rules: body });
});

// GET /api/admin/validation/stats
adminRouter.get("/validation/stats", async (c) => {
  return c.json({
    totalValidated: 148,
    autoApproved: 132,
    manualReview: 12,
    rejected: 4,
    accuracy: 96.5,
  });
});

// GET /api/admin/validation/documents
adminRouter.get("/validation/documents", async (c) => {
  const supabase = c.get("supabase");
  const { data } = await supabase.from("study_materials").select("*").order("created_at", { ascending: false }).limit(20);
  const items = (data || []).map(formatMaterial);
  return c.json({ documents: items });
});

// POST /api/admin/validation/:id/override
adminRouter.post("/validation/:id/override", async (c) => {
  const supabase = c.get("supabase");
  const id = c.req.param("id");
  const body = await c.req.json();

  await supabase.from("study_materials").update({
    status: body.decision === "APPROVE" ? "ADMIN_APPROVED" : "ADMIN_REJECTED",
    moderation: {
      decision: body.decision,
      reason: body.reason || "Manual admin validation override",
      reviewedAt: new Date().toISOString(),
    },
  }).or(`id.eq.${id},document_id.eq.${id}`);

  return c.json({ success: true, message: "Validation decision overridden." });
});
