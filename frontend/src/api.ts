// API client. All backend calls live here.

import type { Appointment, ToolCall, UploadResult } from "./types";

// In production the frontend may be served from a different origin — point this
// at the deployed backend by setting VITE_API_BASE_URL in your build env.
const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

export interface StreamHandlers {
  onStatus?: (phase: string) => void;
  onTool?: (tc: ToolCall) => void;
  onReply?: (data: { content: string; intent?: string; language?: string }) => void;
  onError?: (msg: string) => void;
  onDone?: () => void;
}

/**
 * Stream a chat reply via Server-Sent Events.
 *
 * Why fetch+ReadableStream instead of EventSource?
 *   EventSource only supports GET. Our /chat/stream is POST (body has the message),
 *   so we parse SSE frames manually from a fetch ReadableStream.
 */
export async function streamChat(
  sessionId: string,
  message: string,
  handlers: StreamHandlers
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });

  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => "");
    handlers.onError?.(`Request failed (${res.status}): ${text || res.statusText}`);
    handlers.onDone?.();
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by blank lines
    const frames = buffer.split("\n\n");
    buffer = frames.pop() || "";

    for (const frame of frames) {
      const lines = frame.split("\n");
      let event = "message";
      let data = "";
      for (const line of lines) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (!data) continue;

      let parsed: unknown;
      try {
        parsed = JSON.parse(data);
      } catch {
        continue;
      }

      const p = parsed as Record<string, unknown>;
      switch (event) {
        case "status":
          handlers.onStatus?.(String(p.phase ?? ""));
          break;
        case "tool":
          handlers.onTool?.(p as unknown as ToolCall);
          break;
        case "reply":
          handlers.onReply?.({
            content: String(p.content ?? ""),
            intent: p.intent as string | undefined,
            language: p.language as string | undefined,
          });
          break;
        case "error":
          handlers.onError?.(String(p.message ?? "Unknown error"));
          break;
        case "done":
          handlers.onDone?.();
          break;
      }
    }
  }
  handlers.onDone?.();
}

// ----- Appointments -------------------------------------------------------
export async function listDepartments(): Promise<Record<string, string[]>> {
  const r = await fetch(`${API_BASE}/api/appointments/departments`);
  if (!r.ok) throw new Error("Failed to load departments");
  return r.json();
}

export async function listAppointments(opts: {
  phone?: string;
  email?: string;
  includeCancelled?: boolean;
}): Promise<Appointment[]> {
  const qs = new URLSearchParams();
  if (opts.phone) qs.set("phone", opts.phone);
  if (opts.email) qs.set("email", opts.email);
  if (opts.includeCancelled) qs.set("include_cancelled", "true");
  const r = await fetch(`${API_BASE}/api/appointments?${qs.toString()}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function cancelAppointment(id: number): Promise<void> {
  const r = await fetch(`${API_BASE}/api/appointments/${id}`, { method: "DELETE" });
  if (!r.ok) throw new Error(await r.text());
}

// ----- Documents ----------------------------------------------------------
export async function uploadDocument(
  sessionId: string,
  file: File
): Promise<UploadResult> {
  const fd = new FormData();
  fd.append("session_id", sessionId);
  fd.append("file", file);
  const r = await fetch(`${API_BASE}/api/documents/upload`, {
    method: "POST",
    body: fd,
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(text || `Upload failed (${r.status})`);
  }
  return r.json();
}
