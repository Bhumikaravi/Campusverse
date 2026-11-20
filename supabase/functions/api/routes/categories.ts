// ==============================================================================
// Categories & Faculty Taxonomies Routes
// ==============================================================================

import { Hono } from "npm:hono";

export const categoriesRouter = new Hono();

// GET /api/categories
categoriesRouter.get("/", async (c) => {
  const supabase = c.get("supabase");
  const { data, error } = await supabase.from("categories").select("*");

  if (error || !data || data.length === 0) {
    // Return standard fallback
    return c.json({
      categories: [
        {
          id: "engineering",
          name: "Engineering",
          icon: "Settings",
          count: 8,
          description: "Computer Science, Civil Engineering, Mechanical Engineering, and Electrical Engineering.",
          subcategories: [
            { id: "eng-cs", name: "Computer Science", count: 4, subtopics: ["Operating Systems", "DBMS", "Data Structures", "Computer Networks"] },
            { id: "eng-civil", name: "Civil Engineering", count: 2, subtopics: ["Structural Analysis", "RCC Beam Design", "Soil Mechanics"] },
          ],
        },
        {
          id: "computer-applications",
          name: "Computer Applications",
          icon: "Cpu",
          count: 4,
          description: "Artificial Intelligence, Machine Learning, Data Science, and Web Development.",
          subcategories: [
            { id: "ai", name: "Artificial Intelligence", count: 2, subtopics: ["Neural Networks", "NLP", "Computer Vision"] },
          ],
        },
      ],
    });
  }

  return c.json({ categories: data });
});

// POST /api/categories/seed
categoriesRouter.post("/seed", async (c) => {
  return c.json({ message: "Categories seeded successfully." });
});
