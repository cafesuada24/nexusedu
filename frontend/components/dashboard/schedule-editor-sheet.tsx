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
  Globe,
  Link2,
  Check,
  Info,
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
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
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
import { useSchedule } from "@/hooks/use-schedule"
import {
  DAYS,
  DEFAULT_SCHEDULE,
  type DayKey,
  type Override,
  type WeekSchedule,
} from "@/lib/schedule"

export function ScheduleEditorSheet() {
  const { schedule, setSchedule, resetSchedule } = useSchedule()
  const [open, setOpen] = React.useState(false)

  // Draft state: edits are held locally until "Lưu lịch" is pressed so that
  // the Settings card + Booking page don't flicker while the user is editing.
  const [week, setWeek] = React.useState<WeekSchedule>(schedule.week)
  const [duration, setDuration] = React.useState(String(schedule.duration))
  const [buffer, setBuffer] = React.useState(String(schedule.buffer))
  const [dailyCap, setDailyCap] = React.useState(String(schedule.dailyCap))
  const [minNotice, setMinNotice] = React.useState(schedule.minNotice)
  const [windowDays, setWindowDays] = React.useState(String(schedule.windowDays))
  const [autoConfirm, setAutoConfirm] = React.useState(schedule.autoConfirm)
  const [allowOnline, setAllowOnline] = React.useState(schedule.allowOnline)
  const [requireReason, setRequireReason] = React.useState(
    schedule.requireReason,
  )
  const [timezone, setTimezone] = React.useState(schedule.timezone)
  const [overrides, setOverrides] = React.useState<Override[]>(
    schedule.overrides,
  )
  const [newDate, setNewDate] = React.useState("")
  const [newNote, setNewNote] = React.useState("")

  // Every time the sheet opens, re-hydrate the draft from the latest
  // saved schedule so unsaved edits from a previous session are discarded.
  React.useEffect(() => {
    if (!open) return
    setWeek(schedule.week)
    setDuration(String(schedule.duration))
    setBuffer(String(schedule.buffer))
    setDailyCap(String(schedule.dailyCap))
    setMinNotice(schedule.minNotice)
    setWindowDays(String(schedule.windowDays))
    setAutoConfirm(schedule.autoConfirm)
    setAllowOnline(schedule.allowOnline)
    setRequireReason(schedule.requireReason)
    setTimezone(schedule.timezone)
    setOverrides(schedule.overrides)
  }, [open, schedule])

  const toggleDay = (day: DayKey) =>
    setWeek((w) => ({ ...w, [day]: { ...w[day], enabled: !w[day].enabled } }))

  const addSlot = (day: DayKey) =>
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

  const removeSlot = (day: DayKey, id: string) =>
    setWeek((w) => ({
      ...w,
      [day]: { ...w[day], slots: w[day].slots.filter((s) => s.id !== id) },
    }))

  const updateSlot = (
    day: DayKey,
    id: string,
    field: "from" | "to",
    value: string,
  ) =>
    setWeek((w) => ({
      ...w,
      [day]: {
        ...w[day],
        slots: w[day].slots.map((s) =>
          s.id === id ? { ...s, [field]: value } : s,
        ),
      },
    }))

  const copyWeekday = (source: DayKey) => {
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
    toast.success(`Đã áp lịch ${DAYS.find((d) => d.key === source)?.long} cho T2–T6`)
  }

  const addOverride = () => {
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
  }

  const removeOverride = (id: string) =>
    setOverrides((prev) => prev.filter((o) => o.id !== id))

  const reset = () => {
    setWeek(DEFAULT_SCHEDULE.week)
    setOverrides(DEFAULT_SCHEDULE.overrides)
    setDuration(String(DEFAULT_SCHEDULE.duration))
    setBuffer(String(DEFAULT_SCHEDULE.buffer))
    setDailyCap(String(DEFAULT_SCHEDULE.dailyCap))
    setMinNotice(DEFAULT_SCHEDULE.minNotice)
    setWindowDays(String(DEFAULT_SCHEDULE.windowDays))
    setAutoConfirm(DEFAULT_SCHEDULE.autoConfirm)
    setAllowOnline(DEFAULT_SCHEDULE.allowOnline)
    setRequireReason(DEFAULT_SCHEDULE.requireReason)
    setTimezone(DEFAULT_SCHEDULE.timezone)
    resetSchedule()
    toast.success("Đã khôi phục lịch mặc định")
  }

  const save = () => {
    setSchedule({
      week,
      overrides,
      duration: parseInt(duration, 10) || DEFAULT_SCHEDULE.duration,
      buffer: parseInt(buffer, 10) || 0,
      dailyCap: parseInt(dailyCap, 10) || DEFAULT_SCHEDULE.dailyCap,
      minNotice,
      windowDays: parseInt(windowDays, 10) || DEFAULT_SCHEDULE.windowDays,
      autoConfirm,
      allowOnline,
      requireReason,
      timezone,
    })
    toast.success("Đã lưu lịch chi tiết", {
      description: "Thay đổi đã áp dụng cho trang đặt lịch và card Giờ làm việc.",
    })
    setOpen(false)
  }

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
    const dur = (parseInt(duration, 10) || 0) + (parseInt(buffer, 10) || 0)
    if (!dur) return 0
    return Math.floor((Number(totalActiveHours) * 60) / dur)
  }, [totalActiveHours, duration, buffer])

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
        className="w-full gap-0 overflow-y-auto p-0 sm:max-w-2xl"
      >
        <SheetHeader className="sticky top-0 z-10 border-b border-border/60 bg-background/95 px-6 py-5 backdrop-blur">
          <div className="flex items-start justify-between gap-4">
            <div>
              <SheetTitle className="flex items-center gap-2 font-serif text-xl">
                <span className="grid size-8 place-items-center rounded-lg bg-primary/15 text-primary">
                  <CalendarDays className="size-4" />
                </span>
                Chỉnh sửa lịch chi tiết
              </SheetTitle>
              <SheetDescription className="mt-1">
                Tuỳ chỉnh khung giờ tiếp sinh viên, độ dài mỗi cuộc, ngày nghỉ
                và quy tắc đặt lịch công khai.
              </SheetDescription>
            </div>
            <div className="hidden items-center gap-2 sm:flex">
              <Badge variant="secondary" className="gap-1 rounded-full">
                <Clock className="size-3" />
                {totalActiveHours} giờ / tuần
              </Badge>
              <Badge variant="outline" className="gap-1 rounded-full">
                <Users className="size-3" />~{weeklyCapacity} cuộc
              </Badge>
            </div>
          </div>
        </SheetHeader>

        <div className="grid gap-8 px-6 py-6">
          {/* Weekly schedule */}
          <section className="grid gap-3">
            <div className="flex items-end justify-between gap-3">
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
                className="rounded-lg"
                onClick={() => copyWeekday("mon")}
              >
                <Copy className="size-4" />
                Copy T2 → T6
              </Button>
            </div>

            <div className="grid gap-2">
              {DAYS.map((d) => {
                const cfg = week[d.key]
                return (
                  <div
                    key={d.key}
                    className={cn(
                      "rounded-xl border p-3 transition-colors",
                      cfg.enabled
                        ? "border-border/70 bg-card"
                        : "border-border/40 bg-muted/30",
                    )}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div
                          className={cn(
                            "grid size-9 place-items-center rounded-lg text-sm font-semibold",
                            cfg.enabled
                              ? "bg-primary/15 text-primary"
                              : "bg-muted text-muted-foreground",
                          )}
                        >
                          {d.short}
                        </div>
                        <div>
                          <p className="text-sm font-medium">{d.long}</p>
                          <p className="text-xs text-muted-foreground">
                            {cfg.enabled
                              ? `${cfg.slots.length} khoảng giờ`
                              : "Nghỉ"}
                          </p>
                        </div>
                      </div>
                      <Switch
                        checked={cfg.enabled}
                        onCheckedChange={() => toggleDay(d.key)}
                      />
                    </div>

                    {cfg.enabled && (
                      <div className="mt-3 grid gap-2 pl-12">
                        {cfg.slots.map((slot) => (
                          <div
                            key={slot.id}
                            className="flex items-center gap-2"
                          >
                            <Input
                              type="time"
                              value={slot.from}
                              onChange={(e) =>
                                updateSlot(
                                  d.key,
                                  slot.id,
                                  "from",
                                  e.target.value,
                                )
                              }
                              className="h-9 w-28 rounded-lg"
                            />
                            <span className="text-xs text-muted-foreground">
                              đến
                            </span>
                            <Input
                              type="time"
                              value={slot.to}
                              onChange={(e) =>
                                updateSlot(d.key, slot.id, "to", e.target.value)
                              }
                              className="h-9 w-28 rounded-lg"
                            />
                            <Button
                              variant="ghost"
                              size="icon"
                              className="size-8 rounded-lg text-muted-foreground hover:text-destructive"
                              onClick={() => removeSlot(d.key, slot.id)}
                              aria-label="Xoá khoảng giờ"
                            >
                              <Trash2 className="size-4" />
                            </Button>
                          </div>
                        ))}
                        <Button
                          variant="ghost"
                          size="sm"
                          className="w-fit rounded-lg text-muted-foreground"
                          onClick={() => addSlot(d.key)}
                        >
                          <Plus className="size-4" />
                          Thêm khoảng giờ
                        </Button>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </section>

          <Separator />

          {/* Meeting parameters */}
          <section className="grid gap-4">
            <div>
              <h3 className="font-serif text-base font-medium">
                Thông số cuộc hẹn
              </h3>
              <p className="text-xs text-muted-foreground">
                Quyết định độ dài mỗi cuộc, thời gian nghỉ giữa các cuộc và
                giới hạn mỗi ngày.
              </p>
            </div>

            <div className="grid gap-2">
              <Label className="text-sm">Thời lượng mỗi cuộc (phút)</Label>
              <ToggleGroup
                type="single"
                value={duration}
                onValueChange={(v) => v && setDuration(v)}
                variant="outline"
                className="w-fit rounded-lg"
              >
                {["15", "30", "45", "60"].map((m) => (
                  <ToggleGroupItem
                    key={m}
                    value={m}
                    aria-label={`${m} phút`}
                    className="px-4"
                  >
                    {m}
                  </ToggleGroupItem>
                ))}
              </ToggleGroup>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="grid gap-1.5">
                <Label htmlFor="buffer" className="text-sm">
                  Nghỉ giữa hai cuộc
                </Label>
                <Select value={buffer} onValueChange={setBuffer}>
                  <SelectTrigger id="buffer" className="rounded-lg">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="0">Không nghỉ</SelectItem>
                    <SelectItem value="5">5 phút</SelectItem>
                    <SelectItem value="10">10 phút</SelectItem>
                    <SelectItem value="15">15 phút</SelectItem>
                    <SelectItem value="30">30 phút</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="cap" className="text-sm">
                  Số cuộc tối đa mỗi ngày
                </Label>
                <Input
                  id="cap"
                  type="number"
                  min={1}
                  max={20}
                  value={dailyCap}
                  onChange={(e) => setDailyCap(e.target.value)}
                  className="rounded-lg"
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="notice" className="text-sm">
                  Báo trước tối thiểu
                </Label>
                <Select value={minNotice} onValueChange={setMinNotice}>
                  <SelectTrigger id="notice" className="rounded-lg">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1h">1 giờ</SelectItem>
                    <SelectItem value="4h">4 giờ</SelectItem>
                    <SelectItem value="12h">12 giờ</SelectItem>
                    <SelectItem value="24h">24 giờ</SelectItem>
                    <SelectItem value="48h">48 giờ</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="window" className="text-sm">
                  Cửa sổ đặt lịch (ngày)
                </Label>
                <Input
                  id="window"
                  type="number"
                  min={1}
                  max={90}
                  value={windowDays}
                  onChange={(e) => setWindowDays(e.target.value)}
                  className="rounded-lg"
                />
                <p className="text-[11px] text-muted-foreground">
                  Sinh viên chỉ được đặt trước tối đa {windowDays} ngày kể từ
                  hôm nay.
                </p>
              </div>
            </div>

            <Separator />

            <div className="grid gap-3">
              {[
                {
                  key: "auto",
                  icon: Check,
                  label: "Tự động xác nhận đặt lịch",
                  detail:
                    "Khung giờ rảnh sẽ được xác nhận ngay mà không cần bạn duyệt thủ công.",
                  value: autoConfirm,
                  set: setAutoConfirm,
                },
                {
                  key: "online",
                  icon: Globe,
                  label: "Cho phép cuộc hẹn online",
                  detail:
                    "Link Google Meet / Teams được tạo tự động khi sinh viên chọn hình thức online.",
                  value: allowOnline,
                  set: setAllowOnline,
                },
                {
                  key: "reason",
                  icon: Info,
                  label: "Bắt buộc nhập lý do",
                  detail:
                    "Sinh viên phải nêu vấn đề cần trao đổi. Giúp bạn chuẩn bị trước cuộc gặp.",
                  value: requireReason,
                  set: setRequireReason,
                },
              ].map((item) => (
                <div
                  key={item.key}
                  className="flex items-start justify-between gap-4 rounded-xl border border-border/60 bg-muted/20 p-3"
                >
                  <div className="flex items-start gap-3">
                    <span className="mt-0.5 grid size-8 place-items-center rounded-lg bg-primary/10 text-primary">
                      <item.icon className="size-4" />
                    </span>
                    <div>
                      <p className="text-sm font-medium">{item.label}</p>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {item.detail}
                      </p>
                    </div>
                  </div>
                  <Switch
                    checked={item.value}
                    onCheckedChange={item.set}
                    className="mt-1"
                  />
                </div>
              ))}
            </div>
          </section>

          <Separator />

          {/* Overrides */}
          <section className="grid gap-3">
            <div>
              <h3 className="font-serif text-base font-medium">
                Ngoại lệ & ngày nghỉ
              </h3>
              <p className="text-xs text-muted-foreground">
                Thêm ngày nghỉ lễ, đi công tác, hoặc khung giờ đặc biệt cho
                ngày cụ thể.
              </p>
            </div>

            <div className="grid gap-2 rounded-xl border border-dashed border-border/60 p-3 sm:grid-cols-[140px_1fr_auto]">
              <Input
                type="text"
                placeholder="dd/mm/yyyy"
                value={newDate}
                onChange={(e) => setNewDate(e.target.value)}
                className="rounded-lg"
              />
              <Input
                type="text"
                placeholder="Lý do, ví dụ: Hội thảo tại Đà Nẵng"
                value={newNote}
                onChange={(e) => setNewNote(e.target.value)}
                className="rounded-lg"
              />
              <Button
                variant="secondary"
                className="rounded-lg"
                onClick={addOverride}
              >
                <Plus className="size-4" />
                Thêm
              </Button>
            </div>

            <div className="overflow-hidden rounded-xl border border-border/60">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/40 hover:bg-muted/40">
                    <TableHead className="w-32">Ngày</TableHead>
                    <TableHead>Ghi chú</TableHead>
                    <TableHead className="w-28">Loại</TableHead>
                    <TableHead className="w-12" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {overrides.length === 0 ? (
                    <TableRow>
                      <TableCell
                        colSpan={4}
                        className="py-6 text-center text-sm text-muted-foreground"
                      >
                        Chưa có ngoại lệ nào. Lịch chạy theo khung giờ tuần.
                      </TableCell>
                    </TableRow>
                  ) : (
                    overrides.map((o) => (
                      <TableRow key={o.id}>
                        <TableCell className="font-mono text-sm">
                          {o.date}
                        </TableCell>
                        <TableCell className="text-sm">{o.note}</TableCell>
                        <TableCell>
                          <Badge
                            variant={o.type === "off" ? "destructive" : "secondary"}
                            className="gap-1 rounded-full font-normal"
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
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-8 rounded-lg text-muted-foreground hover:text-destructive"
                            onClick={() => removeOverride(o.id)}
                            aria-label="Xoá ngoại lệ"
                          >
                            <Trash2 className="size-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </section>

          <Separator />

          {/* Timezone & link */}
          <section className="grid gap-4">
            <div>
              <h3 className="font-serif text-base font-medium">
                Múi giờ & liên kết công khai
              </h3>
              <p className="text-xs text-muted-foreground">
                Sinh viên thấy lịch đã được tự động quy đổi sang múi giờ của
                họ.
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="grid gap-1.5">
                <Label htmlFor="tz" className="text-sm">
                  Múi giờ
                </Label>
                <Select value={timezone} onValueChange={setTimezone}>
                  <SelectTrigger id="tz" className="rounded-lg">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Asia/Ho_Chi_Minh">
                      (GMT+7) Hồ Chí Minh
                    </SelectItem>
                    <SelectItem value="Asia/Bangkok">
                      (GMT+7) Bangkok
                    </SelectItem>
                    <SelectItem value="Asia/Singapore">
                      (GMT+8) Singapore
                    </SelectItem>
                    <SelectItem value="Asia/Tokyo">(GMT+9) Tokyo</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-1.5">
                <Label className="text-sm">Liên kết đặt lịch công khai</Label>
                <div className="flex items-center gap-2 rounded-lg border border-border/60 bg-muted/30 px-3 py-2">
                  <Link2 className="size-4 text-muted-foreground" />
                  <code className="flex-1 truncate text-xs">
                    nexusedu.app/booking/le-ha
                  </code>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-7 rounded-md"
                          onClick={() => {
                            navigator.clipboard?.writeText(
                              "https://nexusedu.app/booking/le-ha",
                            )
                            toast.success("Đã sao chép liên kết")
                          }}
                        >
                          <Copy className="size-3.5" />
                          <span className="sr-only">Copy</span>
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Sao chép liên kết</TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
                <p className="text-[11px] text-muted-foreground">
                  Tự động đính kèm vào email AI gửi sinh viên nguy cơ cao.
                </p>
              </div>
            </div>
          </section>
        </div>

        <SheetFooter className="sticky bottom-0 z-10 flex-row items-center justify-between gap-2 border-t border-border/60 bg-background/95 px-6 py-4 backdrop-blur">
          <Button
            variant="ghost"
            className="rounded-lg text-muted-foreground"
            onClick={reset}
          >
            Khôi phục mặc định
          </Button>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              className="rounded-lg"
              onClick={() => setOpen(false)}
            >
              Huỷ
            </Button>
            <Button className="rounded-lg" onClick={save}>
              <Check className="size-4" />
              Lưu lịch
            </Button>
          </div>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
