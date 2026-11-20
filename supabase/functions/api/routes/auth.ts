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

  let user: any = null;
  let token = "";

  // 1. Try to auto-confirm user with admin API so they don't get blocked by email verification
  try {
    const adminRes = await supabase.auth.admin.createUser({
      email: cleanEmail,
      password,
      email_confirm: true,
      user_metadata: {
        name: resolvedName,
        full_name: resolvedName,
        department,
        course: course || "Computer Science and Engineering",
        academicYear: academicYear || "3rd Year",
        batch: batch || "Batch 2023-2027",
        semester: semester || 1,
        role: "student",
      },
    });

    if (!adminRes.error && adminRes.data?.user) {
      user = adminRes.data.user;
      // Generate active session token
      const signin = await supabase.auth.signInWithPassword({
        email: cleanEmail,
        password,
      });
      token = signin.data?.session?.access_token || "";
    }
  } catch (err) {
    console.warn("Admin createUser notice, falling back to signUp:", err);
  }

  // 2. Fallback to standard signUp if admin API is restricted
  if (!user) {
    const { data: signUpData, error: signUpErr } = await supabase.auth.signUp({
      email: cleanEmail,
      password,
      options: {
        data: {
          name: resolvedName,
          full_name: resolvedName,
          department,
          course: course || "Computer Science and Engineering",
          academicYear: academicYear || "3rd Year",
          batch: batch || "Batch 2023-2027",
          semester: semester || 1,
          role: "student",
        },
      },
    });

    if (signUpErr) {
      return c.json({ detail: signUpErr.message }, 400);
    }

    user = signUpData.user;
    token = signUpData.session?.access_token || "";
  }

  // Ensure user profile in public.profiles table exists
  if (user) {
    await supabase.from("profiles").upsert(
      {
        id: user.id,
        email: user.email,
        name: resolvedName,
        full_name: resolvedName,
        role: "student",
        department,
        course,
        academic_year: academicYear,
        batch,
        semester,
      },
      { onConflict: "id" }
    ).catch(() => {});
  }

  const userObj = {
    id: user?.id,
    email: user?.email,
    name: resolvedName,
    full_name: resolvedName,
    role: "student",
    department,
    course,
    academicYear,
    batch,
    semester,
  };

  return c.json(
    {
      message: "User registered successfully",
      token,
      user: userObj,
    },
    201
  );
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
    // If error is "Email not confirmed", try to auto-confirm user if admin key is available
    if (error.message?.toLowerCase().includes("email not confirmed")) {
      try {
        const { data: usersData } = await supabase.auth.admin.listUsers();
        const found = (usersData?.users || []).find((u: any) => u.email?.toLowerCase() === cleanEmail);
        if (found) {
          await supabase.auth.admin.updateUserById(found.id, { email_confirm: true });
          // Retry login
          const retry = await supabase.auth.signInWithPassword({ email: cleanEmail, password });
          if (!retry.error) {
            return c.json({
              message: "Login successful",
              token: retry.data.session?.access_token || "",
              user: {
                id: retry.data.user.id,
                email: retry.data.user.email,
                name: retry.data.user.user_metadata?.name || retry.data.user.email?.split("@")[0],
                role: retry.data.user.user_metadata?.role || "student",
              },
            });
          }
        }
      } catch (adminErr) {
        console.warn("Auto-confirm fallback notice:", adminErr);
      }
    }
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
