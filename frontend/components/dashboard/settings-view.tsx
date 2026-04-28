"use client";

import * as React from "react";
import Image from "next/image";
import {
  User,
  Sparkles,
  Plug,
  ShieldCheck,
  Palette,
  Check,
  Smartphone,
  Upload,
  KeyRound,
  Monitor,
  Sun,
  Moon,
  GraduationCap,
  Pencil,
  X,
  AlertTriangle,
  FileText,
  CalendarClock,
  Search,
  Inbox,
} from "lucide-react";
import { toast } from "@/hooks/use-toast";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useDataset } from "@/hooks/use-dataset";
import { reclassifyStudentsAndStats } from "@/lib/csv";
const integrations = [
  {
    name: "Google Calendar",
    description: "Đồng bộ lịch hẹn",
    connected: true,
    logo: "/logos/google-calendar.png",
  },
  {
    name: "Microsoft Teams",
    description: "Link meeting tự động",
    connected: true,
    logo: "/logos/ms-teams.png",
  },
  {
    name: "Zalo OA",
    description: "Nhắc qua Zalo",
    connected: false,
    logo: "/logos/zalo.png",
  },
  {
    name: "LMS Moodle",
    description: "Đồng bộ điểm 30p",
    connected: true,
    logo: "/logos/moodle.png",
  },
];

type PdRequestType = "intervention" | "escalation" | "schedule" | "template";
type PdRequestStatus = "pending" | "approved" | "rejected";

type PdRequest = {
  id: string;
  title: string;
  type: PdRequestType;
  submitter: string;
  faculty: string;
  submittedAt: string;
  priority: "high" | "medium" | "low";
  summary: string;
  status: PdRequestStatus;
};

const initialPdRequests: PdRequest[] = [
  {
    id: "REQ-2041",
    title: "Can thiệp khẩn cho SV Nguyễn Văn An (B21DCCN012)",
    type: "intervention",
    submitter: "TS. Lê Thị Hà",
    faculty: "Khoa CNTT",
    submittedAt: "2 giờ trước",
    priority: "high",
    summary:
      "Sinh viên vắng 4/6 buổi liên tiếp môn Lập trình Web, điểm rủi ro 87. Đề xuất buổi gặp 1-1 và thông báo phụ huynh.",
    status: "pending",
  },
  {
    id: "REQ-2039",
    title: "Đổi lịch tư vấn nhóm K21 sang chiều thứ 6",
    type: "schedule",
    submitter: "ThS. Trần Minh Đức",
    faculty: "Khoa KTPM",
    submittedAt: "5 giờ trước",
    priority: "medium",
    summary:
      "Trùng lịch giảng môn Cơ sở dữ liệu. Đề xuất chuyển buổi tư vấn từ 9:00 thứ 4 sang 14:00 thứ 6 hàng tuần.",
    status: "pending",
  },
  {
    id: "REQ-2037",
    title: "Mẫu email cảnh báo dropout - bản v3",
    type: "template",
    submitter: "TS. Phạm Thu Hương",
    faculty: "Khoa HTTT",
    submittedAt: "Hôm qua",
    priority: "low",
    summary:
      "Cập nhật giọng văn ấm áp hơn, bổ sung link đặt lịch và cam kết hỗ trợ học tập trong 2 tuần tới.",
    status: "pending",
  },
  {
    id: "REQ-2034",
    title: "Báo cáo escalation - SV nghỉ học không phép 3 tuần",
    type: "escalation",
    submitter: "TS. Nguyễn Hoàng Long",
    faculty: "Khoa ATTT",
    submittedAt: "2 ngày trước",
    priority: "high",
    summary:
      "Sinh viên Đỗ Thanh Bình (B21DCAT089) không phản hồi 6 lần liên hệ. Cần PD can thiệp và thông báo gia đình.",
    status: "pending",
  },
];

const typeMeta: Record<
  PdRequestType,
  { label: string; icon: typeof FileText; tone: string }
> = {
  intervention: {
    label: "Can thiệp",
    icon: AlertTriangle,
    tone: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
  },
  escalation: {
    label: "Báo cáo cấp trên",
    icon: GraduationCap,
    tone: "bg-rose-500/15 text-rose-600 dark:text-rose-400",
  },
  schedule: {
    label: "Lịch tư vấn",
    icon: CalendarClock,
    tone: "bg-sky-500/15 text-sky-600 dark:text-sky-400",
  },
  template: {
    label: "Mẫu email",
    icon: FileText,
    tone: "bg-violet-500/15 text-violet-600 dark:text-violet-400",
  },
};

const priorityMeta: Record<
  PdRequest["priority"],
  { label: string; tone: string }
> = {
  high: {
    label: "Ưu tiên cao",
    tone: "bg-rose-500/15 text-rose-600 dark:text-rose-400",
  },
  medium: {
    label: "Trung bình",
    tone: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
  },
  low: { label: "Thấp", tone: "bg-muted text-muted-foreground" },
};

const sessions = [
  {
    device: "MacBook Pro · Chrome",
    location: "Hà Nội, VN",
    current: true,
    lastActive: "Hoạt động",
  },
  {
    device: "iPhone 15 · Safari",
    location: "Hà Nội, VN",
    current: false,
    lastActive: "2 giờ trước",
  },
  {
    device: "iPad · Safari",
    location: "Đà Nẵng, VN",
    current: false,
    lastActive: "4 ngày trước",
  },
];

export function SettingsView() {
  // Persisted risk threshold (array used by Slider component)
  const [riskThreshold, setRiskThreshold] = React.useState<number[]>(() => {
    try {
      if (typeof window === "undefined") return [70];
      const raw = window.localStorage.getItem("nexusedu:riskThreshold");
      if (!raw) return [70];
      const parsed = JSON.parse(raw);
      // Expect an array of numbers; fall back to [70] on mismatch
      if (
        Array.isArray(parsed) &&
        parsed.length > 0 &&
        typeof parsed[0] === "number"
      ) {
        return parsed as number[];
      }
    } catch {
      // ignore parse errors
    }
    return [70];
  });

  const [tone, setTone] = React.useState("warm");

  // Save to localStorage whenever riskThreshold changes
  React.useEffect(() => {
    try {
      if (typeof window !== "undefined") {
        window.localStorage.setItem(
          "nexusedu:riskThreshold",
          JSON.stringify(riskThreshold),
        );
      }
    } catch {
      // ignore storage errors
    }
  }, [riskThreshold]);

  // Reclassify existing dataset when the risk threshold changes so Alert Center updates.
  const { dataset, setDataset } = useDataset();

  React.useEffect(() => {
    if (!dataset) return;
    try {
      const stats = reclassifyStudentsAndStats(dataset.students);

      // Only write back to dataset if any of the aggregated stats actually changed.
      // This prevents an update loop where setDataset -> dataset changes -> effect runs again.
      const hasChanged =
        stats.totalStudents !== dataset.totalStudents ||
        stats.totalTests !== dataset.totalTests ||
        Math.abs((stats.averageScore || 0) - (dataset.averageScore || 0)) >
          1e-6 ||
        stats.highRisk !== dataset.highRisk ||
        stats.mediumRisk !== dataset.mediumRisk ||
        stats.lowRisk !== dataset.lowRisk ||
        stats.draftEmails !== dataset.draftEmails ||
        // shallow compare problemCounts by keys we care about
        (stats.problemCounts.failed_final || 0) !==
          (dataset.problemCounts?.failed_final || 0) ||
        (stats.problemCounts.failed_midterm || 0) !==
          (dataset.problemCounts?.failed_midterm || 0) ||
        (stats.problemCounts.low_average || 0) !==
          (dataset.problemCounts?.low_average || 0);

      if (hasChanged) {
        setDataset({
          ...dataset,
          students: stats.students,
          totalStudents: stats.totalStudents,
          totalTests: stats.totalTests,
          averageScore: stats.averageScore,
          highRisk: stats.highRisk,
          mediumRisk: stats.mediumRisk,
          lowRisk: stats.lowRisk,
          draftEmails: stats.draftEmails,
          problemCounts: stats.problemCounts,
          yearRisk: stats.yearRisk,
        });
      }
    } catch (e) {
      // swallow to avoid breaking settings UI
      // eslint-disable-next-line no-console
      console.warn("[settings] reclassify failed", e);
    }
  }, [riskThreshold, dataset, setDataset]);

  const [pdRequests, setPdRequests] =
    React.useState<PdRequest[]>(initialPdRequests);
  const [editingRequest, setEditingRequest] = React.useState<PdRequest | null>(
    null,
  );
  const [editDraft, setEditDraft] = React.useState({ title: "", summary: "" });
  const [rejectingRequest, setRejectingRequest] =
    React.useState<PdRequest | null>(null);
  const [pdFilter, setPdFilter] = React.useState<"all" | PdRequestStatus>(
    "pending",
  );
  const [pdSearch, setPdSearch] = React.useState("");

  const pendingCount = pdRequests.filter((r) => r.status === "pending").length;
  const approvedCount = pdRequests.filter(
    (r) => r.status === "approved",
  ).length;
  const rejectedCount = pdRequests.filter(
    (r) => r.status === "rejected",
  ).length;

  const filteredPdRequests = pdRequests.filter((r) => {
    const matchStatus = pdFilter === "all" ? true : r.status === pdFilter;
    const matchSearch =
      pdSearch.trim() === ""
        ? true
        : `${r.title} ${r.summary} ${r.submitter} ${r.faculty} ${r.id}`
            .toLowerCase()
            .includes(pdSearch.toLowerCase());
    return matchStatus && matchSearch;
  });

  const handleApprove = (req: PdRequest) => {
    setPdRequests((prev) =>
      prev.map((r) => (r.id === req.id ? { ...r, status: "approved" } : r)),
    );
    toast({
      title: "Đã phê duyệt",
      description: `${req.id} · ${req.title}`,
    });
  };

  const handleConfirmReject = () => {
    if (!rejectingRequest) return;
    setPdRequests((prev) =>
      prev.map((r) =>
        r.id === rejectingRequest.id ? { ...r, status: "rejected" } : r,
      ),
    );
    toast({
      title: "Đã từ chối",
      description: `${rejectingRequest.id} · ${rejectingRequest.title}`,
      variant: "destructive",
    });
    setRejectingRequest(null);
  };

  const openEdit = (req: PdRequest) => {
    setEditingRequest(req);
    setEditDraft({ title: req.title, summary: req.summary });
  };

  const handleSaveEdit = () => {
    if (!editingRequest) return;
    setPdRequests((prev) =>
      prev.map((r) =>
        r.id === editingRequest.id
          ? { ...r, title: editDraft.title, summary: editDraft.summary }
          : r,
      ),
    );
    toast({
      title: "Đã lưu thay đổi",
      description: `${editingRequest.id} đã được cập nhật.`,
    });
    setEditingRequest(null);
  };

  return (
    <Tabs defaultValue="profile" className="gap-6">
      <TabsList className="h-auto w-full justify-start gap-1 overflow-x-auto rounded-xl border border-border/60 bg-muted/40 p-1">
        <TabsTrigger
          value="profile"
          className="gap-2 rounded-lg data-[state=active]:bg-card data-[state=active]:shadow-sm"
        >
          <User className="size-4" /> Hồ sơ
        </TabsTrigger>

        <TabsTrigger
          value="ai"
          className="gap-2 rounded-lg data-[state=active]:bg-card data-[state=active]:shadow-sm"
        >
          <Sparkles className="size-4" /> Quy tắc AI
        </TabsTrigger>
        <TabsTrigger
          value="integrations"
          className="gap-2 rounded-lg data-[state=active]:bg-card data-[state=active]:shadow-sm"
        >
          <Plug className="size-4" /> Tích hợp
        </TabsTrigger>
        <TabsTrigger
          value="security"
          className="gap-2 rounded-lg data-[state=active]:bg-card data-[state=active]:shadow-sm"
        >
          <ShieldCheck className="size-4" /> Bảo mật
        </TabsTrigger>
        <TabsTrigger
          value="appearance"
          className="gap-2 rounded-lg data-[state=active]:bg-card data-[state=active]:shadow-sm"
        >
          <Palette className="size-4" /> Giao diện
        </TabsTrigger>
        <TabsTrigger
          value="pd"
          className="gap-2 rounded-lg data-[state=active]:bg-card data-[state=active]:shadow-sm"
        >
          <GraduationCap className="size-4" /> Phòng Đào tạo
          {pendingCount > 0 && (
            <Badge className="ml-1 rounded-md bg-primary/15 text-primary hover:bg-primary/20">
              {pendingCount}
            </Badge>
          )}
        </TabsTrigger>
      </TabsList>

      {/* Profile */}
      <TabsContent value="profile" className="grid gap-6">
        <Card className="stripe-sky rounded-2xl border-accent-sky/15 bg-gradient-to-br from-accent-sky/22 via-accent-sky/10 to-card">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2">
              <User className="size-4 text-primary" />
              Thông tin cố vấn
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-5">
            <div className="flex items-center gap-4">
              <div className="grid size-20 place-items-center rounded-2xl bg-primary/10 text-primary text-2xl font-semibold ring-2 ring-primary/20">
                LH
              </div>
              <div className="flex flex-col gap-1.5">
                <Button variant="outline" size="sm" className="rounded-lg">
                  <Upload className="size-4" />
                  Tải ảnh
                </Button>
                <p className="font-mono text-[11px] text-muted-foreground">
                  PNG · JPG · 2MB
                </p>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="grid gap-1.5">
                <Label htmlFor="full-name">Họ và tên</Label>
                <Input
                  id="full-name"
                  defaultValue="TS. Lê Thị Hà"
                  className="rounded-lg"
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="title">Chức danh</Label>
                <Input
                  id="title"
                  defaultValue="Giảng viên chính · Cố vấn học tập"
                  className="rounded-lg"
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="email">Email trường</Label>
                <Input
                  id="email"
                  type="email"
                  defaultValue="ha.le@nexusedu.edu.vn"
                  className="rounded-lg"
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="phone">Số điện thoại</Label>
                <Input
                  id="phone"
                  defaultValue="+84 912 345 678"
                  className="rounded-lg"
                />
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
                <Input
                  id="office"
                  defaultValue="A2-312 · Toà A2"
                  className="rounded-lg"
                />
              </div>
            </div>

            <div className="grid gap-1.5">
              <div className="flex items-center justify-between">
                <Label htmlFor="bio">Giới thiệu</Label>
                <span className="font-mono text-[11px] text-muted-foreground">
                  ≤ 280
                </span>
              </div>
              <Textarea
                id="bio"
                className="min-h-24 rounded-lg"
                defaultValue="Quan tâm đến AI ứng dụng trong giáo dục. Sẵn sàng hỗ trợ sinh viên về định hướng nghề nghiệp, kỹ năng lập trình và nghiên cứu khoa học."
              />
            </div>
          </CardContent>
        </Card>
      </TabsContent>

      {/* AI */}
      <TabsContent value="ai" className="grid gap-6 lg:grid-cols-3">
        <Card className="stripe-primary rounded-2xl border-primary/15 bg-gradient-to-br from-primary/18 via-primary/8 to-card lg:col-span-2">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="size-4 text-primary" />
              Ngưỡng cảnh báo
            </CardTitle>
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
              <Label htmlFor="tone">Giọng văn AI</Label>
              <Select value={tone} onValueChange={setTone}>
                <SelectTrigger id="tone" className="rounded-lg">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="warm">Ấm áp</SelectItem>
                  <SelectItem value="formal">Trang trọng</SelectItem>
                  <SelectItem value="direct">Thẳng thắn</SelectItem>
                  <SelectItem value="motivational">Truyền cảm hứng</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="signature">Chữ ký</Label>
              <Textarea
                id="signature"
                className="min-h-24 rounded-lg font-mono text-xs"
                defaultValue={`Thân mến,\nTS. Lê Thị Hà\nKhoa CNTT · NexusEdu University\n+84 912 345 678`}
              />
            </div>
          </CardContent>
        </Card>

        <Card className="stripe-success rounded-2xl border-success/15 bg-gradient-to-br from-success/18 via-success/8 to-card">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="size-4 text-success" />
              Quy tắc an toàn
            </CardTitle>
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
                      <Button
                        variant="outline"
                        size="sm"
                        className="rounded-lg"
                      >
                        Cấu hình
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="rounded-lg text-destructive hover:text-destructive"
                      >
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
        <Card className="stripe-success rounded-2xl border-success/15 bg-gradient-to-br from-success/18 via-success/8 to-card">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="size-4 text-success" />
              Mật khẩu &amp; 2FA
            </CardTitle>
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

        <Card className="stripe-primary rounded-2xl border-primary/15 bg-gradient-to-br from-primary/18 via-primary/8 to-card">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2">
              <Monitor className="size-4 text-primary" />
              Phiên đăng nhập
            </CardTitle>
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
                  <Button
                    variant="ghost"
                    size="sm"
                    className="rounded-lg text-destructive hover:text-destructive"
                  >
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
        <Card className="stripe-indigo rounded-2xl border-accent-indigo/15 bg-gradient-to-br from-accent-indigo/22 via-accent-indigo/10 to-card">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2">
              <Palette className="size-4 text-primary" />
              Giao diện
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-6">
            <div className="grid gap-3">
              <Label>Chủ đề</Label>
              <div className="grid gap-3 sm:grid-cols-3">
                {[
                  { id: "light", label: "Sáng", icon: Sun, active: false },
                  { id: "dark", label: "Tối", icon: Moon, active: true },
                  {
                    id: "system",
                    label: "Hệ thống",
                    icon: Monitor,
                    active: false,
                  },
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
                    {t.active && (
                      <Check className="ml-auto size-4 text-primary" />
                    )}
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
                <Label htmlFor="density">Mật độ</Label>
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
              <p className="text-sm font-medium">Hiệu ứng chuyển động</p>
              <Switch defaultChecked />
            </div>
          </CardContent>
        </Card>
      </TabsContent>

      {/* Phòng Đào tạo */}
      <TabsContent value="pd" className="grid gap-4">
        {/* Toolbar: filter + search */}
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-wrap gap-2">
            {[
              {
                key: "pending" as const,
                label: "Chờ duyệt",
                count: pendingCount,
              },
              {
                key: "approved" as const,
                label: "Đã đồng ý",
                count: approvedCount,
              },
              {
                key: "rejected" as const,
                label: "Đã từ chối",
                count: rejectedCount,
              },
            ].map((f) => (
              <Button
                key={f.key}
                type="button"
                variant={pdFilter === f.key ? "default" : "outline"}
                size="sm"
                onClick={() => setPdFilter(f.key)}
                className="h-10 rounded-full px-4"
              >
                {f.label}
                <span
                  className={`ml-1 rounded-full px-1.5 text-xs ${
                    pdFilter === f.key
                      ? "bg-primary-foreground/20"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {f.count}
                </span>
              </Button>
            ))}
          </div>
          <div className="relative w-full md:w-64">
            <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Tìm đề xuất..."
              value={pdSearch}
              onChange={(e) => setPdSearch(e.target.value)}
              className="h-10 rounded-xl pl-9"
            />
          </div>
        </div>

        {/* Danh sách */}
        <div className="grid gap-3">
          {filteredPdRequests.length === 0 && (
            <div className="grid place-items-center gap-2 rounded-2xl border border-dashed border-border/60 bg-muted/30 px-4 py-14 text-center">
              <Inbox className="size-8 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                Chưa có đề xuất nào.
              </p>
            </div>
          )}

          {filteredPdRequests.map((req) => {
            const TypeIcon = typeMeta[req.type].icon;
            const isPending = req.status === "pending";
            return (
              <div
                key={req.id}
                className="flex flex-col gap-4 rounded-2xl border border-border/60 bg-card p-4 md:flex-row md:items-center md:p-5"
              >
                <div
                  className={`grid size-11 shrink-0 place-items-center rounded-xl ${typeMeta[req.type].tone}`}
                  aria-hidden
                >
                  <TypeIcon className="size-5" />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    {req.priority === "high" && isPending && (
                      <Badge className="gap-1 rounded-md bg-rose-500/15 text-xs text-rose-700 hover:bg-rose-500/20 dark:text-rose-400">
                        <AlertTriangle className="size-3" />
                        Khẩn
                      </Badge>
                    )}
                    {req.status === "approved" && (
                      <Badge className="gap-1 rounded-md bg-emerald-500/15 text-xs text-emerald-700 hover:bg-emerald-500/20 dark:text-emerald-400">
                        Đã đồng ý
                      </Badge>
                    )}
                    {req.status === "rejected" && (
                      <Badge className="gap-1 rounded-md bg-rose-500/15 text-xs text-rose-700 hover:bg-rose-500/20 dark:text-rose-400">
                        Đã từ chối
                      </Badge>
                    )}
                  </div>
                  <h4 className="mt-1 font-semibold leading-snug">
                    {req.title}
                  </h4>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {req.submitter} · {req.faculty} · {req.submittedAt}
                  </p>
                </div>

                {isPending ? (
                  <div className="flex gap-2 md:shrink-0">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => openEdit(req)}
                      className="size-10 rounded-xl"
                      aria-label="Sửa"
                    >
                      <Pencil className="size-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => setRejectingRequest(req)}
                      className="size-10 rounded-xl border-rose-200 text-rose-600 hover:bg-rose-50 hover:text-rose-700 dark:border-rose-900/40 dark:text-rose-400 dark:hover:bg-rose-950/40"
                      aria-label="Từ chối"
                    >
                      <X className="size-4" />
                    </Button>
                    <Button
                      onClick={() => handleApprove(req)}
                      className="h-10 rounded-xl bg-emerald-600 px-4 font-semibold text-white hover:bg-emerald-700"
                    >
                      <Check className="size-4" />
                      Đồng ý
                    </Button>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </TabsContent>

      {/* Edit dialog */}
      <Dialog
        open={!!editingRequest}
        onOpenChange={(open) => !open && setEditingRequest(null)}
      >
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Sửa đề xuất</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4">
            <div className="grid gap-1.5">
              <Label htmlFor="edit-title">Tiêu đề</Label>
              <Input
                id="edit-title"
                value={editDraft.title}
                onChange={(e) =>
                  setEditDraft((d) => ({ ...d, title: e.target.value }))
                }
                className="h-10 rounded-lg"
              />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="edit-summary">Nội dung</Label>
              <Textarea
                id="edit-summary"
                value={editDraft.summary}
                onChange={(e) =>
                  setEditDraft((d) => ({ ...d, summary: e.target.value }))
                }
                className="min-h-32 rounded-lg"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingRequest(null)}>
              Huỷ
            </Button>
            <Button onClick={handleSaveEdit}>Lưu</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reject confirmation */}
      <AlertDialog
        open={!!rejectingRequest}
        onOpenChange={(open) => !open && setRejectingRequest(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Từ chối đề xuất?</AlertDialogTitle>
            <p className="text-sm text-muted-foreground">
              {rejectingRequest?.title}
            </p>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Huỷ</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmReject}
              className="bg-rose-600 text-white hover:bg-rose-700"
            >
              Từ chối
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Tabs>
  );
}
