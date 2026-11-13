import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

/**
 * MarkdownSummary — renders Markdown-formatted AI summaries with
 * proper headings, bullet points, bold text, and LaTeX math formulas.
 *
 * Props:
 *   content   — markdown string to render
 *   className — optional extra CSS classes on the wrapper
 *   compact   — if true, uses smaller text for card contexts
 */
export function cleanMarkdownContent(md) {
  if (!md || typeof md !== "string") return "";

  // Normalize line endings
  let text = md.replace(/\r\n/g, "\n");

  // If text contains inline bullets like "Heading: • Topic 1... • Topic 2...",
  // convert inline bullets to separate newlines with markdown list dashes: "\n- "
  text = text.replace(
    /([^\n])\s+[•·∙●○▪▫■□►▻▶▷⁃‣·\u2022\u25cf\u25cb\u25a0\u25a1\u25aa\u25ab\u25c6\u25c7\u25ba\u25bb\u25b6\u25b7\u2023\u2043\u2219\u00b7\uf0b7]\s+/g,
    "$1\n- "
  );

  return text
    .split("\n")
    .map((line) => {
      let l = line.trim();
      if (!l) return "";

      // 1. If line is already a list item e.g. "- . • Text" or "* • Text" or "1. • Text"
      const listMatch = l.match(/^(\s*(?:[-*+]|\d+\.)\s+)(.*)$/);
      if (listMatch) {
        const prefix = listMatch[1];
        let itemContent = listMatch[2];
        itemContent = itemContent
          .replace(/^[\s•·∙●○▪▫■□►▻▶▷⁃‣·\u2022\u25cf\u25cb\u25a0\u25a1\u25aa\u25ab\u25c6\u25c7\u25ba\u25bb\u25b6\u25b7\u2023\u2043\u2219\u00b7\uf0b7\-_.:]+\s*/, "")
          .trim();
        return prefix + itemContent;
      }

      // 2. If line starts with a raw unicode bullet e.g. "• Text"
      if (/^[•·∙●○▪▫■□►▻▶▷⁃‣·\u2022\u25cf\u25cb\u25a0\u25a1\u25aa\u25ab\u25c6\u25c7\u25ba\u25bb\u25b6\u25b7\u2023\u2043\u2219\u00b7\uf0b7]/.test(l)) {
        let itemContent = l
          .replace(/^[•·∙●○▪▫■□►▻▶▷⁃‣·\u2022\u25cf\u25cb\u25a0\u25a1\u25aa\u25ab\u25c6\u25c7\u25ba\u25bb\u25b6\u25b7\u2023\u2043\u2219\u00b7\uf0b7\s\-_.:]+\s*/, "")
          .trim();
        return "- " + itemContent;
      }

      // 3. Clean duplicate periods or stray leading punctuation
      l = l.replace(/^[•·∙●○▪▫■□►▻▶▷⁃‣·\u2022\u25cf\u25cb\u25a0\u25a1\u25aa\u25ab\u25c6\u25c7\u25ba\u25bb\u25b6\u25b7\u2023\u2043\u2219\u00b7\uf0b7\-_.:]+\s*/, "");
      l = l.replace(/\.{2,}/g, ".");
      return l;
    })
    .join("\n");
}

export default function MarkdownSummary({ content, className = "", compact = false }) {
  if (!content) return null;

  const sanitizedContent = cleanMarkdownContent(content);
  const baseTextSize = compact ? "text-[11px]" : "text-sm";

  return (
    <div
      className={`markdown-summary prose prose-sm max-w-none ${baseTextSize} leading-relaxed text-gray-800 ${className}`}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          // Headings
          h1: ({ children }) => (
            <h2 className={`${compact ? "text-sm" : "text-base"} font-extrabold text-brand-950 mt-4 mb-2 border-b border-brand-200/80 pb-1.5 flex items-center gap-2`}>
              <span className="w-2 h-4 bg-brand-700 rounded-xs inline-block"></span>
              {children}
            </h2>
          ),
          h2: ({ children }) => (
            <h3 className={`${compact ? "text-xs" : "text-sm"} font-bold text-brand-900 mt-3.5 mb-1.5 flex items-center gap-1.5 pb-1 border-b border-brand-100/70`}>
              <span className="w-1.5 h-3.5 bg-brand-600 rounded-xs inline-block"></span>
              {children}
            </h3>
          ),
          h3: ({ children }) => (
            <h4 className={`${compact ? "text-[11px]" : "text-xs"} font-bold text-gray-800 mt-2.5 mb-1`}>
              {children}
            </h4>
          ),
          // Paragraphs
          p: ({ children }) => (
            <p className={`${baseTextSize} leading-relaxed text-gray-800 mb-2.5`}>
              {children}
            </p>
          ),
          // Unordered lists
          ul: ({ children }) => (
            <ul className="space-y-1.5 my-2.5 pl-1">
              {children}
            </ul>
          ),
          // Ordered lists
          ol: ({ children }) => (
            <ol className="list-decimal list-inside space-y-1.5 my-2.5 pl-1">
              {children}
            </ol>
          ),
          // List items
          li: ({ children }) => {
            const cleanLeadingSymbols = (val) => {
              if (typeof val === "string") {
                return val.replace(/^[\s•·∙●○▪▫■□►▻▶▷⁃‣·\u2022\u25cf\u25cb\u25a0\u25a1\u25aa\u25ab\u25c6\u25c7\u25ba\u25bb\u25b6\u25b7\u2023\u2043\u2219\u00b7\uf0b7\-_.:]+\s*/, "").trim();
              }
              if (Array.isArray(val)) {
                return val.map((item, idx) => (idx === 0 ? cleanLeadingSymbols(item) : item));
              }
              if (val && typeof val === "object" && val.props) {
                // If React element wraps content (e.g. <p> tag), unwrap or clean children
                if (val.props.children) {
                  return cleanLeadingSymbols(val.props.children);
                }
              }
              return val;
            };

            const rendered = cleanLeadingSymbols(children);

            return (
              <li className={`${baseTextSize} text-gray-800 flex items-start gap-2 leading-relaxed my-1`}>
                <span className="text-brand-600 font-bold shrink-0 mt-0.5">•</span>
                <span className="flex-1">{rendered}</span>
              </li>
            );
          },
          // Bold
          strong: ({ children }) => (
            <strong className="font-semibold text-gray-900">{children}</strong>
          ),
          // Code inline
          code: ({ children }) => (
            <code className="bg-gray-100 text-gray-800 px-1 py-0.5 rounded text-[10px] font-mono">
              {children}
            </code>
          ),
          // Code block
          pre: ({ children }) => (
            <pre className="bg-gray-50 border border-gray-200 rounded-lg p-3 overflow-x-auto text-[11px] mb-2">
              {children}
            </pre>
          ),
          // Blockquote (used for formulas section emphasis)
          blockquote: ({ children }) => (
            <blockquote className="border-l-3 border-brand-400 bg-brand-50/50 pl-3 py-1 my-2 rounded-r-lg">
              {children}
            </blockquote>
          ),
        }}
      >
        {sanitizedContent}
      </ReactMarkdown>
    </div>
  );
}
