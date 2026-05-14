"use client"

import * as React from "react"
import {
  CalendarDays,
  Plus,
  Trash2,
  Copy,
  Clock,
  Users,
  CalendarX,
  Link2,
  Check,
  Loader2,
  Calendar as CalendarIcon,
} from "lucide-react"
import { toast } from "sonner"
import { format } from "date-fns"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
  SheetTrigger,
} from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { Calendar } from "@/components/ui/calendar"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"
import { useScheduleQuery } from "@/hooks/use-schedule-query"
import {
  DAYS,
  DEFAULT_SCHEDULE,
  type DayKey,
  type Override,
  type WeekSchedule,
  type DayConfig,
  type Slot,
} from "@/lib/schedule"

/* ────────────────────────────────────────────────────────────────
 * State Management (Context Selector Store for 100fps)
 * ──────────────────────────────────────────────────────────────── */

type ScheduleState = {
  week: WeekSchedule
  overrides: Override[]
}

const HHMM_24H_REGEX = /^([01]?\d|2[0-3]):([0-5]\d)(?::[0-5]\d)?$/
const HHMM_AMPM_REGEX = /^(\d{1,2}):([0-5]\d)\s*([AP]M)$/i
const STRICT_HHMM_REGEX = /^([01]\d|2[0-3]):([0-5]\d)$/

function normalizeTimeToHHMM(value: string): string {
  const raw = value.trim()
  if (!raw) return ""

  const ampmMatch = raw.match(HHMM_AMPM_REGEX)
  if (ampmMatch) {
    const hour = Number(ampmMatch[1])
    const minute = Number(ampmMatch[2])
    if (Number.isNaN(hour) || Number.isNaN(minute) || hour < 1 || hour > 12) {
      return ""
    }
    const period = ampmMatch[3].toUpperCase()
    const hour24 = (hour % 12) + (period === "PM" ? 12 : 0)
    return `${hour24.toString().padStart(2, "0")}:${minute.toString().padStart(2, "0")}`
  }

  const twentyFourMatch = raw.match(HHMM_24H_REGEX)
  if (!twentyFourMatch) return ""

  const hour = Number(twentyFourMatch[1])
  const minute = Number(twentyFourMatch[2])
  return `${hour.toString().padStart(2, "0")}:${minute.toString().padStart(2, "0")}`
}

function normalizeWeekToHHMM(week: WeekSchedule): WeekSchedule {
  return (Object.keys(week) as DayKey[]).reduce<WeekSchedule>((acc, dayKey) => {
    const day = week[dayKey]
    acc[dayKey] = {
      ...day,
      slots: day.slots.map((slot) => ({
        ...slot,
        from: normalizeTimeToHHMM(slot.from) || slot.from,
        to: normalizeTimeToHHMM(slot.to) || slot.to,
      })),
    }
    return acc
  }, {} as WeekSchedule)
}

function openNativeTimePicker(input: HTMLInputElement) {
  if ("showPicker" in input && typeof input.showPicker === "function") {
    input.showPicker()
  }
}

class ScheduleStore {
  private state: ScheduleState
  private listeners = new Set<() => void>()

  constructor(initialState: ScheduleState) {
    this.state = initialState
  }

  getState = () => this.state

  setState = (nextState: Partial<ScheduleState> | ((prev: ScheduleState) => ScheduleState)) => {
    this.state = typeof nextState === "function" ? nextState(this.state) : { ...this.state, ...nextState }
    this.listeners.forEach((l) => l())
  }

  subscribe = (listener: () => void) => {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }
}

const ScheduleStoreContext = React.createContext<ScheduleStore | null>(null)

function useScheduleStore<T>(selector: (state: ScheduleState) => T): T {
  const store = React.useContext(ScheduleStoreContext)
  if (!store) throw new Error("useScheduleStore must be used within ScheduleStoreProvider")
  return React.useSyncExternalStore(store.subscribe, () => selector(store.getState()))
}

function useScheduleDispatch() {
  const store = React.useContext(ScheduleStoreContext)
  if (!store) throw new Error("useScheduleDispatch must be used within ScheduleStoreProvider")
  return store.setState
}

/* ────────────────────────────────────────────────────────────────
 * Sub-components (Memoized for 100fps performance)
 * ──────────────────────────────────────────────────────────────── */

const MemoizedCalendar = React.memo(Calendar)

const OverrideForm = React.memo(() => {
  const dispatch = useScheduleDispatch()
  const [date, setDate] = React.useState<Date>()
  const [note, setNote] = React.useState("")

  const handleAdd = React.useCallback(() => {
    if (!date || !note) {
      toast.error("Vui lòng nhập ngày và lý do")
      return
    }
    
    dispatch((prev) => ({
      ...prev,
      overrides: [
        {
          id: crypto.randomUUID(),
          date: format(date, "dd/MM/yyyy"),
          type: "off",
          note: note,
        },
        ...prev.overrides,
      ],
    }))
    
    toast.success("Đã thêm ngày nghỉ")
    setDate(undefined)
    setNote("")
  }, [date, note, dispatch])

  return (
    <div className="grid gap-3 rounded-xl border border-primary/20 bg-primary/5 p-4 shadow-sm transition-all duration-300 hover:shadow-md sm:grid-cols-[160px_1fr_auto]">
      <Popover>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            className={cn(
              "h-10 rounded-lg border-primary/20 bg-background px-4 justify-start text-left font-sans text-sm font-normal transition-all duration-200 hover:border-primary/40 hover:bg-primary/5",
              !date && "text-muted-foreground",
            )}
          >
            <CalendarIcon className="mr-2 size-4 text-primary" />
            {date ? format(date, "dd/MM/yyyy") : <span>Chọn ngày</span>}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <MemoizedCalendar
            mode="single"
            selected={date}
            onSelect={setDate}
            disabled={(date) =>
              date < new Date(new Date().setHours(0, 0, 0, 0))
            }
            initialFocus
          />
        </PopoverContent>
      </Popover>
      <Input
        type="text"
        placeholder="Lý do, ví dụ: Hội thảo tại Đà Nẵng"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        className="h-10 rounded-lg border-primary/20 bg-background px-4 font-sans text-sm transition-all duration-200 focus:border-primary/50"
      />
      <Button
        className="h-10 rounded-lg bg-primary px-6 font-bold text-primary-foreground transition-all duration-200 hover:bg-primary/90 active:scale-95"
        onClick={handleAdd}
      >
        <Plus className="mr-1.5 size-4" />
        Thêm
      </Button>
    </div>
  )
})
OverrideForm.displayName = "OverrideForm"

const SlotRow = React.memo(
  ({
    dayKey,
    slot,
  }: {
    dayKey: DayKey
    slot: Slot
  }) => {
    const dispatch = useScheduleDispatch()
    const [draftFrom, setDraftFrom] = React.useState(() => normalizeTimeToHHMM(slot.from))
    const [draftTo, setDraftTo] = React.useState(() => normalizeTimeToHHMM(slot.to))

    React.useEffect(() => {
      setDraftFrom(normalizeTimeToHHMM(slot.from))
      setDraftTo(normalizeTimeToHHMM(slot.to))
    }, [slot.from, slot.to])

    const updateSlot = React.useCallback(
      (field: "from" | "to", value: string) => {
        const normalized = normalizeTimeToHHMM(value)
        if (!normalized) return

        dispatch((prev) => ({
          ...prev,
          week: {
            ...prev.week,
            [dayKey]: {
              ...prev.week[dayKey],
              slots: prev.week[dayKey].slots.map((s) =>
                s.id === slot.id ? { ...s, [field]: normalized } : s,
              ),
            },
          },
        }))
      },
      [dayKey, slot.id, dispatch],
    )

    const commitFrom = React.useCallback(() => {
      const normalizedDraft = normalizeTimeToHHMM(draftFrom)
      const normalizedSlot = normalizeTimeToHHMM(slot.from)
      if (STRICT_HHMM_REGEX.test(normalizedDraft) && normalizedDraft !== normalizedSlot) {
        setDraftFrom(normalizedDraft)
        updateSlot("from", normalizedDraft)
      } else if (!STRICT_HHMM_REGEX.test(normalizedDraft)) {
        setDraftFrom(normalizedSlot)
      }
    }, [draftFrom, slot.from, updateSlot])

    const commitTo = React.useCallback(() => {
      const normalizedDraft = normalizeTimeToHHMM(draftTo)
      const normalizedSlot = normalizeTimeToHHMM(slot.to)
      if (STRICT_HHMM_REGEX.test(normalizedDraft) && normalizedDraft !== normalizedSlot) {
        setDraftTo(normalizedDraft)
        updateSlot("to", normalizedDraft)
      } else if (!STRICT_HHMM_REGEX.test(normalizedDraft)) {
        setDraftTo(normalizedSlot)
      }
    }, [draftTo, slot.to, updateSlot])

    const removeSlot = React.useCallback(() => {
      dispatch((prev) => ({
        ...prev,
        week: {
          ...prev.week,
          [dayKey]: {
            ...prev.week[dayKey],
            slots: prev.week[dayKey].slots.filter((s) => s.id !== slot.id),
          },
        },
      }))
    }, [dayKey, slot.id, dispatch])

    const fromValue = normalizeTimeToHHMM(draftFrom)
    const toValue = normalizeTimeToHHMM(draftTo)

    return (
      <div className="flex items-center gap-3">
        <div className="relative">
          <Input
            key={`slot-${slot.id}-from-${fromValue || "empty"}`}
            type="time"
            value={fromValue}
            onChange={(e) => {
              const val = e.target.value
              const normalized = normalizeTimeToHHMM(val)
              setDraftFrom(normalized)
              if (STRICT_HHMM_REGEX.test(normalized)) {
                updateSlot("from", normalized)
              }
            }}
            onBlur={commitFrom}
            onClick={(e) => openNativeTimePicker(e.currentTarget)}
            onKeyDown={(e) => {
              if (e.key === "Enter") commitFrom()
            }}
            className="h-9 w-[124px] cursor-pointer rounded-lg border-primary/20 bg-background px-3 py-0 font-sans text-sm tabular-nums leading-normal [text-indent:0] [line-height:1.2] transition-colors duration-200 focus-visible:ring-1 focus-visible:ring-primary/30 hover:border-primary/40 [&::-webkit-calendar-picker-indicator]:opacity-80 [&::-webkit-datetime-edit]:p-0 [&::-webkit-datetime-edit-fields-wrapper]:p-0 [&::-webkit-datetime-edit-hour-field]:p-0 [&::-webkit-datetime-edit-minute-field]:p-0 [&::-webkit-datetime-edit-hour-field]:text-left"
          />
        </div>
        <span className="text-[11px] font-bold uppercase tracking-wider text-primary/60">
          đến
        </span>
        <div className="relative">
          <Input
            key={`slot-${slot.id}-to-${toValue || "empty"}`}
            type="time"
            value={toValue}
            onChange={(e) => {
              const val = e.target.value
              const normalized = normalizeTimeToHHMM(val)
              setDraftTo(normalized)
              if (STRICT_HHMM_REGEX.test(normalized)) {
                updateSlot("to", normalized)
              }
            }}
            onBlur={commitTo}
            onClick={(e) => openNativeTimePicker(e.currentTarget)}
            onKeyDown={(e) => {
              if (e.key === "Enter") commitTo()
            }}
            className="h-9 w-[124px] cursor-pointer rounded-lg border-primary/20 bg-background px-3 py-0 font-sans text-sm tabular-nums leading-normal [text-indent:0] [line-height:1.2] transition-colors duration-200 focus-visible:ring-1 focus-visible:ring-primary/30 hover:border-primary/40 [&::-webkit-calendar-picker-indicator]:opacity-80 [&::-webkit-datetime-edit]:p-0 [&::-webkit-datetime-edit-fields-wrapper]:p-0 [&::-webkit-datetime-edit-hour-field]:p-0 [&::-webkit-datetime-edit-minute-field]:p-0 [&::-webkit-datetime-edit-hour-field]:text-left"
          />
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="size-9 shrink-0 rounded-lg text-muted-foreground transition-colors duration-200 hover:bg-destructive/10 hover:text-destructive"
          onClick={removeSlot}
          aria-label="Xoá khoảng giờ"
        >
          <Trash2 className="size-4" />
        </Button>
      </div>
    )
  },
)
SlotRow.displayName = "SlotRow"

const DayRow = React.memo(
  ({
    dayKey,
    label,
    shortLabel,
    showErrors,
  }: {
    dayKey: DayKey
    label: string
    shortLabel: string
    showErrors: boolean
  }) => {
    const config = useScheduleStore((s) => s.week[dayKey])
    const dispatch = useScheduleDispatch()

    const isInvalid = showErrors && config.enabled && config.slots.length === 0

    const toggleDay = React.useCallback(() => {
      dispatch((prev) => {
        const currentConfig = prev.week[dayKey]
        const nextEnabled = !currentConfig.enabled
        const nextSlots =
          nextEnabled && currentConfig.slots.length === 0
            ? [{ id: crypto.randomUUID(), from: "09:00", to: "17:00" }]
            : currentConfig.slots

        return {
          ...prev,
          week: {
            ...prev.week,
            [dayKey]: {
              ...currentConfig,
              enabled: nextEnabled,
              slots: nextSlots,
            },
          },
        }
      })
    }, [dayKey, dispatch])

    const addSlot = React.useCallback(() => {
      dispatch((prev) => ({
        ...prev,
        week: {
          ...prev.week,
          [dayKey]: {
            ...prev.week[dayKey],
            enabled: true,
            slots: [
              ...prev.week[dayKey].slots,
              { id: crypto.randomUUID(), from: "13:00", to: "14:00" },
            ],
          },
        },
      }))
    }, [dayKey, dispatch])

    return (
      <div
        className={cn(
          "group rounded-xl border p-4",
          config.enabled
            ? isInvalid
              ? "border-destructive/50 bg-destructive/5 shadow-md"
              : "border-primary/10 bg-card shadow-md hover:shadow-lg"
            : "border-border/30 bg-muted/20 opacity-80",
        )}
      >
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div
              className={cn(
                "grid size-11 place-items-center rounded-full text-sm font-black shadow-sm transition-transform duration-500",
                config.enabled
                  ? isInvalid
                    ? "bg-destructive text-destructive-foreground ring-4 ring-destructive/10"
                    : "bg-primary text-primary-foreground ring-4 ring-primary/10"
                  : "bg-muted text-muted-foreground/60",
              )}
            >
              {shortLabel}
            </div>
            <div>
              <p
                className={cn(
                  "font-sans text-[15px] font-bold tracking-tight",
                  isInvalid ? "text-destructive" : "text-foreground/90",
                )}
              >
                {label}
              </p>
              <p
                className={cn(
                  "text-[11px] leading-none transition-colors",
                  isInvalid ? "font-bold text-destructive" : "font-medium text-primary/60",
                )}
              >
                {config.enabled
                  ? isInvalid
                    ? "Vui lòng thêm khung giờ"
                    : `${config.slots.length} khoảng giờ làm việc`
                  : "Đang được thiết lập là ngày nghỉ"}
              </p>
            </div>
          </div>
          <Switch
            checked={config.enabled}
            onCheckedChange={toggleDay}
            className={cn(
              isInvalid && "ring-2 ring-destructive/20 ring-offset-2",
              "data-[state=checked]:bg-primary transition-colors duration-200",
            )}
          />
        </div>

        {config.enabled && (
          <div className="mt-5 grid gap-3 pl-14">
            {config.slots.map((slot) => (
              <SlotRow
                key={slot.id}
                dayKey={dayKey}
                slot={slot}
              />
            ))}
            <Button
              variant="ghost"
              size="sm"
              className="mt-1 w-fit rounded-lg border border-dashed border-primary/20 bg-primary/5 px-4 text-[11px] font-bold text-primary transition-colors duration-200 hover:border-primary/40 hover:bg-primary/10"
              onClick={addSlot}
            >
              <Plus className="mr-1.5 size-3.5" />
              Thêm khoảng giờ
            </Button>
          </div>
        )}
      </div>
    )
  },
)
DayRow.displayName = "DayRow"

const StatsBadges = React.memo(() => {
  const week = useScheduleStore((s) => s.week)
  
  const stats = React.useMemo(() => {
    let minutes = 0
    Object.values(week).forEach((d) => {
      if (!d.enabled) return
      d.slots.forEach((s) => {
        const [fh, fm] = s.from.split(":").map(Number)
        const [th, tm] = s.to.split(":").map(Number)
        const diff = th * 60 + tm - (fh * 60 + fm)
        if (diff > 0) minutes += diff
      })
    })
    const hours = (minutes / 60).toFixed(1)
    const dur = DEFAULT_SCHEDULE.duration + DEFAULT_SCHEDULE.buffer
    const capacity = dur ? Math.floor((Number(hours) * 60) / dur) : 0
    
    return { hours, capacity }
  }, [week])

  return (
    <div className="hidden items-center gap-2 sm:flex">
      <Badge variant="secondary" className="gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-primary shadow-sm border-none font-bold">
        <Clock className="size-3.5" />
        {stats.hours} giờ / tuần
      </Badge>
      <Badge variant="outline" className="gap-1.5 rounded-full border-primary/20 px-3 py-1 text-primary shadow-sm font-bold">
        <Users className="size-3.5" />~{stats.capacity} cuộc
      </Badge>
    </div>
  )
})
StatsBadges.displayName = "StatsBadges"

const OverrideRow = React.memo(({ override: o }: { override: Override }) => {
  const dispatch = useScheduleDispatch()
  
  const removeOverride = React.useCallback(() => {
    dispatch((prev) => ({
      ...prev,
      overrides: prev.overrides.filter((item) => item.id !== o.id)
    }))
  }, [o.id, dispatch])

  return (
    <div
      className="grid grid-cols-[100px_1fr_100px_48px] items-center border-b border-primary/5 hover:bg-primary/[0.02]"
    >
      <div className="px-4 font-mono text-[12px] font-bold text-primary">
        {o.date}
      </div>
      <div className="px-4 text-[12px] font-medium text-foreground/80 truncate">
        {o.note}
      </div>
      <div className="px-4">
        <Badge
          variant={o.type === "off" ? "destructive" : "secondary"}
          className={cn(
            "h-6 gap-1.5 rounded-full px-2.5 text-[10px] font-black tracking-wide uppercase shadow-sm transition-all duration-300",
            o.type === "off" 
              ? "bg-destructive text-destructive-foreground shadow-destructive/20" 
              : "bg-primary/10 text-primary shadow-primary/5 hover:bg-primary/20"
          )}
        >
          {o.type === "off" ? (
            <>
              <CalendarX className="size-3" />
              Nghỉ
            </>
          ) : (
            <>
              <Clock className="size-3" />
              Giờ riêng
            </>
          )}
        </Badge>
      </div>
      <div className="px-4 text-right">
        <Button
          variant="ghost"
          size="icon"
          className="size-8 rounded-lg text-muted-foreground/40 transition-colors duration-200 hover:bg-destructive/10 hover:text-destructive"
          onClick={removeOverride}
          aria-label="Xoá ngày nghỉ"
        >
          <Trash2 className="size-3.5" />
        </Button>
      </div>
    </div>
  )
})
OverrideRow.displayName = "OverrideRow"

/* ────────────────────────────────────────────────────────────────
 * Main Component
 * ──────────────────────────────────────────────────────────────── */

export function ScheduleEditorSheet() {
  const { schedule, setSchedule, resetSchedule, isMutating } = useScheduleQuery()
  const [open, setOpen] = React.useState(false)

  // Store instance
  const storeRef = React.useRef<ScheduleStore>(new ScheduleStore({
    week: schedule.week,
    overrides: schedule.overrides
  }))

  // Validation state
  const [showErrors, setShowErrors] = React.useState(false)

  React.useEffect(() => {
    if (open) {
      storeRef.current.setState({
        week: normalizeWeekToHHMM(schedule.week),
        overrides: schedule.overrides
      })
      setShowErrors(false)
    }
  }, [open, schedule])

  const copyWeekday = React.useCallback(
    (source: DayKey) => {
      const state = storeRef.current.getState()
      const sourceSlots = state.week[source].slots
      
      const nextWeek = { ...state.week }
      ;(["mon", "tue", "wed", "thu", "fri"] as DayKey[]).forEach((d) => {
        nextWeek[d] = {
          enabled: true,
          slots: sourceSlots.map((s) => ({ ...s, id: crypto.randomUUID() })),
        }
      })
      
      storeRef.current.setState({ week: nextWeek })
      toast.success(
        `Đã áp lịch ${DAYS.find((d) => d.key === source)?.long} cho T2–T6`,
      )
    },
    [],
  )

  const reset = React.useCallback(() => {
    storeRef.current.setState({
      week: DEFAULT_SCHEDULE.week,
      overrides: DEFAULT_SCHEDULE.overrides
    })
    resetSchedule()
    toast.success("Đã khôi phục lịch mặc định")
  }, [resetSchedule])

  const save = React.useCallback(() => {
    const { week, overrides } = storeRef.current.getState()
    
    const invalidDays = (Object.keys(week) as DayKey[]).filter(
      (key) => week[key].enabled && week[key].slots.length === 0,
    )

    if (invalidDays.length > 0) {
      setShowErrors(true)
      toast.error("Vui lòng thêm đầy đủ khoảng thời gian cho các ngày đã chọn.")
      return
    }

    setSchedule({
      ...DEFAULT_SCHEDULE,
      week,
      overrides,
      timezone: schedule.timezone,
    })
    toast.success("Đã lưu lịch chi tiết", {
      description:
        "Thay đổi đã áp dụng cho trang đặt lịch và card Giờ làm việc.",
    })
    setOpen(false)
    setShowErrors(false)
  }, [
    setSchedule,
    schedule.timezone,
  ])

  return (
    <ScheduleStoreContext.Provider value={storeRef.current}>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger asChild>
          <Button variant="outline" size="sm" className="mt-2 rounded-lg">
            <CalendarDays className="size-4" />
            Chỉnh sửa lịch chi tiết
          </Button>
        </SheetTrigger>
        <SheetContent
          side="right"
          className="w-full gap-0 overflow-y-auto border-l border-primary/10 bg-background p-0 font-sans antialiased sm:max-w-2xl"
        >
          <SheetHeader className="sticky top-0 z-10 border-b border-primary/10 bg-background px-6 py-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <SheetTitle className="flex items-center gap-3 font-sans text-xl font-black tracking-tight text-primary">
                  <span className="grid size-10 place-items-center rounded-xl bg-primary shadow-lg shadow-primary/20 text-primary-foreground">
                    <CalendarDays className="size-5" />
                  </span>
                  Chỉnh sửa lịch chi tiết
                </SheetTitle>
                <SheetDescription className="mt-2 text-pretty font-sans text-sm font-medium text-muted-foreground/80">
                  Tuỳ chỉnh khung giờ tiếp sinh viên và ngày nghỉ với hiệu năng tối ưu.
                </SheetDescription>
              </div>
              <StatsBadges />
            </div>
          </SheetHeader>

          <div className="grid gap-8 px-6 py-8">
            {/* Weekly schedule */}
            <section className="grid gap-5">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h3 className="font-sans text-base font-black text-foreground/90 uppercase tracking-tight">
                    Khung giờ theo tuần
                  </h3>
                  <p className="text-xs font-medium text-muted-foreground/70">
                    Bật/tắt theo ngày, thêm nhiều khoảng giờ linh hoạt.
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-9 min-w-[130px] rounded-lg border-primary/20 bg-primary/5 text-primary font-bold transition-all duration-300 hover:bg-primary/10 hover:border-primary/40 hover:shadow-md"
                  onClick={() => copyWeekday("mon")}
                >
                  <Copy className="size-3.5 mr-2" />
                  Copy T2 → T6
                </Button>
              </div>

              <div className="grid gap-4">
                {DAYS.map((d) => (
                  <DayRow
                    key={d.key}
                    dayKey={d.key}
                    label={d.long}
                    shortLabel={d.short}
                    showErrors={showErrors}
                  />
                ))}
              </div>
            </section>

            <Separator className="bg-primary/5" />

            {/* Overrides */}
            <section className="grid gap-5">
              <div>
                <h3 className="font-sans text-base font-black text-foreground/90 uppercase tracking-tight">
                  Ngày nghỉ & Ngoại lệ
                </h3>
                <p className="text-[11px] font-medium text-muted-foreground/70">
                  Thêm ngày nghỉ lễ, đi công tác, hoặc khung giờ đặc biệt cho
                  ngày cụ thể.
                </p>
              </div>

              <OverrideForm />

              <OverridesList />
            </section>

            <Separator className="bg-primary/5" />

            {/* Timezone & link */}
            <section className="grid gap-5">
              <div>
                <h3 className="font-sans text-base font-black text-foreground/90 uppercase tracking-tight">
                  Liên kết đặt lịch công khai
                </h3>
                <p className="text-[11px] font-medium text-muted-foreground/70">
                  Sinh viên có thể đặt lịch hẹn trực tiếp qua liên kết này.
                </p>
              </div>

              <div className="grid gap-2">
                <div className="flex items-center gap-3 rounded-xl border border-primary/10 bg-primary/5 px-4 py-3 shadow-inner transition-colors duration-300 hover:bg-primary/[0.08]">
                  <Link2 className="size-4 text-primary" />
                  <code className="flex-1 truncate font-mono text-[12px] font-bold text-primary">
                    nexusedu.app/booking/le-ha
                  </code>
                  <TooltipProvider delayDuration={100}>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8 rounded-lg text-primary/60 transition-colors duration-200 hover:bg-primary/10 hover:text-primary active:scale-95"
                          onClick={() => {
                            navigator.clipboard?.writeText(
                              "https://nexusedu.app/booking/le-ha",
                            )
                            toast.success("Đã sao chép liên kết", {
                              description:
                                "Thông tin đã được lưu vào bộ nhớ tạm của bạn",
                            })
                          }}
                        >
                          <Copy className="size-3.5" />
                          <span className="sr-only">Copy</span>
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent side="top">Sao chép liên kết</TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
                <p className="text-[10px] font-medium text-muted-foreground/50">
                  Tự động đính kèm vào email AI gửi sinh viên.
                </p>
              </div>
            </section>
          </div>

          <SheetFooter className="sticky bottom-0 z-10 flex-row items-center justify-between gap-3 border-t border-primary/10 bg-background px-6 py-5">
            <Button
              variant="ghost"
              className="h-10 rounded-xl text-[13px] font-bold text-muted-foreground transition-colors duration-200 hover:bg-muted/50 hover:text-foreground"
              onClick={reset}
            >
              Khôi phục mặc định
            </Button>
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                className="h-10 rounded-xl border-primary/20 px-6 text-[13px] font-bold text-primary transition-colors duration-200 hover:bg-primary/5 hover:shadow-sm"
                onClick={() => setOpen(false)}
              >
                Huỷ
              </Button>
              <Button 
                className="h-10 rounded-xl bg-primary px-8 text-[13px] font-black text-primary-foreground shadow-lg shadow-primary/20 transition-transform hover:scale-[1.02] hover:bg-primary/90 active:scale-[0.98]" 
                onClick={save}
                disabled={isMutating}
              >
                {isMutating ? (
                  <Loader2 className="mr-2 size-4 animate-spin" />
                ) : (
                  <Check className="mr-2 size-4" />
                )}
                {isMutating ? "Đang lưu…" : "Lưu lịch"}
              </Button>
            </div>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </ScheduleStoreContext.Provider>
  )
}

function OverridesList() {
  const overrides = useScheduleStore((s) => s.overrides)

  return (
    <div className="overflow-hidden rounded-xl border border-primary/10 bg-card shadow-md transition-all duration-300">
      <div className="grid grid-cols-[100px_1fr_100px_48px] bg-primary/5 border-b border-primary/10">
        <div className="h-11 flex items-center px-4 font-sans text-[12px] font-black uppercase tracking-wider text-primary/70">Ngày</div>
        <div className="h-11 flex items-center px-4 font-sans text-[12px] font-black uppercase tracking-wider text-primary/70">Ghi chú</div>
        <div className="h-11 flex items-center px-4 font-sans text-[12px] font-black uppercase tracking-wider text-primary/70">Loại</div>
        <div className="h-11 w-12 px-4" />
      </div>

      {overrides.length === 0 ? (
        <div className="py-12 text-center text-[12px] text-muted-foreground/60 italic font-medium bg-muted/5">
          Chưa có ngày nghỉ nào. Lịch chạy theo khung giờ tuần.
        </div>
      ) : (
        <div className="hide-scrollbar max-h-80 overflow-y-auto">
          {overrides.map((override) => (
            <OverrideRow key={override.id} override={override} />
          ))}
        </div>
      )}
    </div>
  )
}
