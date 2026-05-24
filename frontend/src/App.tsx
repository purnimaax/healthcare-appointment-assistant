import { Calendar, FileText, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { streamChat, uploadDocument } from "./api";
import { AgentTimeline } from "./components/AgentTimeline";
import { AppointmentsPanel } from "./components/AppointmentsPanel";
import { ChatInput } from "./components/ChatInput";
import { Header } from "./components/Header";
import { MessageBubble } from "./components/MessageBubble";
import type { ChatMessage, ToolCall, UploadResult } from "./types";

// Stable per-tab session id (= LangGraph thread_id, = RAG upload scope)
function getSessionId(): string {
  const k = "mykare_session_id";
  let id = sessionStorage.getItem(k);
  if (!id) {
    id = `s_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
    sessionStorage.setItem(k, id);
  }
  return id;
}

const SUGGESTIONS = [
  "I'd like to book a cardiology appointment for next Tuesday",
  "What should I bring for a dermatology visit?",
  "Do you accept HDFC ERGO insurance?",
  "मुझे अगले हफ्ते डॉक्टर से मिलना है", // Hindi: "I'd like to see a doctor next week"
];

export default function App() {
  const [sessionId] = useState(getSessionId);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [toolEvents, setToolEvents] = useState<ToolCall[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [showAppts, setShowAppts] = useState(false);
  const [uploads, setUploads] = useState<UploadResult[]>([]);

  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the latest message on every update
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, streaming]);

  async function handleSend(text: string) {
    if (streaming) return;

    // Optimistic user message + empty assistant placeholder to stream into
    const userMsg: ChatMessage = {
      id: `u_${Date.now()}`,
      role: "user",
      content: text,
    };
    const asstId = `a_${Date.now()}`;
    setMessages((m) => [...m, userMsg, { id: asstId, role: "assistant", content: "" }]);
    setToolEvents([]);
    setStreaming(true);

    let collectedTools: ToolCall[] = [];

    await streamChat(sessionId, text, {
      onTool: (tc) => {
        // Replace running with done for the same tool/args pair; otherwise append
        collectedTools = mergeToolEvent(collectedTools, tc);
        setToolEvents([...collectedTools]);
      },
      onReply: ({ content, intent, language }) => {
        setMessages((m) =>
          m.map((msg) =>
            msg.id === asstId
              ? { ...msg, content, intent, language, toolCalls: collectedTools }
              : msg
          )
        );
      },
      onError: (msg) => {
        setMessages((m) =>
          m.map((msg2) =>
            msg2.id === asstId
              ? {
                  ...msg2,
                  content: `⚠️ Something went wrong: ${msg}\n\nIf this is the first message, double-check that GROQ_API_KEY is set in backend/.env.`,
                }
              : msg2
          )
        );
      },
      onDone: () => setStreaming(false),
    });
  }

  async function handleUpload(file: File) {
    setUploading(true);
    try {
      const result = await uploadDocument(sessionId, file);
      setUploads((u) => [...u, result]);

      // Surface the upload as a system-style message in the chat so the user
      // sees the result immediately
      const note = [
        `📎 Uploaded **${result.filename}** (${result.type}).`,
        result.summary ? `\n\n**Summary**\n\n${result.summary}` : "",
        `\n\n_You can now ask questions about this document._`,
      ].join("");

      setMessages((m) => [
        ...m,
        { id: `up_${Date.now()}`, role: "assistant", content: note },
      ]);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Upload failed";
      setMessages((m) => [
        ...m,
        { id: `e_${Date.now()}`, role: "assistant", content: `⚠️ Upload failed: ${msg}` },
      ]);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="h-full flex flex-col">
      <Header />

      <div className="flex-1 min-h-0 max-w-7xl w-full mx-auto px-4 py-4">
        <div className="h-full grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-4">
          {/* Chat column */}
          <div className="flex flex-col h-full min-h-0 bg-paper-50 border border-paper-200 rounded-2xl shadow-card overflow-hidden">
            <ChatToolbar
              uploadsCount={uploads.length}
              onOpenAppts={() => setShowAppts(true)}
            />

            <div
              ref={scrollRef}
              className="flex-1 overflow-y-auto scrollbar-thin px-5 py-6"
            >
              {messages.length === 0 ? (
                <Welcome onPick={handleSend} />
              ) : (
                <div className="max-w-3xl mx-auto space-y-4">
                  {messages.map((m, i) => (
                    <MessageBubble
                      key={m.id}
                      message={m}
                      isStreaming={
                        streaming && i === messages.length - 1 && m.role === "assistant"
                      }
                    />
                  ))}
                </div>
              )}
            </div>

            <ChatInput
              onSend={handleSend}
              onUpload={handleUpload}
              disabled={streaming || uploading}
              uploading={uploading}
            />
          </div>

          {/* Agent activity column */}
          <div className="hidden lg:block border border-paper-200 rounded-2xl shadow-card overflow-hidden">
            <AgentTimeline events={toolEvents} />
          </div>
        </div>
      </div>

      <AppointmentsPanel open={showAppts} onClose={() => setShowAppts(false)} />
    </div>
  );
}

// Merge incoming tool event: if a running tool with same name+args exists,
// replace it. Otherwise append.
function mergeToolEvent(events: ToolCall[], incoming: ToolCall): ToolCall[] {
  const key = (e: ToolCall) =>
    `${e.tool}::${JSON.stringify(e.args || {})}`;
  const incomingKey = key(incoming);
  // If incoming is a "done"/"error", find the matching "running" and replace it
  if (incoming.status !== "running") {
    const idx = events.findIndex(
      (e) => key(e) === incomingKey && e.status === "running"
    );
    if (idx !== -1) {
      const next = events.slice();
      next[idx] = incoming;
      return next;
    }
  }
  return [...events, incoming];
}

function ChatToolbar({
  uploadsCount,
  onOpenAppts,
}: {
  uploadsCount: number;
  onOpenAppts: () => void;
}) {
  return (
    <div className="border-b border-paper-200 px-5 py-3 flex items-center justify-between bg-paper-50">
      <div className="flex items-center gap-2 text-sm text-ink-500">
        <Sparkles className="w-3.5 h-3.5 text-sage-600" />
        <span className="font-mono text-xs">Conversation</span>
      </div>
      <div className="flex items-center gap-1.5">
        {uploadsCount > 0 && (
          <span className="flex items-center gap-1.5 text-xs text-ink-500 px-2.5 py-1 rounded-full bg-sage-50 border border-sage-200 font-mono">
            <FileText className="w-3 h-3" />
            {uploadsCount} doc{uploadsCount > 1 ? "s" : ""}
          </span>
        )}
        <button
          type="button"
          onClick={onOpenAppts}
          className="flex items-center gap-1.5 text-xs text-ink-700 px-3 py-1.5 rounded-full hover:bg-paper-200 transition-colors"
        >
          <Calendar className="w-3.5 h-3.5" />
          My Appointments
        </button>
      </div>
    </div>
  );
}

function Welcome({ onPick }: { onPick: (text: string) => void }) {
  return (
    <div className="max-w-2xl mx-auto py-10 animate-fade-in">
      <div className="text-center">
        <div className="inline-block px-3 py-1 rounded-full bg-sage-50 border border-sage-200 text-xs font-mono text-sage-800 mb-5">
          welcome
        </div>
        <h1 className="font-display text-3xl sm:text-4xl tracking-tight text-ink-900 leading-tight">
          How can we help you today?
        </h1>
        <p className="mt-3 text-ink-500 text-[15px] max-w-md mx-auto leading-relaxed">
          Book an appointment, ask about our departments, or upload a lab report
          for a quick summary. I respond in your language.
        </p>
      </div>

      <div className="mt-9 grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {SUGGESTIONS.map((s, i) => (
          <button
            key={i}
            type="button"
            onClick={() => onPick(s)}
            className="text-left p-3.5 rounded-xl border border-paper-200 bg-paper-100/40 hover:bg-paper-100 hover:border-sage-200 transition-all text-sm text-ink-700 leading-relaxed group"
          >
            <span className="block group-hover:text-sage-800 transition-colors">
              {s}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
