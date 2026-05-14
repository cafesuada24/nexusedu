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
} from "lucide-react"
import { toast } from "sonner"
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
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
 * Sub-components (Memoized for 100fps performance)
 * ──────────────────────────────────────────────────────────────── */

const SlotRow = React.memo(
  ({
    dayKey,
    slot,
    onUpdate,
    onRemove,
  }: {
    dayKey: DayKey
    slot: Slot
    onUpdate: (day: DayKey, id: string, field: "from" | "to", value: string) => void
    onRemove: (day: DayKey, id: string) => void
  }) => {
    return (
      <div className="flex items-center gap-3 transition-all animate-in fade-in slide-in-from-left-2 duration-200">
        <div className="relative">
          <Input
            type="time"
            value={slot.from}
            onChange={(e) => onUpdate(dayKey, slot.id, "from", e.target.value)}
            className="h-9 w-[110px] rounded-lg border-border/60 bg-background px-3 font-mono text-sm transition-shadow focus-visible:ring-1"
          />
        </div>
        <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground/70">
          đến
        </span>
        <div className="relative">
          <Input
            type="time"
            value={slot.to}
            onChange={(e) => onUpdate(dayKey, slot.id, "to", e.target.value)}
            className="h-9 w-[110px] rounded-lg border-border/60 bg-background px-3 font-mono text-sm transition-shadow focus-visible:ring-1"
          />
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="size-9 shrink-0 rounded-lg text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
          onClick={() => onRemove(dayKey, slot.id)}
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
    config,
    onToggle,
    onAddSlot,
    onRemoveSlot,
    onUpdateSlot,
    isInvalid,
  }: {
    dayKey: DayKey
    label: string
    shortLabel: string
    config: DayConfig
    onToggle: (day: DayKey) => void
    onAddSlot: (day: DayKey) => void
    onRemoveSlot: (day: DayKey, id: string) => void
    onUpdateSlot: (day: DayKey, id: string, field: "from" | "to", value: string) => void
    isInvalid?: boolean
  }) => {
    return (
      <div
        className={cn(
          "group rounded-2xl border p-4 transition-all duration-300",
          config.enabled
            ? isInvalid
              ? "border-destructive/50 bg-destructive/5 shadow-sm"
              : "border-border/80 bg-card shadow-sm"
            : "border-border/30 bg-muted/20 opacity-80",
        )}
      >
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div
              className={cn(
                "grid size-10 place-items-center rounded-xl text-sm font-bold shadow-sm transition-colors",
                config.enabled
                  ? isInvalid
                    ? "bg-destructive/15 text-destructive ring-1 ring-destructive/20"
                    : "bg-primary/15 text-primary ring-1 ring-primary/20"
                  : "bg-muted text-muted-foreground/60",
              )}
            >
              {shortLabel}
            </div>
            <div>
              <p
                className={cn(
                  "font-serif text-[15px] font-semibold tracking-tight",
                  isInvalid && "text-destructive",
                )}
              >
                {label}
              </p>
              <p
                className={cn(
                  "text-[11px] leading-none transition-colors",
                  isInvalid ? "font-medium text-destructive" : "text-muted-foreground/80",
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
            onCheckedChange={() => onToggle(dayKey)}
            className={cn(isInvalid && "ring-2 ring-destructive/20 ring-offset-2", "data-[state=checked]:bg-primary")}
          />
        </div>

        {config.enabled && (
          <div className="mt-5 grid gap-3 pl-14">
            {config.slots.map((slot) => (
              <SlotRow
                key={slot.id}
                dayKey={dayKey}
                slot={slot}
                onUpdate={onUpdateSlot}
                onRemove={onRemoveSlot}
              />
            ))}
            <Button
              variant="ghost"
              size="sm"
              className="mt-1 w-fit rounded-lg border border-dashed border-border/60 bg-muted/30 px-4 text-[11px] font-medium text-muted-foreground hover:border-primary/40 hover:bg-primary/5 hover:text-primary"
              onClick={() => onAddSlot(dayKey)}
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

/* ────────────────────────────────────────────────────────────────
 * Main Component
 * ──────────────────────────────────────────────────────────────── */

export function ScheduleEditorSheet() {
  const { schedule, setSchedule, resetSchedule, isMutating } = useScheduleQuery()
  const [open, setOpen] = React.useState(false)

  // Draft state
  const [week, setWeek] = React.useState<WeekSchedule>(schedule.week)
  const [overrides, setOverrides] = React.useState<Override[]>(
    schedule.overrides,
  )
  const [newDate, setNewDate] = React.useState("")
  const [newNote, setNewNote] = React.useState("")

  // Validation state
  const [showErrors, setShowErrors] = React.useState(false)

  const invalidDays = React.useMemo(() => {
    return (Object.keys(week) as DayKey[]).filter(
      (key) => week[key].enabled && week[key].slots.length === 0,
    )
  }, [week])

  React.useEffect(() => {
    if (!open) {
      setShowErrors(false)
      return
    }
    setWeek(schedule.week)
    setOverrides(schedule.overrides)
  }, [open, schedule])

  const toggleDay = React.useCallback((day: DayKey) => {
    setWeek((w) => ({ ...w, [day]: { ...w[day], enabled: !w[day].enabled } }))
  }, [])

  const addSlot = React.useCallback((day: DayKey) => {
    setWeek((w) => ({
      ...w,
      [day]: {
        ...w[day],
        enabled: true,
        slots: [
          ...w[day].slots,
          { id: crypto.randomUUID(), from: "13:00", to: "14:00" },
        ],
      },
    }))
  }, [])

  const removeSlot = React.useCallback((day: DayKey, id: string) => {
    setWeek((w) => ({
      ...w,
      [day]: { ...w[day], slots: w[day].slots.filter((s) => s.id !== id) },
    }))
  }, [])

  const updateSlot = React.useCallback(
    (day: DayKey, id: string, field: "from" | "to", value: string) => {
      setWeek((w) => ({
        ...w,
        [day]: {
          ...w[day],
          slots: w[day].slots.map((s) =>
            s.id === id ? { ...s, [field]: value } : s,
          ),
        },
      }))
    },
    [],
  )

  const copyWeekday = React.useCallback(
    (source: DayKey) => {
      const sourceSlots = week[source].slots
      setWeek((w) => {
        const next = { ...w }
        ;(["mon", "tue", "wed", "thu", "fri"] as DayKey[]).forEach((d) => {
          next[d] = {
            enabled: true,
            slots: sourceSlots.map((s) => ({ ...s, id: crypto.randomUUID() })),
          }
        })
        return next
      })
      toast.success(
        `Đã áp lịch ${DAYS.find((d) => d.key === source)?.long} cho T2–T6`,
      )
    },
    [week],
  )

  const addOverride = React.useCallback(() => {
    if (!newDate || !newNote) {
      toast.error("Vui lòng nhập ngày và lý do")
      return
    }
    setOverrides((prev) => [
      { id: crypto.randomUUID(), date: newDate, type: "off", note: newNote },
      ...prev,
    ])
    setNewDate("")
    setNewNote("")
    toast.success("Đã thêm ngoại lệ lịch")
  }, [newDate, newNote])

  const removeOverride = React.useCallback((id: string) => {
    setOverrides((prev) => prev.filter((o) => o.id !== id))
  }, [])

  const reset = React.useCallback(() => {
    setWeek(DEFAULT_SCHEDULE.week)
    setOverrides(DEFAULT_SCHEDULE.overrides)
    resetSchedule()
    toast.success("Đã khôi phục lịch mặc định")
  }, [resetSchedule])

  const save = React.useCallback(() => {
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
    week,
    overrides,
    schedule.timezone,
    invalidDays,
  ])

  const totalActiveHours = React.useMemo(() => {
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
    return (minutes / 60).toFixed(1)
  }, [week])

  const weeklyCapacity = React.useMemo(() => {
    const dur = DEFAULT_SCHEDULE.duration + DEFAULT_SCHEDULE.buffer
    if (!dur) return 0
    return Math.floor((Number(totalActiveHours) * 60) / dur)
  }, [totalActiveHours])

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="outline" size="sm" className="mt-2 rounded-lg">
          <CalendarDays className="size-4" />
          Chỉnh sửa lịch chi tiết
        </Button>
      </SheetTrigger>
      <SheetContent
        side="right"
        className="will-change-transform translate-z-0 w-full gap-0 overflow-y-auto p-0 sm:max-w-2xl border-l border-border/60 bg-background shadow-2xl"
      >
        <SheetHeader className="sticky top-0 z-10 border-b border-border/60 bg-background/95 px-6 py-5 backdrop-blur-md">
          <div className="flex items-start justify-between gap-4">
            <div>
              <SheetTitle className="flex items-center gap-2 font-serif text-xl">
                <span className="grid size-8 place-items-center rounded-lg bg-primary/15 text-primary">
                  <CalendarDays className="size-4" />
                </span>
                Chỉnh sửa lịch chi tiết
              </SheetTitle>
              <SheetDescription className="mt-1 text-pretty">
                Tuỳ chỉnh khung giờ tiếp sinh viên và ngày nghỉ ngoại lệ.
              </SheetDescription>
            </div>
            <div className="hidden items-center gap-2 sm:flex">
              <Badge variant="secondary" className="gap-1 rounded-full px-2.5">
                <Clock className="size-3" />
                {totalActiveHours} giờ / tuần
              </Badge>
              <Badge variant="outline" className="gap-1 rounded-full px-2.5">
                <Users className="size-3" />~{weeklyCapacity} cuộc
              </Badge>
            </div>
          </div>
        </SheetHeader>

        <div className="grid gap-8 px-6 py-6">
          {/* Weekly schedule */}
          <section className="grid gap-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="font-serif text-base font-medium">
                  Khung giờ theo tuần
                </h3>
                <p className="text-xs text-muted-foreground">
                  Bật/tắt theo ngày, thêm nhiều khoảng giờ trong cùng một ngày.
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 min-w-[120px] rounded-lg border border-border/40 hover:bg-muted/80"
                onClick={() => copyWeekday("mon")}
              >
                <Copy className="size-3.5" />
                Copy T2 → T6
              </Button>
            </div>

            <div className="grid gap-3">
              {DAYS.map((d) => (
                <DayRow
                  key={d.key}
                  dayKey={d.key}
                  label={d.long}
                  shortLabel={d.short}
                  config={week[d.key]}
                  onToggle={toggleDay}
                  onAddSlot={addSlot}
                  onRemoveSlot={removeSlot}
                  onUpdateSlot={updateSlot}
                  isInvalid={showErrors && invalidDays.includes(d.key)}
                />
              ))}
            </div>
          </section>

          <Separator className="bg-border/60" />

          {/* Overrides */}
          <section className="grid gap-4">
            <div>
              <h3 className="font-serif text-base font-medium text-foreground/90">
                Ngoại lệ & ngày nghỉ
              </h3>
              <p className="text-[11px] text-muted-foreground">
                Thêm ngày nghỉ lễ, đi công tác, hoặc khung giờ đặc biệt cho
                ngày cụ thể.
              </p>
            </div>

            <div className="grid gap-3 rounded-2xl border border-dashed border-border/80 bg-muted/10 p-4 sm:grid-cols-[160px_1fr_auto]">
              <Input
                type="text"
                placeholder="dd/mm/yyyy"
                value={newDate}
                onChange={(e) => setNewDate(e.target.value)}
                className="h-10 rounded-xl border-border/60 bg-background px-4"
              />
              <Input
                type="text"
                placeholder="Lý do, ví dụ: Hội thảo tại Đà Nẵng"
                value={newNote}
                onChange={(e) => setNewNote(e.target.value)}
                className="h-10 rounded-xl border-border/60 bg-background px-4"
              />
              <Button
                variant="secondary"
                className="h-10 rounded-xl bg-primary/10 text-primary hover:bg-primary/15"
                onClick={addOverride}
              >
                <Plus className="mr-1.5 size-4" />
                Thêm
              </Button>
            </div>

            <div className="overflow-hidden rounded-2xl border border-border/60 shadow-sm">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/50 hover:bg-muted/50">
                    <TableHead className="h-11 px-4 font-serif text-[13px] font-bold">Ngày</TableHead>
                    <TableHead className="h-11 px-4 font-serif text-[13px] font-bold">Ghi chú</TableHead>
                    <TableHead className="h-11 px-4 font-serif text-[13px] font-bold">Loại</TableHead>
                    <TableHead className="h-11 w-12 px-4" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {overrides.length === 0 ? (
                    <TableRow>
                      <TableCell
                        colSpan={4}
                        className="py-8 text-center text-[12px] text-muted-foreground italic"
                      >
                        Chưa có ngoại lệ nào. Lịch chạy theo khung giờ tuần.
                      </TableCell>
                    </TableRow>
                  ) : (
                    overrides.map((o) => (
                      <TableRow key={o.id} className="hover:bg-muted/30">
                        <TableCell className="px-4 font-mono text-[12px] font-medium">
                          {o.date}
                        </TableCell>
                        <TableCell className="px-4 text-[12px] text-foreground/80">{o.note}</TableCell>
                        <TableCell className="px-4">
                          <Badge
                            variant={o.type === "off" ? "destructive" : "secondary"}
                            className="h-6 gap-1.5 rounded-full px-2.5 text-[10px] font-semibold tracking-wide uppercase"
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
                        </TableCell>
                        <TableCell className="px-4 text-right">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-8 rounded-lg text-muted-foreground/60 transition-colors hover:bg-destructive/10 hover:text-destructive"
                            onClick={() => removeOverride(o.id)}
                            aria-label="Xoá ngoại lệ"
                          >
                            <Trash2 className="size-3.5" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </section>

          <Separator className="bg-border/60" />

          {/* Timezone & link */}
          <section className="grid gap-5">
            <div>
              <h3 className="font-serif text-base font-medium text-foreground/90">
                Liên kết đặt lịch công khai
              </h3>
              <p className="text-[11px] text-muted-foreground">
                Sinh viên có thể đặt lịch hẹn trực tiếp qua liên kết này.
              </p>
            </div>

            <div className="grid gap-2">
              <div className="flex items-center gap-3 rounded-xl border border-border/60 bg-muted/30 px-4 py-2.5 shadow-inner">
                <Link2 className="size-4 text-muted-foreground/70" />
                <code className="flex-1 truncate font-mono text-[12px] text-foreground/70">
                  nexusedu.app/booking/le-ha
                </code>
                <TooltipProvider delayDuration={100}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-8 rounded-lg text-muted-foreground/60 transition-colors hover:bg-primary/10 hover:text-primary"
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
              <p className="text-[10px] text-muted-foreground/70">
                Tự động đính kèm vào email AI gửi sinh viên.
              </p>
            </div>
          </section>
        </div>

        <SheetFooter className="sticky bottom-0 z-10 flex-row items-center justify-between gap-3 border-t border-border/60 bg-background/95 px-6 py-5 backdrop-blur-md">
          <Button
            variant="ghost"
            className="h-10 rounded-xl text-[13px] font-medium text-muted-foreground hover:bg-muted/50"
            onClick={reset}
          >
            Khôi phục mặc định
          </Button>
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              className="h-10 rounded-xl border-border/80 px-6 text-[13px] font-medium transition-colors hover:bg-muted/50"
              onClick={() => setOpen(false)}
            >
              Huỷ
            </Button>
            <Button 
              className="h-10 rounded-xl bg-primary px-8 text-[13px] font-bold text-primary-foreground shadow-lg shadow-primary/20 transition-all hover:scale-[1.02] hover:bg-primary/90 active:scale-[0.98]" 
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
  )
}
