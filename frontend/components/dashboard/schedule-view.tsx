"use client"

import * as React from "react"
import {
  CalendarClock,
  Clock,
  Users,
  CalendarX,
  Link2,
  Copy,
  Globe,
  Check,
  Hourglass,
  type LucideIcon,
} from "lucide-react"
import { toast } from "sonner"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { ScheduleEditorSheet } from "@/components/dashboard/schedule-editor-sheet"
import { useScheduleQuery } from "@/hooks/use-schedule-query"
import { summarizeWeek, totalWeeklyHours, type DayKey } from "@/lib/schedule"
import { cn } from "@/lib/utils"

type StatTone = "primary" | "success" | "warning" | "muted"

const TONE_CLASSES: Record<StatTone, string> = {
  primary: "bg-primary/10 text-primary ring-1 ring-primary/15",
  success: "bg-success/10 text-success ring-1 ring-success/15",
  warning: "bg-warning/15 text-warning ring-1 ring-warning/20",
  muted: "bg-accent-indigo/10 text-accent-indigo ring-1 ring-accent-indigo/15",
}

const STAT_CARD_CLASSES: Record<StatTone, string> = {
  primary:
    "stripe-primary border-primary/15 bg-gradient-to-br from-primary/18 via-primary/8 to-card",
  success:
    "stripe-success border-success/15 bg-gradient-to-br from-success/18 via-success/8 to-card",
  warning:
    "stripe-warning border-warning/20 bg-gradient-to-br from-warning/22 via-warning/10 to-card",
  muted:
    "stripe-indigo border-accent-indigo/15 bg-gradient-to-br from-accent-indigo/22 via-accent-indigo/10 to-card",
}

export function ScheduleView() {
  const { schedule, setSchedule } = useScheduleQuery()

  const weekSummary = React.useMemo(
    () => summarizeWeek(schedule.week),
    [schedule.week],
  )

  const weeklyHours = React.useMemo(
    () => totalWeeklyHours(schedule.week),
    [schedule.week],
  )

  const weeklyCapacity = React.useMemo(() => {
    const step = schedule.duration + schedule.buffer
    if (!step) return 0
    return Math.floor((weeklyHours * 60) / step)
  }, [weeklyHours, schedule.duration, schedule.buffer])

  const upcomingOverrides = React.useMemo(
    () => schedule.overrides.slice(0, 4),
    [schedule.overrides],
  )

  const toggleGroup = (keys: DayKey[], enabled: boolean) => {
    setSchedule((prev) => {
      const next = { ...prev.week }
      keys.forEach((k) => {
        next[k] = { ...next[k], enabled }
      })
      return { ...prev, week: next }
    })
  }

  const stats: Array<{
    label: string
    value: string
    icon: LucideIcon
    tone: StatTone
  }> = [
    {
      label: "Giờ/tuần",
      value: weeklyHours.toFixed(1),
      icon: Clock,
      tone: "primary",
    },
    {
      label: "Sức chứa",
      value: `~${weeklyCapacity}`,
      icon: Users,
      tone: "success",
    },
    {
      label: "Phút/cuộc",
      value: `${schedule.duration}`,
      icon: CalendarClock,
      tone: "warning",
    },
    {
      label: "Báo trước",
      value: schedule.minNotice,
      icon: Hourglass,
      tone: "muted",
    },
  ]

  return (
    <TooltipProvider delayDuration={150}>
      <div className="grid gap-6">
        {/* Stats — large numbers + tinted icons */}
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((s) => (
            <Card
              key={s.label}
              className={cn(
                "rounded-2xl transition-shadow hover:shadow-md",
                STAT_CARD_CLASSES[s.tone],
              )}
            >
              <CardContent className="flex items-center gap-3 p-4">
                <div
                  className={cn(
                    "grid size-11 place-items-center rounded-xl",
                    TONE_CLASSES[s.tone],
                  )}
                >
                  <s.icon className="size-5" />
                </div>
                <div className="min-w-0">
                  <p className="font-serif text-xl font-bold leading-none tabular-nums">
                    {s.value}
                  </p>
                  <p className="mt-1 truncate text-xs text-muted-foreground">
                    {s.label}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Working hours summary */}
          <Card className="stripe-indigo rounded-2xl border-accent-indigo/15 bg-gradient-to-br from-accent-indigo/22 via-accent-indigo/10 to-card lg:col-span-2">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Clock className="size-4 text-primary" />
                Giờ làm việc
              </CardTitle>
              <ScheduleEditorSheet />
            </CardHeader>
            <CardContent className="grid gap-2 text-sm">
              {weekSummary.map((group) => (
                <div
                  key={group.keys.join("-")}
                  className="flex items-center justify-between rounded-xl border border-border/60 bg-muted/30 px-4 py-3"
                >
                  <div className="flex min-w-0 items-center gap-2.5">
                    <span
                      aria-hidden
                      className={cn(
                        "size-2 rounded-full transition-colors",
                        group.enabled ? "bg-success" : "bg-muted-foreground/30",
                      )}
                    />
                    <div className="min-w-0">
                      <p className="font-medium">{group.label}</p>
                      <p className="truncate font-mono text-[11px] text-muted-foreground">
                        {group.hours}
                      </p>
                    </div>
                  </div>
                  <Switch
                    checked={group.enabled}
                    onCheckedChange={(v) => toggleGroup(group.keys, v)}
                  />
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Overrides + booking link */}
          <div className="grid gap-6">
            <Card className="stripe-warning rounded-2xl border-warning/20 bg-gradient-to-br from-warning/22 via-warning/10 to-card">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <CalendarX className="size-4 text-warning" />
                  Ngoại lệ
                </CardTitle>
              </CardHeader>
              <CardContent className="grid gap-2">
                {upcomingOverrides.length === 0 ? (
                  <div className="grid place-items-center gap-1.5 rounded-lg border border-dashed border-border/60 px-3 py-5">
                    <span className="grid size-8 place-items-center rounded-lg bg-muted text-muted-foreground">
                      <CalendarX className="size-3.5" />
                    </span>
                  </div>
                ) : (
                  upcomingOverrides.map((o) => (
                    <div
                      key={o.id}
                      className="flex items-start gap-3 rounded-lg border border-border/60 bg-muted/30 px-3 py-2.5"
                    >
                      <div
                        className={cn(
                          "grid size-8 shrink-0 place-items-center rounded-lg ring-1",
                          o.type === "off"
                            ? "bg-destructive/10 text-destructive ring-destructive/20"
                            : "bg-warning/15 text-warning ring-warning/25",
                        )}
                      >
                        {o.type === "off" ? (
                          <CalendarX className="size-4" />
                        ) : (
                          <Clock className="size-4" />
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <p className="font-mono text-xs font-medium">
                            {o.date}
                          </p>
                          <Badge
                            variant={
                              o.type === "off" ? "destructive" : "secondary"
                            }
                            className="rounded-full px-1.5 py-0 text-[10px] font-normal"
                          >
                            {o.type === "off" ? "Nghỉ" : "Riêng"}
                          </Badge>
                        </div>
                        <p className="mt-0.5 truncate text-xs text-muted-foreground">
                          {o.note}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            {/* Booking link — icon-led indicator strip */}
            <Card className="stripe-primary rounded-2xl border-primary/15 bg-gradient-to-br from-primary/18 via-primary/8 to-card">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Link2 className="size-4 text-primary" />
                  Liên kết đặt lịch
                </CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3">
                <div className="flex items-center gap-2 rounded-lg border border-border/60 bg-muted/30 px-3 py-2">
                  <Globe className="size-4 shrink-0 text-muted-foreground" />
                  <code className="flex-1 truncate font-mono text-xs">
                    nexusedu.app/booking/le-ha
                  </code>
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
                          toast.success("Đã sao chép")
                        }}
                        aria-label="Sao chép liên kết"
                      >
                        <Copy className="size-3.5" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Sao chép</TooltipContent>
                  </Tooltip>
                </div>

                <Separator />

                {/* Status grid — icon-led, single line each */}
                <ul className="grid grid-cols-2 gap-2 text-xs">
                  <BookingStat
                    icon={Globe}
                    label="Múi giờ"
                    value={schedule.timezone.replace("Asia/", "")}
                  />
                  <BookingStat
                    icon={Check}
                    label="Tự xác nhận"
                    value={schedule.autoConfirm ? "Bật" : "Tắt"}
                    active={schedule.autoConfirm}
                  />
                  <BookingStat
                    icon={Users}
                    label="Online"
                    value={schedule.allowOnline ? "Có" : "Không"}
                    active={schedule.allowOnline}
                  />
                  <BookingStat
                    icon={CalendarClock}
                    label="Cửa sổ"
                    value={`${schedule.windowDays}d`}
                  />
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </TooltipProvider>
  )
}

function BookingStat({
  icon: Icon,
  label,
  value,
  active,
}: {
  icon: LucideIcon
  label: string
  value: string
  active?: boolean
}) {
  return (
    <li className="flex items-center gap-2 rounded-lg border border-border/60 bg-muted/30 px-2.5 py-1.5">
      <Icon
        className={cn(
          "size-3.5 shrink-0",
          active === undefined
            ? "text-muted-foreground"
            : active
              ? "text-success"
              : "text-muted-foreground/60",
        )}
      />
      <span className="truncate text-muted-foreground">{label}</span>
      <span className="ml-auto truncate font-mono text-[11px] font-medium">
        {value}
      </span>
    </li>
  )
}
