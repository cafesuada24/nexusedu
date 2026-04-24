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
  Filter,
  Search,
  Mail,
  Upload,
} from "lucide-react"
import { toast } from "sonner"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group"
import { Skeleton } from "@/components/ui/skeleton"
import { EmailEditorDialog } from "@/components/dashboard/email-editor-dialog"
import { useDataset } from "@/hooks/use-dataset"
import {
  describeProblem,
  problemLabels,
  type Problem,
  type StudentRow,
  type TestRow,
} from "@/lib/csv"

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
  // Chỉ lấy sinh viên nguy cơ cao để số email cần gửi khớp với số "Nguy cơ cao".
  return students
    .filter((s) => s.severity === "high")
    .sort((a, b) => {
      // Never-contacted first, then lowest average score.
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
      }
    })
}

export function AlertCenter() {
  const { dataset, isLoading } = useDataset()
  const [filter, setFilter] = React.useState<"all" | Problem>("all")
  const [query, setQuery] = React.useState("")
  const [alerts, setAlerts] = React.useState<Alert[]>([])
  const [editing, setEditing] = React.useState<Alert | null>(null)
  const [hasInitialized, setHasInitialized] = React.useState(false)

  // Rebuild alerts whenever the underlying dataset changes.
  // We compare by filename + upload time so edits in this session aren't
  // blown away on every re-render.
  const datasetStamp = dataset
    ? `${dataset.fileName}:${dataset.uploadedAt}:${dataset.totalStudents}`
    : null

  React.useEffect(() => {
    if (!dataset) {
      setAlerts([])
      setHasInitialized(false)
      return
    }
    setAlerts(buildAlerts(dataset.students))
    setHasInitialized(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetStamp])

  const filtered = alerts.filter((a) => {
    const matchesFilter = filter === "all" || a.problem === filter
    const q = query.trim().toLowerCase()
    const matchesQuery =
      !q ||
      a.name.toLowerCase().includes(q) ||
      a.mssv.toLowerCase().includes(q) ||
      a.email.toLowerCase().includes(q) ||
      a.summary.toLowerCase().includes(q)
    return matchesFilter && matchesQuery
  })

  const countFor = (p: Problem) => alerts.filter((a) => a.problem === p).length

  const send = (a: Alert) => {
    setAlerts((arr) => arr.filter((x) => x.id !== a.id))
    toast.success(`Đã gửi email tới ${a.name}`, {
      description: a.email
        ? `Gửi đến ${a.email} — sinh viên sẽ nhận lời nhắn trong giây lát.`
        : "Sinh viên sẽ nhận được lời nhắn ấm áp trong giây lát.",
    })
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

  if (isLoading || !hasInitialized) {
    return (
      <Card className="rounded-2xl border-border/60">
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-72" />
        </CardHeader>
        <CardContent className="grid gap-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-28 rounded-2xl" />
          ))}
        </CardContent>
      </Card>
    )
  }

  if (!dataset) {
    return (
      <Card className="rounded-2xl border-dashed border-border/60">
        <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
          <span className="grid size-12 place-items-center rounded-xl bg-primary/10 text-primary">
            <Upload className="size-5" />
          </span>
          <div>
            <p className="font-serif text-lg font-semibold">
              Chưa có dữ liệu để phân tích
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              Hãy nhập file CSV điểm sinh viên để AI soạn sẵn email cảnh báo.
            </p>
          </div>
          <Button asChild className="rounded-xl">
            <Link href="/dashboard/import">
              <Upload className="size-4" />
              Nhập CSV ngay
            </Link>
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <>
      <Card className="rounded-2xl border-border/60">
        <CardHeader className="gap-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <CardTitle className="font-serif text-xl">
                Danh sách cảnh báo
              </CardTitle>
              <CardDescription>
                Bản nháp email do AI soạn từ{" "}
                <span className="font-mono text-xs">{dataset.fileName}</span>{" "}
                — con người là người quyết định gửi.
              </CardDescription>
            </div>
            <div className="flex w-full flex-col gap-2 md:w-auto md:flex-row md:items-center">
              <InputGroup className="h-10 w-full rounded-xl md:w-72">
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
            </div>
          </div>

          <Tabs
            value={filter}
            onValueChange={(v) => setFilter(v as typeof filter)}
          >
            <TabsList className="h-10 rounded-xl">
              <TabsTrigger value="all" className="rounded-lg">
                <Filter className="size-3.5" />
                Tất cả ({alerts.length})
              </TabsTrigger>
              <TabsTrigger value="failed_final" className="rounded-lg">
                {problemLabels.failed_final} ({countFor("failed_final")})
              </TabsTrigger>
              <TabsTrigger value="failed_midterm" className="rounded-lg">
                {problemLabels.failed_midterm} ({countFor("failed_midterm")})
              </TabsTrigger>
              <TabsTrigger value="low_average" className="rounded-lg">
                {problemLabels.low_average} ({countFor("low_average")})
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </CardHeader>

        <CardContent className="grid gap-3">
          {filtered.length === 0 && (
            <div className="rounded-xl border border-dashed border-border p-10 text-center">
              <Mail className="mx-auto size-10 text-muted-foreground" />
              <p className="mt-3 font-serif text-lg font-semibold">
                {alerts.length === 0
                  ? "Không có sinh viên nào cần cảnh báo"
                  : "Không có cảnh báo phù hợp"}
              </p>
              <p className="text-sm text-muted-foreground">
                {alerts.length === 0
                  ? "Tất cả sinh viên trong file đều trong ngưỡng an toàn."
                  : "Thử thay đổi bộ lọc hoặc từ khoá tìm kiếm."}
              </p>
            </div>
          )}

          {filtered.map((a) => {
            const meta = problemMeta[a.problem]
            return (
              <article
                key={a.id}
                className="group rounded-2xl border border-border/60 bg-card p-4 transition-all hover:border-primary/30 hover:shadow-md md:p-5"
              >
                <div className="flex flex-col gap-4 md:flex-row md:items-start">
                  <div className="flex items-start gap-3 md:min-w-64">
                    <Avatar className="size-11">
                      <AvatarFallback className="bg-primary/10 text-primary font-semibold">
                        {getInitials(a.name)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="truncate font-semibold">{a.name}</p>
                        {a.severity === "high" && (
                          <Badge className="h-5 shrink-0 rounded-md bg-destructive/15 text-destructive hover:bg-destructive/15">
                            Nguy cơ cao
                          </Badge>
                        )}
                        {a.lastContactedAt === null && (
                          <Badge
                            variant="outline"
                            className="h-5 shrink-0 rounded-md border-primary/30 text-primary"
                          >
                            Chưa liên hệ
                          </Badge>
                        )}
                      </div>
                      <p className="truncate font-mono text-[11px] text-muted-foreground">
                        {a.email || `MSSV ${a.mssv}`}
                      </p>
                      <Badge
                        variant="outline"
                        className={`mt-2 rounded-md ring-1 ${meta.tone} border-transparent`}
                      >
                        <meta.icon className="size-3" />
                        {meta.label} · {a.summary}
                      </Badge>
                    </div>
                  </div>

                  <div className="flex-1 rounded-xl border border-border/60 bg-muted/40 p-3">
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      <Sparkles className="size-3.5 text-primary" />
                      Bản nháp AI · gợi ý nhẹ nhàng
                    </div>
                    <p className="mt-1.5 truncate text-sm font-medium">
                      {a.subject}
                    </p>
                    <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                      {a.body.split("\n\n")[1] ?? a.body}
                    </p>
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap items-center justify-end gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="rounded-lg text-destructive hover:bg-destructive/10 hover:text-destructive"
                    onClick={() => remove(a)}
                  >
                    <Trash2 className="size-4" />
                    Xoá
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="rounded-lg"
                    onClick={() => setEditing(a)}
                  >
                    <Pencil className="size-4" />
                    Chỉnh sửa
                  </Button>
                  <Button
                    size="sm"
                    className="rounded-lg"
                    onClick={() => send(a)}
                    disabled={!a.email}
                    title={!a.email ? "Sinh viên chưa có email trong CSV" : undefined}
                  >
                    <Send className="size-4" />
                    Gửi ngay
                  </Button>
                </div>
              </article>
            )
          })}
        </CardContent>
      </Card>

      <EmailEditorDialog
        alert={editing}
        onClose={() => setEditing(null)}
        onSave={saveEdit}
      />
    </>
  )
}
