import { useState, useEffect, useRef } from "react";
import { useSearchParams, Link } from "react-router-dom";
import {
  Bot,
  Send,
  Plus,
  Trash2,
  FileText,
  Sparkles,
  BookOpen,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  ChevronRight,
  MessageSquare,
  ShieldCheck,
  ShieldAlert,
  Shield,
  X,
} from "lucide-react";
import { chatApi } from "../services/endpoints";
import { useToast } from "../context/ToastContext";
import Loader from "../components/Loader";
import MarkdownSummary from "../components/MarkdownSummary";

export default function ChatWithNotes() {
  const [searchParams] = useSearchParams();
  const initialMaterialId = searchParams.get("materialId");
  const { showToast } = useToast();

  const [availableMaterials, setAvailableMaterials] = useState([]);
  const [selectedMaterialIds, setSelectedMaterialIds] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [currentSession, setCurrentSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputQuestion, setInputQuestion] = useState("");
  const [loadingMaterials, setLoadingMaterials] = useState(true);
  const [sending, setSending] = useState(false);
  const [showGuardrailsModal, setShowGuardrailsModal] = useState(false);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, sending]);

  // Load available materials & sessions on mount
  const loadMaterialsAndSessions = () => {
    setLoadingMaterials(true);
    Promise.all([chatApi.getMaterials(), chatApi.getSessions()])
      .then(([matRes, sessRes]) => {
        let mats = matRes?.data?.materials || [];
        if (mats.length === 0) {
          try {
            const rawMock = localStorage.getItem("cv-mock-materials");
            if (rawMock) {
              const localItems = JSON.parse(rawMock);
              if (Array.isArray(localItems) && localItems.length > 0) {
                mats = localItems.map((m) => ({
                  id: String(m.id || m._id || m.documentId),
                  title: m.title || "Untitled Note",
                  subject: m.subject || m.department || "",
                  department: m.department || "",
                  pageCount: m.totalPageCount || m.pageCount || 1,
                  fileType: String(m.extension || m.fileType || "pdf").toUpperCase().replace(".", ""),
                  status: m.status || "Available",
                }));
              }
            }
          } catch (e) {
            console.error("Local storage load notice:", e);
          }
        }
        setAvailableMaterials(mats);
        const sessList = sessRes?.data?.sessions || [];
        setSessions(sessList);

        if (initialMaterialId) {
          const match = mats.find((m) => m.id === initialMaterialId);
          if (match) setSelectedMaterialIds([match.id]);
          else if (mats.length > 0) setSelectedMaterialIds(mats.map((m) => m.id));
        } else if (mats.length > 0) {
          setSelectedMaterialIds((prev) => (prev.length > 0 ? prev : mats.map((m) => m.id)));
        }
      })
      .catch((err) => {
        try {
          const rawMock = localStorage.getItem("cv-mock-materials");
          if (rawMock) {
            const localItems = JSON.parse(rawMock);
            if (Array.isArray(localItems) && localItems.length > 0) {
              const fallbackMats = localItems.map((m) => ({
                id: String(m.id || m._id || m.documentId),
                title: m.title || "Untitled Note",
                subject: m.subject || m.department || "",
                department: m.department || "",
                pageCount: m.totalPageCount || m.pageCount || 1,
                fileType: String(m.extension || m.fileType || "pdf").toUpperCase().replace(".", ""),
                status: m.status || "Available",
              }));
              setAvailableMaterials(fallbackMats);
              setSelectedMaterialIds([fallbackMats[0].id]);
              return;
            }
          }
        } catch {}
        showToast("Could not load study materials for chat.", "error");
      })
      .finally(() => setLoadingMaterials(false));
  };

  useEffect(() => {
    loadMaterialsAndSessions();
  }, [initialMaterialId]);

  // Load session history when currentSessionId changes
  useEffect(() => {
    if (!currentSessionId) return;
    chatApi
      .getSessionHistory(currentSessionId)
      .then((res) => {
        setCurrentSession(res.data.session);
        setMessages(res.data.messages || []);
      })
      .catch(() => {
        showToast("Failed to load session history.", "error");
      });
  }, [currentSessionId]);

  const handleStartNewSession = async () => {
    let matsToUse = selectedMaterialIds;
    if (matsToUse.length === 0) {
      if (availableMaterials.length > 0) {
        matsToUse = [availableMaterials[0].id];
        setSelectedMaterialIds(matsToUse);
      } else {
        showToast("Please upload notes or choose a document first.", "error");
        return;
      }
    }

    try {
      const res = await chatApi.createSession({
        materialIds: matsToUse,
      });
      const newSession = res.data;
      setSessions((prev) => [newSession, ...prev]);
      setCurrentSessionId(newSession.sessionId);
      showToast("New conversation started!", "success");
    } catch (err) {
      showToast(err.friendlyMessage || "Failed to start chat session.", "error");
    }
  };

  const handleToggleMaterial = (matId) => {
    setSelectedMaterialIds((prev) =>
      prev.includes(matId) ? prev.filter((id) => id !== matId) : [...prev, matId]
    );
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    const q = inputQuestion.trim();
    if (!q) return;

    // If no session active, create one first
    let activeSessionId = currentSessionId;
    if (!activeSessionId) {
      let matsToUse = selectedMaterialIds;
      if (matsToUse.length === 0) {
        if (availableMaterials.length > 0) {
          matsToUse = [availableMaterials[0].id];
          setSelectedMaterialIds(matsToUse);
        } else {
          showToast("Select at least one document to start chatting.", "error");
          return;
        }
      }
      try {
        const createRes = await chatApi.createSession({
          materialIds: matsToUse,
        });
        activeSessionId = createRes.data.sessionId;
        setCurrentSessionId(activeSessionId);
        setSessions((prev) => [createRes.data, ...prev]);
      } catch (err) {
        showToast("Could not create chat session.", "error");
        return;
      }
    }

    // Optimistically append user message
    const userMsg = {
      role: "user",
      content: q,
      createdAt: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInputQuestion("");
    setSending(true);

    try {
      const res = await chatApi.sendMessage(activeSessionId, q);
      const aiMsg = res.data;
      setMessages((prev) => [...prev, aiMsg]);
    } catch (err) {
      showToast(err.friendlyMessage || "Failed to generate answer.", "error");
    } finally {
      setSending(false);
    }
  };

  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    try {
      await chatApi.deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.sessionId !== sessionId));
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setCurrentSession(null);
        setMessages([]);
      }
      showToast("Chat session deleted.", "success");
    } catch {
      showToast("Failed to delete session.", "error");
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[80vh] min-h-[600px]">
        {/* Left Sidebar: Document Context & Sessions */}
        <div className="lg:col-span-1 card p-4 bg-white/95 rounded-2xl shadow-md border border-white/40 flex flex-col justify-between overflow-hidden">
          <div className="space-y-4 overflow-y-auto pr-1">
            <button
              onClick={handleStartNewSession}
              className="btn-primary w-full flex items-center justify-center gap-2 !py-2.5 text-xs font-bold shadow-sm"
            >
              <Plus size={15} />
              <span>New Conversation</span>
            </button>

            {/* Document Context Selector */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold uppercase tracking-wider text-gray-700 flex items-center gap-1.5">
                  <BookOpen size={13} className="text-brand-600" />
                  <span>Select Notes Context</span>
                </h4>
                <button
                  type="button"
                  onClick={loadMaterialsAndSessions}
                  title="Refresh uploaded notes"
                  className="p-1 rounded-md text-gray-400 hover:text-brand-700 hover:bg-brand-50 transition text-[11px]"
                >
                  <Sparkles size={13} />
                </button>
              </div>
              <div className="flex items-center justify-between">
                <p className="text-[11px] text-gray-500">
                  Choose documents for the AI to retrieve answers from:
                </p>
                {availableMaterials.length > 1 && (
                  <button
                    type="button"
                    onClick={() => {
                      if (selectedMaterialIds.length === availableMaterials.length) {
                        setSelectedMaterialIds([]);
                      } else {
                        setSelectedMaterialIds(availableMaterials.map((m) => m.id));
                      }
                    }}
                    className="text-[10px] text-brand-700 font-bold hover:underline shrink-0 ml-1"
                  >
                    {selectedMaterialIds.length === availableMaterials.length ? "Deselect All" : "Select All"}
                  </button>
                )}
              </div>

              {loadingMaterials ? (
                <Loader label="Loading materials..." size="sm" />
              ) : availableMaterials.length === 0 ? (
                <div className="text-xs text-gray-500 p-3.5 text-center bg-brand-50/40 rounded-xl border border-dashed border-brand-200/80">
                  <p className="font-semibold text-gray-700 mb-1">No notes detected</p>
                  <p className="text-[11px] text-gray-500 mb-3">Upload your study material to activate grounded AI chat.</p>
                  <Link
                    to="/dashboard#upload-material"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#3e362e] text-white text-[11px] font-bold shadow-xs hover:bg-[#2a241e] transition"
                  >
                    <Plus size={12} /> Upload Notes Now
                  </Link>
                </div>
              ) : (
                <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                  {availableMaterials.map((mat) => {
                    const isSelected = selectedMaterialIds.includes(mat.id);
                    return (
                      <label
                        key={mat.id}
                        className={`flex items-start gap-2 p-2 rounded-xl border text-xs cursor-pointer transition ${
                          isSelected
                            ? "bg-brand-50/80 border-brand-300 text-brand-900 font-semibold"
                            : "bg-gray-50/50 border-gray-200 text-gray-600 hover:bg-gray-100"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => handleToggleMaterial(mat.id)}
                          className="mt-0.5 rounded text-brand-600 focus:ring-brand-500"
                        />
                        <div className="overflow-hidden">
                          <span className="block truncate">{mat.title}</span>
                          <span className="text-[10px] text-gray-400 font-normal block">
                            {mat.subject || mat.department} • {mat.pageCount}p
                          </span>
                        </div>
                      </label>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Chat Sessions History */}
            <div className="space-y-2 pt-2 border-t border-gray-100">
              <h4 className="text-xs font-bold uppercase tracking-wider text-gray-700 flex items-center gap-1.5">
                <MessageSquare size={13} className="text-brand-600" />
                <span>Saved Conversations</span>
              </h4>

              {sessions.length === 0 ? (
                <div className="text-[11px] text-gray-400 p-2 text-center">
                  No previous conversations.
                </div>
              ) : (
                <div className="space-y-1 max-h-40 overflow-y-auto pr-1">
                  {sessions.map((sess) => {
                    const isActive = currentSessionId === sess.sessionId;
                    return (
                      <div
                        key={sess.sessionId}
                        onClick={() => setCurrentSessionId(sess.sessionId)}
                        className={`group flex items-center justify-between p-2 rounded-xl text-xs cursor-pointer transition ${
                          isActive
                            ? "bg-brand-100 text-brand-900 font-bold"
                            : "text-gray-600 hover:bg-gray-100"
                        }`}
                      >
                        <span className="truncate pr-2">{sess.title}</span>
                        <button
                          type="button"
                          onClick={(e) => handleDeleteSession(e, sess.sessionId)}
                          className="opacity-0 group-hover:opacity-100 hover:text-red-600 transition p-1"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          <div className="text-[11px] text-gray-400 pt-3 border-t border-gray-100 text-center">
            CampusVerse RAG Retrieval Engine
          </div>
        </div>

        {/* Main Chat Interface */}
        <div className="lg:col-span-3 card p-0 bg-white/95 rounded-2xl shadow-md border border-white/40 flex flex-col justify-between overflow-hidden">
          {/* Header */}
          <div className="p-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/70">
            <div className="flex items-center gap-2.5">
              <div className="h-9 w-9 rounded-xl bg-brand-600 text-white flex items-center justify-center shadow-xs">
                <Bot size={20} />
              </div>
              <div>
                <h3 className="font-bold text-sm text-gray-900">
                  {currentSession?.title || "Academic Study Notes Assistant"}
                </h3>
                <p className="text-xs text-gray-500">
                  Active Context:{" "}
                  <strong className="text-brand-800">
                    {currentSession?.materialTitles?.join(", ") ||
                      availableMaterials
                        .filter((m) => selectedMaterialIds.includes(m.id))
                        .map((m) => m.title)
                        .join(", ") ||
                      "No documents selected"}
                  </strong>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setShowGuardrailsModal(true)}
                className="flex items-center gap-1.5 text-xs text-brand-900 bg-brand-50 hover:bg-brand-100 px-3 py-1 rounded-full border border-brand-300 font-semibold transition shadow-xs cursor-pointer"
                title="View Active AI Safety Guardrails"
              >
                <ShieldCheck size={14} className="text-emerald-600" />
                <span>AI Guardrails Active</span>
              </button>
              <div className="flex items-center gap-1.5 text-xs text-emerald-800 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200 font-semibold">
                <CheckCircle2 size={13} className="text-emerald-600" />
                <span>Grounded in Notes</span>
              </div>
            </div>
          </div>

          {/* Messages Stream */}
          <div className="flex-1 p-5 overflow-y-auto space-y-4">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-3">
                <div className="h-12 w-12 rounded-2xl bg-brand-100 text-brand-700 flex items-center justify-center">
                  <Sparkles size={24} />
                </div>
                <h3 className="font-bold text-base text-gray-800">Ask Anything About Your Notes</h3>
                <p className="text-xs text-gray-500 max-w-md">
                  Select your study materials on the left, type a question below, and the AI will synthesize an answer grounded strictly in your uploaded notes.
                </p>
                <div className="flex flex-wrap justify-center gap-2 pt-2">
                  {[
                    "What is supervised learning?",
                    "Explain database normalization.",
                    "Summarize chapter 1 formulas.",
                  ].map((preset, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setInputQuestion(preset);
                      }}
                      className="text-xs px-3 py-1.5 rounded-full bg-brand-50 hover:bg-brand-100 text-brand-800 border border-brand-200/80 transition"
                    >
                      "{preset}"
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg, idx) => {
                const isUser = msg.role === "user";
                const sources = msg.sources || [];
                const isGuardrailBlocked = !isUser && (msg.guardrailTriggered || msg.content?.includes("CampusVerse AI Safety Guardrail Alert"));

                return (
                  <div
                    key={idx}
                    className={`flex ${isUser ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-2xl p-4 space-y-2.5 text-sm shadow-xs ${
                        isUser
                          ? "bg-[#93785b] text-white rounded-br-xs"
                          : isGuardrailBlocked
                          ? "bg-rose-50/95 text-rose-950 rounded-bl-xs border border-rose-300 shadow-sm"
                          : "bg-gray-100/90 text-gray-900 rounded-bl-xs border border-gray-200/60"
                      }`}
                    >
                      {isGuardrailBlocked && (
                        <div className="flex items-center gap-2 text-rose-700 font-bold text-xs pb-1.5 border-b border-rose-200">
                          <ShieldAlert size={15} />
                          <span>CampusVerse AI Guardrail Intercepted</span>
                        </div>
                      )}

                      {isUser ? (
                        <p className="leading-relaxed whitespace-pre-line">{msg.content}</p>
                      ) : (
                        <MarkdownSummary content={msg.content} />
                      )}

                      {/* Source Citations */}
                      {!isUser && sources.length > 0 && (
                        <div className="pt-2 border-t border-gray-200/70 space-y-1">
                          <span className="text-[11px] font-bold text-brand-900 uppercase tracking-wider block">
                            Sources:
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {sources.filter(Boolean).map((src, sIdx) => {
                              const rawId = src.materialId || src.id || src._id;
                              let resolvedId =
                                rawId && String(rawId) !== "undefined" && String(rawId) !== "null"
                                  ? String(rawId).trim()
                                  : "";
                              if (!resolvedId) {
                                const match = availableMaterials.find(
                                  (m) =>
                                    (src.title && m.title && m.title.toLowerCase().trim() === src.title.toLowerCase().trim()) ||
                                    (src.title && m.title && (m.title.toLowerCase().includes(src.title.toLowerCase()) || src.title.toLowerCase().includes(m.title.toLowerCase())))
                                );
                                if (match) {
                                  resolvedId = String(match.id);
                                } else if (selectedMaterialIds.length === 1) {
                                  resolvedId = String(selectedMaterialIds[0]);
                                }
                              }
                              const hasValidId = Boolean(
                                resolvedId &&
                                  resolvedId !== "undefined" &&
                                  resolvedId !== "null" &&
                                  resolvedId.trim() !== ""
                              );
                              const pageLabel =
                                src.pageNumber && !isNaN(src.pageNumber)
                                  ? `, Page ${src.pageNumber}`
                                  : "";
                              const cleanTitle = (src.title || "Study Note").trim().replace(/,\s*$/, "");

                              return hasValidId ? (
                                <Link
                                  key={sIdx}
                                  to={`/materials/${resolvedId}`}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md bg-white border border-gray-300 text-gray-700 hover:text-brand-800 hover:border-brand-300 text-xs transition shadow-2xs"
                                >
                                  <FileText size={11} className="text-brand-600" />
                                  <span className="font-semibold">{cleanTitle}</span>
                                  {pageLabel}
                                  <ExternalLink size={10} className="text-gray-400" />
                                </Link>
                              ) : (
                                <span
                                  key={sIdx}
                                  className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md bg-white border border-gray-200 text-gray-700 text-xs"
                                >
                                  <FileText size={11} className="text-brand-600" />
                                  <span className="font-semibold">{cleanTitle}</span>
                                  {pageLabel}
                                </span>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            )}

            {sending && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-2xl rounded-bl-xs p-4 text-xs text-gray-600 flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-brand-600 animate-ping" />
                  <span>Searching notes chunks & synthesizing grounded answer...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Box */}
          <form
            onSubmit={handleSendMessage}
            className="p-3 border-t border-gray-100 bg-gray-50/50 flex items-center gap-2"
          >
            <input
              type="text"
              value={inputQuestion}
              onChange={(e) => setInputQuestion(e.target.value)}
              placeholder="Ask a question grounded in your selected notes..."
              className="input-field flex-1 !py-2.5 text-sm"
              disabled={sending}
            />
            <button
              type="submit"
              disabled={sending || !inputQuestion.trim()}
              className="btn-primary !px-4 !py-2.5 flex items-center gap-1.5 shadow-sm"
            >
              <Send size={15} />
              <span className="hidden sm:inline">Send</span>
            </button>
          </form>
        </div>
      </div>

      {/* AI Guardrails Details Modal */}
      {showGuardrailsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-gray-100 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center">
                  <ShieldCheck size={18} />
                </div>
                <div>
                  <h3 className="font-bold text-gray-900 text-sm">CampusVerse AI Guardrails Architecture</h3>
                  <p className="text-[11px] text-emerald-700 font-semibold">Active & Enforcing • Real-Time Safety Pipeline</p>
                </div>
              </div>
              <button
                onClick={() => setShowGuardrailsModal(false)}
                className="text-gray-400 hover:text-gray-600 p-1 rounded-lg hover:bg-gray-100 transition"
              >
                <X size={18} />
              </button>
            </div>

            <p className="text-xs text-gray-600 leading-relaxed">
              Every message sent to the CampusVerse AI engine is screened through multi-layered academic safety guardrails before query retrieval and response generation.
            </p>

            <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
              <div className="p-3 rounded-xl bg-gray-50 border border-gray-200/80 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-gray-900 flex items-center gap-1.5">
                    <Shield size={13} className="text-emerald-600" />
                    Layer 1: Prompt Injection & Jailbreak Defense
                  </span>
                  <span className="text-[10px] uppercase font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">Enforcing</span>
                </div>
                <p className="text-[11px] text-gray-500">
                  Blocks attempts to override system prompts, bypass instructions, exfiltrate API secrets, or activate unrestricted jailbreak personas (e.g., DAN).
                </p>
              </div>

              <div className="p-3 rounded-xl bg-gray-50 border border-gray-200/80 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-gray-900 flex items-center gap-1.5">
                    <Shield size={13} className="text-emerald-600" />
                    Layer 2: Content Safety & Cyber Defense
                  </span>
                  <span className="text-[10px] uppercase font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">Enforcing</span>
                </div>
                <p className="text-[11px] text-gray-500">
                  Intercepts requests for malicious scripts (ransomware, keyloggers), weapons, harassment, and severe toxicity.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-gray-50 border border-gray-200/80 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-gray-900 flex items-center gap-1.5">
                    <Shield size={13} className="text-emerald-600" />
                    Layer 3: Personally Identifiable Information (PII) Shield
                  </span>
                  <span className="text-[10px] uppercase font-bold text-blue-700 bg-blue-100 px-2 py-0.5 rounded-full">Redacting</span>
                </div>
                <p className="text-[11px] text-gray-500">
                  Scans and masks student phone numbers, credit card numbers, Aadhaar/national IDs, and API keys before sending queries to LLMs.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-gray-50 border border-gray-200/80 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-gray-900 flex items-center gap-1.5">
                    <Shield size={13} className="text-emerald-600" />
                    Layer 4: Academic Integrity & Exam Boundary
                  </span>
                  <span className="text-[10px] uppercase font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">Enforcing</span>
                </div>
                <p className="text-[11px] text-gray-500">
                  Prevents unauthorized requests to solve live proctored examinations or alter academic portal grades.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-gray-50 border border-gray-200/80 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-gray-900 flex items-center gap-1.5">
                    <Shield size={13} className="text-emerald-600" />
                    Layer 5: Clinical Safety & Disclaimer Invariant
                  </span>
                  <span className="text-[10px] uppercase font-bold text-purple-700 bg-purple-100 px-2 py-0.5 rounded-full">Enforcing</span>
                </div>
                <p className="text-[11px] text-gray-500">
                  Guarantees that medical or dosage notes include mandatory academic disclaimers and prevents unauthorized clinical treatment advice.
                </p>
              </div>
            </div>

            <div className="pt-2 border-t border-gray-100 flex justify-end">
              <button
                onClick={() => setShowGuardrailsModal(false)}
                className="btn-primary !py-2 !px-4 text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
