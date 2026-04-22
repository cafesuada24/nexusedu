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
  HeartPulse,
  CheckCircle2,
} from "lucide-react"
import {
  Card,
  CardContent,
  CardDescription,
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
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group"
import { Kbd } from "@/components/ui/kbd"

const quickLinks = [
  {
    icon: FileSpreadsheet,
    title: "Nhập dữ liệu CSV",
    desc: "Hướng dẫn định dạng, mapping cột và xử lý lỗi import.",
    time: "5 phút đọc",
  },
  {
    icon: BellRing,
    title: "Hiểu điểm rủi ro",
    desc: "Cách AI tính điểm, trọng số các yếu tố và cách hiệu chỉnh.",
    time: "8 phút đọc",
  },
  {
    icon: Sparkles,
    title: "Tối ưu email AI",
    desc: "Chọn giọng văn, prompt, và các quy tắc an toàn.",
    time: "4 phút đọc",
  },
  {
    icon: BarChart3,
    title: "Đọc BGH Dashboard",
    desc: "Các chỉ số KPI và cách diễn giải cho lãnh đạo khoa.",
    time: "6 phút đọc",
  },
  {
    icon: CalendarDays,
    title: "Cấu hình lịch đặt hẹn",
    desc: "Khung giờ, buffer, đồng bộ Google Calendar & Teams.",
    time: "3 phút đọc",
  },
  {
    icon: Shield,
    title: "Quyền riêng tư sinh viên",
    desc: "Chính sách bảo mật, lưu trữ và quyền truy cập dữ liệu.",
    time: "7 phút đọc",
  },
]

const faqs = [
  {
    q: "Điểm rủi ro được tính như thế nào?",
    a: "NexusEdu kết hợp 4 nhóm dữ liệu: kết quả học tập (GPA, điểm quá trình, điểm thành phần — trọng số 40%), mức độ tham gia lớp học (điểm danh, nộp bài, tương tác LMS — 30%), tín hiệu hành vi (đăng nhập, thời gian online, số lần huỷ môn — 20%) và tín hiệu chủ quan do cố vấn ghi nhận (10%). Điểm được cập nhật mỗi 30 phút khi có dữ liệu mới.",
  },
  {
    q: "Làm sao để thêm một sinh viên mới vào hệ thống?",
    a: "Có hai cách. Cách 1: vào mục Nhập CSV và upload file theo template chuẩn — hệ thống sẽ tự động tạo hồ sơ nếu mã sinh viên chưa tồn tại. Cách 2: đồng bộ trực tiếp với LMS Moodle đã kết nối, sinh viên mới sẽ được thêm tự động mỗi đầu kỳ.",
  },
  {
    q: "Email AI có tự động gửi cho sinh viên không?",
    a: "Không. Mọi email đều phải được cố vấn bấm nút Duyệt & Gửi. Đây là nguyên tắc Human-in-the-Loop bắt buộc. Bạn có thể chỉnh sửa nội dung, đổi giọng văn, thêm file đính kèm trước khi gửi. Hệ thống chỉ tự động gửi email nhắc nhở lịch hẹn đã được bạn xác nhận trước đó.",
  },
  {
    q: "Sinh viên có thấy được điểm rủi ro của mình không?",
    a: "Không. Điểm rủi ro là công cụ nội bộ dành cho cố vấn và ban giám hiệu. Sinh viên chỉ thấy được lịch hẹn và các thông điệp cố vấn chủ động gửi. Chúng tôi tin rằng con người — chứ không phải con số — nên là điểm tiếp xúc chính với sinh viên.",
  },
  {
    q: "Dữ liệu được lưu trữ ở đâu?",
    a: "Toàn bộ dữ liệu được lưu trên hạ tầng Vercel & AWS khu vực Singapore, mã hoá AES-256 cả khi lưu trữ lẫn truyền tải. NexusEdu tuân thủ Luật An ninh mạng Việt Nam và GDPR. Xem chi tiết tại Chính sách bảo mật.",
  },
  {
    q: "Nếu AI gợi ý sai thì sao?",
    a: "Bạn có thể bấm \u201CBáo cáo sai\u201D ở bất kỳ gợi ý nào. Thông tin phản hồi sẽ được gửi về đội ngũ mô hình để tinh chỉnh. Đồng thời, bạn có thể chỉnh ngưỡng cảnh báo tại Cài đặt → Quy tắc AI để phù hợp với đặc thù khoa của mình.",
  },
  {
    q: "Tôi có thể xuất báo cáo cho BGH không?",
    a: "Có. Tại BGH Dashboard, bấm nút Xuất báo cáo (góc phải trên). Bạn có thể chọn định dạng PDF (cho họp) hoặc Excel (cho phân tích sâu), và lọc theo khoa, kỳ học, hoặc nhóm rủi ro.",
  },
  {
    q: "NexusEdu có phiên bản mobile không?",
    a: "Có. Ứng dụng iOS và Android đã có trên App Store và Google Play với tên NexusEdu Advisor. Bạn dùng cùng tài khoản để đăng nhập. Tính năng chính: xem alert, duyệt email, xác nhận lịch hẹn. Nhập CSV và báo cáo tổng hợp vẫn chỉ có trên web.",
  },
]

const shortcuts = [
  { keys: ["⌘", "K"], label: "Tìm kiếm nhanh" },
  { keys: ["G", "D"], label: "Mở Tổng quan" },
  { keys: ["G", "A"], label: "Mở Alert Center" },
  { keys: ["G", "M"], label: "Mở BGH Dashboard" },
  { keys: ["N"], label: "Duyệt alert tiếp theo" },
  { keys: ["E"], label: "Soạn email AI" },
  { keys: ["Esc"], label: "Đóng dialog hiện tại" },
  { keys: ["?"], label: "Hiện danh sách phím tắt" },
]

export function SupportView() {
  const [query, setQuery] = React.useState("")

  const filteredFaqs = faqs.filter(
    (f) =>
      f.q.toLowerCase().includes(query.toLowerCase()) ||
      f.a.toLowerCase().includes(query.toLowerCase()),
  )

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="lg:col-span-2 grid gap-6">
        {/* System status + search */}
        <div className="rounded-2xl border border-border/60 bg-gradient-to-br from-primary/5 via-card to-card p-5">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-3">
              <div className="grid size-11 place-items-center rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <HeartPulse className="size-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold">Mọi dịch vụ hoạt động bình thường</h3>
                  <Badge className="rounded-md bg-emerald-500/15 text-emerald-600 hover:bg-emerald-500/20 dark:text-emerald-400">
                    99.98% uptime
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">
                  Cập nhật lần cuối: 2 phút trước
                </p>
              </div>
            </div>
            <Button asChild variant="outline" size="sm" className="rounded-lg">
              <Link href="#">
                Xem trang trạng thái
                <ArrowUpRight className="size-4" />
              </Link>
            </Button>
          </div>

          <div className="mt-5">
            <InputGroup className="h-11 rounded-xl">
              <InputGroupAddon>
                <Search className="size-4 text-muted-foreground" />
              </InputGroupAddon>
              <InputGroupInput
                placeholder={'Tìm câu hỏi, ví dụ "cách import CSV"...'}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                aria-label="Tìm kiếm trợ giúp"
              />
              <InputGroupAddon align="inline-end">
                <Kbd>/</Kbd>
              </InputGroupAddon>
            </InputGroup>
          </div>
        </div>

        {/* Quick links / docs */}
        <Card className="rounded-2xl border-border/60">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="size-5 text-primary" />
                Bài viết phổ biến
              </CardTitle>
              <CardDescription>
                Tài liệu ngắn được biên soạn cho cố vấn mới bắt đầu.
              </CardDescription>
            </div>
            <Button asChild variant="ghost" size="sm" className="rounded-lg">
              <Link href="#">
                Xem tất cả
                <ArrowUpRight className="size-4" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            {quickLinks.map((l) => (
              <Link
                key={l.title}
                href="#"
                className="group flex items-start gap-3 rounded-xl border border-border/60 bg-muted/30 p-4 transition-colors hover:border-primary/30 hover:bg-primary/5"
              >
                <div className="grid size-10 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
                  <l.icon className="size-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <h4 className="font-medium leading-tight group-hover:text-primary">
                      {l.title}
                    </h4>
                    <ArrowUpRight className="size-3.5 text-muted-foreground transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-primary" />
                  </div>
                  <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                    {l.desc}
                  </p>
                  <p className="mt-1.5 text-xs text-muted-foreground">{l.time}</p>
                </div>
              </Link>
            ))}
          </CardContent>
        </Card>

        {/* FAQ */}
        <Card className="rounded-2xl border-border/60">
          <CardHeader>
            <CardTitle>Câu hỏi thường gặp</CardTitle>
            <CardDescription>
              {query
                ? `${filteredFaqs.length} kết quả cho "${query}"`
                : "Những câu hỏi các cố vấn hỏi nhiều nhất trong 30 ngày qua."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {filteredFaqs.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border/60 p-8 text-center">
                <p className="text-sm text-muted-foreground">
                  Không tìm thấy câu hỏi phù hợp. Hãy thử từ khoá khác hoặc gửi yêu cầu bên phải.
                </p>
              </div>
            ) : (
              <Accordion type="single" collapsible className="w-full">
                {filteredFaqs.map((f, i) => (
                  <AccordionItem key={i} value={`q-${i}`} className="border-border/60">
                    <AccordionTrigger className="text-left text-sm font-medium hover:no-underline">
                      {f.q}
                    </AccordionTrigger>
                    <AccordionContent className="text-sm leading-relaxed text-muted-foreground">
                      {f.a}
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            )}
          </CardContent>
        </Card>

        {/* Video tutorials */}
        <Card className="rounded-2xl border-border/60">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PlayCircle className="size-5 text-primary" />
              Video hướng dẫn
            </CardTitle>
            <CardDescription>
              Series 3 tập ngắn giúp bạn quen với NexusEdu trong 15 phút.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-3">
            {[
              { title: "Tổng quan giao diện", duration: "4:32", step: "Tập 1" },
              { title: "Xử lý alert đầu tiên", duration: "5:18", step: "Tập 2" },
              { title: "Gửi email AI hiệu quả", duration: "4:55", step: "Tập 3" },
            ].map((v, i) => (
              <button
                key={i}
                className="group relative overflow-hidden rounded-xl border border-border/60 bg-gradient-to-br from-primary/10 via-muted/50 to-muted/20 p-4 text-left transition-colors hover:border-primary/30"
              >
                <div className="flex items-center justify-between">
                  <Badge variant="outline" className="rounded-md text-xs">
                    {v.step}
                  </Badge>
                  <div className="grid size-10 place-items-center rounded-full bg-primary text-primary-foreground shadow-sm transition-transform group-hover:scale-105">
                    <PlayCircle className="size-5" />
                  </div>
                </div>
                <div className="mt-8">
                  <p className="font-medium leading-tight">{v.title}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{v.duration}</p>
                </div>
              </button>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Right column */}
      <div className="grid gap-6">
        {/* Contact card */}
        <Card className="rounded-2xl border-border/60">
          <CardHeader>
            <CardTitle>Liên hệ đội ngũ</CardTitle>
            <CardDescription>Chúng tôi trả lời trong 2 giờ làm việc.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2.5">
            {[
              { icon: MessageCircle, label: "Chat trực tiếp", detail: "Đang online · 8 nhân viên", primary: true },
              { icon: Mail, label: "Email hỗ trợ", detail: "support@nexusedu.vn" },
              { icon: Phone, label: "Hotline", detail: "1900 0175 (T2–T7, 8h–20h)" },
            ].map((c) => (
              <button
                key={c.label}
                className={`flex items-center gap-3 rounded-xl border px-3 py-3 text-left transition-colors ${
                  c.primary
                    ? "border-primary/30 bg-primary/5 hover:bg-primary/10"
                    : "border-border/60 hover:bg-muted/40"
                }`}
              >
                <div
                  className={`grid size-10 place-items-center rounded-lg ${
                    c.primary
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-foreground"
                  }`}
                >
                  <c.icon className="size-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{c.label}</p>
                  <p className="truncate text-xs text-muted-foreground">{c.detail}</p>
                </div>
                <ArrowUpRight className="size-4 text-muted-foreground" />
              </button>
            ))}
          </CardContent>
        </Card>

        {/* Submit ticket */}
        <Card className="rounded-2xl border-border/60">
          <CardHeader>
            <CardTitle>Gửi yêu cầu hỗ trợ</CardTitle>
            <CardDescription>Mô tả càng rõ, chúng tôi giải đáp càng nhanh.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="grid gap-1.5">
              <Label htmlFor="ticket-category">Chủ đề</Label>
              <Select defaultValue="usage">
                <SelectTrigger id="ticket-category" className="rounded-lg">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="usage">Hướng dẫn sử dụng</SelectItem>
                  <SelectItem value="bug">Báo lỗi hệ thống</SelectItem>
                  <SelectItem value="data">Dữ liệu không chính xác</SelectItem>
                  <SelectItem value="ai">Chất lượng gợi ý AI</SelectItem>
                  <SelectItem value="billing">Gói dịch vụ &amp; hoá đơn</SelectItem>
                  <SelectItem value="other">Khác</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="ticket-priority">Mức độ ưu tiên</Label>
              <Select defaultValue="normal">
                <SelectTrigger id="ticket-priority" className="rounded-lg">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Thấp</SelectItem>
                  <SelectItem value="normal">Bình thường</SelectItem>
                  <SelectItem value="high">Cao</SelectItem>
                  <SelectItem value="urgent">Khẩn cấp (chặn công việc)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="ticket-subject">Tiêu đề</Label>
              <Input
                id="ticket-subject"
                placeholder="VD: Không import được file CSV tuần 12"
                className="rounded-lg"
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="ticket-body">Mô tả chi tiết</Label>
              <Textarea
                id="ticket-body"
                className="min-h-28 rounded-lg"
                placeholder="Mô tả các bước bạn đã làm, kết quả mong đợi và kết quả thực tế..."
              />
            </div>
            <Button className="rounded-lg">
              <MessageCircle className="size-4" />
              Gửi yêu cầu
            </Button>
            <p className="text-xs text-muted-foreground">
              Bằng việc gửi, bạn đồng ý đội hỗ trợ có thể truy cập log phiên làm việc của bạn để xử lý sự cố.
            </p>
          </CardContent>
        </Card>

        {/* Shortcuts */}
        <Card className="rounded-2xl border-border/60">
          <CardHeader>
            <CardTitle>Phím tắt</CardTitle>
            <CardDescription>Tăng tốc thao tác hằng ngày.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-1">
            {shortcuts.map((s) => (
              <div
                key={s.label}
                className="flex items-center justify-between rounded-lg px-2 py-1.5 hover:bg-muted/50"
              >
                <span className="text-sm">{s.label}</span>
                <div className="flex items-center gap-1">
                  {s.keys.map((k) => (
                    <Kbd key={k}>{k}</Kbd>
                  ))}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Trust */}
        <div className="rounded-2xl border border-border/60 bg-muted/30 p-4">
          <div className="flex items-center gap-2 text-sm font-medium">
            <CheckCircle2 className="size-4 text-emerald-600 dark:text-emerald-400" />
            Cam kết hỗ trợ
          </div>
          <ul className="mt-2 grid gap-1.5 text-sm text-muted-foreground">
            <li>&middot; Phản hồi đầu tiên &lt; 2 giờ làm việc</li>
            <li>&middot; Khắc phục lỗi nghiêm trọng &lt; 24 giờ</li>
            <li>&middot; Đội ngũ tại Việt Nam, hỗ trợ tiếng Việt</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
