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
} from "lucide-react";
import { toast } from "sonner";
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
import { useTheme } from "next-themes";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
    AdvisorProfileUpdateSchema,
    type AdvisorProfileUpdate,
    fetchAdvisorProfile,
    updateAdvisorProfile,
} from "@/lib/api";
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import { Skeleton } from "@/components/ui/skeleton";

const integrations = [
    {
        name: "Google Calendar",
        description: "Đồng bộ lịch hẹn",
        connected: true,
        logo: "/logos/google-calendar.png",
    },
    {
        name: "Zalo OA",
        description: "Nhắc qua Zalo",
        connected: false,
        logo: "/logos/zalo.png",
    },
];

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

    const { theme, setTheme } = useTheme();
    const [mounted, setMounted] = React.useState(false);
    const [lang, setLang] = React.useState("vi");
    const [motion, setMotion] = React.useState(true);

    React.useEffect(() => {
        setMounted(true);
    }, []);

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
    
    const queryClient = useQueryClient();
    const { data: profile, isLoading: isProfileLoading } = useQuery({
        queryKey: ["advisor-profile"],
        queryFn: fetchAdvisorProfile,
    });

    const updateProfileMutation = useMutation({
        mutationFn: updateAdvisorProfile,
        onSuccess: () => {
            toast.success("Thành công", {
                description: "Đã cập nhật hồ sơ cố vấn.",
            });
            queryClient.invalidateQueries({ queryKey: ["advisor-profile"] });
        },
        onError: (err: any) => {
            toast.error("Lỗi", {
                description: err.message || "Không thể cập nhật hồ sơ.",
            });
        },
    });

    const form = useForm<AdvisorProfileUpdate>({
        resolver: zodResolver(AdvisorProfileUpdateSchema),
        defaultValues: {
            name: "",
            title: "",
            phone: "",
            faculty: "cntt",
            office: "",
            bio: "",
        },
    });

    React.useEffect(() => {
        if (profile) {
            form.reset({
                name: profile.name || "",
                title: profile.title || "",
                phone: profile.phone || "",
                faculty: profile.faculty || "cntt",
                office: profile.office || "",
                bio: profile.bio || "",
            });
        }
    }, [profile, form]);

    const onSubmit = (values: AdvisorProfileUpdate) => {
        updateProfileMutation.mutate(values);
    };

    React.useEffect(() => {
        if (!dataset) return;
        try {
            const stats = reclassifyStudentsAndStats(dataset.students);

            // Only write back to dataset if any of the aggregated stats actually changed.
            // This prevents an update loop where setDataset -> dataset changes -> effect runs again.
            const hasChanged =
                stats.totalStudents !== dataset.totalStudents ||
                stats.totalTests !== dataset.totalTests ||
                Math.abs(
                    (stats.averageScore || 0) - (dataset.averageScore || 0),
                ) > 1e-6 ||
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
                        {isProfileLoading ? (
                            <div className="space-y-4">
                                <Skeleton className="h-10 w-full" />
                                <Skeleton className="h-10 w-full" />
                                <Skeleton className="h-10 w-full" />
                            </div>
                        ) : (
                        <Form {...form}>
                            <form id="settings-profile-form" onSubmit={form.handleSubmit(onSubmit)} className="grid gap-5">
                                <div className="flex items-center gap-4">
                                    <div className="grid size-20 place-items-center rounded-2xl bg-primary/10 text-primary text-2xl font-semibold ring-2 ring-primary/20">
                                        {profile?.name ? profile.name.slice(0,2).toUpperCase() : "AD"}
                                    </div>
                                    <div className="flex flex-col gap-1.5">
                                        <Button
                                            type="button"
                                            variant="outline"
                                            size="sm"
                                            className="rounded-lg"
                                            onClick={() => toast.info("Đang phát triển", { description: "Tính năng tải ảnh đang được cập nhật." })}
                                        >
                                            <Upload className="size-4" />
                                            Tải ảnh
                                        </Button>
                                        <p className="font-mono text-[11px] text-muted-foreground">
                                            PNG · JPG · 2MB
                                        </p>
                                    </div>
                                </div>

                                <div className="grid gap-4 md:grid-cols-2">
                                    <FormField
                                        control={form.control}
                                        name="name"
                                        render={({ field }) => (
                                            <FormItem className="grid gap-1.5">
                                                <FormLabel>Họ và tên</FormLabel>
                                                <FormControl>
                                                    <Input {...field} value={field.value || ""} className="rounded-lg" />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                    <FormField
                                        control={form.control}
                                        name="title"
                                        render={({ field }) => (
                                            <FormItem className="grid gap-1.5">
                                                <FormLabel>Chức danh</FormLabel>
                                                <FormControl>
                                                    <Input {...field} value={field.value || ""} className="rounded-lg" />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                    <div className="grid gap-1.5">
                                        <Label htmlFor="email">Email trường</Label>
                                        <Input
                                            id="email"
                                            type="email"
                                            value={profile?.email || ""}
                                            disabled
                                            className="rounded-lg bg-muted/50"
                                        />
                                    </div>
                                    <FormField
                                        control={form.control}
                                        name="phone"
                                        render={({ field }) => (
                                            <FormItem className="grid gap-1.5">
                                                <FormLabel>Số điện thoại</FormLabel>
                                                <FormControl>
                                                    <Input {...field} value={field.value || ""} className="rounded-lg" />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                    <FormField
                                        control={form.control}
                                        name="faculty"
                                        render={({ field }) => (
                                            <FormItem className="grid gap-1.5">
                                                <FormLabel>Khoa</FormLabel>
                                                <Select onValueChange={field.onChange} value={field.value || "cntt"}>
                                                    <FormControl>
                                                        <SelectTrigger className="rounded-lg">
                                                            <SelectValue placeholder="Chọn khoa" />
                                                        </SelectTrigger>
                                                    </FormControl>
                                                    <SelectContent>
                                                        <SelectItem value="cntt">Công nghệ thông tin</SelectItem>
                                                        <SelectItem value="ktpm">Kỹ thuật phần mềm</SelectItem>
                                                        <SelectItem value="httt">Hệ thống thông tin</SelectItem>
                                                        <SelectItem value="attt">An toàn thông tin</SelectItem>
                                                    </SelectContent>
                                                </Select>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                    <FormField
                                        control={form.control}
                                        name="office"
                                        render={({ field }) => (
                                            <FormItem className="grid gap-1.5">
                                                <FormLabel>Phòng làm việc</FormLabel>
                                                <FormControl>
                                                    <Input {...field} value={field.value || ""} className="rounded-lg" />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />
                                </div>

                                <FormField
                                    control={form.control}
                                    name="bio"
                                    render={({ field }) => (
                                        <FormItem className="grid gap-1.5">
                                            <div className="flex items-center justify-between">
                                                <FormLabel>Giới thiệu</FormLabel>
                                                <span className="font-mono text-[11px] text-muted-foreground">
                                                    ≤ 280
                                                </span>
                                            </div>
                                            <FormControl>
                                                <Textarea {...field} value={field.value || ""} className="min-h-24 rounded-lg" />
                                            </FormControl>
                                            <FormMessage />
                                        </FormItem>
                                    )}
                                />
                            </form>
                        </Form>
                        )}
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
                                    <SelectItem value="formal">
                                        Trang trọng
                                    </SelectItem>
                                    <SelectItem value="direct">
                                        Thẳng thắn
                                    </SelectItem>
                                    <SelectItem value="motivational">
                                        Truyền cảm hứng
                                    </SelectItem>
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
                        <Button
                            variant="outline"
                            size="sm"
                            className="mt-1 rounded-lg"
                        >
                            Thêm quy tắc tuỳ chỉnh
                        </Button>
                    </CardContent>
                </Card>
            </TabsContent>

            {/* Integrations */}
            <TabsContent
                value="integrations"
                className="grid gap-4 md:grid-cols-2"
            >
                {integrations.map((it) => (
                    <Card
                        key={it.name}
                        className="rounded-2xl border-border/60"
                    >
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
                                        <Badge
                                            variant="outline"
                                            className="rounded-md"
                                        >
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
                                        <Button
                                            size="sm"
                                            className="rounded-lg"
                                        >
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
                                    <p className="text-sm font-medium">
                                        Mật khẩu
                                    </p>
                                    <p className="text-xs text-muted-foreground">
                                        Cập nhật lần cuối: 18/03/2026
                                    </p>
                                </div>
                            </div>
                            <Button
                                variant="outline"
                                size="sm"
                                className="rounded-lg"
                            >
                                Đổi mật khẩu
                            </Button>
                        </div>
                        <div className="flex items-center justify-between rounded-xl border border-border/60 bg-muted/30 px-4 py-3">
                            <div className="flex items-center gap-3">
                                <div className="grid size-10 place-items-center rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                                    <ShieldCheck className="size-4" />
                                </div>
                                <div>
                                    <p className="text-sm font-medium">
                                        Xác thực 2 lớp
                                    </p>
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
                                            <p className="text-sm font-medium">
                                                {s.device}
                                            </p>
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
                        <Button
                            variant="outline"
                            size="sm"
                            className="rounded-lg w-fit"
                        >
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
                                    { id: "light", label: "Sáng", icon: Sun },
                                    { id: "dark", label: "Tối", icon: Moon },
                                    {
                                        id: "system",
                                        label: "Hệ thống",
                                        icon: Monitor,
                                    },
                                ].map((t) => {
                                    const isActive = mounted && theme === t.id;
                                    return (
                                        <button
                                            key={t.id}
                                            onClick={() => setTheme(t.id)}
                                            className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-left transition-colors ${
                                                isActive
                                                    ? "border-primary/60 bg-primary/5 ring-2 ring-primary/20"
                                                    : "border-border/60 hover:border-border hover:bg-muted/40"
                                            }`}
                                        >
                                            <div className="grid size-9 place-items-center rounded-lg bg-muted">
                                                <t.icon className="size-4" />
                                            </div>
                                            <span className="text-sm font-medium">
                                                {t.label}
                                            </span>
                                            {isActive && (
                                                <Check className="ml-auto size-4 text-primary" />
                                            )}
                                        </button>
                                    );
                                })}
                            </div>
                        </div>

                        <Separator />

                        <div className="grid gap-4">
                            <div className="grid gap-1.5">
                                <Label htmlFor="lang">Ngôn ngữ</Label>
                                <Select value={lang} onValueChange={setLang}>
                                    <SelectTrigger
                                        id="lang"
                                        className="rounded-lg"
                                    >
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="vi">
                                            Tiếng Việt
                                        </SelectItem>
                                        <SelectItem value="en">
                                            English
                                        </SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        <div className="flex items-center justify-between rounded-xl border border-border/60 bg-muted/30 px-4 py-3">
                            <p className="text-sm font-medium">
                                Hiệu ứng chuyển động
                            </p>
                            <Switch
                                checked={motion}
                                onCheckedChange={setMotion}
                            />
                        </div>
                    </CardContent>
                </Card>
            </TabsContent>
        </Tabs>
    );
}
