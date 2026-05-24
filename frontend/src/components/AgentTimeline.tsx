import {
  Activity,
  Check,
  ChevronDown,
  ChevronRight,
  CircleAlert,
  Loader2,
  Route,
} from "lucide-react";
import { useState } from "react";
import type { ToolCall } from "../types";

interface Props {
  events: ToolCall[];
}

// Shows each tool call as a row with status icon, label, and expandable args/result.
export function AgentTimeline({ events }: Props) {
  return (
    <aside className="h-full flex flex-col bg-paper-100/60 border-l border-paper-200">
      <div className="px-5 py-4 border-b border-paper-200 flex items-center gap-2">
        <Activity className="w-4 h-4 text-sage-600" />
        <h2 className="font-display text-lg tracking-tight">Agent Activity</h2>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {events.length === 0 ? (
          <EmptyState />
        ) : (
          <ol className="px-5 py-4 space-y-2.5">
            {events.map((e, i) => (
              <TimelineRow key={i} event={e} index={i} />
            ))}
          </ol>
        )}
      </div>
    </aside>
  );
}

function EmptyState() {
  return (
    <div className="px-5 py-12 text-center">
      <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-paper-200/60 flex items-center justify-center">
        <Activity className="w-5 h-5 text-ink-300" />
      </div>
      <p className="text-sm text-ink-500 leading-relaxed">
        Tool calls and agent routing will appear here when you send a message.
      </p>
      <p className="text-xs text-ink-300 mt-3 font-mono">
        router · appointment · rag · document · summary
      </p>
    </div>
  );
}

function TimelineRow({ event, index }: { event: ToolCall; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const hasDetails =
    (event.args && Object.keys(event.args).length > 0) ||
    (event.result && Object.keys(event.result).length > 0);

  return (
    <li
      className={
        "rounded-lg border bg-paper-50 transition-colors animate-fade-in " +
        (event.status === "running"
          ? "border-sage-200 stripe-running"
          : event.status === "error"
            ? "border-clay-400/40"
            : "border-paper-200")
      }
    >
      <button
        type="button"
        onClick={() => hasDetails && setExpanded((v) => !v)}
        disabled={!hasDetails}
        className="w-full px-3 py-2.5 flex items-center gap-3 text-left disabled:cursor-default"
      >
        <span className="shrink-0 text-[10px] font-mono text-ink-300 tabular-nums w-5">
          {String(index + 1).padStart(2, "0")}
        </span>
        <StatusIcon status={event.status} tool={event.tool} />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-ink-900 truncate">
            {event.label}
          </div>
          <div className="text-[11px] font-mono text-ink-500 mt-0.5">
            {event.tool}
          </div>
        </div>
        {hasDetails &&
          (expanded ? (
            <ChevronDown className="w-4 h-4 text-ink-300 shrink-0" />
          ) : (
            <ChevronRight className="w-4 h-4 text-ink-300 shrink-0" />
          ))}
      </button>

      {expanded && hasDetails && (
        <div className="border-t border-paper-200 px-3 py-2.5 bg-paper-100/60 text-[11px] font-mono space-y-2">
          {event.args && Object.keys(event.args).length > 0 && (
            <DetailBlock title="args" data={event.args} />
          )}
          {event.result && Object.keys(event.result).length > 0 && (
            <DetailBlock title="result" data={event.result} />
          )}
        </div>
      )}
    </li>
  );
}

function StatusIcon({ status, tool }: { status: ToolCall["status"]; tool: string }) {
  if (tool === "router") {
    return <Route className="w-4 h-4 text-sage-600 shrink-0" />;
  }
  if (status === "running")
    return <Loader2 className="w-4 h-4 text-sage-600 animate-spin shrink-0" />;
  if (status === "error")
    return <CircleAlert className="w-4 h-4 text-clay-600 shrink-0" />;
  return <Check className="w-4 h-4 text-sage-600 shrink-0" />;
}

function DetailBlock({
  title,
  data,
}: {
  title: string;
  data: Record<string, unknown>;
}) {
  return (
    <div>
      <div className="text-ink-500 uppercase tracking-wider text-[9px] mb-1">
        {title}
      </div>
      <pre className="whitespace-pre-wrap break-words text-ink-700 leading-relaxed">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}
