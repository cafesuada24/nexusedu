"use client"

import * as React from "react"
import Image from "next/image"
import {
  User,
  Bell,
  Sparkles,
  Plug,
  ShieldCheck,
  Palette,
  Check,
  Mail,
  MessageSquare,
  Smartphone,
  Upload,
  KeyRound,
  Monitor,
  Sun,
  Moon,
} from "lucide-react"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { Slider } from "@/components/ui/slider"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ScheduleEditorSheet } from "@/components/dashboard/schedule-editor-sheet"
import { useSchedule } from "@/hooks/use-schedule"
import { summarizeWeek, type DayKey } from "@/lib/schedule"

const integrations = [
  {
    name: "Google Calendar",
    description: "Đồng bộ lịch hẹn 1-1 và auto-block khung giờ bận.",
    connected: true,
    logo: "/logos/google-calendar.png",
  },
  {
    name: "Microsoft Teams",
    description: "Tạo link meeting tự động khi sinh viên đặt lịch.",
    connected: true,
    logo: "/logos/ms-teams.png",
  },
  {
    name: "Zalo OA",
    description: "Gửi nhắc nhở qua Zalo cho sinh viên không mở email.",
    connected: false,
    logo: "/logos/zalo.png",
  },
  {
    name: "LMS Moodle",
    description: "Tự động nhập điểm & hoạt động mỗi 30 phút.",
    connected: true,
    logo: "/logos/moodle.png",
  },
]

const sessions = [
  { device: "MacBook Pro · Chrome", location: "Hà Nội, VN", current: true, lastActive: "Hoạt động" },
  { device: "iPhone 15 · Safari", location: "Hà Nội, VN", current: false, lastActive: "2 giờ trước" },
  { device: "iPad · Safari", location: "Đà Nẵng, VN", current: false, lastActive: "4 ngày trước" },
]

export function SettingsView() {
  const [riskThreshold, setRiskThreshold] = React.useState([70])
  const [tone, setTone] = React.useState("warm")
  const { schedule, setSchedule } = useSchedule()
  const weekSummary = React.useMemo(
    () => summarizeWeek(schedule.week),
    [schedule.week],
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

  return (
    <Tabs defaultValue="profile" className="gap-6">
      <TabsList className="h-auto w-full justify-start gap-1 overflow-x-auto rounded-xl border border-border/60 bg-muted/40 p-1">
        <TabsTrigger value="profile" className="gap-2 rounded-lg data-[state=active]:bg-card data-[state=active]:shadow-sm">
          <User className="size-4" /> Hồ sơ
        </TabsTrigger>
        <TabsTrigger value="notifications" className="gap-2 rounded-lg data-[state=active]:bg-card data-[state=active]:shadow-sm">
          <Bell className="size-4" /> Thông báo
        </TabsTrigger>
        <TabsTrigger value="ai" className="gap-2 rounded-lg data-[state=active]:bg-card data-[state=active]:shadow-sm">
          <Sparkles className="size-4" /> Quy tắc AI
        </TabsTrigger>
        <TabsTrigger value="integrations" className="gap-2 rounded-lg data-[state=active]:bg-card data-[state=active]:shadow-sm">
          <Plug className="size-4" /> Tích hợp
        </TabsTrigger>
        <TabsTrigger value="security" className="gap-2 rounded-lg data-[state=active]:bg-card data-[state=active]:shadow-sm">
          <ShieldCheck className="size-4" /> Bảo mật
        </TabsTrigger>
        <TabsTrigger value="appearance" className="gap-2 rounded-lg data-[state=active]:bg-card data-[state=active]:shadow-sm">
          <Palette className="size-4" /> Giao diện
        </TabsTrigger>
      </TabsList>

      {/* Profile */}
      <TabsContent value="profile" className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2 rounded-2xl border-border/60">
          <CardHeader>
            <CardTitle>Thông tin cố vấn</CardTitle>
            <CardDescription>
              Thông tin này xuất hiện trong email gửi sinh viên và trang đặt lịch công khai.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-5">
            <div className="flex items-center gap-4">
              <div className="grid size-20 place-items-center rounded-2xl bg-primary/10 text-primary text-2xl font-semibold ring-2 ring-primary/20">
                LH
              </div>
              <div className="flex flex-col gap-2">
                <Button variant="outline" size="sm" className="rounded-lg">
                  <Upload className="size-4" />
                  Tải ảnh lên
                </Button>
                <p className="text-xs text-muted-foreground">PNG, JPG tối đa 2MB</p>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="grid gap-1.5">
                <Label htmlFor="full-name">Họ và tên</Label>
                <Input id="full-name" defaultValue="TS. Lê Thị Hà" className="rounded-lg" />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="title">Chức danh</Label>
                <Input id="title" defaultValue="Giảng viên chính · Cố vấn học tập" className="rounded-lg" />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="email">Email trường</Label>
                <Input id="email" type="email" defaultValue="ha.le@nexusedu.edu.vn" className="rounded-lg" />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="phone">Số điện thoại</Label>
                <Input id="phone" defaultValue="+84 912 345 678" className="rounded-lg" />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="faculty">Khoa</Label>
                <Select defaultValue="cntt">
                  <SelectTrigger id="faculty" className="rounded-lg">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="cntt">Công nghệ thông tin</SelectItem>
                    <SelectItem value="ktpm">Kỹ thuật phần mềm</SelectItem>
                    <SelectItem value="httt">Hệ thống thông tin</SelectItem>
                    <SelectItem value="attt">An toàn thông tin</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="office">Phòng làm việc</Label>
                <Input id="office" defaultValue="A2-312 · Toà A2" className="rounded-lg" />
              </div>
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="bio">Giới thiệu ngắn</Label>
              <Textarea
                id="bio"
                className="min-h-24 rounded-lg"
                defaultValue="Quan tâm đến AI ứng dụng trong giáo dục. Sẵn sàng hỗ trợ sinh viên về định hướng nghề nghiệp, kỹ năng lập trình và nghiên cứu khoa học."
              />
              <p className="text-xs text-muted-foreground">
                Hiển thị trên trang đặt lịch công khai. Tối đa 280 ký tự.
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-2xl border-border/60">
          <CardHeader>
            <CardTitle>Giờ làm việc</CardTitle>
            <CardDescription>
              Khung giờ sinh viên có thể đặt lịch 1-1 với bạn.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 text-sm">
            {weekSummary.map((group) => (
              <div
                key={group.keys.join("-")}
                className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/30 px-3 py-2.5"
              >
                <div>
                  <p className="font-medium">{group.label}</p>
                  <p className="text-xs text-muted-foreground">{group.hours}</p>
                </div>
                <Switch
                  checked={group.enabled}
                  onCheckedChange={(v) => toggleGroup(group.keys, v)}
                />
              </div>
            ))}
            <ScheduleEditorSheet />
          </CardContent>
        </Card>
      </TabsContent>

      {/* Notifications */}
      <TabsContent value="notifications" className="grid gap-6">
        <Card className="rounded-2xl border-border/60">
          <CardHeader>
            <CardTitle>Kênh nhận thông báo</CardTitle>
            <CardDescription>
              Chọn cách bạn muốn được báo khi có sinh viên rơi vào vùng nguy cơ.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-1">
            {[
              {
                icon: Mail,
                label: "Email",
                detail: "ha.le@nexusedu.edu.vn",
                on: true,
              },
              {
                icon: Smartphone,
                label: "Push trên điện thoại",
                detail: "iPhone 15 · NexusEdu Mobile",
                on: true,
              },
              {
                icon: MessageSquare,
                label: "Tin nhắn Zalo",
                detail: "Kết nối qua Zalo OA của nhà trường",
                on: false,
              },
            ].map((c) => (
              <div
                key={c.label}
                className="flex items-center justify-between rounded-xl px-3 py-3 hover:bg-muted/40"
              >
                <div className="flex items-center gap-3">
                  <div className="grid size-10 place-items-center rounded-lg bg-primary/10 text-primary">
                    <c.icon className="size-4" />
                  </div>
                  <div>
                    <p className="text-sm font-medium">{c.label}</p>
                    <p className="text-xs text-muted-foreground">{c.detail}</p>
                  </div>
                </div>
                <Switch defaultChecked={c.on} />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="rounded-2xl border-border/60">
          <CardHeader>
            <CardTitle>Loại sự kiện</CardTitle>
            <CardDescription>
              Bạn sẽ chỉ nhận những loại thông báo được bật bên dưới.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-1">
            {[
              { label: "Sinh viên mới vào vùng Nguy cơ cao", level: "Tức thì", on: true },
              { label: "Sinh viên Nguy cơ trung bình 3 tuần liên tiếp", level: "Hằng ngày", on: true },
              { label: "Email đã gửi nhưng sinh viên chưa mở sau 48h", level: "Hằng ngày", on: true },
              { label: "Sinh viên đặt / huỷ lịch hẹn", level: "Tức thì", on: true },
              { label: "Báo cáo tổng hợp tuần", level: "Thứ Hai, 08:00", on: true },
              { label: "Cập nhật phiên bản hệ thống", level: "Khi có bản mới", on: false },
            ].map((e) => (
              <div
                key={e.label}
                className="flex items-center justify-between rounded-xl px-3 py-2.5 hover:bg-muted/40"
              >
                <div>
                  <p className="text-sm font-medium">{e.label}</p>
                  <p className="text-xs text-muted-foreground">{e.level}</p>
                </div>
                <Switch defaultChecked={e.on} />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="rounded-2xl border-border/60">
          <CardHeader>
            <CardTitle>Giờ yên tĩnh</CardTitle>
            <CardDescription>
              Không gửi push / SMS trong khoảng thời gian này.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-3">
            <div className="grid gap-1.5">
              <Label htmlFor="quiet-from">Từ</Label>
              <Input id="quiet-from" type="time" defaultValue="21:00" className="rounded-lg" />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="quiet-to">Đến</Label>
              <Input id="quiet-to" type="time" defaultValue="07:00" className="rounded-lg" />
            </div>
            <div className="flex items-end">
              <div className="flex w-full items-center justify-between rounded-lg border border-border/60 bg-muted/30 px-3 py-2.5">
                <Label htmlFor="quiet-weekend" className="text-sm">
                  Tắt cả cuối tuần
                </Label>
                <Switch id="quiet-weekend" />
              </div>
            </div>
          </CardContent>
        </Card>
      </TabsContent>

      {/* AI */}
      <TabsContent value="ai" className="grid gap-6 lg:grid-cols-3">
        <Card className="rounded-2xl border-border/60 lg:col-span-2">
          <CardHeader>
            <CardTitle>Ngưỡng cảnh báo</CardTitle>
            <CardDescription>
              Điểm rủi ro vượt ngưỡng sẽ tự động tạo alert trong Alert Center.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-6">
            <div className="grid gap-3">
              <div className="flex items-center justify-between">
                <Label>Ngưỡng &ldquo;Nguy cơ cao&rdquo;</Label>
                <Badge className="rounded-md bg-primary/15 text-primary hover:bg-primary/20">
                  {riskThreshold[0]} điểm
                </Badge>
              </div>
              <Slider
                value={riskThreshold}
                onValueChange={setRiskThreshold}
                min={40}
                max={95}
                step={1}
                className="py-2"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>Nhạy hơn (nhiều alert)</span>
                <span>Chặt hơn (ít alert)</span>
              </div>
            </div>

            <Separator />

            <div className="grid gap-1.5">
              <Label htmlFor="tone">Giọng văn email AI gợi ý</Label>
              <Select value={tone} onValueChange={setTone}>
                <SelectTrigger id="tone" className="rounded-lg">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="warm">Ấm áp, gần gũi</SelectItem>
                  <SelectItem value="formal">Trang trọng, học thuật</SelectItem>
                  <SelectItem value="direct">Thẳng thắn, ngắn gọn</SelectItem>
                  <SelectItem value="motivational">Truyền cảm hứng</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Áp dụng mặc định cho mọi email AI sinh. Bạn vẫn có thể đổi giọng văn tại từng email.
              </p>
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="signature">Chữ ký chèn cuối email</Label>
              <Textarea
                id="signature"
                className="min-h-24 rounded-lg font-mono text-xs"
                defaultValue={`Thân mến,\nTS. Lê Thị Hà\nKhoa CNTT · NexusEdu University\n+84 912 345 678`}
              />
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-2xl border-border/60">
          <CardHeader>
            <CardTitle>Quy tắc an toàn</CardTitle>
            <CardDescription>Các quy tắc AI luôn tuân thủ khi soạn email.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 text-sm">
            {[
              "Không tiết lộ điểm số của sinh viên khác",
              "Luôn gọi sinh viên theo đúng tên và đại từ đã khai báo",
              "Không dùng ngôn ngữ đe doạ hay phán xét",
              "Luôn đề xuất ít nhất 1 hành động cụ thể sinh viên có thể làm",
              "Luôn kèm link đặt lịch 1-1 nếu mức rủi ro > trung bình",
              "Không gửi quá 2 email/tuần cho cùng một sinh viên",
            ].map((r, i) => (
              <div key={i} className="flex items-start gap-2.5">
                <div className="mt-0.5 grid size-5 shrink-0 place-items-center rounded-md bg-emerald-500/15 text-emerald-600 dark:text-emerald-400">
                  <Check className="size-3" />
                </div>
                <p className="leading-relaxed">{r}</p>
              </div>
            ))}
            <Button variant="outline" size="sm" className="mt-1 rounded-lg">
              Thêm quy tắc tuỳ chỉnh
            </Button>
          </CardContent>
        </Card>
      </TabsContent>

      {/* Integrations */}
      <TabsContent value="integrations" className="grid gap-4 md:grid-cols-2">
        {integrations.map((it) => (
          <Card key={it.name} className="rounded-2xl border-border/60">
            <CardContent className="flex items-start gap-4 p-5">
              <div className="grid size-12 shrink-0 place-items-center overflow-hidden rounded-xl bg-muted ring-1 ring-border/60">
                <Image
                  src={it.logo || "/placeholder.svg"}
                  alt=""
                  width={32}
                  height={32}
                  className="size-8 object-contain"
                />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold">{it.name}</h3>
                  {it.connected ? (
                    <Badge className="rounded-md bg-emerald-500/15 text-emerald-600 hover:bg-emerald-500/20 dark:text-emerald-400">
                      <Check className="size-3" />
                      Đã kết nối
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="rounded-md">
                      Chưa kết nối
                    </Badge>
                  )}
                </div>
                <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                  {it.description}
                </p>
                <div className="mt-3 flex gap-2">
                  {it.connected ? (
                    <>
                      <Button variant="outline" size="sm" className="rounded-lg">
                        Cấu hình
                      </Button>
                      <Button variant="ghost" size="sm" className="rounded-lg text-destructive hover:text-destructive">
                        Ngắt kết nối
                      </Button>
                    </>
                  ) : (
                    <Button size="sm" className="rounded-lg">
                      Kết nối
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </TabsContent>

      {/* Security */}
      <TabsContent value="security" className="grid gap-6">
        <Card className="rounded-2xl border-border/60">
          <CardHeader>
            <CardTitle>Mật khẩu &amp; xác thực hai lớp</CardTitle>
            <CardDescription>
              Bảo vệ tài khoản với mật khẩu mạnh và 2FA.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-5">
            <div className="flex items-center justify-between rounded-xl border border-border/60 bg-muted/30 px-4 py-3">
              <div className="flex items-center gap-3">
                <div className="grid size-10 place-items-center rounded-lg bg-primary/10 text-primary">
                  <KeyRound className="size-4" />
                </div>
                <div>
                  <p className="text-sm font-medium">Mật khẩu</p>
                  <p className="text-xs text-muted-foreground">
                    Cập nhật lần cuối: 18/03/2026
                  </p>
                </div>
              </div>
              <Button variant="outline" size="sm" className="rounded-lg">
                Đổi mật khẩu
              </Button>
            </div>
            <div className="flex items-center justify-between rounded-xl border border-border/60 bg-muted/30 px-4 py-3">
              <div className="flex items-center gap-3">
                <div className="grid size-10 place-items-center rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                  <ShieldCheck className="size-4" />
                </div>
                <div>
                  <p className="text-sm font-medium">Xác thực 2 lớp</p>
                  <p className="text-xs text-muted-foreground">
                    Bật qua ứng dụng Authenticator
                  </p>
                </div>
              </div>
              <Switch defaultChecked />
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-2xl border-border/60">
          <CardHeader>
            <CardTitle>Phiên đăng nhập đang hoạt động</CardTitle>
            <CardDescription>
              Danh sách thiết bị đang truy cập tài khoản của bạn.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-1">
            {sessions.map((s, i) => (
              <div
                key={i}
                className="flex items-center justify-between rounded-xl px-3 py-3 hover:bg-muted/40"
              >
                <div className="flex items-center gap-3">
                  <div className="grid size-10 place-items-center rounded-lg bg-muted">
                    <Monitor className="size-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium">{s.device}</p>
                      {s.current && (
                        <Badge className="rounded-md bg-primary/15 text-primary hover:bg-primary/20">
                          Thiết bị này
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {s.location} &middot; {s.lastActive}
                    </p>
                  </div>
                </div>
                {!s.current && (
                  <Button variant="ghost" size="sm" className="rounded-lg text-destructive hover:text-destructive">
                    Đăng xuất
                  </Button>
                )}
              </div>
            ))}
            <Separator className="my-2" />
            <Button variant="outline" size="sm" className="rounded-lg w-fit">
              Đăng xuất khỏi tất cả thiết bị
            </Button>
          </CardContent>
        </Card>
      </TabsContent>

      {/* Appearance */}
      <TabsContent value="appearance" className="grid gap-6">
        <Card className="rounded-2xl border-border/60">
          <CardHeader>
            <CardTitle>Giao diện</CardTitle>
            <CardDescription>Chọn theme và ngôn ngữ hiển thị.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-6">
            <div className="grid gap-3">
              <Label>Chủ đề</Label>
              <div className="grid gap-3 sm:grid-cols-3">
                {[
                  { id: "light", label: "Sáng", icon: Sun, active: false },
                  { id: "dark", label: "Tối", icon: Moon, active: true },
                  { id: "system", label: "Theo hệ thống", icon: Monitor, active: false },
                ].map((t) => (
                  <button
                    key={t.id}
                    className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-left transition-colors ${
                      t.active
                        ? "border-primary/60 bg-primary/5 ring-2 ring-primary/20"
                        : "border-border/60 hover:border-border hover:bg-muted/40"
                    }`}
                  >
                    <div className="grid size-9 place-items-center rounded-lg bg-muted">
                      <t.icon className="size-4" />
                    </div>
                    <span className="text-sm font-medium">{t.label}</span>
                    {t.active && <Check className="ml-auto size-4 text-primary" />}
                  </button>
                ))}
              </div>
            </div>

            <Separator />

            <div className="grid gap-4 md:grid-cols-2">
              <div className="grid gap-1.5">
                <Label htmlFor="lang">Ngôn ngữ</Label>
                <Select defaultValue="vi">
                  <SelectTrigger id="lang" className="rounded-lg">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="vi">Tiếng Việt</SelectItem>
                    <SelectItem value="en">English</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="density">Mật độ giao diện</Label>
                <Select defaultValue="comfortable">
                  <SelectTrigger id="density" className="rounded-lg">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="comfortable">Thoải mái</SelectItem>
                    <SelectItem value="compact">Nén</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex items-center justify-between rounded-xl border border-border/60 bg-muted/30 px-4 py-3">
              <div>
                <p className="text-sm font-medium">Hiệu ứng chuyển động</p>
                <p className="text-xs text-muted-foreground">
                  Tắt nếu bạn thích giao diện tĩnh hơn.
                </p>
              </div>
              <Switch defaultChecked />
            </div>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  )
}
