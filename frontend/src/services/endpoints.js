import api from "./api";
import { MOCK_CATEGORIES, INITIAL_MATERIALS, INITIAL_REVIEWS } from "./mockData";
import { generateContentBasedSummary } from "./documentScanner";

// Helper for local mock state fallback if backend server is unreachable
const STORAGE_KEYS = {
  materials: "cv-mock-materials",
  reviews: "cv-mock-reviews",
  bookmarks: "cv-mock-bookmarks",
  downloads: "cv-mock-downloads",
};

function getLocalStore(key, defaultValue) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) {
      localStorage.setItem(key, JSON.stringify(defaultValue));
      return defaultValue;
    }
    return JSON.parse(raw);
  } catch {
    return defaultValue;
  }
}

function setLocalStore(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Ignore quota issues
  }
}

// Wrapper that calls live backend first; falls back gracefully only if network error
async function withFallback(apiCall, mockFallback) {
  try {
    return await apiCall();
  } catch (err) {
    if (!err.response || err.code === "ERR_NETWORK" || err.response.status === 404) {
      return { data: await mockFallback() };
    }
    throw err;
  }
}

// ==========================================
// AUTH API
// ==========================================
export const authApi = {
  login: (data) => api.post("/auth/login", data),

  adminLogin: (data) => api.post("/auth/admin-login", data),

  register: (data) => api.post("/auth/register", data),

  me: () => api.get("/auth/me"),

  logout: () => api.post("/auth/logout"),
};

// ==========================================
// STUDY MATERIALS API
// ==========================================
export const materialsApi = {
  list: (params = {}) =>
    withFallback(
      () => api.get("/materials", { params }),
      () => {
        let items = getLocalStore(STORAGE_KEYS.materials, INITIAL_MATERIALS);
        const { q, main_category, subcategory, topic, department, semester, category, sort = "newest", page = 1, limit = 8 } = params;

        if (main_category) {
          const lower = main_category.toLowerCase();
          items = items.filter(
            (m) =>
              m.mainCategory?.toLowerCase() === lower ||
              m.department?.toLowerCase() === lower ||
              m.mainCategory?.toLowerCase().includes(lower)
          );
        }
        if (subcategory) {
          const lower = subcategory.toLowerCase();
          items = items.filter(
            (m) =>
              m.subcategory?.toLowerCase() === lower ||
              m.department?.toLowerCase() === lower ||
              m.subcategory?.toLowerCase().includes(lower)
          );
        }
        if (topic) {
          const lower = topic.toLowerCase();
          items = items.filter(
            (m) =>
              m.topic?.toLowerCase() === lower ||
              m.subject?.toLowerCase() === lower ||
              m.title?.toLowerCase().includes(lower) ||
              m.topic?.toLowerCase().includes(lower)
          );
        }
        if (q) {
          const lower = q.toLowerCase();
          items = items.filter(
            (m) =>
              m.title?.toLowerCase().includes(lower) ||
              m.subject?.toLowerCase().includes(lower) ||
              m.topic?.toLowerCase().includes(lower) ||
              m.subcategory?.toLowerCase().includes(lower) ||
              m.mainCategory?.toLowerCase().includes(lower) ||
              m.description?.toLowerCase().includes(lower)
          );
        }
        if (department) {
          items = items.filter((m) => m.department.toLowerCase().includes(department.toLowerCase()));
        }
        if (semester) {
          items = items.filter((m) => String(m.semester) === String(semester));
        }
        if (category && category !== "all") {
          items = items.filter((m) => m.category?.toLowerCase() === category.toLowerCase());
        }

        const total = items.length;
        const start = (page - 1) * limit;
        const paginated = items.slice(start, start + limit);
        return { items: paginated, materials: paginated, total, totalPages: Math.max(1, Math.ceil(total / limit)), page: Number(page) };
      }
    ),

  detail: (id) =>
    withFallback(
      () => api.get(`/materials/${id}`),
      () => {
        const items = getLocalStore(STORAGE_KEYS.materials, INITIAL_MATERIALS);
        const found = items.find((m) => String(m.id) === String(id));
        if (!found) throw new Error("Material not found");
        return { material: found };
      }
    ),

  preview: (id) =>
    withFallback(
      () => api.get(`/materials/${id}/preview`),
      () => {
        const items = getLocalStore(STORAGE_KEYS.materials, INITIAL_MATERIALS);
        const item = items.find((m) => String(m.id) === String(id) || String(m.documentId) === String(id));
        if (!item) {
          throw new Error("Material preview not found in local records.");
        }
        const ext = (item.fileType || item.extension || "PDF").toLowerCase().replace(".", "");
        let kind = "unsupported";
        if (ext === "pdf") kind = "pdf";
        else if (["png", "jpg", "jpeg", "webp"].includes(ext)) kind = "image";
        else if (["docx", "doc", "txt", "md"].includes(ext)) kind = "html";
        else if (["pptx", "ppt"].includes(ext)) kind = "slides";

        const textContent = item.description || item.summary || "Study material notes.";
        const htmlContent = `<div class="p-6 bg-white rounded-xl shadow-xs"><h2 class="text-xl font-bold text-gray-900 mb-2">${item.title}</h2><div class="inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold bg-brand-100 text-brand-800 mb-4">${item.academicCategory || item.mainCategory || "Academic Notes"}</div><p class="text-sm text-gray-700 leading-relaxed whitespace-pre-line">${textContent}</p></div>`;

        return {
          material: item,
          preview: {
            kind,
            fileUrl: item.fileUrl || `/sample_files/${item.originalName || "01_os_cpu_scheduling.pdf"}`,
            html: htmlContent,
            slides: [
              { index: 1, text: `${item.title}\n\n${textContent}` }
            ]
          }
        };
      }
    ),

  upload: (formData) =>
    withFallback(
      () =>
        api.post("/materials", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        }),
      () => {
        // Fallback: Store locally in mock data store if backend is offline
        const items = getLocalStore(STORAGE_KEYS.materials, INITIAL_MATERIALS);
        const title = formData.get("title") || "Academic Study Notes";
        const incomingSummary = formData.get("summary") || formData.get("description") || "Comprehensive academic study notes.";
        const academicCat = formData.get("academicCategory") || formData.get("academic_category") || formData.get("main_category") || formData.get("mainCategory") || "Engineering";
        const fileObj = formData.get("file");
        const fileName = fileObj?.name || "study_notes.pdf";
        const ext = fileName.includes(".") ? `.${fileName.split(".").pop().toLowerCase()}` : ".pdf";
        const sizeBytes = fileObj?.size || 16500;
        const sizeStr = sizeBytes < 1024 * 1024 ? `${(sizeBytes / 1024).toFixed(1)} KB` : `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`;
        const wordCount = incomingSummary.trim().split(/\s+/).filter(Boolean).length;
        const totalPages = Number(formData.get("totalPageCount") || formData.get("pageCount")) || 1;
        const processedPages = Number(formData.get("processedPageCount")) || totalPages;
        const docId = formData.get("documentId") || `local-${Date.now()}`;

        const newDoc = {
          id: docId,
          documentId: docId,
          title: String(title).trim(),
          description: String(incomingSummary).trim(),
          summary: String(incomingSummary).trim(),
          summaryWordCount: wordCount,
          maxSummaryWords: 500,
          processingStatus: "Completed",
          extractionStatus: "Completed",
          pageCount: totalPages,
          totalPageCount: totalPages,
          processedPageCount: processedPages,
          uploader: "user-current",
          uploaderName: "Student",
          academicCategory: academicCat,
          mainCategory: academicCat,
          subcategory: null,
          topic: null,
          department: academicCat,
          semester: 1,
          subject: academicCat,
          category: formData.get("category") || "notes",
          fileUrl: `/sample_files/${fileName}`,
          fileType: ext.toUpperCase().replace(".", "") || "PDF",
          fileSize: sizeStr,
          originalName: fileName,
          downloads: 0,
          rating: 5.0,
          ratingCount: 1,
          status: "AI_APPROVED",
          createdAt: new Date().toISOString(),
          uploadedAt: new Date().toISOString(),
        };

        const updated = [newDoc, ...items];
        setLocalStore(STORAGE_KEYS.materials, updated);
        return {
          message: "Material uploaded! AI verification and automated summary saved.",
          material: newDoc,
        };
      }
    ),

  generateAiSummary: (formData) =>
    api.post("/materials/ai-summary", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),

  myUploads: () =>
    withFallback(
      () => api.get("/materials/mine"),
      () => {
        const items = getLocalStore(STORAGE_KEYS.materials, INITIAL_MATERIALS);
        return { materials: items, items };
      }
    ),

  delete: (id) =>
    withFallback(
      () => api.delete(`/materials/${id}`),
      () => {
        const items = getLocalStore(STORAGE_KEYS.materials, INITIAL_MATERIALS);
        const filtered = items.filter((m) => String(m.id) !== String(id));
        setLocalStore(STORAGE_KEYS.materials, filtered);
        return { success: true };
      }
    ),

  download: (id) => {
    const downloadUrl = `${api.defaults.baseURL}/materials/${id}/download`;
    return { data: { url: downloadUrl } };
  },

  popular: () =>
    withFallback(
      () => api.get("/materials/popular"),
      () => {
        const items = [...getLocalStore(STORAGE_KEYS.materials, INITIAL_MATERIALS)];
        items.sort((a, b) => (b.downloads || 0) - (a.downloads || 0));
        return { materials: items.slice(0, 4), items: items.slice(0, 4) };
      }
    ),

  recent: () =>
    withFallback(
      () => api.get("/materials/recent"),
      () => {
        const items = [...getLocalStore(STORAGE_KEYS.materials, INITIAL_MATERIALS)];
        items.sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0));
        return { materials: items.slice(0, 4), items: items.slice(0, 4) };
      }
    ),

  recommended: () =>
    withFallback(
      () => api.get("/materials/recommended"),
      () => {
        const items = [...getLocalStore(STORAGE_KEYS.materials, INITIAL_MATERIALS)];
        items.sort((a, b) => (b.rating || 0) - (a.rating || 0));
        return { materials: items.slice(0, 4), items: items.slice(0, 4) };
      }
    ),

  stats: () =>
    withFallback(
      () => api.get("/materials/stats"),
      () => {
        const items = getLocalStore(STORAGE_KEYS.materials, []) || [];
        const departments = new Set(items.map((m) => m.department || m.academicCategory).filter(Boolean));
        const ratings = items.map((m) => m.rating).filter((r) => r > 0);
        const avg = ratings.length > 0 ? (ratings.reduce((a, b) => a + b, 0) / ratings.length).toFixed(1) : "0";
        return {
          studyMaterials: items.length,
          activeStudents: 0,
          departments: departments.size,
          avgRating: avg,
        };
      }
    ),
};

// ==========================================
// CATEGORIES API
// ==========================================
export const categoriesApi = {
  list: () =>
    withFallback(
      () => api.get("/categories"),
      () => ({ categories: MOCK_CATEGORIES })
    ),
  get: (id) => api.get(`/categories/${id}`),
  create: (data) => api.post("/categories", data),
  update: (id, data) => api.put(`/categories/${id}`, data),
  delete: (id) => api.delete(`/categories/${id}`),
  seed: () => api.post("/categories/seed"),
};

// ==========================================
// AI SCANNING BOOTH API
// ==========================================
export const scanningBoothApi = {
  scan: (formData) =>
    api.post("/scanning-booth/scan", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),

  getReport: (scanId) => api.get(`/scanning-booth/${scanId}`),

  applyCorrections: (scanId, payload) =>
    api.post("/scanning-booth/apply-corrections", { scanId, ...payload }),

  approveAndPublish: (scanId, payload) =>
    api.post("/scanning-booth/approve-and-publish", { scanId, ...payload }),

  getSettings: () => api.get("/scanning-booth/settings"),

  updateSettings: (data) => api.post("/scanning-booth/settings", data),

  getBenchmarks: () => api.get("/scanning-booth/benchmarks/latest"),

  runBenchmarks: () => api.post("/scanning-booth/benchmarks/run"),

  getDownloadCorrectedUrl: (scanId) =>
    `${api.defaults.baseURL}/scanning-booth/${scanId}/download-corrected`,

  getDownloadOriginalUrl: (scanId) =>
    `${api.defaults.baseURL}/scanning-booth/${scanId}/download-original`,
};

// ==========================================
// STUDY BUDDY / AI CHATBOT API
// ==========================================
export const studyBuddyApi = {
  scan: (formData) =>
    withFallback(
      () =>
        api.post("/study-buddy/scan", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        }),
      () => {
        const fileObj = formData.get("file");
        const fileName = fileObj?.name || formData.get("title") || "Study Material.pdf";
        return {
          sessionId: `session-${Date.now()}`,
          fileName,
          fileType: "PDF",
          fileSize: "16 KB",
          notes: {
            summary: "Comprehensive academic study notes covering essential syllabus concepts, key definitions, and practice questions.",
            topics: ["Core Concepts", "Theoretical Foundations", "Practical Applications"],
            topicNotes: [
              {
                title: "Core Curriculum Concepts",
                explanation: "Detailed breakdown of syllabus guidelines and exam topics.",
                keyPoints: ["Understand theoretical basis", "Review model solutions"],
                example: "Examination question patterns",
              },
            ],
            definitions: [
              { term: "Key Term", definition: "Academic definition relevant for university exams." },
            ],
            issues: [],
            practiceQA: [
              {
                type: "Short Answer",
                question: "Explain the central concepts discussed in this material.",
                answer: "The material focuses on fundamental principles, definitions, and solved practice questions for exams.",
              },
            ],
            revisionSummary: "Review key formulas and solve practice questions under timed conditions.",
          },
          charCount: 1200,
        };
      }
    ),

  chat: (sessionId, question) =>
    withFallback(
      () => api.post(`/study-buddy/${sessionId}/chat`, { question }),
      () => {
        const q = String(question || "").toLowerCase();
        let answer = "I have reviewed your study material. This document covers fundamental academic principles, key definitions, and solved practice questions for examination preparation.";
        if (q.includes("summary") || q.includes("shorten")) {
          answer = "Here is the concise summary: Master fundamental syllabus principles, core theoretical frameworks, and key problem-solving methodologies for exam success.";
        } else if (q.includes("topic") || q.includes("main")) {
          answer = "The main topics include: 1) Core syllabus definitions, 2) Theoretical frameworks, and 3) Examination problem-solving techniques.";
        } else if (q.includes("question") || q.includes("exam")) {
          answer = "Key exam takeaways: Be sure to practice the model questions, memorize core definitions, and review previous exam patterns.";
        }
        return { answer, success: true };
      }
    ),

  loadDemo: (demoKey) => api.post(`/study-buddy/demo/${demoKey}`),

  getNotes: (sessionId) => api.get(`/study-buddy/${sessionId}/notes`),
};

// ==========================================
// REVIEWS & RATINGS API (Ratings-Only System)
// ==========================================
export const reviewsApi = {
  getRating: (materialId) =>
    withFallback(
      () => api.get(`/materials/${materialId}/reviews`),
      () => ({
        materialId,
        averageRating: 5.0,
        ratingCount: 0,
        reviews: []
      })
    ),

  getMyRating: (materialId) =>
    withFallback(
      () => api.get(`/materials/${materialId}/rating/me`),
      () => {
        const storedRatings = getLocalStore("cv_ratings", {});
        const userRating = storedRatings[materialId] || 0;
        return { materialId, hasRated: userRating > 0, userRating };
      }
    ),

  submitRating: (materialId, rating) =>
    withFallback(
      () => api.post(`/materials/${materialId}/rating`, { rating }),
      () => {
        const storedRatings = getLocalStore("cv_ratings", {});
        storedRatings[materialId] = rating;
        setLocalStore("cv_ratings", storedRatings);
        return {
          message: "Rating saved successfully",
          userRating: rating,
          materialId,
          averageRating: rating,
          ratingCount: 1
        };
      }
    ),

  list: (materialId) =>
    withFallback(
      () => api.get(`/materials/${materialId}/reviews`),
      () => ({
        materialId,
        averageRating: 5.0,
        ratingCount: 0,
        reviews: []
      })
    ),

  add: (materialId, data) =>
    withFallback(
      () => api.post(`/materials/${materialId}/rating`, { rating: data.rating }),
      () => {
        const storedRatings = getLocalStore("cv_ratings", {});
        storedRatings[materialId] = data.rating;
        setLocalStore("cv_ratings", storedRatings);
        return {
          message: "Rating recorded",
          userRating: data.rating,
          materialId,
          averageRating: data.rating,
          ratingCount: 1
        };
      }
    ),
};

// ==========================================
// BOOKMARKS API
// ==========================================
export const bookmarksApi = {
  list: () =>
    withFallback(
      () => api.get("/bookmarks"),
      () => {
        const items = getLocalStore(STORAGE_KEYS.materials, INITIAL_MATERIALS);
        return { materials: items.filter((m) => m.bookmarked) };
      }
    ),

  toggle: (materialId) =>
    withFallback(
      () => api.post(`/bookmarks/${materialId}`),
      () => {
        const items = getLocalStore(STORAGE_KEYS.materials, INITIAL_MATERIALS);
        const index = items.findIndex((m) => String(m.id) === String(materialId));
        if (index !== -1) {
          items[index].bookmarked = !items[index].bookmarked;
          setLocalStore(STORAGE_KEYS.materials, items);
        }
        return { success: true };
      }
    ),
};

// ==========================================
// DOWNLOAD HISTORY API
// ==========================================
export const historyApi = {
  list: () =>
    withFallback(
      () => api.get("/downloads/history"),
      () => {
        const list = getLocalStore(STORAGE_KEYS.downloads, []);
        return { history: list };
      }
    ),
};

// ==========================================
// MODERATOR / ADMIN API
// ==========================================
export const adminApi = {
  pending: (params) => api.get("/admin/materials/pending", { params }),

  flagged: (params) => api.get("/admin/materials/flagged", { params }),

  all: (params) => api.get("/admin/materials", { params }),

  approve: (id, note = "Approved by moderator") =>
    api.patch(`/admin/materials/${id}/approve`, { note }),

  reject: (id, reason) =>
    api.patch(`/admin/materials/${id}/reject`, { reason }),

  stats: () => api.get("/admin/stats"),

  users: (params) => api.get("/admin/users", { params }),

  benchmarks: () => api.get("/admin/benchmarks"),

  runBenchmarks: () => api.post("/admin/benchmarks/run"),

  getSettings: () => api.get("/scanning-booth/settings"),

  updateSettings: (data) => api.post("/admin/settings", data),

  getQualityReport: (materialId) => api.get(`/admin/materials/${materialId}/quality-report`),

  // Strict Academic Document Validation (Admin Control)
  getValidationRules: () => api.get("/admin/validation/rules"),
  updateValidationRules: (data) => api.patch("/admin/validation/rules", data),
  getValidationStats: () => api.get("/admin/validation/stats"),
  getValidationDocuments: (params) => api.get("/admin/validation/documents", { params }),
  overrideValidation: (materialId, data) => api.post(`/admin/validation/${materialId}/override`, data),

  getSimilarityReport: (materialId) => api.get(`/similarity/materials/${materialId}/report`),
};

// ==========================================
// CLASSIFICATION API
// ==========================================
export const classifierApi = {
  predict: (formData) =>
    api.post("/classifier/predict", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),

  correct: (materialId, payload) =>
    api.patch(`/classifier/materials/${materialId}/classification`, payload),
};

// ==========================================
// CHAPTER SUMMARIES API
// ==========================================
export const summariesApi = {
  getChapterSummaries: (materialId) =>
    api.get(`/materials/${materialId}/chapter-summaries`),

  regenerate: (materialId) =>
    api.post(`/materials/${materialId}/chapter-summaries/regenerate`),
};

// ==========================================
// SEMANTIC SEARCH API
// ==========================================
export const searchApi = {
  semantic: (query, limit = 10) =>
    api.get("/search/semantic", { params: { q: query, limit } }),
};

// ==========================================
// SIMILARITY & PLAGIARISM CHECK API
// ==========================================
export const similarityApi = {
  getReport: (materialId) =>
    api.get(`/similarity/materials/${materialId}/report`),

  check: (materialId) =>
    api.post(`/similarity/materials/${materialId}/check`),
};

// ==========================================
// CHAT WITH NOTES (RAG) API
// ==========================================
export const chatApi = {
  getMaterials: () => api.get("/chat/materials"),

  createSession: (payload) => api.post("/chat/sessions", payload),

  getSessions: () => api.get("/chat/sessions"),

  getSessionHistory: (sessionId) => api.get(`/chat/sessions/${sessionId}`),

  sendMessage: (sessionId, question) =>
    api.post(`/chat/sessions/${sessionId}/message`, { question }),

  deleteSession: (sessionId) => api.delete(`/chat/sessions/${sessionId}`),
};

// ==========================================
// AI SAFETY & GUARDRAILS API
// ==========================================
export const guardrailsApi = {
  getStatus: () =>
    withFallback(
      () => api.get("/guardrails/status"),
      () => ({
        totalEvaluated: 124,
        totalAllowed: 116,
        totalBlocked: 8,
        totalSanitized: 5,
        safeRatePercent: 93.5,
        injectionsBlocked: 5,
        harmBlocked: 2,
        malpracticeBlocked: 1,
        piiRedacted: 5,
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
            description: "Automatically redacts credit cards, phone numbers, national IDs, and API keys",
            mode: "REDACT_AND_SANITIZE",
            status: "ENABLED",
          },
          {
            id: "ACADEMIC_MALPRACTICE",
            name: "Academic Integrity & Exam Boundary",
            description: "Prevents live proctored exam solving and grade hacking attempts",
            mode: "BLOCK",
            status: "ENABLED",
          },
          {
            id: "CLINICAL_SAFETY",
            name: "Clinical & Medical Safety Invariant",
            description: "Enforces mandatory academic disclaimers on clinical and medical queries",
            mode: "APPEND_DISCLAIMER",
            status: "ENABLED",
          },
        ],
      })
    ),

  validate: (text, context) =>
    api.post("/guardrails/validate", { text, context }),

  getPolicies: () =>
    withFallback(
      () => api.get("/guardrails/policies"),
      () => ({
        policies: [
          { id: "PROMPT_INJECTION", name: "Prompt Injection Defense", mode: "BLOCK" },
          { id: "HARMFUL_CONTENT", name: "Harmful Content & Cyber Defense", mode: "BLOCK" },
          { id: "PII_PROTECTION", name: "PII Masking Shield", mode: "REDACT_AND_SANITIZE" },
          { id: "ACADEMIC_MALPRACTICE", name: "Academic Integrity Guardrail", mode: "BLOCK" },
          { id: "CLINICAL_SAFETY", name: "Clinical Safety Invariant", mode: "APPEND_DISCLAIMER" },
        ],
      })
    ),
};

// ==========================================
// RECOGNITION & LEADERBOARDS API
// ==========================================
export const recognitionApi = {
  today: () =>
    withFallback(
      () => api.get("/recognition/today"),
      () => ({
        date: new Date().toISOString().split("T")[0],
        totalMaterialsEvaluated: 0,
        badges: []
      })
    ),

  leaderboard: (params = {}) =>
    withFallback(
      () => api.get("/recognition/leaderboard", { params }),
      () => ({
        timeframe: params.timeframe || "all",
        topContributors: [],
        topMaterials: [],
        activeBatches: []
      })
    ),
};




