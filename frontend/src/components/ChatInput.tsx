import { ArrowUp, Loader2, Paperclip } from "lucide-react";
import { useRef, useState } from "react";

interface Props {
  onSend: (text: string) => void;
  onUpload: (file: File) => void;
  disabled?: boolean;
  uploading?: boolean;
}

// Composer at the bottom of the chat. Multi-line textarea (auto-grows up to
// a cap), enter-to-send / shift+enter for newline, paperclip for upload.
export function ChatInput({ onSend, onUpload, disabled, uploading }: Props) {
  const [text, setText] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  function handleSend() {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
    // Reset textarea height
    if (taRef.current) taRef.current.style.height = "auto";
  }

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleInput(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setText(e.target.value);
    const ta = e.target;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  }

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
    e.target.value = ""; // reset so same file can be uploaded again
  }

  return (
    <div className="border-t border-paper-200 bg-paper-50 px-5 py-4">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-end gap-2 bg-paper-100 border border-paper-200 rounded-2xl px-3 py-2 shadow-soft focus-within:border-sage-400 transition-colors">
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={disabled || uploading}
            title="Upload a PDF or image"
            className="shrink-0 w-9 h-9 rounded-full flex items-center justify-center text-ink-500 hover:bg-paper-200 hover:text-sage-600 transition-colors disabled:opacity-40"
          >
            {uploading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Paperclip className="w-4 h-4" />
            )}
          </button>
          <input
            ref={fileRef}
            type="file"
            className="hidden"
            accept=".pdf,.png,.jpg,.jpeg,.webp,.gif"
            onChange={handleFile}
          />
          <textarea
            ref={taRef}
            value={text}
            onChange={handleInput}
            onKeyDown={handleKey}
            placeholder={disabled ? "Thinking…" : "Ask anything, or try: book me a cardiology appointment next Monday"}
            rows={1}
            disabled={disabled}
            className="flex-1 bg-transparent border-0 outline-none resize-none py-1.5 px-1 text-[15px] placeholder:text-ink-300 leading-relaxed disabled:opacity-60"
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={!text.trim() || disabled}
            className="shrink-0 w-9 h-9 rounded-full bg-sage-600 text-paper-50 flex items-center justify-center disabled:bg-paper-200 disabled:text-ink-300 transition-colors hover:bg-sage-800"
          >
            <ArrowUp className="w-4 h-4" />
          </button>
        </div>
        <p className="text-[11px] text-ink-300 mt-2 px-2 font-mono">
          Enter to send · Shift+Enter for newline · PDFs & images up to 10 MB
        </p>
      </div>
    </div>
  );
}
