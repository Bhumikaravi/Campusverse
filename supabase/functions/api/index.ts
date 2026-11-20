// ==============================================================================
// CampusVerse Unified Supabase Edge Function API Entrypoint
// Powered by Hono on Deno Runtime
// ==============================================================================

import { Hono } from "npm:hono";
import { createClient } from "npm:@supabase/supabase-js";

import { authRouter } from "./routes/auth.ts";
import { materialsRouter } from "./routes/materials.ts";
import { chatRouter } from "./routes/chat.ts";
import { studyBuddyRouter } from "./routes/studyBuddy.ts";
import { scanningBoothRouter } from "./routes/scanningBooth.ts";
import { adminRouter } from "./routes/admin.ts";
import { categoriesRouter } from "./routes/categories.ts";
import { searchRouter } from "./routes/search.ts";
import { guardrailsRouter } from "./routes/guardrails.ts";
import { recognitionRouter } from "./routes/recognition.ts";
import { bookmarksRouter, downloadsRouter } from "./routes/bookmarks.ts";

export const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, GET, OPTIONS, PUT, DELETE, PATCH",
  "Access-Control-Max-Age": "86400",
};

const app = new Hono();

// Inject Supabase Admin Client into context
app.use("*", async (c, next) => {
  const supabaseUrl = Deno.env.get("SUPABASE_URL") || "https://eeklurlqjcdcspmjlwlc.supabase.co";
  const supabaseServiceKey =
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ||
    Deno.env.get("SUPABASE_ANON_KEY") ||
    "";

  const supabase = createClient(supabaseUrl, supabaseServiceKey, {
    auth: { persistSession: false },
  });

  c.set("supabase", supabase);
  await next();
});

// Root Health Check
app.get("/", (c) =>
  c.json({ status: "healthy", service: "CampusVerse Supabase Edge API", version: "2.0.0" })
);
app.get("/health", (c) => c.json({ status: "ok", time: new Date().toISOString() }));

// Mount Sub-routers (both with and without '/api' prefix for bulletproof routing)
const mountRouters = (prefix: string) => {
  app.route(`${prefix}/auth`, authRouter);
  app.route(`${prefix}/materials`, materialsRouter);
  app.route(`${prefix}/chat`, chatRouter);
  app.route(`${prefix}/study-buddy`, studyBuddyRouter);
  app.route(`${prefix}/scanning-booth`, scanningBoothRouter);
  app.route(`${prefix}/admin`, adminRouter);
  app.route(`${prefix}/categories`, categoriesRouter);
  app.route(`${prefix}/search`, searchRouter);
  app.route(`${prefix}/guardrails`, guardrailsRouter);
  app.route(`${prefix}/recognition`, recognitionRouter);
  app.route(`${prefix}/bookmarks`, bookmarksRouter);
  app.route(`${prefix}/downloads`, downloadsRouter);
};

mountRouters("");
mountRouters("/api");

// Global 404 Handler
app.notFound((c) => c.json({ error: "Endpoint not found", path: c.req.path }, 404));

// Global Error Handler
app.onError((err, c) => {
  console.error("Unhandled Edge API error:", err);
  return c.json({ error: err.message || "Internal Server Error" }, 500);
});

// Top-level Deno fetch handler with guaranteed CORS preflight
Deno.serve(async (req) => {
  // Explicitly answer all OPTIONS preflight requests with 200 OK
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  const res = await app.fetch(req);
  const headers = new Headers(res.headers);
  Object.entries(corsHeaders).forEach(([k, v]) => headers.set(k, v));

  return new Response(res.body, {
    status: res.status,
    headers,
  });
});
