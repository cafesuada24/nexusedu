"use client"

import * as React from "react"
import Link from "next/link"
import {
  BookOpen,
  PlayCircle,
  MessageCircle,
  Phone,
  Mail,
  Search,
  ArrowUpRight,
  Sparkles,
  FileSpreadsheet,
  BellRing,
  BarChart3,
  CalendarDays,
  Shield,
  Database,
  Smartphone,
  Copy,
  Check,
  type LucideIcon,
} from "lucide-react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group"
import { Kbd } from "@/components/ui/kbd"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

/* ────────────────────────────────────────────────────────────────
 * Topic taxonomy — color + icon, no extra prose
 * ──────────────────────────────────────────────────────────────── */

type TopicKey = "ai" | "data" | "report" | "privacy" | "platform"

const TOPICS: Record<
  TopicKey,
  { label: string; icon: LucideIcon; dot: string; bg: string; text: string }
> = {
  ai: {
    label: "AI",
    icon: Sparkles,
    dot: "bg-primary",
    bg: "bg-primary/10",
    text: "text-primary",
  },
  data: {
    label: "Dữ liệu",
    icon: Database,
    dot: "bg-warning",
    bg: "bg-warning/15",
    text: "text-warning",
  },
  report: {
    label: "Báo cáo",
    icon: BarChart3,
    dot: "bg-accent-foreground",
    bg: "bg-accent",
    text: "text-accent-foreground",
  },
  privacy: {
    label: "Bảo mật",
    icon: Shield,
    dot: "bg-success",
    bg: "bg-success/10",
    text: "text-success",
  },
  platform: {
    label: "Nền tảng",
    icon: Smartphone,
    dot: "bg-muted-foreground",
    bg: "bg-muted",
    text: "text-foreground",
  },
}

/* ────────────────────────────────────────────────────────────────
 * Quick links — varied colored icon tiles
 * ──────────────────────────────────────────────────────────────── */

type QuickLink = {
  icon: LucideIcon
  title: string
  time: string
  topic: TopicKey
}

const quickLinks: QuickLink[] = [
  { icon: FileSpreadsheet, title: "Nhập CSV", time: "5p", topic: "data" },
  { icon: BellRing, title: "Điểm rủi ro", time: "8p", topic: "ai" },
  { icon: Sparkles, title: "Email AI", time: "4p", topic: "ai" },
  { icon: BarChart3, title: "BGH Dashboard", time: "6p", topic: "report" },
  { icon: CalendarDays, title: "Lịch hẹn", time: "3p", topic: "platform" },
  { icon: Shield, title: "Bảo mật", time: "7p", topic: "privacy" },
]

/* ────────────────────────────────────────────────────────────────
 * FAQs — each tagged with a topic
 * ──────────────────────────────────────────────────────────────── */

type Faq = { q: string; a: string; topic: TopicKey }

const faqs: Faq[] = [
  {
    q: "Điểm rủi ro được tính như thế nào?",
    a: "Kết quả học tập 40% · Tham gia 30% · Hành vi 20% · Cố vấn 10%. Cập nhật mỗi 30 phút.",
    topic: "ai",
  },
  {
    q: "Làm sao để thêm sinh viên mới?",
    a: "Upload CSV theo template hoặc đồng bộ trực tiếp với LMS Moodle.",
    topic: "data",
  },
  {
    q: "Email AI có tự động gửi không?",
    a: "Không. Mọi email phải được cố vấn duyệt — Human-in-the-Loop bắt buộc.",
    topic: "ai",
  },
  {
    q: "Sinh viên có thấy điểm rủi ro của mình?",
    a: "Không. Sinh viên chỉ thấy lịch hẹn và thông điệp cố vấn gửi.",
    topic: "privacy",
  },
  {
    q: "Dữ liệu lưu trữ ở đâu?",
    a: "Vercel & AWS Singapore, AES-256. Tuân thủ ANM VN và GDPR.",
    topic: "privacy",
  },
  {
    q: "Nếu AI gợi ý sai?",
    a: "Bấm 'Báo cáo sai'. Có thể chỉnh ngưỡng tại Cài đặt → Quy tắc AI.",
    topic: "ai",
  },
  {
    q: "Tôi xuất báo cáo cho BGH thế nào?",
    a: "BGH Dashboard → Xuất báo cáo (PDF / Excel), lọc theo khoa hoặc kỳ.",
    topic: "report",
  },
  {
    q: "Có phiên bản mobile không?",
    a: "Có — NexusEdu Advisor trên iOS & Android, dùng cùng tài khoản.",
    topic: "platform",
  },
]

/* ────────────────────────────────────────────────────────────────
 * View
 * ──────────────────────────────────────────────────────────────── */

export function SupportView() {
  const [query, setQuery] = React.useState("")
  const [activeTopic, setActiveTopic] = React.useState<TopicKey | "all">("all")
  const [copiedLabel, setCopiedLabel] = React.useState<string | null>(null)

  const handleCopy = (text: string, label: string) => {
    navigator.clipboard.writeText(text)
    setCopiedLabel(label)
    toast.success(`Đã sao chép ${label.toLowerCase()}`, {
      description: `Thông tin đã được lưu vào bộ nhớ tạm của bạn.`,
    })
    setTimeout(() => setCopiedLabel(null), 2000)
  }

  const filteredFaqs = faqs.filter((f) => {
    const matchesTopic = activeTopic === "all" || f.topic === activeTopic
    const q = query.trim().toLowerCase()
    const matchesQuery =
      q.length === 0 ||
      f.q.toLowerCase().includes(q) ||
      f.a.toLowerCase().includes(q)
    return matchesTopic && matchesQuery
  })

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      {/* ────── Left column ────── */}
      <div className="grid gap-6 lg:col-span-2">
        {/* Search — Promoted to top */}
        <InputGroup className="h-11 rounded-xl">
          <InputGroupAddon>
            <Search className="size-4 text-muted-foreground" />
          </InputGroupAddon>
          <InputGroupInput
            placeholder="Tìm hướng dẫn, FAQ..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Tìm kiếm trợ giúp"
          />
          <InputGroupAddon align="inline-end">
            <Kbd>/</Kbd>
          </InputGroupAddon>
        </InputGroup>

        {/* Quick links — colored icon grid */}
        <Card className="stripe-sky rounded-2xl border-accent-sky/15 bg-gradient-to-br from-accent-sky/22 via-accent-sky/10 to-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <BookOpen className="size-4 text-primary" />
              Bài viết
            </CardTitle>
            <Button asChild variant="ghost" size="sm" className="rounded-lg">
              <Link href="#" aria-label="Tất cả bài viết">
                <ArrowUpRight className="size-4" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent className="grid gap-2 sm:grid-cols-3">
            {quickLinks.map((l) => {
              const t = TOPICS[l.topic]
              return (
                <Link
                  key={l.title}
                  href="#"
                  className="group flex items-center gap-2.5 rounded-xl border border-border/60 bg-muted/30 p-3 transition-colors hover:border-primary/30 hover:bg-primary/5"
                >
                  <div
                    className={cn(
                      "grid size-9 shrink-0 place-items-center rounded-lg",
                      t.bg,
                      t.text,
                    )}
                  >
                    <l.icon className="size-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="truncate text-sm font-medium leading-tight group-hover:text-primary">
                      {l.title}
                    </h4>
                    <p className="font-mono text-[11px] text-muted-foreground">
                      {l.time}
                    </p>
                  </div>
                </Link>
              )
            })}
          </CardContent>
        </Card>

        {/* FAQ — chip filters + colored category dots */}
        <Card className="stripe-cyan rounded-2xl border-accent-cyan/15 bg-gradient-to-br from-accent-cyan/22 via-accent-cyan/10 to-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <MessageCircle className="size-4 text-primary" />
              FAQ
            </CardTitle>
            <Badge
              variant="outline"
              className="rounded-md font-mono text-[11px]"
            >
              {filteredFaqs.length}/{faqs.length}
            </Badge>
          </CardHeader>
          <CardContent className="grid gap-3">
            {/* Topic chips — visual filter, almost no text */}
            <div className="flex flex-wrap gap-1.5">
              <button
                type="button"
                onClick={() => setActiveTopic("all")}
                className={cn(
                  "rounded-full border px-2.5 py-1 text-xs transition-colors",
                  activeTopic === "all"
                    ? "border-primary/30 bg-primary/10 text-primary"
                    : "border-border/60 bg-muted/30 text-muted-foreground hover:bg-muted/60",
                )}
              >
                Tất cả
              </button>
              {(Object.keys(TOPICS) as TopicKey[]).map((key) => {
                const t = TOPICS[key]
                const Icon = t.icon
                const active = activeTopic === key
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setActiveTopic(key)}
                    aria-label={t.label}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs transition-colors",
                      active
                        ? cn("border-transparent", t.bg, t.text)
                        : "border-border/60 bg-muted/30 text-muted-foreground hover:bg-muted/60",
                    )}
                  >
                    <Icon className="size-3" />
                    {t.label}
                  </button>
                )
              })}
            </div>

            {filteredFaqs.length === 0 ? (
              <div className="grid place-items-center gap-2 rounded-xl border border-dashed border-border/60 p-6 text-center">
                <span className="grid size-9 place-items-center rounded-lg bg-muted text-muted-foreground">
                  <Search className="size-4" />
                </span>
              </div>
            ) : (
              <Accordion type="single" collapsible className="w-full">
                {filteredFaqs.map((f, i) => {
                  const t = TOPICS[f.topic]
                  return (
                    <AccordionItem
                      key={i}
                      value={`q-${i}`}
                      className="border-border/60"
                    >
                      <AccordionTrigger className="text-left text-sm font-medium hover:no-underline">
                        <span className="flex items-center gap-2">
                          <span
                            aria-hidden
                            className={cn("size-2 shrink-0 rounded-full", t.dot)}
                          />
                          {f.q}
                        </span>
                      </AccordionTrigger>
                      <AccordionContent className="pl-4 text-sm leading-relaxed text-muted-foreground">
                        {f.a}
                      </AccordionContent>
                    </AccordionItem>
                  )
                })}
              </Accordion>
            )}
          </CardContent>
        </Card>

        {/* Video tutorials — gradient tiles, minimal text */}
        <Card className="stripe-indigo rounded-2xl border-accent-indigo/15 bg-gradient-to-br from-accent-indigo/22 via-accent-indigo/10 to-card">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <PlayCircle className="size-4 text-primary" />
              Video
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-3">
            {[
              { title: "Giao diện", duration: "4:32", from: "from-primary/15" },
              {
                title: "Alert đầu tiên",
                duration: "5:18",
                from: "from-warning/15",
              },
              { title: "Email AI", duration: "4:55", from: "from-success/15" },
            ].map((v, i) => (
              <button
                key={i}
                className={cn(
                  "group relative overflow-hidden rounded-xl border border-border/60 bg-gradient-to-br via-muted/40 to-muted/20 p-4 text-left transition-colors hover:border-primary/30",
                  v.from,
                )}
              >
                <div className="flex items-center justify-between">
                  <Badge
                    variant="outline"
                    className="rounded-md bg-background/80 font-mono text-[10px] backdrop-blur"
                  >
                    {String(i + 1).padStart(2, "0")}
                  </Badge>
                  <div className="grid size-10 place-items-center rounded-full bg-primary text-primary-foreground shadow-md transition-transform group-hover:scale-110">
                    <PlayCircle className="size-5" />
                  </div>
                </div>
                <div className="mt-8 flex items-end justify-between">
                  <p className="font-medium leading-tight">{v.title}</p>
                  <p className="font-mono text-[11px] text-muted-foreground">
                    {v.duration}
                  </p>
                </div>
              </button>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* ────── Right column ────── */}
      <div className="grid gap-6">
        {/* Contact tiles — Promoted for layout balance */}
        <Card className="stripe-primary rounded-2xl border-primary/15 bg-gradient-to-br from-primary/18 via-primary/8 to-white dark:to-slate-900/40">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Phone className="size-4 text-primary" />
              Liên hệ
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2">
            {[
              { icon: Mail, label: "Email", detail: "support@nexusedu.vn", primary: true },
              { icon: Phone, label: "Hotline", detail: "1900 0175" },
            ].map((c) => {
              const isCopied = copiedLabel === c.label
              return (
                <button
                  key={c.label}
                  onClick={() => handleCopy(c.detail, c.label)}
                  className={cn(
                    "group flex items-center gap-3 rounded-xl border px-3 py-2.5 text-left transition-all duration-200",
                    c.primary
                      ? "border-primary/30 bg-primary/5 hover:bg-primary/10"
                      : "border-border/60 hover:bg-muted/40",
                  )}
                >
                  <div
                    className={cn(
                      "grid size-9 place-items-center rounded-lg transition-transform group-active:scale-95",
                      c.primary
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-foreground",
                    )}
                  >
                    <c.icon className="size-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{c.label}</p>
                    <p className="truncate font-mono text-[11px] text-muted-foreground">
                      {c.detail}
                    </p>
                  </div>
                  <div className="relative size-8 shrink-0">
                    <div
                      className={cn(
                        "absolute inset-0 grid place-items-center transition-all duration-300",
                        isCopied ? "scale-0 opacity-0" : "scale-100 opacity-100",
                      )}
                    >
                      <Copy className="size-4 text-muted-foreground transition-colors group-hover:text-primary" />
                    </div>
                    <div
                      className={cn(
                        "absolute inset-0 grid place-items-center transition-all duration-300",
                        isCopied ? "scale-100 opacity-100" : "scale-0 opacity-0",
                      )}
                    >
                      <Check className="size-4 text-success" />
                    </div>
                  </div>
                </button>
              )
            })}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
