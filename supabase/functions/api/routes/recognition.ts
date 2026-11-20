// ==============================================================================
// Recognition & Leaderboards Routes
// ==============================================================================

import { Hono } from "npm:hono";

export const recognitionRouter = new Hono();

// GET /api/recognition/today
recognitionRouter.get("/today", (c) => {
  return c.json({
    date: new Date().toISOString().split("T")[0],
    totalMaterialsEvaluated: 24,
    badges: [
      { id: "top-contributor", title: "Top Academic Contributor", recipient: "Bhumika Ravi", department: "Computer Science" },
      { id: "high-rated", title: "Highest Rated Material", recipient: "Operating Systems Lecture Notes", rating: 5.0 },
    ],
  });
});

// GET /api/recognition/leaderboard
recognitionRouter.get("/leaderboard", (c) => {
  const timeframe = c.req.query("timeframe") || "all";
  return c.json({
    timeframe,
    topContributors: [
      { id: "usr-1", name: "Bhumika Ravi", department: "Computer Science & Engineering", uploads: 14, totalDownloads: 3420, avgRating: 4.9 },
      { id: "usr-2", name: "Academic Faculty", department: "Information Technology", uploads: 11, totalDownloads: 2850, avgRating: 4.8 },
      { id: "usr-3", name: "Campus Moderator", department: "Electrical Engineering", uploads: 8, totalDownloads: 1940, avgRating: 4.8 },
    ],
    topMaterials: [
      { id: "mat-1", title: "Operating Systems - CPU Scheduling Notes", downloads: 1420, rating: 4.9 },
      { id: "mat-2", title: "Database Systems - Normalization Guide", downloads: 1280, rating: 4.8 },
    ],
    activeBatches: ["Batch 2023-2027", "Batch 2022-2026"],
  });
});
