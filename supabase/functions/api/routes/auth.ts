// ==============================================================================
// Authentication Routes (Supabase Auth Integration)
// ==============================================================================

import { Hono } from "npm:hono";

export const authRouter = new Hono();

// Helper to extract bearer token
export function getBearerToken(req: Request): string | null {
  const authHeader = req.headers.get("Authorization");
  if (!authHeader || !authHeader.startsWith("Bearer ")) return null;
  return authHeader.substring(7).trim();
}

// POST /api/auth/register
authRouter.post("/register", async (c) => {
  const supabase = c.get("supabase");
  const body = await c.req.json();
  const { email, password, name, full_name, department, course, academicYear, batch, semester } = body;

  const resolvedName = (full_name || name || email.split("@")[0]).trim();
  const cleanEmail = email.trim().toLowerCase();

  const { data, error } = await supabase.auth.signUp({
    email: cleanEmail,
    password,
    options: {
      data: {
        name: resolvedName,
        full_name: resolvedName,
        department,
        course,
        academicYear,
        batch,
        semester,
        role: "student",
      },
    },
  });

  if (error) {
    return c.json({ detail: error.message }, 400);
  }

  const user = data.user;
  const token = data.session?.access_token || "";

  // Query profile
  const { data: profile } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", user?.id)
    .single();

  const userObj = {
    id: user?.id,
    email: user?.email,
    name: profile?.name || resolvedName,
    full_name: profile?.full_name || resolvedName,
    role: profile?.role || "student",
    department: profile?.department || department,
    course: profile?.course || course,
    academicYear: profile?.academic_year || academicYear,
    batch: profile?.batch || batch,
    semester: profile?.semester || semester,
  };

  return c.json({
    message: "User registered successfully",
    token,
    user: userObj,
  }, 201);
});

// POST /api/auth/login
authRouter.post("/login", async (c) => {
  const supabase = c.get("supabase");
  const body = await c.req.json();
  const { email, password } = body;

  const cleanEmail = (email || "").trim().toLowerCase();

  const { data, error } = await supabase.auth.signInWithPassword({
    email: cleanEmail,
    password,
  });

  if (error) {
    return c.json({ detail: error.message || "Invalid email or password." }, 401);
  }

  const user = data.user;
  const token = data.session?.access_token || "";

  // Get profile
  const { data: profile } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", user.id)
    .single();

  const userObj = {
    id: user.id,
    email: user.email,
    name: profile?.name || user.user_metadata?.name || user.email?.split("@")[0],
    full_name: profile?.full_name || user.user_metadata?.full_name || user.email?.split("@")[0],
    role: profile?.role || user.user_metadata?.role || "student",
    department: profile?.department || user.user_metadata?.department,
    course: profile?.course || user.user_metadata?.course,
    academicYear: profile?.academic_year || user.user_metadata?.academicYear,
    batch: profile?.batch || user.user_metadata?.batch,
    semester: profile?.semester || user.user_metadata?.semester,
  };

  return c.json({
    message: "Login successful",
    token,
    user: userObj,
  });
});

// POST /api/auth/admin-login
authRouter.post("/admin-login", async (c) => {
  const supabase = c.get("supabase");
  const body = await c.req.json();
  const { email, password } = body;

  const cleanEmail = (email || "").trim().toLowerCase();

  const { data, error } = await supabase.auth.signInWithPassword({
    email: cleanEmail,
    password,
  });

  if (error) {
    return c.json({ detail: "Invalid admin credentials." }, 401);
  }

  const user = data.user;

  // Verify staff role
  const { data: profile } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", user.id)
    .single();

  const role = profile?.role || user.user_metadata?.role;
  if (role !== "admin" && role !== "moderator") {
    return c.json({ detail: "Access denied. Admin or moderator privileges required." }, 403);
  }

  const userObj = {
    id: user.id,
    email: user.email,
    name: profile?.name || "CampusVerse Admin",
    full_name: profile?.full_name || "CampusVerse Admin",
    role,
    department: profile?.department || "Administration",
  };

  return c.json({
    message: "Admin authentication successful",
    token: data.session?.access_token || "",
    user: userObj,
  });
});

// GET /api/auth/me
authRouter.get("/me", async (c) => {
  const supabase = c.get("supabase");
  const token = getBearerToken(c.req.raw);

  if (!token) {
    return c.json({ detail: "Not authenticated" }, 401);
  }

  const { data: { user }, error } = await supabase.auth.getUser(token);
  if (error || !user) {
    return c.json({ detail: "Session expired or invalid" }, 401);
  }

  const { data: profile } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", user.id)
    .single();

  const userObj = {
    id: user.id,
    email: user.email,
    name: profile?.name || user.user_metadata?.name || user.email?.split("@")[0],
    full_name: profile?.full_name || user.user_metadata?.full_name || user.email?.split("@")[0],
    role: profile?.role || user.user_metadata?.role || "student",
    department: profile?.department,
    course: profile?.course,
    academicYear: profile?.academic_year,
    batch: profile?.batch,
    semester: profile?.semester,
  };

  return c.json({ user: userObj });
});

// POST /api/auth/logout
authRouter.post("/logout", async (c) => {
  const supabase = c.get("supabase");
  const token = getBearerToken(c.req.raw);
  if (token) {
    await supabase.auth.admin?.signOut(token).catch(() => {});
  }
  return c.json({ message: "Logged out successfully" });
});
