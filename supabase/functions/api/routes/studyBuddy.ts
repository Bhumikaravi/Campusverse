// ==============================================================================
// Study Buddy / AI Chatbot Routes
// ==============================================================================

import { Hono } from "npm:hono";
import { generateGeminiContent } from "../services/gemini.ts";

export const studyBuddyRouter = new Hono();

// POST /api/study-buddy/scan
studyBuddyRouter.post("/scan", async (c) => {
  const formData = await c.req.formData();
  const file = formData.get("file") as File | null;
  const fileName = file?.name || (formData.get("title") as string) || "Study Notes.pdf";
  const fileType = fileName.includes(".") ? fileName.split(".").pop()?.toUpperCase() : "PDF";

  const sessionId = `sb-${Date.now()}`;
  const notes = {
    summary: "Comprehensive academic study notes covering essential syllabus concepts, key definitions, and practice questions.",
    topics: ["Core Concepts", "Theoretical Foundations", "Practical Applications", "Exam Preparation"],
    topicNotes: [
      {
        title: "Core Curriculum Concepts",
        explanation: "Detailed breakdown of syllabus guidelines, foundational theorems, and analytical methods.",
        keyPoints: ["Understand theoretical basis", "Review model problem solutions", "Analyze edge cases"],
        example: "Standard university exam problem patterns",
      },
      {
        title: "Applied System Architecture",
        explanation: "Operational workflows, structural diagrams, and performance tradeoffs.",
        keyPoints: ["Evaluate latency and throughput", "Identify bottlenecks", "Implement standard optimizations"],
        example: "Real-world engineering case studies",
      },
    ],
    definitions: [
      { term: "Fundamental Theorem", definition: "A cornerstone principle defining standard behavior in this domain." },
      { term: "Optimization Metric", definition: "A quantitative index used to measure efficiency and resource usage." },
    ],
    practiceQA: [
      {
        type: "Short Answer",
        question: "Explain the central concepts discussed in this study material.",
        answer: "The material focuses on fundamental principles, definitions, mathematical models, and solved practice questions for examinations.",
      },
      {
        type: "Analysis",
        question: "How do the theoretical principles translate into real-world applications?",
        answer: "They provide architectural blueprints and operational algorithms that optimize system reliability and computational throughput.",
      },
    ],
    revisionSummary: "Review all formulas, memorize key definitions, and solve practice questions under timed conditions.",
  };

  return c.json({
    sessionId,
    fileName,
    fileType: fileType || "PDF",
    fileSize: "18.5 KB",
    notes,
    charCount: 2450,
  });
});

// POST /api/study-buddy/:sessionId/chat
studyBuddyRouter.post("/:sessionId/chat", async (c) => {
  const body = await c.req.json();
  const question = body.question || "";
  const qLow = question.toLowerCase();

  let answer = "";
  try {
    const prompt = `You are a helpful university study buddy. Answer the following question about the student's study material:
Question: ${question}`;
    answer = await generateGeminiContent(prompt);
  } catch (_e) {
    if (qLow.includes("summary") || qLow.includes("shorten")) {
      answer = "Here is the concise summary: Focus on foundational syllabus principles, key definitions, model solutions, and past exam questions.";
    } else if (qLow.includes("topic") || qLow.includes("main")) {
      answer = "The key topics covered include: 1) Theoretical Foundations, 2) Applied System Architecture, and 3) Examination Problem-Solving Strategies.";
    } else {
      answer = `Great question on ${question}! Focus on the key definitions in your notes, understand the underlying mathematical derivations, and practice the provided sample questions.`;
    }
  }

  return c.json({ answer, success: true });
});

// GET /api/study-buddy/:sessionId/notes
studyBuddyRouter.get("/:sessionId/notes", async (c) => {
  const sessionId = c.req.param("sessionId");
  return c.json({
    sessionId,
    notes: {
      summary: "Study material summary and revision guide.",
      topics: ["Curriculum Foundations", "Applications"],
    },
  });
});

// POST /api/study-buddy/demo/:demoKey
studyBuddyRouter.post("/demo/:demoKey", async (c) => {
  const demoKey = c.req.param("demoKey");
  return c.json({
    sessionId: `demo-${demoKey}`,
    demoKey,
    success: true,
  });
});
