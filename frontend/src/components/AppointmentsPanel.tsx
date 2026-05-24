import { Calendar, Loader2, X } from "lucide-react";
import { useState } from "react";
import { cancelAppointment, listAppointments } from "../api";
import type { Appointment } from "../types";

interface Props {
  open: boolean;
  onClose: () => void;
}

// Talks to REST endpoints directly — no AI in the loop.
export function AppointmentsPanel({ open, onClose }: Props) {
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [appts, setAppts] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  if (!open) return null;

  async function search() {
    if (!phone && !email) {
      setError("Enter a phone or email.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await listAppointments({
        phone: phone || undefined,
        email: email || undefined,
        includeCancelled: true,
      });
      setAppts(data);
      setSearched(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lookup failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleCancel(id: number) {
    if (!confirm(`Cancel appointment #${id}?`)) return;
    try {
      await cancelAppointment(id);
      await search();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cancel failed");
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/40 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl mx-4 bg-paper-50 rounded-2xl shadow-card border border-paper-200 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-paper-200">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-sage-600" />
            <h2 className="font-display text-xl tracking-tight">
              My Appointments
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center text-ink-500 hover:bg-paper-200"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="px-6 py-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Input
              label="Phone"
              value={phone}
              onChange={setPhone}
              placeholder="9876543210"
            />
            <Input
              label="Email"
              value={email}
              onChange={setEmail}
              placeholder="you@example.com"
            />
          </div>
          <div className="flex gap-3 mt-4">
            <button
              type="button"
              onClick={search}
              disabled={loading}
              className="px-4 py-2 rounded-full bg-sage-600 text-paper-50 text-sm font-medium hover:bg-sage-800 disabled:opacity-50 flex items-center gap-2"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              Look up
            </button>
            {error && (
              <p className="text-sm text-clay-600 self-center">{error}</p>
            )}
          </div>

          <div className="mt-6 max-h-[50vh] overflow-y-auto scrollbar-thin">
            {searched && appts.length === 0 && (
              <p className="text-sm text-ink-500 py-6 text-center">
                No appointments found for that identifier.
              </p>
            )}
            {appts.length > 0 && (
              <ul className="space-y-2">
                {appts.map((a) => (
                  <li
                    key={a.appointment_id}
                    className="flex items-center justify-between border border-paper-200 rounded-lg px-4 py-3 bg-paper-100/60"
                  >
                    <div>
                      <div className="font-medium text-ink-900">
                        {a.department} · {a.doctor}
                      </div>
                      <div className="text-xs text-ink-500 mt-1 font-mono">
                        {a.date} · {a.time} · #{a.appointment_id}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span
                        className={
                          "text-[10px] uppercase tracking-wider font-mono px-2 py-1 rounded-full " +
                          (a.status === "cancelled"
                            ? "bg-paper-200 text-ink-500"
                            : "bg-sage-50 text-sage-800")
                        }
                      >
                        {a.status}
                      </span>
                      {a.status === "booked" && (
                        <button
                          type="button"
                          onClick={() => handleCancel(a.appointment_id)}
                          className="text-xs text-clay-600 hover:underline"
                        >
                          Cancel
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Input({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="block">
      <span className="block text-[11px] uppercase tracking-wider text-ink-500 font-mono mb-1">
        {label}
      </span>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-paper-100 border border-paper-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-sage-400"
      />
    </label>
  );
}
