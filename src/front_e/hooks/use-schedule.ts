"use client"

import * as React from "react"
import { DEFAULT_SCHEDULE, type Schedule } from "@/lib/schedule"

// Module-level singleton so every `useSchedule()` in the same tab shares
// the exact same state. Persistence is done via a server API so that the
// advisor's dashboard and the student's booking link (possibly on a
// different device/browser) see the same schedule.
let state: Schedule = DEFAULT_SCHEDULE
let hydrated = false
let hydratingPromise: Promise<void> | null = null
const listeners = new Set<() => void>()
const POLL_MS = 4000

function notify() {
  listeners.forEach((l) => l())
}

async function fetchSchedule(): Promise<Schedule> {
  const res = await fetch("/api/schedule", { cache: "no-store" })
  if (!res.ok) throw new Error("failed to load schedule")
  const data = (await res.json()) as Partial<Schedule>
  return { ...DEFAULT_SCHEDULE, ...data }
}

function ensureHydrated(): Promise<void> {
  if (hydrated) return Promise.resolve()
  if (hydratingPromise) return hydratingPromise
  hydratingPromise = fetchSchedule()
    .then((s) => {
      state = s
      hydrated = true
      notify()
    })
    .catch(() => {
      // Leave state as DEFAULT_SCHEDULE; will retry on next poll.
    })
    .finally(() => {
      hydratingPromise = null
    })
  return hydratingPromise
}

async function refresh() {
  try {
    const s = await fetchSchedule()
    // Only update + notify if something actually changed to avoid
    // unnecessary re-renders.
    if (JSON.stringify(s) !== JSON.stringify(state)) {
      state = s
      notify()
    }
  } catch {
    // ignore transient errors
  }
}

async function persist(next: Schedule) {
  state = next
  notify()
  try {
    await fetch("/api/schedule", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(next),
      cache: "no-store",
    })
  } catch {
    // swallow; UI already reflects the optimistic update
  }
}

export function useSchedule() {
  const [local, setLocal] = React.useState<Schedule>(state)

  React.useEffect(() => {
    const listener = () => setLocal({ ...state })
    listeners.add(listener)

    // Hydrate from server on mount (SSR-safe).
    ensureHydrated().then(() => setLocal({ ...state }))

    // Poll so the student booking page reflects advisor changes
    // without needing a manual refresh.
    const interval = window.setInterval(() => {
      refresh()
    }, POLL_MS)

    // Refresh on focus / tab visibility for snappier updates.
    const onFocus = () => refresh()
    const onVisibility = () => {
      if (document.visibilityState === "visible") refresh()
    }
    window.addEventListener("focus", onFocus)
    document.addEventListener("visibilitychange", onVisibility)

    return () => {
      listeners.delete(listener)
      window.clearInterval(interval)
      window.removeEventListener("focus", onFocus)
      document.removeEventListener("visibilitychange", onVisibility)
    }
  }, [])

  return {
    schedule: local,
    setSchedule: (
      updater: Schedule | ((prev: Schedule) => Schedule),
    ) => {
      const next =
        typeof updater === "function"
          ? (updater as (p: Schedule) => Schedule)(state)
          : updater
      void persist(next)
    },
    resetSchedule: () => {
      void persist(DEFAULT_SCHEDULE)
    },
  }
}
