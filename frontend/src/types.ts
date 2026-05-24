// Shared types between components.

export type Role = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  intent?: string;
  language?: string;
  toolCalls?: ToolCall[];
}

export interface ToolCall {
  tool: string;
  label: string;
  status: "running" | "done" | "error";
  args?: Record<string, unknown>;
  result?: Record<string, unknown>;
}

export interface Appointment {
  appointment_id: number;
  department: string;
  doctor: string;
  date: string;
  time: string;
  status: string;
  notes?: string | null;
}

export interface UploadResult {
  filename: string;
  type: "pdf" | "image";
  chunks_indexed: number;
  extracted_text_preview: string;
  summary?: string | null;
  uploaded_at: string;
}
