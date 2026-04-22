"use client"

import * as React from "react"
import {
  Wallet,
  BookOpen,
  CalendarX,
  Send,
  Pencil,
  Trash2,
  Sparkles,
  Filter,
  Search,
  Mail,
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
import {
  Avatar,
  AvatarFallback,
} from "@/components/ui/avatar"
import {
  Tabs,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group"
import { EmailEditorDialog } from "@/components/dashboard/email-editor-dialog"

type Problem = "financial" | "grades" | "absence"

type Alert = {
  id: string
  name: string
  mssv: string
  faculty: string
  problem: Problem
  summary: string
  severity: "high" | "medium"
  subject: string
  body: string
}

const seed: Alert[] = [
  {
    id: "a1",
    name: "Nguyễn Minh An",
    mssv: "20215032",
    faculty: "CNTT",
    problem: "financial",
    summary: "Học phí quá hạn 14 ngày",
    severity: "high",
    subject: "NexusEdu · Thầy nhắn An một chút nhé",
    body: `Chào An,

Thầy tình cờ thấy khoản học phí kỳ này của em vẫn chưa được cập nhật. Thầy hiểu đôi khi có những trục trặc ngoài ý muốn, nên muốn hỏi xem em có đang gặp khó khăn gì không.

Nếu em cần, mình có thể gặp 15 phút để cùng xem các phương án — trả góp, học bổng khẩn cấp, hoặc chỉ là lắng nghe. Em cứ đặt lịch theo link này nhé:
→ nexusedu.app/booking/le-ha

Thầy luôn ở đây,
TS. Lê Hà`,
  },
  {
    id: "a2",
    name: "Trần Hoàng Bình",
    mssv: "20215098",
    faculty: "CNTT",
    problem: "grades",
    summary: "Điểm giữa kỳ < 4.0 ở 3 môn",
    severity: "high",
    subject: "NexusEdu · Cùng nhìn lại kỳ này nhé Bình",
    body: `Chào Bình,

Thầy xem kết quả giữa kỳ và thấy em đang gặp một chút khó khăn ở vài môn. Không sao cả — đây là thời điểm tốt để mình điều chỉnh, và vẫn còn đủ thời gian để cải thiện.

Em thử đặt một buổi 20 phút với thầy để mình cùng xem lộ trình học, và có thể kết nối em với nhóm hỗ trợ của khoa nhé.
→ nexusedu.app/booking/le-ha

Thầy tin ở em,
TS. Lê Hà`,
  },
  {
    id: "a3",
    name: "Phạm Thu Hà",
    mssv: "20215172",
    faculty: "Kinh tế",
    problem: "absence",
    summary: "Vắng 6/10 buổi gần nhất",
    severity: "medium",
    subject: "NexusEdu · Hà có khoẻ không?",
    body: `Chào Hà,

Cô thấy em vắng khá nhiều buổi gần đây. Cô không muốn làm phiền, chỉ muốn hỏi thăm xem em có ổn không — sức khoẻ, gia đình, hoặc bất cứ điều gì.

Khi nào em sẵn sàng, mình có thể trò chuyện 15 phút nhé.
→ nexusedu.app/booking/le-ha

Chăm sóc bản thân nhé Hà,
TS. Lê Hà`,
  },
  {
    id: "a4",
    name: "Lê Quốc Huy",
    mssv: "20215211",
    faculty: "CNTT",
    problem: "grades",
    summary: "Điểm TB giảm 2 kỳ liên tiếp",
    severity: "medium",
    subject: "NexusEdu · Cùng nhìn lại lộ trình của em nhé",
    body: `Chào Huy,

Thầy nhận thấy điểm trung bình của em giảm đều 2 kỳ gần đây. Thầy nghĩ mình có thể nói chuyện để hiểu rõ hơn điều em đang gặp phải và cùng tìm hướng đi phù hợp.

Em đặt lịch khi nào thuận tiện nhé:
→ nexusedu.app/booking/le-ha

Thân mến,
TS. Lê Hà`,
  },
  {
    id: "a5",
    name: "Võ Thảo Nguyên",
    mssv: "20215384",
    faculty: "Kinh tế",
    problem: "financial",
    summary: "Chưa hoàn tất học phí, gần hạn",
    severity: "medium",
    subject: "NexusEdu · Một lời nhắc nhỏ cho Nguyên",
    body: `Chào Nguyên,

Chỉ là một lời nhắc nhẹ: học phí kỳ này sắp tới hạn. Nếu em đang có bất kỳ khó khăn nào, đừng ngại nhắn cô nhé — có nhiều phương án em có thể chưa biết.

→ nexusedu.app/booking/le-ha

Thân mến,
TS. Lê Hà`,
  },
]

const problemMeta: Record<
  Problem,
  { label: string; icon: React.ElementType; tone: string }
> = {
  financial: {
    label: "Học phí",
    icon: Wallet,
    tone: "bg-destructive/10 text-destructive ring-destructive/20",
  },
  grades: {
    label: "Điểm số",
    icon: BookOpen,
    tone: "bg-warning/15 text-warning ring-warning/25",
  },
  absence: {
    label: "Vắng học",
    icon: CalendarX,
    tone: "bg-primary/10 text-primary ring-primary/20",
  },
}

export function AlertCenter() {
  const [filter, setFilter] = React.useState<"all" | Problem>("all")
  const [query, setQuery] = React.useState("")
  const [alerts, setAlerts] = React.useState(seed)
  const [editing, setEditing] = React.useState<Alert | null>(null)

  const filtered = alerts.filter((a) => {
    const matchesFilter = filter === "all" || a.problem === filter
    const q = query.trim().toLowerCase()
    const matchesQuery =
      !q ||
      a.name.toLowerCase().includes(q) ||
      a.mssv.includes(q) ||
      a.summary.toLowerCase().includes(q)
    return matchesFilter && matchesQuery
  })

  const send = (a: Alert) => {
    setAlerts((arr) => arr.filter((x) => x.id !== a.id))
    toast.success(`Đã gửi email tới ${a.name}`, {
      description: "Sinh viên sẽ nhận được lời nhắn ấm áp trong giây lát.",
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
                Bản nháp email do AI soạn — con người là người quyết định gửi.
              </CardDescription>
            </div>
            <div className="flex w-full flex-col gap-2 md:w-auto md:flex-row md:items-center">
              <InputGroup className="h-10 w-full rounded-xl md:w-72">
                <InputGroupAddon>
                  <Search className="size-4 text-muted-foreground" />
                </InputGroupAddon>
                <InputGroupInput
                  placeholder="Tìm theo tên, MSSV..."
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
              <TabsTrigger value="financial" className="rounded-lg">
                Học phí
              </TabsTrigger>
              <TabsTrigger value="grades" className="rounded-lg">
                Điểm số
              </TabsTrigger>
              <TabsTrigger value="absence" className="rounded-lg">
                Vắng học
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </CardHeader>

        <CardContent className="grid gap-3">
          {filtered.length === 0 && (
            <div className="rounded-xl border border-dashed border-border p-10 text-center">
              <Mail className="mx-auto size-10 text-muted-foreground" />
              <p className="mt-3 font-serif text-lg font-semibold">
                Không có cảnh báo phù hợp
              </p>
              <p className="text-sm text-muted-foreground">
                Tuyệt vời — hoặc thử thay đổi bộ lọc / từ khoá tìm kiếm.
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
                        {a.name
                          .split(" ")
                          .map((n) => n[0])
                          .slice(-2)
                          .join("")}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-semibold">{a.name}</p>
                        {a.severity === "high" && (
                          <Badge className="h-5 rounded-md bg-destructive/15 text-destructive hover:bg-destructive/15">
                            Nguy cơ cao
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        MSSV {a.mssv} · Khoa {a.faculty}
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
                      {a.body.split("\n\n")[1]}
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
