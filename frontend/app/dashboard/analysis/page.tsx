"use client"

import Link from "next/link"
import {
  Users,
  AlertTriangle,
  MailCheck,
  ArrowRight,
  Upload,
  FileSpreadsheet,
  RefreshCw,
  LineChart,
  GraduationCap,
  type LucideIcon,
} from "lucide-react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { RiskTrendChart } from "@/components/dashboard/risk-trend-chart"
import { RecentAlerts } from "@/components/dashboard/recent-alerts"
import { PendingEmails } from "@/components/dashboard/pending-emails"
import { OverviewEmptyState } from "@/components/dashboard/overview-empty-state"
import { useDataset, type Dataset } from "@/hooks/use-dataset"
import { cn } from "@/lib/utils"

type Stat = {
  label: string
  value: string
  hint: string
  icon: LucideIcon
  tone: "primary" | "destructive" | "warning" | "success"
}

function buildStats(d: Dataset): Stat[] {
  const highPct =
    d.totalStudents > 0 ? Math.round((d.highRisk / d.totalStudents) * 100) : 0

  return [
    {
      label: "Sinh viên",
      value: d.totalStudents.toLocaleString("vi-VN"),
      hint: `${d.totalTests.toLocaleString("vi-VN")} bài`,
      icon: Users,
      tone: "primary",
    },
    {
      label: "Nguy cơ cao",
      value: d.highRisk.toLocaleString("vi-VN"),
      hint: `${highPct}%`,
      icon: AlertTriangle,
      tone: "destructive",
    },
    {
      label: "Email chờ gửi",
      value: d.draftEmails.toLocaleString("vi-VN"),
      hint: "draft",
      icon: MailCheck,
      tone: "warning",
    },
    {
      label: "Điểm TB",
      value: d.averageScore.toFixed(1),
      hint: "/100",
      icon: GraduationCap,
      tone: "success",
    },
  ]
}

function formatTimeAgo(iso: string) {
  const diffMs = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diffMs / 60000)
  if (mins < 1) return "vừa xong"
  if (mins < 60) return `${mins}p`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h`
  const days = Math.floor(hours / 24)
  return `${days}d`
}

const toneClasses: Record<
  Stat["tone"],
  { tile: string; value: string; card: string; stripe: string }
> = {
  primary: {
    tile: "bg-primary/10 text-primary ring-1 ring-primary/15",
    value: "text-foreground",
    card: "border-primary/15 bg-gradient-to-br from-primary/20 via-primary/8 to-card",
    stripe: "stripe-primary",
  },
  destructive: {
    tile: "bg-destructive/10 text-destructive ring-1 ring-destructive/15",
    value: "text-destructive",
    card: "border-destructive/15 bg-gradient-to-br from-destructive/20 via-destructive/8 to-card",
    stripe: "stripe-destructive",
  },
  warning: {
    tile: "bg-warning/15 text-warning ring-1 ring-warning/20",
    value: "text-foreground",
    card: "border-warning/20 bg-gradient-to-br from-warning/22 via-warning/10 to-card",
    stripe: "stripe-warning",
  },
  success: {
    tile: "bg-success/10 text-success ring-1 ring-success/15",
    value: "text-success",
    card: "border-success/15 bg-gradient-to-br from-success/20 via-success/8 to-card",
    stripe: "stripe-success",
  },
}

export default function AnalysisPage() {
  const { dataset, isLoading } = useDataset()

  return (
    <TooltipProvider delayDuration={150}>
      <div className="flex w-full flex-1 flex-col gap-6">
        {/* Compact icon header */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-xl bg-accent-cyan/10 text-accent-cyan ring-1 ring-accent-cyan/20 shadow-sm shadow-accent-cyan/10">
              <LineChart className="size-5" />
            </div>
            <h1 className="font-serif text-2xl font-bold tracking-tight md:text-3xl">
              Phân tích
            </h1>
          </div>
          <div className="flex items-center gap-2">
            {dataset ? (
              <>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      asChild
                      variant="outline"
                      size="icon"
                      className="size-9 rounded-xl"
                    >
                      <Link href="/dashboard/import" aria-label="Tải CSV mới">
                        <Upload className="size-4" />
                      </Link>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Tải CSV mới</TooltipContent>
                </Tooltip>
                <Button asChild size="sm" className="rounded-xl">
                  <Link href="/dashboard/alerts">
                    Cảnh báo
                    <ArrowRight className="size-4" />
                  </Link>
                </Button>
              </>
            ) : (
              <Button asChild size="sm" className="rounded-xl">
                <Link href="/dashboard/import">
                  <Upload className="size-4" />
                  Nhập CSV
                </Link>
              </Button>
            )}
          </div>
        </div>

        {isLoading ? (
          <AnalysisSkeleton />
        ) : !dataset ? (
          <OverviewEmptyState />
        ) : (
          <>
            <div
              aria-hidden
              className="h-px w-full bg-gradient-to-r from-accent-cyan/40 via-primary/25 to-transparent"
            />

            {/* Dataset chip — minimal info */}
            <Card className="stripe-cyan rounded-2xl border-accent-cyan/25 bg-gradient-to-br from-accent-cyan/25 via-primary/12 to-card">
              <CardContent className="flex flex-wrap items-center gap-3 p-3">
                <span className="grid size-9 place-items-center rounded-xl bg-primary/15 text-primary">
                  <FileSpreadsheet className="size-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-mono text-xs font-medium">
                    {dataset.fileName}
                  </p>
                </div>
                <Badge variant="outline" className="rounded-md font-mono text-[10px]">
                  {dataset.totalStudents.toLocaleString("vi-VN")}
                </Badge>
                <Badge
                  variant="secondary"
                  className="rounded-md bg-muted font-mono text-[10px] text-muted-foreground hover:bg-muted"
                >
                  {formatTimeAgo(dataset.uploadedAt)}
                </Badge>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      asChild
                      variant="ghost"
                      size="icon"
                      className="size-8 rounded-lg"
                    >
                      <Link href="/dashboard/import" aria-label="Cập nhật">
                        <RefreshCw className="size-3.5" />
                      </Link>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Cập nhật</TooltipContent>
                </Tooltip>
              </CardContent>
            </Card>

            {/* KPI tiles — large numbers + tinted icons */}
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {buildStats(dataset).map((s) => {
                const tone = toneClasses[s.tone]
                return (
                  <Card
                    key={s.label}
                    className={cn(
                      "rounded-2xl transition-shadow hover:shadow-md",
                      tone.card,
                      tone.stripe,
                    )}
                  >
                    <CardContent className="flex items-center gap-3 p-4">
                      <span
                        className={cn(
                          "grid size-11 shrink-0 place-items-center rounded-xl",
                          tone.tile,
                        )}
                      >
                        <s.icon className="size-5" />
                      </span>
                      <div className="min-w-0">
                        <div
                          className={cn(
                            "font-serif text-2xl font-bold leading-none tabular-nums",
                            tone.value,
                          )}
                        >
                          {s.value}
                        </div>
                        <div className="mt-1 flex items-center gap-1.5 text-xs">
                          <span className="text-muted-foreground">
                            {s.label}
                          </span>
                          <span className="text-muted-foreground/70">·</span>
                          <span className="font-mono text-muted-foreground">
                            {s.hint}
                          </span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>

            <div className="grid gap-4 lg:grid-cols-3">
              <Card className="stripe-primary rounded-2xl border-primary/15 bg-gradient-to-br from-primary/15 via-primary/6 to-card lg:col-span-2">
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 font-serif text-lg">
                    <span className="grid size-7 place-items-center rounded-lg bg-primary/10 text-primary">
                      <LineChart className="size-3.5" />
                    </span>
                    Phân bố vấn đề
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <RiskTrendChart problemCounts={dataset.problemCounts} />
                </CardContent>
              </Card>

              <Card className="stripe-destructive rounded-2xl border-destructive/15 bg-gradient-to-br from-destructive/18 via-destructive/8 to-card">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="flex items-center gap-2 font-serif text-lg">
                    <span className="grid size-7 place-items-center rounded-lg bg-destructive/10 text-destructive">
                      <AlertTriangle className="size-3.5" />
                    </span>
                    Cảnh báo mới
                  </CardTitle>
                  <Button
                    asChild
                    variant="ghost"
                    size="icon"
                    className="size-8 rounded-lg"
                  >
                    <Link href="/dashboard/alerts" aria-label="Xem tất cả">
                      <ArrowRight className="size-4" />
                    </Link>
                  </Button>
                </CardHeader>
                <CardContent>
                  <RecentAlerts students={dataset.students} />
                </CardContent>
              </Card>
            </div>

            <Card className="stripe-warning rounded-2xl border-warning/20 bg-gradient-to-br from-warning/22 via-warning/10 to-card">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="flex items-center gap-2 font-serif text-lg">
                  <span className="grid size-7 place-items-center rounded-lg bg-warning/15 text-warning">
                    <MailCheck className="size-3.5" />
                  </span>
                  Email chờ gửi
                </CardTitle>
                <Badge
                  variant="secondary"
                  className="rounded-md bg-warning/15 text-warning hover:bg-warning/15"
                >
                  {dataset.draftEmails.toLocaleString("vi-VN")}
                </Badge>
              </CardHeader>
              <CardContent>
                <PendingEmails students={dataset.students} />
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </TooltipProvider>
  )
}

function AnalysisSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      <Skeleton className="h-14 rounded-2xl" />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-20 rounded-2xl" />
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Skeleton className="h-80 rounded-2xl lg:col-span-2" />
        <Skeleton className="h-80 rounded-2xl" />
      </div>
    </div>
  )
}
