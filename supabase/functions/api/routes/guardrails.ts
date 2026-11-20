// ==============================================================================
// AI Safety & Guardrails Routes
// ==============================================================================

import { Hono } from "npm:hono";
import { evaluateInputGuardrails } from "../services/guardrails.ts";

export const guardrailsRouter = new Hono();

// GET /api/guardrails/status
guardrailsRouter.get("/status", (c) => {
  return c.json({
    totalEvaluated: 168,
    totalAllowed: 159,
    totalBlocked: 9,
    totalSanitized: 7,
    safeRatePercent: 94.6,
    injectionsBlocked: 6,
    harmBlocked: 3,
    malpracticeBlocked: 2,
    piiRedacted: 7,
    avgLatencyMs: 0.12,
    status: "ACTIVE_AND_ENFORCING",
    activePolicies: [
      {
        id: "PROMPT_INJECTION",
        name: "Prompt Injection & Jailbreak Shield",
        description: "Intercepts overrides, system prompt exfiltration, and persona jailbreaks",
        mode: "BLOCK",
        status: "ENABLED",
      },
      {
        id: "HARMFUL_CONTENT",
        name: "Harmful Content & Cyber Defense",
        description: "Blocks weapon synthesis, malware creation, and hate speech",
        mode: "BLOCK",
        status: "ENABLED",
      },
      {
        id: "PII_PROTECTION",
        name: "Personally Identifiable Information Shield",
        description: "Automatically redacts credit cards, phone numbers, and API keys",
        mode: "REDACT_AND_SANITIZE",
        status: "ENABLED",
      },
    ],
  });
});

// GET /api/guardrails/policies
guardrailsRouter.get("/policies", (c) => {
  return c.json({
    policies: [
      { id: "PROMPT_INJECTION", name: "Prompt Injection Defense", mode: "BLOCK" },
      { id: "HARMFUL_CONTENT", name: "Harmful Content & Cyber Defense", mode: "BLOCK" },
      { id: "PII_PROTECTION", name: "PII Masking Shield", mode: "REDACT_AND_SANITIZE" },
    ],
  });
});

// POST /api/guardrails/validate
guardrailsRouter.post("/validate", async (c) => {
  const body = await c.req.json();
  const text = body.text || "";
  const result = evaluateInputGuardrails(text);
  return c.json(result);
});
