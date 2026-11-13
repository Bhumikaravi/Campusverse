import { useState, useRef } from "react";
import {
  Bot,
  Sparkles,
  UploadCloud,
  FileText,
  AlertTriangle,
  HelpCircle,
  MessageSquare,
  BookOpen,
  Copy,
  Download,
  RotateCcw,
  CheckCircle,
  FileCode,
  Send,
  Loader2,
  ListOrdered,
  FileCheck2,
  Lightbulb,
  ExternalLink,
  Zap,
} from "lucide-react";
import { studyBuddyApi } from "../services/endpoints";
import { useToast } from "../context/ToastContext";

export default function StudyBuddy() {
  const { addToast } = useToast();
  const fileInputRef = useRef(null);

  // Input states
  const [activeInputTab, setActiveInputTab] = useState("upload"); // 'upload' | 'paste' | 'demo'
  const [selectedFile, setSelectedFile] = useState(null);
  const [pastedTitle, setPastedTitle] = useState("");
  const [pastedText, setPastedText] = useState("");
  const [dragActive, setDragActive] = useState(false);

  // Scanning / Processing state
  const [isScanning, setIsScanning] = useState(false);
  const [scanStep, setScanStep] = useState("");
  const [progress, setProgress] = useState(0);

  // Result state
  const [session, setSession] = useState(null);
  const [activeResultTab, setActiveResultTab] = useState("summary"); // 'summary' | 'notes' | 'issues' | 'questions' | 'chat'

  // Chat state
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [isAsking, setIsAsking] = useState(false);

  // Drag and drop handlers
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  // Run Scan & Analysis
  const handleScan = async (e) => {
    if (e) e.preventDefault();

    if (activeInputTab === "upload" && !selectedFile) {
      addToast("Please select a study material file (PDF, DOCX, TXT, PPTX).", "error");
      return;
    }
    if (activeInputTab === "paste" && !pastedText.trim()) {
      addToast("Please paste your study notes or lecture text.", "error");
      return;
    }

    setIsScanning(true);
    setProgress(15);
    setScanStep("Reading and verifying file security...");

    try {
      const formData = new FormData();
      if (activeInputTab === "upload" && selectedFile) {
        formData.append("file", selectedFile);
        formData.append("title", selectedFile.name.replace(/\.[^/.]+$/, ""));
      } else {
        formData.append("title", pastedTitle || "Custom Lecture Notes");
        formData.append("text_content", pastedText);
      }

      setTimeout(() => {
        setProgress(45);
        setScanStep("Extracting academic content and checking structure...");
      }, 400);

      setTimeout(() => {
        setProgress(75);
        setScanStep("Running AI model: detecting mistakes, generating notes & practice Q&A...");
      }, 900);

      const res = await studyBuddyApi.scan(formData);
      setProgress(100);
      setScanStep("Analysis complete!");

      setTimeout(() => {
        setSession(res.data);
        setIsScanning(false);
        setActiveResultTab("summary");
        addToast("Study material analyzed successfully!", "success");
        // Initialize chat with greeting and concise summary
        const conciseSummary = res.data.notes?.summary || "Comprehensive academic study notes covering essential syllabus concepts.";
        setChatMessages([
          {
            role: "bot",
            text: `Hello! I have analyzed **${res.data.fileName}** and generated an accurate, concise summary:\n\n"${conciseSummary}"\n\nYou do not need to type descriptions manually. Ask me any doubts, practice problems, or explanations from this material!`,
          },
        ]);
      }, 500);
    } catch (err) {
      setIsScanning(false);
      const detail = err.response?.data?.detail || "Failed to analyze study material. Please try again.";
      addToast(detail, "error");
    }
  };

  // Quick Demo Loader
  const handleLoadDemo = async (demoKey) => {
    setIsScanning(true);
    setProgress(30);
    setScanStep(`Loading pre-bundled sample (${demoKey.toUpperCase()})...`);

    try {
      setTimeout(() => {
        setProgress(70);
        setScanStep("Running academic analysis on sample file...");
      }, 500);

      const res = await studyBuddyApi.loadDemo(demoKey);
      setProgress(100);
      setScanStep("Demo loaded!");

      setTimeout(() => {
        setSession(res.data);
        setIsScanning(false);
        setActiveResultTab("summary");
        addToast(`Demo loaded: ${res.data.fileName}`, "success");
        setChatMessages([
          {
            role: "bot",
            text: `Hello! I have loaded the demo file **${res.data.fileName}**. Ask me anything about this material or test one of the suggested sample questions below!`,
          },
        ]);
      }, 400);
    } catch (err) {
      setIsScanning(false);
      addToast(err.response?.data?.detail || "Could not load demo file.", "error");
    }
  };

  // Interactive Chat
  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    if (!chatInput.trim() || !session?.sessionId || isAsking) return;

    const userText = chatInput.trim();
    setChatInput("");
    setChatMessages((prev) => [...prev, { role: "user", text: userText }]);
    setIsAsking(true);

    try {
      const res = await studyBuddyApi.chat(session.sessionId, userText);
      setChatMessages((prev) => [
        ...prev,
        { role: "bot", text: res.data.answer || "I processed your question based on your notes." },
      ]);
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        {
          role: "bot",
          text: "I could not reach the AI service right now. Please refer to the generated Topic Notes tab for standard answers.",
        },
      ]);
    } finally {
      setIsAsking(false);
    }
  };

  // Copy Notes to Clipboard
  const handleCopyNotes = () => {
    if (!session?.notes) return;
    const n = session.notes;
    let text = `# ${session.fileName} - Study Notes\n\n`;
    text += `## Summary\n${n.summary}\n\n`;
    text += `## Key Topics\n${(n.topics || []).join(", ")}\n\n`;
    text += `## Detailed Notes\n`;
    (n.topicNotes || []).forEach((t) => {
      text += `### ${t.title}\n${t.explanation}\n`;
      if (t.keyPoints) text += `Key Points:\n${t.keyPoints.map((k) => `- ${k}`).join("\n")}\n`;
      if (t.example) text += `Example: ${t.example}\n\n`;
    });
    text += `## Definitions\n`;
    (n.definitions || []).forEach((d) => {
      text += `- **${d.term}**: ${d.definition}\n`;
    });
    text += `\n## Practice Questions\n`;
    (n.practiceQA || []).forEach((q, idx) => {
      text += `${idx + 1}. [${q.type}] ${q.question}\nAnswer: ${q.answer}\n\n`;
    });

    navigator.clipboard.writeText(text);
    addToast("Complete study notes copied to clipboard!", "success");
  };

  // Download Notes as TXT
  const handleDownloadTxt = () => {
    if (!session?.notes) return;
    const n = session.notes;
    let content = `CAMPUSVERSE STUDY BUDDY - GENERATED STUDY NOTES\n`;
    content += `File: ${session.fileName} (${session.fileType}, ${session.fileSize})\n`;
    content += `Date: ${new Date().toLocaleDateString()}\n`;
    content += `============================================================\n\n`;
    content += `1. SUMMARY:\n${n.summary}\n\n`;
    content += `------------------------------------------------------------\n`;
    content += `2. TOPIC-WISE STUDY NOTES:\n`;
    (n.topicNotes || []).forEach((t, i) => {
      content += `\n[Topic ${i + 1}] ${t.title}\n`;
      content += `${t.explanation}\n`;
      if (t.keyPoints) {
        content += `Key Revision Points:\n`;
        t.keyPoints.forEach((kp) => (content += `  * ${kp}\n`));
      }
      if (t.example) content += `Example: ${t.example}\n`;
    });
    content += `\n------------------------------------------------------------\n`;
    content += `3. IMPORTANT DEFINITIONS & FORMULAS:\n`;
    (n.definitions || []).forEach((d) => {
      content += `* ${d.term}: ${d.definition}\n`;
    });
    content += `\n------------------------------------------------------------\n`;
    content += `4. DETECTED ISSUES & CORRECTIONS:\n`;
    (n.issues || []).forEach((iss, idx) => {
      content += `[${iss.severity}] ${iss.type}: ${iss.issue}\n  Recommendation: ${iss.suggestion}\n`;
    });
    content += `\n------------------------------------------------------------\n`;
    content += `5. PRACTICE QUESTIONS & ANSWERS:\n`;
    (n.practiceQA || []).forEach((qa, idx) => {
      content += `\nQ${idx + 1} (${qa.type}): ${qa.question}\nAns: ${qa.answer}\n`;
    });
    content += `\n------------------------------------------------------------\n`;
    content += `6. REVISION SUMMARY:\n${n.revisionSummary || "Review concepts prior to exam."}\n`;

    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${session.fileName.replace(/\.[^/.]+$/, "")}_StudyNotes.txt`;
    link.click();
    URL.revokeObjectURL(url);
    addToast("Notes downloaded as TXT file!", "success");
  };

  // Reset demo
  const handleReset = () => {
    setSession(null);
    setSelectedFile(null);
    setPastedText("");
    setPastedTitle("");
    setChatMessages([]);
  };

  return (
    <div className="min-h-screen bg-[#f5f2eb] dark:bg-stone-900 py-8 px-4 sm:px-6 lg:px-8 text-stone-900 dark:text-stone-100">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header Banner */}
        <div className="bg-gradient-to-r from-[#3e362e] via-[#5c4d3c] to-[#93785b] rounded-2xl p-6 sm:p-8 text-white shadow-xl relative overflow-hidden">
          <div className="relative z-10 max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/20 text-xs font-semibold backdrop-blur-sm mb-3">
              <Sparkles size={14} className="text-yellow-300" /> AI-Powered Academic Assistant
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight">Study Buddy</h1>
            <p className="mt-2 text-white/90 text-sm sm:text-base leading-relaxed">
              Upload your lecture PDFs, DOCX, slides, or handwritten notes. Study Buddy extracts the text, detects
              potential mistakes, organizes topic-wise revision notes, generates exam questions, and provides an
              interactive AI tutor for doubts.
            </p>
          </div>

          {/* Animated 3D-Style Robot Avatar at the Right Side */}
          <div className="absolute right-6 -bottom-4 hidden md:flex flex-col items-center select-none pointer-events-none group">
            <div className="relative w-40 h-40 flex items-center justify-center">
              {/* Soft glow behind robot */}
              <div className="absolute w-36 h-36 bg-amber-400/20 rounded-full blur-2xl animate-pulse"></div>
              {/* SVG Modern Friendly AI Robot */}
              <svg
                className="w-36 h-36 filter drop-shadow-2xl transition-transform duration-700 hover:scale-105"
                viewBox="0 0 200 200"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                {/* Antenna */}
                <line x1="100" y1="35" x2="100" y2="15" stroke="#fcd34d" strokeWidth="5" strokeLinecap="round" />
                <circle cx="100" cy="12" r="7" fill="#fbbf24" className="animate-ping" style={{ transformOrigin: "100px 12px" }} />
                <circle cx="100" cy="12" r="6" fill="#f59e0b" />

                {/* Head */}
                <rect x="55" y="35" width="90" height="65" rx="18" fill="#e7e5e4" stroke="#a8a29e" strokeWidth="4" />
                {/* Screen Face */}
                <rect x="65" y="45" width="70" height="45" rx="10" fill="#1c1917" />
                {/* Glowing Eyes */}
                <circle cx="85" cy="65" r="7" fill="#38bdf8" className="animate-pulse" />
                <circle cx="115" cy="65" r="7" fill="#38bdf8" className="animate-pulse" />
                <circle cx="87" cy="63" r="2.5" fill="#ffffff" />
                <circle cx="117" cy="63" r="2.5" fill="#ffffff" />
                {/* Friendly Smile */}
                <path d="M 88 78 Q 100 86 112 78" stroke="#38bdf8" strokeWidth="3" strokeLinecap="round" fill="none" />

                {/* Ears */}
                <rect x="47" y="55" width="8" height="25" rx="3" fill="#d97706" />
                <rect x="145" y="55" width="8" height="25" rx="3" fill="#d97706" />

                {/* Neck */}
                <rect x="88" y="100" width="24" height="12" rx="3" fill="#78716c" />

                {/* Body */}
                <rect x="45" y="112" width="110" height="80" rx="22" fill="#f5f5f4" stroke="#a8a29e" strokeWidth="4" />
                {/* Chest Display badge */}
                <rect x="75" y="125" width="50" height="35" rx="8" fill="#292524" />
                <path d="M 85 142 L 95 132 L 105 147 L 115 135" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                
                {/* Arms */}
                <rect x="22" y="120" width="18" height="48" rx="8" fill="#e7e5e4" stroke="#a8a29e" strokeWidth="3" transform="rotate(12 22 120)" />
                <circle cx="27" cy="172" r="8" fill="#d97706" />
                {/* Waving Right Arm */}
                <rect x="156" y="108" width="18" height="48" rx="8" fill="#e7e5e4" stroke="#a8a29e" strokeWidth="3" transform="rotate(-30 156 108)" />
                <circle cx="185" cy="100" r="8" fill="#d97706" />
              </svg>
            </div>
            <div className="bg-black/40 backdrop-blur-md px-3 py-1 rounded-full text-[11px] font-medium text-amber-200 border border-amber-300/30 -mt-2">
              Ready to learn!
            </div>
          </div>
        </div>

        {/* Input / Scanner Section */}
        {!session && (
          <div className="bg-white dark:bg-stone-800 rounded-2xl shadow-md border border-stone-200 dark:border-stone-700 overflow-hidden p-6 sm:p-8">
            <div className="space-y-5">
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-2xl p-8 sm:p-14 text-center cursor-pointer transition ${
                  dragActive
                    ? "border-[#865d36] bg-[#865d36]/10"
                    : "border-stone-300 dark:border-stone-600 hover:border-[#865d36] bg-stone-50/50 dark:bg-stone-800/40"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  accept=".pdf,.docx,.doc,.txt,.pptx,.ppt,.png,.jpg,.jpeg"
                  onChange={handleFileChange}
                />
                <div className="mx-auto w-16 h-16 rounded-2xl bg-[#93785b]/10 dark:bg-[#93785b]/20 flex items-center justify-center text-[#865d36] dark:text-amber-400 mb-4 shadow-inner">
                  <UploadCloud size={32} />
                </div>
                {selectedFile ? (
                  <div>
                    <p className="font-bold text-lg text-stone-900 dark:text-stone-100">{selectedFile.name}</p>
                    <p className="text-sm text-stone-500 mt-1">
                      {(selectedFile.size / 1024).toFixed(1)} KB &bull; Click or drag another file to replace
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="font-semibold text-lg text-stone-800 dark:text-stone-200">
                      Click to browse or drag and drop your study document
                    </p>
                    <p className="text-xs sm:text-sm text-stone-500 dark:text-stone-400 mt-1.5">
                      Supports PDF, DOCX, TXT, PPTX &amp; Scanned Handwritten Notes &bull; Max size 25MB
                    </p>
                  </div>
                )}
              </div>

              {/* Action Button & Status */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
                <div className="text-xs text-stone-500">
                  {selectedFile ? (
                    <span className="flex items-center gap-1.5 font-medium text-emerald-600 dark:text-emerald-400 text-sm">
                      <CheckCircle size={16} /> Ready to scan: {selectedFile.name}
                    </span>
                  ) : (
                    <span className="text-stone-400 text-xs">
                      Select a study material file to begin scanning and notes generation.
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  onClick={handleScan}
                  disabled={isScanning || !selectedFile}
                  className="w-full sm:w-auto px-7 py-3 rounded-xl bg-[#865d36] hover:bg-[#6e4c2b] text-white font-bold flex items-center justify-center gap-2 shadow-md transition disabled:opacity-50"
                >
                  {isScanning ? (
                    <>
                      <Loader2 size={18} className="animate-spin" /> Analyzing Content...
                    </>
                  ) : (
                    <>
                      <Sparkles size={18} /> Scan &amp; Generate Notes
                    </>
                  )}
                </button>
              </div>

              {/* Progress Indicator */}
              {isScanning && (
                <div className="p-4 rounded-xl bg-amber-50 dark:bg-stone-900/80 border border-amber-200 dark:border-stone-700 animate-fade-in">
                  <div className="flex justify-between text-xs font-semibold text-stone-700 dark:text-stone-300 mb-1.5">
                    <span>{scanStep}</span>
                    <span>{progress}%</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-stone-200 dark:bg-stone-700 overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-amber-500 to-[#865d36] transition-all duration-300"
                      style={{ width: `${progress}%` }}
                    ></div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* RESULTS & INTERACTIVE TABS */}
        {session && (
          <div className="space-y-6 animate-fade-in">
            {/* Control Bar */}
            <div className="flex flex-wrap items-center justify-between gap-4 bg-white dark:bg-stone-800 p-4 rounded-2xl shadow-sm border border-stone-200 dark:border-stone-700">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-[#865d36]/10 text-[#865d36] dark:text-amber-400 flex items-center justify-center">
                  <FileText size={20} />
                </div>
                <div>
                  <h2 className="font-bold text-base sm:text-lg text-stone-900 dark:text-stone-100 flex items-center gap-2">
                    {session.fileName}
                    <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-semibold">
                      {session.fileType} &bull; {session.fileSize}
                    </span>
                  </h2>
                  <p className="text-xs text-stone-500">
                    Scanned {session.charCount ? `${session.charCount.toLocaleString()} characters` : "complete text"} &bull; AI analysis active
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                <button
                  type="button"
                  onClick={handleCopyNotes}
                  className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-stone-100 hover:bg-stone-200 dark:bg-stone-700 text-stone-800 dark:text-stone-200 flex items-center gap-1.5 transition"
                >
                  <Copy size={14} /> Copy All
                </button>
                <button
                  type="button"
                  onClick={handleDownloadTxt}
                  className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-[#865d36] hover:bg-[#6e4c2b] text-white flex items-center gap-1.5 shadow-sm transition"
                >
                  <Download size={14} /> Download TXT
                </button>
                <button
                  type="button"
                  onClick={handleReset}
                  className="px-3 py-2 rounded-xl text-xs font-semibold border border-stone-300 dark:border-stone-600 text-stone-600 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-700 flex items-center gap-1 transition"
                >
                  <RotateCcw size={14} /> Scan Another
                </button>
              </div>
            </div>

            {/* Navigation Tabs */}
            <div className="flex border-b border-stone-200 dark:border-stone-700 overflow-x-auto gap-2 pb-1">
              {[
                { id: "summary", label: "Summary", icon: BookOpen },
                { id: "notes", label: "Study Notes", icon: ListOrdered },
                {
                  id: "issues",
                  label: `Detected Issues (${session.notes?.issues?.length || 0})`,
                  icon: AlertTriangle,
                },
                {
                  id: "questions",
                  label: `Practice Q&A (${session.notes?.practiceQA?.length || 0})`,
                  icon: HelpCircle,
                },
                { id: "chat", label: "Ask Study Buddy", icon: MessageSquare },
              ].map((tab) => {
                const Icon = tab.icon;
                const active = activeResultTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setActiveResultTab(tab.id)}
                    className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold whitespace-nowrap transition ${
                      active
                        ? "bg-[#865d36] text-white shadow-sm"
                        : "text-stone-600 dark:text-stone-400 hover:bg-stone-100 dark:hover:bg-stone-800"
                    }`}
                  >
                    <Icon size={16} />
                    {tab.label}
                  </button>
                );
              })}
            </div>

            {/* TAB CONTENT 1: SUMMARY */}
            {activeResultTab === "summary" && (
              <div className="bg-white dark:bg-stone-800 rounded-2xl p-6 sm:p-8 shadow-sm border border-stone-200 dark:border-stone-700 space-y-6">
                <div>
                  <h3 className="text-lg font-bold text-stone-900 dark:text-stone-100 flex items-center gap-2 mb-2">
                    <BookOpen size={20} className="text-[#865d36]" /> Quick Overview
                  </h3>
                  <p className="text-stone-700 dark:text-stone-300 leading-relaxed text-base">
                    {session.notes?.summary || "No overview available."}
                  </p>
                </div>

                {/* Key Topics Tag Cloud */}
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-stone-500 mb-2">
                    Major Topics Identified
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {(session.notes?.topics || []).map((topic, i) => (
                      <span
                        key={i}
                        className="px-3 py-1 rounded-lg bg-amber-50 dark:bg-amber-950/40 text-amber-900 dark:text-amber-200 border border-amber-200 dark:border-amber-800 text-xs font-semibold"
                      >
                        {topic}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Important Definitions */}
                {session.notes?.definitions?.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-stone-500 mb-3">
                      Key Definitions &amp; Formulas
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {session.notes.definitions.map((d, i) => (
                        <div
                          key={i}
                          className="p-4 rounded-xl bg-stone-50 dark:bg-stone-900/50 border border-stone-200 dark:border-stone-700"
                        >
                          <span className="font-bold text-sm text-[#865d36] dark:text-amber-400 block mb-1">
                            {d.term}
                          </span>
                          <p className="text-xs text-stone-600 dark:text-stone-300 leading-relaxed">{d.definition}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Final Revision Summary */}
                {session.notes?.revisionSummary && (
                  <div className="p-4 rounded-xl bg-[#93785b]/10 dark:bg-[#93785b]/20 border border-[#93785b]/30">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-[#865d36] dark:text-amber-300 mb-1 flex items-center gap-1.5">
                      <Lightbulb size={16} /> Final Revision Summary for Exams
                    </h4>
                    <p className="text-xs sm:text-sm text-stone-800 dark:text-stone-200 leading-relaxed">
                      {session.notes.revisionSummary}
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* TAB CONTENT 2: STUDY NOTES */}
            {activeResultTab === "notes" && (
              <div className="space-y-4">
                {(session.notes?.topicNotes || []).map((t, idx) => (
                  <div
                    key={idx}
                    className="bg-white dark:bg-stone-800 rounded-2xl p-6 shadow-sm border border-stone-200 dark:border-stone-700 space-y-4"
                  >
                    <div className="flex items-start justify-between">
                      <h3 className="text-lg font-bold text-stone-900 dark:text-stone-100 flex items-center gap-2">
                        <span className="w-7 h-7 rounded-lg bg-[#865d36] text-white text-xs flex items-center justify-center font-bold">
                          {idx + 1}
                        </span>
                        {t.title}
                      </h3>
                    </div>

                    <p className="text-sm text-stone-700 dark:text-stone-300 leading-relaxed">{t.explanation}</p>

                    {t.keyPoints && t.keyPoints.length > 0 && (
                      <div className="bg-stone-50 dark:bg-stone-900/40 p-4 rounded-xl border border-stone-200 dark:border-stone-700">
                        <span className="text-xs font-bold uppercase tracking-wider text-stone-500 block mb-2">
                          Key Exam Points
                        </span>
                        <ul className="space-y-1.5 text-xs text-stone-700 dark:text-stone-300">
                          {t.keyPoints.map((kp, kidx) => (
                            <li key={kidx} className="flex items-start gap-2">
                              <span className="text-amber-600 font-bold mt-0.5">&bull;</span>
                              <span>{kp}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {t.example && (
                      <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/50 text-xs text-amber-900 dark:text-amber-200">
                        <span className="font-bold block mb-1">Example / Numerical Application:</span>
                        {t.example}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* TAB CONTENT 3: DETECTED ISSUES */}
            {activeResultTab === "issues" && (
              <div className="bg-white dark:bg-stone-800 rounded-2xl p-6 sm:p-8 shadow-sm border border-stone-200 dark:border-stone-700 space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-bold text-stone-900 dark:text-stone-100 flex items-center gap-2">
                      <AlertTriangle size={20} className="text-amber-500" /> AI Content Analysis &amp; Issue Detection
                    </h3>
                    <p className="text-xs text-stone-500 mt-1">
                      Study Buddy inspects spelling, contradictions, missing syllabus topics, and verifies factual clarity.
                    </p>
                  </div>
                </div>

                <div className="space-y-3">
                  {(session.notes?.issues || []).map((iss, idx) => {
                    const isHigh = iss.severity === "High";
                    const isMed = iss.severity === "Medium";
                    return (
                      <div
                        key={idx}
                        className={`p-4 rounded-xl border transition ${
                          isHigh
                            ? "bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-900/50"
                            : isMed
                            ? "bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-900/50"
                            : "bg-stone-50 dark:bg-stone-900/50 border-stone-200 dark:border-stone-700"
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-white dark:bg-stone-800 text-stone-700 dark:text-stone-300 border border-stone-200 dark:border-stone-700">
                            {iss.type}
                          </span>
                          <span
                            className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                              isHigh
                                ? "bg-red-100 text-red-800"
                                : isMed
                                ? "bg-amber-100 text-amber-800"
                                : "bg-emerald-100 text-emerald-800"
                            }`}
                          >
                            {iss.severity} Severity &bull; {iss.verified ? "Verified" : "To Verify"}
                          </span>
                        </div>
                        <p className="font-semibold text-sm text-stone-900 dark:text-stone-100">{iss.issue}</p>
                        <p className="text-xs text-stone-600 dark:text-stone-300 mt-1.5">
                          <span className="font-bold text-[#865d36] dark:text-amber-400">Suggestion: </span>
                          {iss.suggestion}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* TAB CONTENT 4: PRACTICE QUESTIONS */}
            {activeResultTab === "questions" && (
              <div className="bg-white dark:bg-stone-800 rounded-2xl p-6 sm:p-8 shadow-sm border border-stone-200 dark:border-stone-700 space-y-6">
                <div>
                  <h3 className="text-lg font-bold text-stone-900 dark:text-stone-100 flex items-center gap-2">
                    <HelpCircle size={20} className="text-[#865d36]" /> Exam Practice Questions
                  </h3>
                  <p className="text-xs text-stone-500 mt-1">
                    Auto-generated from your study material to help you prepare for upcoming university tests.
                  </p>
                </div>

                <div className="space-y-4">
                  {(session.notes?.practiceQA || []).map((qa, idx) => (
                    <div
                      key={idx}
                      className="p-5 rounded-xl border border-stone-200 dark:border-stone-700 bg-stone-50/50 dark:bg-stone-900/40 space-y-3"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-[#865d36] text-white">
                          {qa.type || "Question"}
                        </span>
                        <span className="text-xs text-stone-400 font-semibold">Q{idx + 1}</span>
                      </div>

                      <p className="font-bold text-sm sm:text-base text-stone-900 dark:text-stone-100">{qa.question}</p>

                      {qa.options && qa.options.length > 0 && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                          {qa.options.map((opt, oidx) => (
                            <div
                              key={oidx}
                              className="p-2.5 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800"
                            >
                              {opt}
                            </div>
                          ))}
                        </div>
                      )}

                      <div className="pt-2 border-t border-stone-200 dark:border-stone-700">
                        <span className="text-xs font-bold text-emerald-700 dark:text-emerald-400 uppercase tracking-wider block mb-1">
                          Model Answer / Explanation:
                        </span>
                        <p className="text-xs sm:text-sm text-stone-700 dark:text-stone-300 leading-relaxed">
                          {qa.answer}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TAB CONTENT 5: INTERACTIVE CHAT */}
            {activeResultTab === "chat" && (
              <div className="bg-white dark:bg-stone-800 rounded-2xl shadow-sm border border-stone-200 dark:border-stone-700 overflow-hidden flex flex-col h-[580px]">
                {/* Chat Header */}
                <div className="p-4 border-b border-stone-200 dark:border-stone-700 bg-stone-50 dark:bg-stone-800/80 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-[#865d36] text-white flex items-center justify-center font-bold">
                      <Bot size={16} />
                    </div>
                    <div>
                      <h4 className="font-bold text-sm text-stone-900 dark:text-stone-100">Study Buddy Tutor</h4>
                      <p className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium">
                        Active &bull; Asking based on {session.fileName}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Messages Container */}
                <div className="flex-1 p-4 overflow-y-auto space-y-3">
                  {chatMessages.map((msg, idx) => {
                    const isBot = msg.role === "bot";
                    return (
                      <div key={idx} className={`flex ${isBot ? "justify-start" : "justify-end"}`}>
                        <div
                          className={`max-w-[85%] sm:max-w-[75%] rounded-2xl p-4 text-xs sm:text-sm leading-relaxed ${
                            isBot
                              ? "bg-stone-100 dark:bg-stone-700 text-stone-900 dark:text-stone-100 rounded-tl-none border border-stone-200 dark:border-stone-600"
                              : "bg-[#865d36] text-white rounded-tr-none shadow-sm"
                          }`}
                        >
                          <p className="whitespace-pre-line">{msg.text}</p>
                        </div>
                      </div>
                    );
                  })}
                  {isAsking && (
                    <div className="flex justify-start">
                      <div className="bg-stone-100 dark:bg-stone-700 text-stone-500 rounded-2xl rounded-tl-none p-3 text-xs flex items-center gap-2">
                        <Loader2 size={14} className="animate-spin" /> Thinking and scanning notes...
                      </div>
                    </div>
                  )}
                </div>

                {/* Example Quick Prompts */}
                <div className="p-2 border-t border-stone-100 dark:border-stone-700/60 bg-stone-50/50 dark:bg-stone-900/20 flex gap-2 overflow-x-auto text-xs">
                  {[
                    "Explain CPU scheduling simply",
                    "What are the 4 deadlock conditions?",
                    "Give me a sample 5-mark exam question",
                  ].map((p, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => {
                        setChatInput(p);
                      }}
                      className="whitespace-nowrap px-3 py-1 rounded-full border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 text-stone-600 dark:text-stone-300 hover:border-[#865d36] hover:text-[#865d36] transition"
                    >
                      {p}
                    </button>
                  ))}
                </div>

                {/* Chat Input Bar */}
                <form
                  onSubmit={handleSendMessage}
                  className="p-3 border-t border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 flex items-center gap-2"
                >
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder="Ask a question about this material (e.g. explain step-by-step)..."
                    disabled={isAsking}
                    className="flex-1 px-4 py-2.5 rounded-xl border border-stone-300 dark:border-stone-600 bg-stone-50 dark:bg-stone-700 text-stone-900 dark:text-stone-100 text-sm focus:outline-none focus:ring-2 focus:ring-[#865d36]"
                  />
                  <button
                    type="submit"
                    disabled={!chatInput.trim() || isAsking}
                    className="p-2.5 rounded-xl bg-[#865d36] hover:bg-[#6e4c2b] text-white disabled:opacity-50 transition shadow-sm"
                  >
                    <Send size={18} />
                  </button>
                </form>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
