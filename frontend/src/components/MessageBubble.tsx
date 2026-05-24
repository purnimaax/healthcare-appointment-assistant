import ReactMarkdown from "react-markdown";
import type { ChatMessage } from "../types";

interface Props {
  message: ChatMessage;
  isStreaming?: boolean;
}

// One conversational turn. User messages right-aligned, sage. Assistant
// messages left-aligned, paper-coloured card with intent badge.
export function MessageBubble({ message, isStreaming }: Props) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex gap-3 animate-fade-in ${isUser ? "justify-end" : "justify-start"}`}
    >
      {!isUser && (
        <div className="shrink-0 w-7 h-7 mt-1 rounded-full bg-sage-600 text-paper-50 flex items-center justify-center text-xs font-display">
          m
        </div>
      )}
      <div className={`max-w-[80%] ${isUser ? "items-end" : "items-start"} flex flex-col`}>
        <div
          className={
            isUser
              ? "bg-sage-600 text-paper-50 rounded-2xl rounded-tr-sm px-4 py-2.5 shadow-soft"
              : "bg-paper-100 border border-paper-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-soft text-ink-900"
          }
        >
          {isUser ? (
            <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none prose-p:my-1.5 prose-p:leading-relaxed prose-li:my-0.5 prose-headings:font-display prose-headings:my-2 prose-strong:text-ink-900">
              <ReactMarkdown>{message.content || "…"}</ReactMarkdown>
              {isStreaming && (
                <span className="inline-block w-1.5 h-4 ml-1 bg-sage-600 align-text-bottom animate-pulse-dot" />
              )}
            </div>
          )}
        </div>
        {!isUser && (message.intent || message.language) && (
          <div className="flex gap-2 mt-1.5 px-1 text-[10px] uppercase tracking-wider text-ink-500 font-mono">
            {message.intent && <span>↳ {message.intent}</span>}
            {message.language && message.language !== "en" && (
              <span>· lang: {message.language}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
