export type Slot = { id: string; from: string; to: string }
export type DayKey = "mon" | "tue" | "wed" | "thu" | "fri" | "sat" | "sun"
export type DayConfig = { enabled: boolean; slots: Slot[] }
export type WeekSchedule = Record<DayKey, DayConfig>

export type Override = {
  id: string
  date: string // dd/MM/yyyy
  type: "off" | "custom"
  note: string
}

export type Schedule = {
  week: WeekSchedule
  overrides: Override[]
  duration: number // minutes
  buffer: number // minutes
  dailyCap: number
  autoConfirm: boolean
  allowOnline: boolean
  requireReason: boolean
  timezone: string
}

export const DAYS: {
  key: DayKey
  short: string
  long: string
  jsDay: number
}[] = [
  { key: "mon", short: "T2", long: "Thứ Hai", jsDay: 1 },
  { key: "tue", short: "T3", long: "Thứ Ba", jsDay: 2 },
  { key: "wed", short: "T4", long: "Thứ Tư", jsDay: 3 },
  { key: "thu", short: "T5", long: "Thứ Năm", jsDay: 4 },
  { key: "fri", short: "T6", long: "Thứ Sáu", jsDay: 5 },
  { key: "sat", short: "T7", long: "Thứ Bảy", jsDay: 6 },
  { key: "sun", short: "CN", long: "Chủ Nhật", jsDay: 0 },
]

export const DAY_ORDER: DayKey[] = [
  "mon",
  "tue",
  "wed",
  "thu",
  "fri",
  "sat",
  "sun",
]

export const DEFAULT_WEEK: WeekSchedule = {
  mon: {
    enabled: true,
    slots: [
      { id: "mon-1", from: "09:00", to: "11:30" },
      { id: "mon-2", from: "14:00", to: "17:00" },
    ],
  },
  tue: {
    enabled: true,
    slots: [
      { id: "tue-1", from: "09:00", to: "11:30" },
      { id: "tue-2", from: "14:00", to: "17:00" },
    ],
  },
  wed: {
    enabled: true,
    slots: [
      { id: "wed-1", from: "09:00", to: "11:30" },
      { id: "wed-2", from: "14:00", to: "17:00" },
    ],
  },
  thu: {
    enabled: true,
    slots: [
      { id: "thu-1", from: "09:00", to: "11:30" },
      { id: "thu-2", from: "14:00", to: "17:00" },
    ],
  },
  fri: {
    enabled: true,
    slots: [
      { id: "fri-1", from: "09:00", to: "11:30" },
      { id: "fri-2", from: "14:00", to: "17:00" },
    ],
  },
  sat: { enabled: true, slots: [{ id: "sat-1", from: "09:00", to: "11:00" }] },
  sun: { enabled: false, slots: [] },
}

export const DEFAULT_OVERRIDES: Override[] = [
  { id: "o1", date: "30/04/2026", type: "off", note: "Nghỉ lễ 30/4 – 1/5" },
  { id: "o2", date: "02/09/2026", type: "off", note: "Quốc khánh" },
  {
    id: "o3",
    date: "15/05/2026",
    type: "custom",
    note: "Chỉ nhận 14:00 – 16:00 (họp khoa buổi sáng)",
  },
]

export const DEFAULT_SCHEDULE: Schedule = {
  week: DEFAULT_WEEK,
  overrides: DEFAULT_OVERRIDES,
  duration: 30,
  buffer: 10,
  dailyCap: 6,
  autoConfirm: true,
  allowOnline: true,
  requireReason: true,
  timezone: "Asia/Ho_Chi_Minh",
}

// ---- Helpers ----

export function dateToDDMMYYYY(d: Date): string {
  return `${d.getDate().toString().padStart(2, "0")}/${(d.getMonth() + 1)
    .toString()
    .padStart(2, "0")}/${d.getFullYear()}`
}

export function dayKeyFromDate(d: Date): DayKey {
  const map: DayKey[] = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
  return map[d.getDay()]
}

function toMinutes(hhmm: string): number {
  const [h, m] = hhmm.split(":").map(Number)
  return h * 60 + m
}

function toHHMM(mins: number): string {
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`
}

/** Is this calendar date fully blocked (weekday off, or off override)? */
export function isDateOff(date: Date, schedule: Schedule): boolean {
  const dk = dayKeyFromDate(date)
  if (!schedule.week[dk].enabled) return true
  const ds = dateToDDMMYYYY(date)
  const ov = schedule.overrides.find((o) => o.date === ds)
  return !!(ov && ov.type === "off")
}

/** Returns the "custom" override (e.g. partial-day) for a date, if any. */
export function getCustomOverride(
  date: Date,
  schedule: Schedule,
): Override | null {
  const ds = dateToDDMMYYYY(date)
  return (
    schedule.overrides.find((o) => o.date === ds && o.type === "custom") ?? null
  )
}

/** Generate HH:MM start times for a date based on the schedule. */
export function generateSlotsForDate(
  date: Date,
  schedule: Schedule,
): string[] {
  if (isDateOff(date, schedule)) return []
  const day = schedule.week[dayKeyFromDate(date)]
  const step = schedule.duration + schedule.buffer
  const out: string[] = []
  for (const s of day.slots) {
    const start = toMinutes(s.from)
    const end = toMinutes(s.to)
    for (let t = start; t + schedule.duration <= end; t += step) {
      out.push(toHHMM(t))
    }
  }
  return out
}

export type WeekSummaryGroup = {
  keys: DayKey[]
  label: string
  hours: string
  enabled: boolean
}

/**
 * Collapse consecutive days that share the same schedule into a single
 * row for the Settings summary card.
 */
export function summarizeWeek(week: WeekSchedule): WeekSummaryGroup[] {
  const items = DAY_ORDER.map((k) => ({
    key: k,
    day: week[k],
    sig: week[k].enabled
      ? week[k].slots.map((s) => `${s.from}-${s.to}`).join("|") || "empty"
      : "off",
  }))
  const groups: { keys: DayKey[]; sig: string; day: DayConfig }[] = []
  for (const it of items) {
    const last = groups[groups.length - 1]
    if (last && last.sig === it.sig) last.keys.push(it.key)
    else groups.push({ keys: [it.key], sig: it.sig, day: it.day })
  }
  return groups.map((g) => {
    const labels = g.keys.map((k) => DAYS.find((d) => d.key === k)!.long)
    const label =
      g.keys.length === 1
        ? labels[0]
        : `${labels[0]} – ${labels[labels.length - 1]}`
    const hours = !g.day.enabled
      ? "Nghỉ"
      : g.day.slots.length === 0
      ? "Trống (chưa cấu hình khung giờ)"
      : g.day.slots.map((s) => `${s.from} – ${s.to}`).join(" · ")
    return { keys: g.keys, label, hours, enabled: g.day.enabled }
  })
}

/** Total number of working hours per week. */
export function totalWeeklyHours(week: WeekSchedule): number {
  let minutes = 0
  Object.values(week).forEach((d) => {
    if (!d.enabled) return
    d.slots.forEach((s) => {
      minutes += toMinutes(s.to) - toMinutes(s.from)
    })
  })
  return Math.max(0, minutes / 60)
}
