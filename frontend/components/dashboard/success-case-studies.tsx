"use client"

import {
  ArrowRight,
  CheckCircle2,
  Clock,
  GraduationCap,
  Heart,
  Mail,
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
  metricLabel: string
  before: string
  after: string
  studentName: string
  quote: string
  accent: "success" | "primary"
  icon: LucideIcon
}

export const CASE_STUDIES: CaseStudy[] = [
  {
    id: "an",
    course: "Giải tích 1",
    metricLabel: "Điểm TB",
    before: "3.2",
    after: "7.5",
    studentName: "Nguyễn Văn An",
    quote: "Em hiểu mình mất gốc ở đâu — và biết bắt đầu lại.",
    accent: "success",
    icon: TrendingUp,
  },
  {
    id: "binh",
    course: "GPA học kỳ",
    metricLabel: "GPA",
    before: "2.1",
    after: "3.4",
    studentName: "Trần Thị Bình",
    quote: "Một cuộc gọi 15 phút mỗi tuần — đổi cả học kỳ.",
    accent: "primary",
    icon: GraduationCap,
  },
  {
    id: "duc",
    course: "Vật lý đại cương",
    metricLabel: "Đi học",
    before: "42%",
    after: "96%",
    studentName: "Lê Minh Đức",
    quote: "Em không cảm thấy bị bỏ lại phía sau.",
    accent: "success",
    icon: Heart,
  },
]

export function CaseStudyCard({ data: c }: { data: CaseStudy }) {
  const accent =
    c.accent === "success"
      ? {
          ring: "ring-success/15",
          tint: "bg-success/10 text-success",
          stripe: "from-success/40 via-success/10 to-transparent",
          metric: "text-success",
        }
      : {
          ring: "ring-primary/15",
          tint: "bg-primary/10 text-primary",
          stripe: "from-primary/40 via-primary/10 to-transparent",
          metric: "text-primary",
        }

  const Icon = c.icon
  const initials = c.studentName
    .split(" ")
    .map((p) => p[0])
    .filter(Boolean)
    .slice(-2)
    .join("")
    .toUpperCase()

  return (
    <Card
      className={cn(
        "relative flex flex-col overflow-hidden rounded-2xl border-border/60 bg-white ring-1 transition-shadow hover:shadow-md dark:bg-slate-900/40",
        accent.ring,
      )}
    >
      <div
        aria-hidden
        className={cn(
          "pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r",
          accent.stripe,
        )}
      />

      <CardHeader className="pb-3">
        <Badge
          variant="secondary"
          className={cn(
            "w-fit gap-1 rounded-md font-medium hover:bg-current/10",
            accent.tint,
          )}
        >
          <Icon className="size-3" />
          {c.course}
        </Badge>

        {/* Big number transform — the visual centerpiece */}
        <div className="mt-3 flex items-baseline gap-2">
          <span className="font-mono text-xl font-medium text-muted-foreground line-through decoration-muted-foreground/40">
            {c.before}
          </span>
          <ArrowRight className="size-4 text-muted-foreground" />
          <span
            className={cn(
              "font-serif text-3xl font-bold tabular-nums",
              accent.metric,
            )}
          >
            {c.after}
          </span>
          <span className="ml-auto text-[11px] uppercase tracking-wide text-muted-foreground">
            <span className="mx-1">{c.metricLabel}</span>
          </span>
        </div>
      </CardHeader>

      <CardContent className="mt-auto flex flex-col gap-3 pt-0">
        <figure className="rounded-xl border border-border/60 bg-muted/40 p-3">
          <Quote className="size-3.5 text-muted-foreground/70" aria-hidden />
          <blockquote className="mt-1 text-sm leading-relaxed text-foreground">
            {c.quote}
          </blockquote>
          <figcaption className="mt-2 flex items-center gap-2 text-xs">
            <Avatar className="size-6">
              <AvatarFallback className={cn("text-[10px] font-medium", accent.tint)}>
                {initials}
              </AvatarFallback>
            </Avatar>
            <span className="truncate font-medium">{c.studentName}</span>
          </figcaption>
        </figure>
      </CardContent>
    </Card>
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
