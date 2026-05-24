import { Sparkles } from "lucide-react";

// Top bar with clinic branding.
export function Header() {
  return (
    <header className="border-b border-paper-200 bg-paper-50/80 backdrop-blur supports-[backdrop-filter]:bg-paper-50/60">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-sage-600 text-paper-50 flex items-center justify-center font-display text-lg">
            m
          </div>
          <div>
            <div className="font-display text-xl leading-none tracking-tight">
              Mykare Health
            </div>
            <div className="text-xs text-ink-500 mt-0.5 tracking-wide uppercase">
              Front Desk · AI Assistant
            </div>
          </div>
        </div>
        <div className="hidden sm:flex items-center gap-2 text-xs text-ink-500 font-mono">
          <Sparkles className="w-3.5 h-3.5 text-sage-600" />
          groq · langgraph · chroma
        </div>
      </div>
    </header>
  );
}
