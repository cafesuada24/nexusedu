import { NextResponse } from "next/server"
import { DEFAULT_SCHEDULE, type Schedule } from "@/lib/schedule"

// Ensure this route is always dynamic and runs in Node.js so the
// module-level store below is stable across requests in the same
// server instance.
export const dynamic = "force-dynamic"
export const runtime = "nodejs"

// Cross-reload persistence in dev: stash on globalThis.
const g = globalThis as unknown as { __SCHEDULE_STORE__?: Schedule }
if (!g.__SCHEDULE_STORE__) {
  g.__SCHEDULE_STORE__ = DEFAULT_SCHEDULE
}

export async function GET() {
  return NextResponse.json(g.__SCHEDULE_STORE__, {
    headers: { "Cache-Control": "no-store" },
  })
}

export async function PUT(req: Request) {
  try {
    const body = (await req.json()) as Partial<Schedule>
    const next: Schedule = { ...DEFAULT_SCHEDULE, ...g.__SCHEDULE_STORE__, ...body }
    g.__SCHEDULE_STORE__ = next
    return NextResponse.json(next, {
      headers: { "Cache-Control": "no-store" },
    })
  } catch {
    return NextResponse.json({ error: "invalid body" }, { status: 400 })
  }
}
