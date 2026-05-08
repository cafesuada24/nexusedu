"use client"

import { useMemo, useState } from "react"
import {
  CheckCircle2,
  HandHeart,
  Loader2,
  Mail,
  Users,
  type LucideIcon,
} from "lucide-react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { useAdvisorsLeaderboard } from "@/hooks/use-advisors"
import { cn } from "@/lib/utils"

type TimeWindow = "weekly" | "monthly" | "semester" | "all_time"

const TIME_WINDOWS: { value: TimeWindow; label: string }[] = [
  { value: "weekly", label: "Tuần" },
  { value: "monthly", label: "Tháng" },
  { value: "semester", label: "Học kỳ" },
  { value: "all_time", label: "Tất cả" },
]

type ProcessedAdvisor = {
  advisor_id: string
  name: string
  total_points: number
  sent_count: number
  resolved_count: number
  rank: number
  initials: string
  rate: number
}

// ─── Stat card ────────────────────────────────────────────────────────────────

const STAT_TONE = {
  primary: {
    card: "stripe-primary border-primary/15 bg-gradient-to-br from-primary/18 via-primary/8 to-card",
    icon: "bg-primary/10 text-primary ring-1 ring-primary/15",
  },
  success: {
    card: "stripe-success border-success/15 bg-gradient-to-br from-success/18 via-success/8 to-card",
    icon: "bg-success/10 text-success ring-1 ring-success/15",
  },
} as const

function StatCard({
  icon: Icon,
  value,
  label,
  tone,
}: {
  icon: LucideIcon
  value: number | string | null
  label: string
  tone: keyof typeof STAT_TONE
}) {
  const t = STAT_TONE[tone]
  return (
    <Card className={cn("rounded-2xl transition-shadow hover:shadow-md", t.card)}>
      <CardContent className="flex items-center gap-3 p-4">
        <span className={cn("grid size-11 shrink-0 place-items-center rounded-xl", t.icon)}>
          <Icon className="size-5" />
        </span>
        <div className="min-w-0">
          <p className="font-serif text-2xl font-bold leading-none tabular-nums">
            {value === null ? (
              <Loader2 className="size-5 animate-spin opacity-50" />
            ) : (
              value
            )}
          </p>
          <p className="mt-1 truncate text-xs text-muted-foreground">{label}</p>
        </div>
      </CardContent>
    </Card>
  )
}

// ─── Advisor table ────────────────────────────────────────────────────────────

function AdvisorTable({
  rows,
  isLoading,
  error,
}: {
  rows: ProcessedAdvisor[]
  isLoading: boolean
  error: Error | null
}) {
  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-destructive">
        Không thể tải dữ liệu cố vấn.
      </div>
    )
  }

  if (!rows.length) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
        Chưa có dữ liệu hoạt động trong khoảng thời gian này.
      </div>
    )
  }

  return (
    <TooltipProvider delayDuration={150}>
      <ol className="divide-y divide-border">
        {rows.map((a) => (
          <li
            key={a.advisor_id}
            className="flex flex-col gap-3 py-3 first:pt-0 last:pb-0 md:flex-row md:items-center"
          >
            {/* Rank + avatar + name */}
            <div className="flex items-center gap-3 md:w-72">
              <span
                className="grid size-9 shrink-0 place-items-center rounded-xl bg-muted font-mono text-sm font-semibold text-muted-foreground ring-1 ring-border"
                aria-label={`Thứ hạng ${a.rank}`}
              >
                {a.rank}
              </span>
              <Avatar className="size-9">
                <AvatarFallback className="bg-primary/10 text-xs font-semibold text-primary">
                  {a.initials}
                </AvatarFallback>
              </Avatar>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">{a.name}</p>
                <p className="truncate text-xs text-muted-foreground">
                  {a.total_points} điểm
                </p>
              </div>
            </div>

            {/* Resolve rate progress */}
            <div className="flex-1">
              <div className="mb-1.5 flex items-center justify-between">
                <span
                  className="font-mono text-xs font-semibold text-success"
                  aria-label="Tỷ lệ giải quyết"
                >
                  {a.rate}%
                </span>
                <span className="text-[10px] font-medium uppercase text-muted-foreground">
                  resolved
                </span>
              </div>
              <Progress value={a.rate} className="h-1.5" />
            </div>

            {/* Sent + resolved badges */}
            <div className="flex gap-1.5 md:w-auto md:justify-end">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Badge
                    variant="outline"
                    className="gap-1 rounded-md font-mono text-[11px]"
                  >
                    <Mail className="size-3" />
                    {a.sent_count}
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>{a.sent_count} email đã gửi</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Badge
                    variant="secondary"
                    className="gap-1 rounded-md bg-success/15 font-mono text-[11px] text-success hover:bg-success/15"
                  >
                    <CheckCircle2 className="size-3" />
                    {a.resolved_count}
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>{a.resolved_count} đã xử lý</TooltipContent>
              </Tooltip>
            </div>
          </li>
        ))}
      </ol>
    </TooltipProvider>
  )
}

// ─── Main export ──────────────────────────────────────────────────────────────

export function AdvisorManagement() {
  const [timeWindow, setTimeWindow] = useState<TimeWindow>("all_time")
  const { data, isLoading, error } = useAdvisorsLeaderboard(timeWindow)

  const processed = useMemo<ProcessedAdvisor[]>(() => {
    if (!data?.items.length) return []
    return [...data.items]
      .sort((a, b) => b.total_points - a.total_points)
      .map((item, i) => ({
        ...item,
        rank: i + 1,
        initials: item.name
          .split(" ")
          .map((n) => n[0])
          .join("")
          .toUpperCase()
          .slice(0, 2),
        rate:
          item.sent_count > 0
            ? Math.min(Math.round((item.resolved_count / item.sent_count) * 100), 100)
            : 0,
      }))
  }, [data])

  const stats = useMemo(() => {
    const totalAdvisors = data?.metadata.total_count ?? 0
    const totalSent = processed.reduce((s, a) => s + a.sent_count, 0)
    const avgRate =
      processed.length
        ? Math.round(processed.reduce((s, a) => s + a.rate, 0) / processed.length)
        : 0
    return { totalAdvisors, totalSent, avgRate }
  }, [data, processed])

  return (
    <div className="flex flex-col gap-4">
      {/* Summary stats */}
      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard
          icon={Users}
          value={isLoading ? null : stats.totalAdvisors}
          label="Tổng cố vấn"
          tone="primary"
        />
        <StatCard
          icon={Mail}
          value={isLoading ? null : stats.totalSent}
          label="Email đã gửi"
          tone="primary"
        />
        <StatCard
          icon={CheckCircle2}
          value={isLoading ? null : `${stats.avgRate}%`}
          label="Tỉ lệ resolved TB"
          tone="success"
        />
      </div>

      {/* Leaderboard card */}
      <Card className="stripe-primary rounded-2xl border-primary/15 bg-gradient-to-br from-primary/8 via-primary/4 to-card">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
          <CardTitle className="flex items-center gap-2 font-serif text-lg">
            <span className="grid size-7 place-items-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/15">
              <HandHeart className="size-3.5" />
            </span>
            Hiệu suất cố vấn
          </CardTitle>

          <Tabs
            value={timeWindow}
            onValueChange={(v) => setTimeWindow(v as TimeWindow)}
          >
            <TabsList className="h-8">
              {TIME_WINDOWS.map(({ value, label }) => (
                <TabsTrigger
                  key={value}
                  value={value}
                  className="h-6 px-2.5 text-[11px]"
                >
                  {label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </CardHeader>

        <CardContent>
          <AdvisorTable rows={processed} isLoading={isLoading} error={error} />
        </CardContent>
      </Card>
    </div>
  )
}
