# Demo Script

Quick walkthrough covering every feature — takes about 4-5 minutes.

## Before you start

1. Backend on `:8000`, frontend on `:5173`
2. Hit `/api/health` and confirm `api_key_configured: true` and KB chunks > 0
3. Open frontend in a clean browser window (fresh session ID)
4. Have a sample lab report PDF and a prescription image ready

---

## Act 1 — RAG (20s)

Click the suggestion chip: *"What should I bring for a dermatology visit?"*

Watch the agent panel:
- router → rag
- `retrieve_documents` running → done
- Answer cites `preparation_guide.md`

---

## Act 2 — Booking (90s)

Type: *"I'd like to book a cardiology appointment for next Tuesday morning. My name is Priya, phone 9876543210."*

Agent panel:
- router → appointment
- `fetch_slots` → done (doctor + date resolved)
- Agent asks for the time

Type: *"10:30 works."*

- `book_appointment` → done
- Confirmation with appointment ID

Expand the `book_appointment` row to show args + result.

---

## Act 3 — Reschedule (30s)

Type: *"Actually can you move it to 14:00?"*

- `modify_appointment` → done
- Agent confirms — no need to specify the ID, it remembers

---

## Act 4 — REST surface (20s)

Click *My Appointments*, enter phone `9876543210`, hit *Look up*. Shows the appointment.

Open `/docs` in a new tab briefly.

---

## Act 5 — Document upload (40s)

Click the paperclip, upload a lab report PDF.

- Upload completes, assistant shows filename + summary

Type: *"Were any values outside the normal range?"*

- router → document agent
- `retrieve_documents` (user_uploads scope) → done
- Answer pulled from the PDF

---

## Act 6 — Multilingual (30s)

Type: *"मुझे अगले सोमवार को त्वचा विशेषज्ञ के साथ अपॉइंटमेंट चाहिए"*

- router → appointment, language: hi
- Agent responds in Hindi, tools run as usual

---

## Act 7 — Summary (15s)

Type: *"Quick summary of what we've done?"*

- router → summary agent
- Recap of identity captured, appointments, questions, docs uploaded

---

## If you only have 60 seconds

Run **Act 2** → **Act 5** → **Act 6**. Covers multi-agent routing, tool calling, RAG, multimodal, and multilingual in three messages.
