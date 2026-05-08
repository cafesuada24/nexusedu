"use client"

import {
  ArrowUpRight,
  CheckCircle2,
  Clock,
  GraduationCap,
  Heart,
  Mail,
  MessageSquare,
  Quote,
  Timer,
  TrendingUp,
  type LucideIcon,
} from "lucide-react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

const STUDENTS_HELPED = 47
const PERIOD_TOTAL = 50

type MiniStat = {
  icon: LucideIcon
  value: string
  label: string
  tone: "success" | "primary"
}

const MINI_STATS: MiniStat[] = [
  { icon: Timer, value: "12h", label: "Tiết kiệm", tone: "primary" },
  { icon: Mail, value: "89%", label: "Phản hồi <24h", tone: "success" },
  { icon: CheckCircle2, value: "23", label: "Đã đóng", tone: "success" },
]

export function ImpactHero() {
  const progress = Math.min(
    100,
    Math.round((STUDENTS_HELPED / PERIOD_TOTAL) * 100),
  )

  return (
    <Card className="relative overflow-hidden rounded-2xl border-success/25 bg-white ring-1 ring-success/10 dark:bg-slate-900/40">
      <CardContent className="grid gap-4 p-5 lg:grid-cols-[1.1fr_1fr]">
        {/* Big number with progress */}
        <div className="flex flex-col gap-3 rounded-2xl border border-border/60 bg-card p-5">
          <div className="flex items-center justify-between gap-2">
            <span className="inline-flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              <Heart className="size-3.5 text-success" />
              Tác động kỳ này
            </span>
          </div>

          <div className="flex items-baseline gap-2">
            <span className="font-serif text-6xl font-bold tabular-nums text-success">
              {STUDENTS_HELPED}
            </span>
            <span className="text-sm text-muted-foreground">
              / {PERIOD_TOTAL} SV
            </span>
          </div>

          <div>
            <div
              role="progressbar"
              aria-valuenow={progress}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Tiến độ học kỳ"
              className="h-2 w-full overflow-hidden rounded-full bg-success/10"
            >
              <div
                className="h-full rounded-full bg-success transition-[width] duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="mt-1.5 flex items-center justify-between text-[11px] font-medium">
              <span className="font-mono text-success">{progress}%</span>
              <span className="text-muted-foreground">
                {STUDENTS_HELPED}/{PERIOD_TOTAL}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2 rounded-xl border border-success/20 bg-success/5 px-3 py-2 text-sm">
            <Clock className="size-4 shrink-0 text-success" aria-hidden />
            <span>
              <span className="font-semibold">Trung bình</span>
              <span className="text-muted-foreground"> · phản hồi &lt;24h</span>
            </span>
          </div>
        </div>

        {/* Mini stats — icons + numbers only */}
        <ul role="list" className="grid grid-cols-3 gap-2 lg:grid-cols-1">
          {MINI_STATS.map((s) => {
            const Icon = s.icon
            const tint =
              s.tone === "success"
                ? "bg-success/10 text-success"
                : "bg-primary/10 text-primary"
            const valueTone =
              s.tone === "success" ? "text-success" : "text-primary"
            return (
              <li
                key={s.label}
                className="flex items-center gap-3 rounded-xl border border-border/60 bg-card/60 p-3"
              >
                <span
                  className={cn(
                    "grid size-9 shrink-0 place-items-center rounded-lg",
                    tint,
                  )}
                  aria-hidden
                >
                  <Icon className="size-4" />
                </span>
                <div className="min-w-0">
                  <div
                    className={cn(
                      "font-serif text-xl font-bold leading-none tabular-nums",
                      valueTone,
                    )}
                  >
                    {s.value}
                  </div>
                  <p className="mt-1 truncate text-[11px] text-muted-foreground">
                    {s.label}
                  </p>
                </div>
              </li>
            )
          })}
        </ul>
      </CardContent>
    </Card>
  )
}

export type CaseStudy = {
  id: string
  course: string
  duration: string
  metricLabel: string
  before: string
  after: string
  studentName: string
  studentYear: string
  quote: string
  advisorComment: string
  advisorName: string
  accent: "success" | "primary" | "warning"
  icon: LucideIcon
}

export const CASE_STUDIES: CaseStudy[] = [
  {
    id: "an",
    course: "Giải tích 1",
    duration: "Sau 8 tuần",
    metricLabel: "Điểm TB",
    before: "3.2",
    after: "7.5",
    studentName: "Nguyễn Văn An",
    studentYear: "Sinh viên năm nhất",
    quote: "Em hiểu mình mất gốc ở đâu — và biết bắt đầu lại.",
    advisorComment:
      "An có thái độ học tập tích cực, tiến bộ rất nhanh khi nắm được phương pháp đúng.",
    advisorName: "Cô Nguyễn Lan, Cố vấn học tập",
    accent: "success",
    icon: TrendingUp,
  },
  {
    id: "binh",
    course: "GPA học kỳ",
    duration: "Sau 1 học kỳ",
    metricLabel: "GPA",
    before: "2.1",
    after: "3.4",
    studentName: "Trần Thị Bình",
    studentYear: "Sinh viên năm hai",
    quote: "Một cuộc gọi 15 phút mỗi tuần — đổi cả học kỳ.",
    advisorComment:
      "Bình rất chủ động liên hệ và biết tự đánh giá điểm yếu của mình mỗi tuần.",
    advisorName: "Anh Phạm Quang, Cố vấn học tập",
    accent: "primary",
    icon: GraduationCap,
  },
  {
    id: "duc",
    course: "Vật lý đại cương",
    duration: "Sau 6 tuần",
    metricLabel: "Đi học",
    before: "42%",
    after: "96%",
    studentName: "Lê Minh Đức",
    studentYear: "Sinh viên năm nhất",
    quote: "Em không cảm thấy bị bỏ lại phía sau.",
    advisorComment:
      "Đức kiên trì luyện từng dạng bài. 96% là minh chứng cho sự nỗ lực bền bỉ.",
    advisorName: "Cô Trần Mai, Cố vấn học tập",
    accent: "warning",
    icon: Heart,
  },
]

const ACCENT_MAP = {
  success: {
    badge: "bg-success/10 text-success",
    metric: "text-success",
    line: "text-success",
  },
  primary: {
    badge: "bg-primary/10 text-primary",
    metric: "text-primary",
    line: "text-primary",
  },
  warning: {
    badge: "bg-warning/10 text-warning",
    metric: "text-warning",
    line: "text-warning",
  },
} as const

export function CaseStudyCard({ data: c }: { data: CaseStudy }) {
  const a = ACCENT_MAP[c.accent]
  const Icon = c.icon
  const initials = c.studentName
    .split(" ")
    .map((p) => p[0])
    .filter(Boolean)
    .slice(-2)
    .join("")
    .toUpperCase()

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-border/50 bg-card p-5 transition-shadow hover:shadow-md">
      {/* Badge + duration */}
      <div className="flex items-center gap-2">
        <Badge
          variant="secondary"
          className={cn("gap-1 rounded-md font-medium", a.badge)}
        >
          <Icon className="size-3" />
          {c.course}
        </Badge>
        <span className="text-xs text-muted-foreground">{c.duration}</span>
      </div>

      {/* Trend: before → line → after */}
      <div className="flex items-end gap-4">
        <div className="flex flex-col">
          <span className="mb-0.5 text-[11px] text-muted-foreground">Trước</span>
          <span className="font-mono text-xl font-medium text-muted-foreground">
            {c.before}
          </span>
        </div>
        <div className={cn("relative flex-1 self-stretch", a.line)}>
          <svg
            className="absolute inset-0 h-full w-full"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            aria-hidden
          >
            <line
              x1="0" y1="90" x2="100" y2="10"
              stroke="currentColor" strokeWidth="1.5" opacity="0.45"
              vectorEffect="non-scaling-stroke"
            />
          </svg>
          <span className="absolute right-0 top-[10%] size-2.5 -translate-y-1/2 rounded-full bg-current opacity-80" />
        </div>
        <div className="flex flex-col items-end">
          <span className={cn("mb-0.5 text-[11px]", a.metric)}>Sau</span>
          <span
            className={cn(
              "font-serif text-4xl font-bold tabular-nums leading-none",
              a.metric,
            )}
          >
            {c.after}
          </span>
        </div>
      </div>

      {/* Quote */}
      <p className="text-sm italic leading-relaxed text-foreground">
        &ldquo;{c.quote}&rdquo;
      </p>

      <div className="h-px bg-border/60" />

      {/* Student */}
      <div className="flex items-center gap-2.5">
        <Avatar className="size-8">
          <AvatarFallback className={cn("text-[11px] font-medium", a.badge)}>
            {initials}
          </AvatarFallback>
        </Avatar>
        <div>
          <p className="text-sm font-medium leading-none">{c.studentName}</p>
          <p className="mt-0.5 text-[11px] text-muted-foreground">{c.studentYear}</p>
        </div>
      </div>

      {/* Advisor comment */}
      <div className="rounded-xl bg-muted/40 px-3 py-2.5">
        <div className="mb-1.5 flex items-center gap-1.5">
          <MessageSquare className="size-3 text-muted-foreground/60" aria-hidden />
          <span className="text-[11px] font-medium text-muted-foreground">
            Cố vấn nhận xét
          </span>
        </div>
        <p className="text-sm leading-relaxed text-foreground">
          &ldquo;{c.advisorComment}&rdquo;
        </p>
        <div className="mt-2 flex items-center justify-between">
          <p className="text-[11px] text-muted-foreground">— {c.advisorName}</p>
          <ArrowUpRight className="size-3.5 text-muted-foreground/40" aria-hidden />
        </div>
      </div>
    </div>
  )
}


export type ThankYouNote = {
  id: string
  message: string
  studentName: string
  daysAgo: number
}

export const THANK_YOU_NOTES: ThankYouNote[] = [
  {
    id: "tn-1",
    message:
      "Cảm ơn cô đã không bỏ rơi em. Kỳ này em đã đậu hết các môn rồi ạ.",
    studentName: "Phạm Hoàng Yến",
    daysAgo: 2,
  },
  {
    id: "tn-2",
    message:
      "Email cô gửi đúng lúc em đang nản nhất. Mọi thứ tốt dần lên.",
    studentName: "Đặng Quốc Bảo",
    daysAgo: 5,
  },
  {
    id: "tn-3",
    message:
      "Cô là người đầu tiên hỏi em ổn không, thay vì hỏi vì sao điểm thấp.",
    studentName: "Vũ Linh Chi",
    daysAgo: 9,
  },
]

export function ThankYouNoteCard({ note: n }: { note: ThankYouNote }) {
  const initials = n.studentName
    .split(" ")
    .map((p) => p[0])
    .filter(Boolean)
    .slice(-2)
    .join("")
    .toUpperCase()

  return (
    <figure className="flex flex-col gap-2 rounded-2xl border border-border/60 bg-white p-4 ring-1 ring-primary/5 transition-shadow hover:shadow-md dark:bg-slate-900/40">
      <Quote className="size-4 shrink-0 text-primary/60" aria-hidden />
      <blockquote className="text-pretty text-sm leading-relaxed text-foreground">
        {n.message}
      </blockquote>
      <figcaption className="mt-auto flex items-center gap-2 border-t border-border/60 pt-2">
        <Avatar className="size-7">
          <AvatarFallback className="bg-primary/10 text-[11px] font-medium text-primary">
            {initials}
          </AvatarFallback>
        </Avatar>
        <span className="flex-1 truncate text-xs font-medium">
          {n.studentName}
        </span>
        <span className="shrink-0 text-[11px] font-mono text-muted-foreground">
          {n.daysAgo}d
        </span>
      </figcaption>
    </figure>
  )
}

export function SuccessCaseStudies() {
  return (
    <TooltipProvider delayDuration={150}>
      <div className="flex flex-col gap-4">
        <ImpactHero />

        <Card className="stripe-primary rounded-2xl border-primary/15 bg-gradient-to-br from-primary/18 via-primary/8 to-white dark:to-slate-900/40">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
            <CardTitle className="flex items-center gap-2 font-serif text-lg">
              <span
                aria-hidden
                className="grid size-7 place-items-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/15"
              >
                <Heart className="size-3.5" />
              </span>
              Lời nhắn từ sinh viên
            </CardTitle>
            <Badge
              variant="secondary"
              className="gap-1 rounded-md bg-primary/10 text-primary hover:bg-primary/10"
            >
              <Mail className="size-3" />
              {THANK_YOU_NOTES.length}
            </Badge>
          </CardHeader>
          <CardContent>
            <ul role="list" className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {THANK_YOU_NOTES.map((n) => (
                <li key={n.id} className="contents">
                  <ThankYouNoteCard note={n} />
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </TooltipProvider>
  )
}
