"use client"

import * as React from "react"
import Link from "next/link"
import {
  GraduationCap,
  BookOpen,
  TrendingDown,
  Send,
  Pencil,
  Trash2,
  Sparkles,
  Search,
  Mail,
  Upload,
  MoreHorizontal,
  ArrowRight,
  CalendarCheck,
  Handshake,
  CheckCircle2,
  RotateCcw,
  Inbox,
  ChevronsDown,
  ChevronsUp,
  ChevronDown,
  Clock,
  Target,
} from "lucide-react"
import { toast } from "sonner"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group"
import { Skeleton } from "@/components/ui/skeleton"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { EmailEditorDialog } from "@/components/dashboard/email-editor-dialog"
import {
  GoalsDialog,
  type Goal,
} from "@/components/dashboard/goals-dialog"
import { useDataset } from "@/hooks/use-dataset"
import {
  describeProblem,
  problemLabels,
  type Problem,
  type StudentRow,
  type TestRow,
} from "@/lib/csv"
import {
  fetchAlerts,
  updateAlertStatus,
  type BackendInterventionStatus,
} from "@/lib/api"
import { cn } from "@/lib/utils"

type AlertStatus =
  | "new"
  | "contacted"
  | "scheduled"
  | "in_progress"
  | "resolved"

type Alert = {
  id: string
  name: string
  mssv: string
  email: string
  problem: Problem
  summary: string
  severity: "high" | "medium"
  subject: string
  body: string
  /** 0 = chưa từng liên hệ, >0 = đã liên hệ (Unix seconds). */
  lastContactedAt: number | null
  status: AlertStatus
  /** Khi thẻ chuyển cột gần nhất — dùng để hiển thị thời gian. */
  movedAt: number
  /** Thời gian cuộc hẹn (Unix seconds) — chỉ có khi đã đặt hẹn. */
  appointmentAt: number | null
  /** Danh sách mục tiêu can thiệp. */
  goals: Goal[]
}

const problemMeta: Record<
  Problem,
  { label: string; icon: React.ElementType; tone: string }
> = {
  failed_final: {
    label: problemLabels.failed_final,
    icon: GraduationCap,
    tone: "bg-destructive/10 text-destructive ring-destructive/20",
  },
  failed_midterm: {
    label: problemLabels.failed_midterm,
    icon: BookOpen,
    tone: "bg-warning/15 text-warning ring-warning/25",
  },
  low_average: {
    label: problemLabels.low_average,
    icon: TrendingDown,
    tone: "bg-primary/10 text-primary ring-primary/20",
  },
}

type ColumnDef = {
  id: AlertStatus
  title: string
  icon: React.ElementType
  /** Tailwind classes cho dot và viền nhẹ ở header column. */
  accent: string
  dotClass: string
}

const COLUMNS: ColumnDef[] = [
  {
    id: "new",
    title: "Mới",
    icon: Sparkles,
    accent: "text-destructive",
    dotClass: "bg-destructive",
  },
  {
    id: "contacted",
    title: "Đã liên hệ",
    icon: Send,
    accent: "text-primary",
    dotClass: "bg-primary",
  },
  {
    id: "scheduled",
    title: "Đã đặt hẹn",
    icon: CalendarCheck,
    accent: "text-warning",
    dotClass: "bg-warning",
  },
  {
    id: "in_progress",
    title: "Đang hỗ trợ",
    icon: Handshake,
    accent: "text-foreground",
    dotClass: "bg-muted-foreground",
  },
  {
    id: "resolved",
    title: "Đã giải quyết",
    icon: CheckCircle2,
    accent: "text-success",
    dotClass: "bg-success",
  },
]

function getInitials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .map((n) => n[0]?.toUpperCase() ?? "")
    .slice(-2)
    .join("")
}

function firstName(name: string) {
  const parts = name.trim().split(/\s+/)
  return parts[parts.length - 1] || name
}

function pickMainProblem(s: StudentRow): Problem {
  if (s.hasFailedFinal) return "failed_final"
  if (s.hasFailedMidterm) return "failed_midterm"
  return "low_average"
}

function summarizeStudent(s: StudentRow): string {
  return describeProblem(s)
}

function formatCourseList(tests: TestRow[]): string {
  const names = Array.from(
    new Set(tests.map((t) => t.courseName).filter(Boolean)),
  )
  if (names.length === 0) return "các môn kỳ này"
  if (names.length === 1) return `môn ${names[0]}`
  if (names.length === 2) return `hai môn ${names[0]} và ${names[1]}`
  return `các môn ${names.slice(0, -1).join(", ")} và ${names[names.length - 1]}`
}

function draftEmail(s: StudentRow): { subject: string; body: string } {
  const fn = firstName(s.name)
  const problem = pickMainProblem(s)
  const avg = s.averageScore.toFixed(1)
  const courses = formatCourseList(s.tests)

  if (problem === "failed_final") {
    const failed = s.tests.filter(
      (t) => t.testType === "final_semester" && t.score < 50,
    )
    const failedCourses =
      failed.length > 0
        ? Array.from(new Set(failed.map((t) => t.courseName).filter(Boolean)))
        : []
    const courseLine =
      failedCourses.length > 0
        ? `ở ${failedCourses.join(", ")}`
        : `ở ${courses}`
    return {
      subject: `NexusEdu · Cùng nhìn lại kỳ này nhé ${fn}`,
      body: `Chào ${fn},

Thầy xem kết quả kỳ vừa rồi và thấy em gặp khó khăn trong bài thi cuối kỳ ${courseLine}. Thầy hiểu đây là lúc khá áp lực, nên muốn dành cho em một khoảng để cùng nhìn lại — xem mình có thể điều chỉnh gì cho kỳ tới.

Em đặt một buổi 20 phút với thầy nhé, mình sẽ cùng xem lộ trình học và các phương án thi lại nếu cần.
→ nexusedu.app/booking/le-ha

Thầy tin ở em,
TS. Lê Hà`,
    }
  }

  if (problem === "failed_midterm") {
    const failed = s.tests.filter(
      (t) => t.testType === "middle_semester" && t.score < 50,
    )
    const failedCourses =
      failed.length > 0
        ? Array.from(new Set(failed.map((t) => t.courseName).filter(Boolean)))
        : []
    const courseLine =
      failedCourses.length > 0
        ? `ở ${failedCourses.join(", ")}`
        : `ở ${courses}`
    return {
      subject: `NexusEdu · Vẫn còn thời gian để xoay ${fn} ơi`,
      body: `Chào ${fn},

Cô thấy bài giữa kỳ ${courseLine} của em chưa được như kỳ vọng. Không sao cả — giữa kỳ chỉ là một cột mốc, và vẫn còn đủ thời gian để cải thiện trước bài cuối kỳ.

Mình hẹn nhau một buổi ngắn để cùng xem đề bài, phương pháp ôn tập và kết nối em với nhóm hỗ trợ của khoa nếu cần nhé.
→ nexusedu.app/booking/le-ha

Thân mến,
TS. Lê Hà`,
    }
  }

  return {
    subject: `NexusEdu · Một buổi trò chuyện ngắn với ${fn}?`,
    body: `Chào ${fn},

Thầy tổng hợp lại kết quả của em kỳ này — điểm trung bình hiện tại đang ở mức ${avg}/100 qua ${s.tests.length} bài kiểm tra ${courses}. Không phải là con số quá tệ, nhưng thầy nghĩ mình có thể làm tốt hơn nếu cùng nhau điều chỉnh sớm.

Em thử đặt một buổi 15 phút với thầy nhé, mình chỉ trò chuyện để hiểu em đang gặp gì thôi.
→ nexusedu.app/booking/le-ha

Thầy luôn ở đây,
TS. Lê Hà`,
  }
}

function buildAlerts(students: StudentRow[]): Alert[] {
  const now = Math.floor(Date.now() / 1000)
  return students
    .filter((s) => s.severity === "high")
    .sort((a, b) => {
      const ac = a.lastContactedAt ? 1 : 0
      const bc = b.lastContactedAt ? 1 : 0
      if (ac !== bc) return ac - bc
      return a.averageScore - b.averageScore
    })
    .map((s) => {
      const { subject, body } = draftEmail(s)
      return {
        id: s.id,
        name: s.name,
        mssv: s.id.slice(0, 8).toUpperCase(),
        email: s.email,
        problem: pickMainProblem(s),
        summary: summarizeStudent(s),
        severity: "high" as const,
        subject,
        body,
        lastContactedAt: s.lastContactedAt,
        status: "new" as const,
        movedAt: now,
        appointmentAt: null,
        goals: [],
      }
    })
}

function relativeTime(seconds: number): string {
  const diff = Math.floor(Date.now() / 1000) - seconds
  if (diff < 60) return "vừa xong"
  if (diff < 3600) return `${Math.floor(diff / 60)} phút trước`
  if (diff < 86400) return `${Math.floor(diff / 3600)} giờ trước`
  return `${Math.floor(diff / 86400)} ngày trước`
}

/** Bốc một mốc giờ hợp lý trong giờ làm việc 1–7 ngày tới. */
function pickRandomAppointment(): number {
  const now = Date.now()
  const dayOffset = 1 + Math.floor(Math.random() * 7) // 1..7 ngày
  const hour = 8 + Math.floor(Math.random() * 9) // 8..16
  const minute = Math.random() < 0.5 ? 0 : 30
  const d = new Date(now + dayOffset * 86400 * 1000)
  d.setHours(hour, minute, 0, 0)
  return Math.floor(d.getTime() / 1000)
}

const APPOINTMENT_FORMATTER = new Intl.DateTimeFormat("vi-VN", {
  weekday: "short",
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
})

function formatAppointment(seconds: number): string {
  return APPOINTMENT_FORMATTER.format(new Date(seconds * 1000))
}

/** Bỏ dòng chào, lấy đoạn nội dung đầu của email AI để preview. */
function getEmailPreview(body: string): string {
  const blocks = body.split(/\n\s*\n/).map((b) => b.trim()).filter(Boolean)
  // bỏ qua "Chào ..." nếu có
  const firstContent = blocks.find((b) => !/^chào\b/i.test(b)) ?? blocks[0]
  return (firstContent ?? body).replace(/\s+/g, " ")
}

/* --------------------------------------------------------------------- */
/*  Backend status sync                                                  */
/* --------------------------------------------------------------------- */

/**
 * Translate the local Kanban column to the backend `intervention_status`
 * enum. This is the value persisted by `PATCH /alerts/{sid}/status`.
 */
function toBackendStatus(s: AlertStatus): BackendInterventionStatus {
  switch (s) {
    case "new":
      return "new"
    case "contacted":
      return "sent"
    case "scheduled":
      return "booked"
    case "in_progress":
      return "supporting"
    case "resolved":
      return "resolved"
  }
}

/**
 * Translate the backend status returned by `GET /alerts` to the local
 * column id. `none` and `expired` both fold into "new" — the PD should
 * see them together at the top of the funnel for re-engagement.
 */
function fromBackendStatus(s: BackendInterventionStatus): AlertStatus {
  switch (s) {
    case "sent":
      return "contacted"
    case "booked":
      return "scheduled"
    case "supporting":
      return "in_progress"
    case "resolved":
      return "resolved"
    case "none":
    case "new":
    case "expired":
    default:
      return "new"
  }
}

const PAGE_SIZE = 5

export function AlertCenter() {
  const { dataset, isLoading } = useDataset()
  const [problemFilter, setProblemFilter] = React.useState<"all" | Problem>(
    "all",
  )
  const [query, setQuery] = React.useState("")
  const [alerts, setAlerts] = React.useState<Alert[]>([])
  const [editing, setEditing] = React.useState<Alert | null>(null)
  const [goalsTargetId, setGoalsTargetId] = React.useState<string | null>(null)
  const [hasInitialized, setHasInitialized] = React.useState(false)
  const [collapsedCols, setCollapsedCols] = React.useState<
    Record<AlertStatus, boolean>
  >({
    new: false,
    contacted: false,
    scheduled: false,
    in_progress: false,
    resolved: false,
  })

  const toggleCollapse = (id: AlertStatus) =>
    setCollapsedCols((prev) => ({ ...prev, [id]: !prev[id] }))

  const [expandedCols, setExpandedCols] = React.useState<
    Record<AlertStatus, boolean>
  >({
    new: false,
    contacted: false,
    scheduled: false,
    in_progress: false,
    resolved: false,
  })

  const toggleExpand = (id: AlertStatus) =>
    setExpandedCols((prev) => ({ ...prev, [id]: !prev[id] }))

  const datasetStamp = dataset
    ? `${dataset.fileName}:${dataset.uploadedAt}:${dataset.totalStudents}`
    : null

  React.useEffect(() => {
    if (!dataset) {
      setAlerts([])
      setHasInitialized(false)
      return
    }
    const initial = buildAlerts(dataset.students)
    setAlerts(initial)
    setHasInitialized(true)

    // Best-effort sync with the backend: pull authoritative statuses so the
    // PD sees the same Kanban that the API has stored. If the call fails we
    // silently keep the locally-derived board.
    let cancelled = false
    fetchAlerts()
      .then((remote) => {
        if (cancelled || remote.length === 0) return
        const byId = new Map(remote.map((r) => [r.sid, r]))
        setAlerts((arr) =>
          arr.map((a) => {
            const r = byId.get(a.id)
            if (!r) return a
            const mapped = fromBackendStatus(r.intervention_status)
            if (mapped === a.status) return a
            return {
              ...a,
              status: mapped,
              movedAt: Math.floor(Date.now() / 1000),
            }
          }),
        )
      })
      .catch((err) => {
        console.warn("[v0] /alerts sync skipped", err)
      })

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetStamp])

  const filteredAlerts = React.useMemo(() => {
    const q = query.trim().toLowerCase()
    return alerts.filter((a) => {
      const matchesProblem =
        problemFilter === "all" || a.problem === problemFilter
      const matchesQuery =
        !q ||
        a.name.toLowerCase().includes(q) ||
        a.mssv.toLowerCase().includes(q) ||
        a.email.toLowerCase().includes(q) ||
        a.summary.toLowerCase().includes(q)
      return matchesProblem && matchesQuery
    })
  }, [alerts, problemFilter, query])

  const grouped = React.useMemo(() => {
    const map: Record<AlertStatus, Alert[]> = {
      new: [],
      contacted: [],
      scheduled: [],
      in_progress: [],
      resolved: [],
    }
    for (const a of filteredAlerts) map[a.status].push(a)
    // Cột "Đã đặt hẹn": sắp xếp theo thời gian cuộc hẹn, sớm nhất lên trên.
    map.scheduled.sort((a, b) => {
      const ta = a.appointmentAt ?? Number.POSITIVE_INFINITY
      const tb = b.appointmentAt ?? Number.POSITIVE_INFINITY
      return ta - tb
    })
    return map
  }, [filteredAlerts])

  const totalCounts = React.useMemo(() => {
    const map: Record<AlertStatus, number> = {
      new: 0,
      contacted: 0,
      scheduled: 0,
      in_progress: 0,
      resolved: 0,
    }
    for (const a of alerts) map[a.status]++
    return map
  }, [alerts])

  const countForProblem = (p: Problem) =>
    alerts.filter((a) => a.problem === p).length

  const moveTo = (id: string, status: AlertStatus, message?: string) => {
    setAlerts((arr) =>
      arr.map((x) => {
        if (x.id !== id) return x
        // Khi vào cột "Đã đặt hẹn" mà chưa có giờ hẹn → tạo lịch giả lập.
        const appointmentAt =
          status === "scheduled" && !x.appointmentAt
            ? pickRandomAppointment()
            : x.appointmentAt
        return {
          ...x,
          status,
          movedAt: Math.floor(Date.now() / 1000),
          appointmentAt,
        }
      }),
    )
    if (message) toast.success(message)

    // Persist the transition to the backend. Failures are surfaced inline so
    // the PD knows the local move did not propagate, but we don't roll back
    // the UI — they can retry by moving the card again.
    updateAlertStatus(id, toBackendStatus(status)).catch((err) => {
      console.warn("[v0] PATCH /alerts/status failed", err)
      toast.error("Chưa lưu được trạng thái lên máy chủ", {
        description: "Thay đổi vẫn hiển thị tại đây — thử lại sau.",
      })
    })
  }

  const send = (a: Alert) => {
    moveTo(
      a.id,
      "contacted",
      `Đã gửi email tới ${a.name}`,
    )
    toast.message(
      a.email
        ? `Gửi đến ${a.email}`
        : "Sinh viên sẽ nhận lời nhắn trong giây lát.",
    )
  }

  const remove = (a: Alert) => {
    setAlerts((arr) => arr.filter((x) => x.id !== a.id))
    toast.message(`Đã xoá cảnh báo của ${a.name}`)
  }

  const saveEdit = (updated: Alert) => {
    setAlerts((arr) => arr.map((x) => (x.id === updated.id ? updated : x)))
    setEditing(null)
    toast.success("Đã lưu chỉnh sửa email")
  }

  const addGoal = (
    alertId: string,
    title: string,
    deadline: string | null,
  ) => {
    const newGoal: Goal = {
      id: `g_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`,
      title,
      deadline,
      done: false,
      createdAt: Math.floor(Date.now() / 1000),
    }
    setAlerts((arr) =>
      arr.map((x) =>
        x.id === alertId ? { ...x, goals: [...x.goals, newGoal] } : x,
      ),
    )
    toast.success("Đã thêm mục tiêu mới")
  }

  const toggleGoal = (alertId: string, goalId: string) => {
    setAlerts((arr) =>
      arr.map((x) =>
        x.id === alertId
          ? {
              ...x,
              goals: x.goals.map((g) =>
                g.id === goalId ? { ...g, done: !g.done } : g,
              ),
            }
          : x,
      ),
    )
  }

  const removeGoal = (alertId: string, goalId: string) => {
    setAlerts((arr) =>
      arr.map((x) =>
        x.id === alertId
          ? { ...x, goals: x.goals.filter((g) => g.id !== goalId) }
          : x,
      ),
    )
  }

  const goalsTarget = React.useMemo(
    () => (goalsTargetId ? alerts.find((a) => a.id === goalsTargetId) : null),
    [alerts, goalsTargetId],
  )

  if (isLoading || !hasInitialized) {
    return (
      <Card className="rounded-2xl border-border/60">
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-72" />
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          {[0, 1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-72 rounded-2xl" />
          ))}
        </CardContent>
      </Card>
    )
  }

  if (!dataset) {
    return (
      <Card className="rounded-2xl border-dashed border-border/60">
        <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
          <span className="grid size-12 place-items-center rounded-xl bg-primary/10 text-primary">
            <Inbox className="size-5" />
          </span>
          <Button asChild size="sm" className="rounded-xl">
            <Link href="/dashboard/import">
              <Upload className="size-4" />
              Nhập CSV
            </Link>
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <>
      <div className="flex flex-col gap-3">
        {/* Compact toolbar — sits as a single thin row above the Kanban so
            the columns get more vertical space. The filename / total count
            chips that used to live here are redundant: the page header
            already shows the live "Nguy cơ cao / Email cần gửi" metrics
            from the Analysis dataset, and the per-status counts are in
            each column header. */}
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <InputGroup className="h-9 w-full rounded-lg sm:w-64">
            <InputGroupAddon>
              <Search className="size-4 text-muted-foreground" />
            </InputGroupAddon>
            <InputGroupInput
              placeholder="Tìm theo tên, MSSV, email..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Tìm cảnh báo"
            />
          </InputGroup>
          <Tabs
            value={problemFilter}
            onValueChange={(v) =>
              setProblemFilter(v as typeof problemFilter)
            }
          >
            <TabsList className="h-9 w-full rounded-lg sm:w-auto">
              <TabsTrigger
                value="all"
                className="rounded-md px-2.5 text-xs sm:text-sm"
              >
                Tất cả{" "}
                <span className="ml-1 font-mono text-muted-foreground">
                  {alerts.length}
                </span>
              </TabsTrigger>
              <TabsTrigger
                value="failed_final"
                className="rounded-md px-2.5 text-xs sm:text-sm"
                title={problemLabels.failed_final}
              >
                Cuối kỳ{" "}
                <span className="ml-1 font-mono text-muted-foreground">
                  {countForProblem("failed_final")}
                </span>
              </TabsTrigger>
              <TabsTrigger
                value="failed_midterm"
                className="rounded-md px-2.5 text-xs sm:text-sm"
                title={problemLabels.failed_midterm}
              >
                Giữa kỳ{" "}
                <span className="ml-1 font-mono text-muted-foreground">
                  {countForProblem("failed_midterm")}
                </span>
              </TabsTrigger>
              <TabsTrigger
                value="low_average"
                className="rounded-md px-2.5 text-xs sm:text-sm"
                title={problemLabels.low_average}
              >
                TB thấp{" "}
                <span className="ml-1 font-mono text-muted-foreground">
                  {countForProblem("low_average")}
                </span>
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        {/* Kanban */}
        <div
          className="grid gap-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5"
          role="list"
        >
          {COLUMNS.map((col) => {
            const items = grouped[col.id]
            const totalInColumn = totalCounts[col.id]
            const ColIcon = col.icon
            const isCollapsed = collapsedCols[col.id]

            return (
              <section
                key={col.id}
                role="listitem"
                className={cn(
                  "flex min-w-0 flex-col rounded-2xl border border-border/60 bg-muted/30 transition-colors",
                  isCollapsed && "bg-muted/20",
                )}
                aria-label={col.title}
              >
                <header className="flex items-center justify-between gap-2 border-b border-border/60 px-3 py-3">
                  <div className="flex min-w-0 items-center gap-2.5">
                    <span
                      className={cn(
                        "grid size-9 shrink-0 place-items-center rounded-lg bg-card ring-1 ring-border/60",
                        col.accent,
                      )}
                      aria-hidden
                    >
                      <ColIcon className="size-[18px]" />
                    </span>
                    <p className="truncate text-base font-semibold">
                      {col.title}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1.5">
                    <Badge
                      variant="outline"
                      className="h-7 rounded-md bg-card px-2 font-mono text-sm"
                    >
                      {items.length}
                      {items.length !== totalInColumn ? (
                        <span className="ml-0.5 text-muted-foreground">
                          /{totalInColumn}
                        </span>
                      ) : null}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-7 rounded-md text-muted-foreground hover:text-foreground"
                      onClick={() => toggleCollapse(col.id)}
                      aria-label={
                        isCollapsed
                          ? `Mở rộng cột ${col.title}`
                          : `Thu gọn cột ${col.title}`
                      }
                      aria-expanded={!isCollapsed}
                    >
                      <ChevronDown
                        className={cn(
                          "size-4 transition-transform",
                          isCollapsed && "-rotate-90",
                        )}
                      />
                    </Button>
                  </div>
                </header>

                {isCollapsed ? null : (
                  <div className="flex min-h-[140px] flex-col gap-2.5 p-2.5">
                    {items.length === 0 ? (
                      <div className="flex flex-1 items-center justify-center rounded-xl border border-dashed border-border/60 bg-card/40 p-6 text-center">
                        <span
                          aria-hidden
                          className={cn(
                            "grid size-8 place-items-center rounded-lg bg-card opacity-60 ring-1 ring-border/60",
                            col.accent,
                          )}
                        >
                          <ColIcon className="size-4" />
                        </span>
                      </div>
                    ) : (
                      <>
                        {(expandedCols[col.id]
                          ? items
                          : items.slice(0, PAGE_SIZE)
                        ).map((a) => (
                          <KanbanCard
                            key={a.id}
                            alert={a}
                            onSend={() => send(a)}
                            onEdit={() => setEditing(a)}
                            onRemove={() => remove(a)}
                            onMove={(s, msg) => moveTo(a.id, s, msg)}
                            onOpenGoals={() => setGoalsTargetId(a.id)}
                          />
                        ))}
                        {items.length > PAGE_SIZE ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => toggleExpand(col.id)}
                            className="mt-1 h-10 w-full justify-center gap-2 rounded-lg text-sm font-medium text-muted-foreground hover:bg-card hover:text-foreground"
                            aria-expanded={expandedCols[col.id]}
                          >
                            {expandedCols[col.id] ? (
                              <>
                                <ChevronsUp className="size-4" />
                                Thu gọn
                              </>
                            ) : (
                              <>
                                <ChevronsDown className="size-4" />
                                Xem thêm {items.length - PAGE_SIZE} thẻ
                              </>
                            )}
                          </Button>
                        ) : null}
                      </>
                    )}
                  </div>
                )}
              </section>
            )
          })}
        </div>

        {alerts.length === 0 && (
          <Card className="rounded-2xl border-dashed border-border/60">
            <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
              <Inbox className="size-10 text-muted-foreground" />
              <p className="font-serif text-lg font-semibold">
                Không có cảnh báo
              </p>
            </CardContent>
          </Card>
        )}

        {alerts.length > 0 && filteredAlerts.length === 0 && (
          <Card className="rounded-2xl border-dashed border-border/60">
            <CardContent className="flex flex-col items-center gap-2 py-8 text-center">
              <Mail className="size-8 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                Không có kết quả phù hợp.
              </p>
            </CardContent>
          </Card>
        )}
      </div>

      <EmailEditorDialog
        alert={editing}
        onClose={() => setEditing(null)}
        onSave={saveEdit}
      />

      <GoalsDialog
        alert={
          goalsTarget
            ? {
                id: goalsTarget.id,
                name: goalsTarget.name,
                problem: goalsTarget.problem,
                problemLabel: problemMeta[goalsTarget.problem].label,
                problemTone: problemMeta[goalsTarget.problem].tone,
                problemIcon: problemMeta[goalsTarget.problem].icon,
                goals: goalsTarget.goals,
              }
            : null
        }
        onClose={() => setGoalsTargetId(null)}
        onAdd={addGoal}
        onToggle={toggleGoal}
        onRemove={removeGoal}
      />
    </>
  )
}

/* ----------------------------------------------------------------------- */
/*  Kanban card                                                            */
/* ----------------------------------------------------------------------- */

type KanbanCardProps = {
  alert: Alert
  onSend: () => void
  onEdit: () => void
  onRemove: () => void
  onMove: (status: AlertStatus, message?: string) => void
  onOpenGoals: () => void
}

function KanbanCard({
  alert: a,
  onSend,
  onEdit,
  onRemove,
  onMove,
  onOpenGoals,
}: KanbanCardProps) {
  const meta = problemMeta[a.problem]
  const ProblemIcon = meta.icon
  const goalsTotal = a.goals.length
  const goalsDone = a.goals.filter((g) => g.done).length
  const goalsPct =
    goalsTotal === 0 ? 0 : Math.round((goalsDone / goalsTotal) * 100)
  const hasOverdue = a.goals.some(
    (g) =>
      !g.done &&
      g.deadline !== null &&
      new Date(g.deadline).getTime() < new Date().setHours(0, 0, 0, 0),
  )

  return (
    <article className="group rounded-xl border border-border/60 bg-card p-4 shadow-sm transition-all hover:border-primary/30 hover:shadow-md">
      <div className="flex items-start gap-3">
        <Avatar className="size-12 shrink-0">
          <AvatarFallback className="bg-primary/10 text-primary text-sm font-semibold">
            {getInitials(a.name)}
          </AvatarFallback>
        </Avatar>
        <div className="min-w-0 flex-1">
          <p className="truncate text-base font-semibold leading-tight">
            {a.name}
          </p>
          <p className="mt-0.5 truncate font-mono text-xs text-muted-foreground">
            {a.email || `MSSV ${a.mssv}`}
          </p>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="size-9 shrink-0 rounded-lg text-muted-foreground hover:text-foreground"
              aria-label="Tuỳ chọn thẻ"
            >
              <MoreHorizontal className="size-5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-52 rounded-xl">
            <DropdownMenuLabel className="text-xs text-muted-foreground">
              Chuyển trạng thái
            </DropdownMenuLabel>
            {COLUMNS.filter((c) => c.id !== a.status).map((c) => {
              const Icon = c.icon
              return (
                <DropdownMenuItem
                  key={c.id}
                  onClick={() =>
                    onMove(c.id, `Đã chuyển ${a.name} → ${c.title}`)
                  }
                  className="gap-2"
                >
                  <Icon className={cn("size-4", c.accent)} />
                  {c.title}
                </DropdownMenuItem>
              )
            })}
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onOpenGoals} className="gap-2">
              <Target className="size-4 text-primary" />
              {goalsTotal > 0 ? (
                <span>
                  Mục tiêu{" "}
                  <span className="font-mono text-muted-foreground">
                    ({goalsDone}/{goalsTotal})
                  </span>
                </span>
              ) : (
                "Đặt mục tiêu"
              )}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={onEdit} className="gap-2">
              <Pencil className="size-4" />
              Chỉnh sửa email
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={onRemove}
              className="gap-2 text-destructive focus:text-destructive"
            >
              <Trash2 className="size-4" />
              Xoá thẻ
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <Badge
        variant="outline"
        className={cn(
          "mt-3 max-w-full gap-1.5 rounded-md border-transparent px-2 py-1 text-[13px] ring-1",
          meta.tone,
        )}
      >
        <ProblemIcon className="size-3.5" />
        <span className="truncate">{a.summary}</span>
      </Badge>

      {goalsTotal > 0 ? (
        <button
          type="button"
          onClick={onOpenGoals}
          className="mt-3 flex w-full items-center gap-2.5 rounded-lg border border-border/60 bg-muted/40 px-2.5 py-2 text-left transition-colors hover:border-primary/30 hover:bg-primary/5"
          aria-label={`Xem ${goalsTotal} mục tiêu của ${a.name}`}
        >
          <Target
            className={cn(
              "size-4 shrink-0",
              hasOverdue ? "text-destructive" : "text-primary",
            )}
          />
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between text-xs font-medium">
              <span className="text-foreground">
                Mục tiêu{" "}
                <span className="font-mono text-muted-foreground">
                  {goalsDone}/{goalsTotal}
                </span>
              </span>
              <span
                className={cn(
                  "font-mono",
                  hasOverdue ? "text-destructive" : "text-muted-foreground",
                )}
              >
                {hasOverdue ? "Quá hạn" : `${goalsPct}%`}
              </span>
            </div>
            <div
              className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-border/60"
              role="progressbar"
              aria-valuenow={goalsPct}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div
                className={cn(
                  "h-full rounded-full transition-[width] duration-300",
                  hasOverdue ? "bg-destructive" : "bg-success",
                )}
                style={{ width: `${goalsPct}%` }}
              />
            </div>
          </div>
        </button>
      ) : null}

      {a.status === "new" ? (
        <div className="mt-3 flex flex-col gap-2">
          <Badge
            variant="outline"
            className="w-fit gap-1.5 rounded-md border-transparent bg-primary/10 px-2 py-1 text-xs font-medium text-primary ring-1 ring-primary/20"
          >
            <Sparkles className="size-3.5" />
            Bản nháp AI sẵn sàng
          </Badge>
          <p className="line-clamp-2 text-[13px] leading-snug text-muted-foreground">
            {getEmailPreview(a.body)}
          </p>
        </div>
      ) : a.status === "scheduled" && a.appointmentAt ? (
        <p className="mt-3 flex items-center gap-1.5 text-[13px] font-medium text-warning">
          <Clock className="size-3.5" />
          Hẹn {formatAppointment(a.appointmentAt)}
        </p>
      ) : (
        <p className="mt-3 text-[13px] text-muted-foreground">
          Cập nhật {relativeTime(a.movedAt)}
        </p>
      )}

      <CardActions
        alert={a}
        onSend={onSend}
        onEdit={onEdit}
        onMove={onMove}
        onOpenGoals={onOpenGoals}
      />
    </article>
  )
}

function CardActions({
  alert: a,
  onSend,
  onEdit,
  onMove,
  onOpenGoals,
}: {
  alert: Alert
  onSend: () => void
  onEdit: () => void
  onMove: (status: AlertStatus, message?: string) => void
  onOpenGoals: () => void
}) {
  const hasGoals = a.goals.length > 0
  if (a.status === "new") {
    return (
      <div className="mt-3 flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="h-10 flex-1 rounded-lg text-sm font-medium"
          onClick={onEdit}
        >
          <Pencil className="size-4" />
          Sửa
        </Button>
        <Button
          size="sm"
          className="h-10 flex-1 rounded-lg text-sm font-medium"
          onClick={onSend}
          disabled={!a.email}
          title={!a.email ? "Sinh viên chưa có email trong CSV" : undefined}
        >
          <Send className="size-4" />
          Gửi ngay
        </Button>
      </div>
    )
  }

  if (a.status === "contacted") {
    return (
      <div className="mt-3 flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="h-10 flex-1 rounded-lg text-sm font-medium"
          onClick={() =>
            onMove("scheduled", `${a.name} đã chọn khung giờ họp`)
          }
        >
          <CalendarCheck className="size-4" />
          Đã đặt hẹn
        </Button>
        <Button
          size="sm"
          variant="ghost"
          className="h-10 w-10 shrink-0 rounded-lg"
          onClick={() =>
            onMove("in_progress", `Bắt đầu hỗ trợ ${a.name}`)
          }
          aria-label="Chuyển sang Đang hỗ trợ"
        >
          <ArrowRight className="size-4" />
        </Button>
      </div>
    )
  }

  if (a.status === "scheduled") {
    return (
      <div className="mt-3 flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="h-10 w-10 shrink-0 rounded-lg"
          onClick={onOpenGoals}
          aria-label={hasGoals ? "Xem mục tiêu" : "Đặt mục tiêu"}
          title={hasGoals ? "Xem mục tiêu" : "Đặt mục tiêu"}
        >
          <Target className="size-4" />
        </Button>
        <Button
          size="sm"
          className="h-10 flex-1 rounded-lg text-sm font-medium"
          onClick={() => onMove("in_progress", `Bắt đầu hỗ trợ ${a.name}`)}
        >
          <Handshake className="size-4" />
          Bắt đầu hỗ trợ
        </Button>
      </div>
    )
  }

  if (a.status === "in_progress") {
    return (
      <div className="mt-3 flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="h-10 flex-1 rounded-lg text-sm font-medium"
          onClick={onOpenGoals}
        >
          <Target className="size-4" />
          {hasGoals ? "Mục tiêu" : "Đặt mục tiêu"}
        </Button>
        <Button
          size="sm"
          className="h-10 flex-1 rounded-lg text-sm font-medium"
          onClick={() => onMove("resolved", `Đã đóng case của ${a.name}`)}
        >
          <CheckCircle2 className="size-4" />
          Giải quyết
        </Button>
      </div>
    )
  }

  // resolved
  return (
    <Button
      variant="outline"
      size="sm"
      className="mt-3 h-10 w-full rounded-lg text-sm font-medium"
      onClick={() => onMove("in_progress", `Mở lại case của ${a.name}`)}
    >
      <RotateCcw className="size-4" />
      Mở lại case
    </Button>
  )
}
