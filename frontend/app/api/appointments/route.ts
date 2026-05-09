import { NextResponse } from "next/server"
import type {
  Appointment,
  AppointmentMode,
  CreateAppointmentInput,
} from "@/lib/appointments"

export const dynamic = "force-dynamic"
export const runtime = "nodejs"

const g = globalThis as unknown as { __APPOINTMENTS_STORE__?: Appointment[] }
if (!g.__APPOINTMENTS_STORE__) {
  g.__APPOINTMENTS_STORE__ = []
}

const VALID_MODES: AppointmentMode[] = ["video", "inperson"]
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/
const SLOT_RE = /^\d{2}:\d{2}$/

function isValidInput(body: unknown): body is CreateAppointmentInput {
  if (!body || typeof body !== "object") return false
  const b = body as Record<string, unknown>
  return (
    typeof b.advisorToken === "string" &&
    b.advisorToken.length > 0 &&
    typeof b.caseId === "string" &&
    b.caseId.length > 0 &&
    typeof b.date === "string" &&
    DATE_RE.test(b.date) &&
    typeof b.slot === "string" &&
    SLOT_RE.test(b.slot) &&
    typeof b.mode === "string" &&
    VALID_MODES.includes(b.mode as AppointmentMode)
  )
}

export async function GET(req: Request) {
  const url = new URL(req.url)
  const advisor = url.searchParams.get("advisor")
  const from = url.searchParams.get("from")
  const to = url.searchParams.get("to")

  let list = g.__APPOINTMENTS_STORE__ ?? []
  if (advisor) list = list.filter((a) => a.advisorToken === advisor)
  if (from) list = list.filter((a) => a.date >= from)
  if (to) list = list.filter((a) => a.date <= to)

  return NextResponse.json(list, {
    headers: { "Cache-Control": "no-store" },
  })
}

export async function POST(req: Request) {
  let body: unknown
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 })
  }

  if (!isValidInput(body)) {
    return NextResponse.json({ error: "invalid_body" }, { status: 400 })
  }

  const store = g.__APPOINTMENTS_STORE__ ?? []
  const conflict = store.find(
    (a) =>
      a.advisorToken === body.advisorToken &&
      a.date === body.date &&
      a.slot === body.slot,
  )
  if (conflict) {
    return NextResponse.json({ error: "slot_taken" }, { status: 409 })
  }

  const appointment: Appointment = {
    id: crypto.randomUUID(),
    createdAt: Date.now(),
    ...body,
  }
  store.push(appointment)
  g.__APPOINTMENTS_STORE__ = store

  return NextResponse.json(appointment, {
    status: 201,
    headers: { "Cache-Control": "no-store" },
  })
}
