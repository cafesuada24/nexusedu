"use client";

import * as React from "react";
import {
    AlertTriangle,
    Eye,
    Inbox,
    Search,
} from "lucide-react";
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useOpenCases } from "@/hooks/use-alerts";
import { useDataset } from "@/hooks/use-dataset";
import { type TaskItem, type BackendInterventionStatus } from "@/lib/api";
import { type StudentRow, type Problem } from "@/lib/csv";
import { type Alert, getInitials, fromBackendStatus } from "@/lib/alerts";
import { cn } from "@/lib/utils";
import { StudentDetailDrawer } from "@/components/dashboard/alert-center/student-detail-drawer";

const INTERVENTION_LABEL: Record<BackendInterventionStatus, string> = {
    none: "Chưa khởi tạo",
    notified: "Mới",
    sent: "Đã gửi email",
    booked: "Đã đặt hẹn",
    supporting: "Đang hỗ trợ",
    resolved: "Đã giải quyết",
    dismissed: "Đã đóng",
    expired: "Đã hết hạn",
};

const INTERVENTION_TONE: Record<BackendInterventionStatus, string> = {
    none: "bg-muted/40 text-muted-foreground ring-border/60",
    notified: "bg-red-500/10 text-red-600 ring-red-500/20 dark:text-red-300",
    sent: "bg-amber-500/10 text-amber-700 ring-amber-500/25 dark:text-amber-300",
    booked: "bg-green-500/10 text-green-700 ring-green-500/25 dark:text-green-300",
    supporting: "bg-blue-500/10 text-blue-700 ring-blue-500/25 dark:text-blue-300",
    resolved: "bg-emerald-500/10 text-emerald-700 ring-emerald-500/25 dark:text-emerald-300",
    dismissed: "bg-muted/40 text-muted-foreground ring-border/60",
    expired: "bg-muted/40 text-muted-foreground ring-border/60",
};

const RISK_TONE_BY_KEY: Record<string, string> = {
    critical: "bg-destructive/10 text-destructive ring-destructive/20",
    elevated: "bg-warning/15 text-warning ring-warning/25",
    normal: "bg-emerald-500/10 text-emerald-700 ring-emerald-500/25 dark:text-emerald-300",
    unknown: "bg-muted/40 text-muted-foreground ring-border/60",
};

const RISK_LABEL_BY_KEY: Record<string, string> = {
    critical: "Nguy cấp",
    elevated: "Tăng cao",
    normal: "Bình thường",
    unknown: "Chưa rõ",
};

function riskKey(value: string): "critical" | "elevated" | "normal" | "unknown" {
    const v = value.toLowerCase();
    if (v.includes("critical")) return "critical";
    if (v.includes("elevated")) return "elevated";
    if (v.includes("normal")) return "normal";
    return "unknown";
}

function getProblemFromRisk(risk: string): Problem {
    const s = risk.toLowerCase();
    if (s.includes("final")) return "failed_final";
    if (s.includes("midterm") || s.includes("critical")) return "failed_midterm";
    return "low_average";
}

function toAlert(row: TaskItem): Alert {
    const now = Math.floor(Date.now() / 1000);
    const severity: Alert["severity"] = row.current_risk_status
        .toLowerCase()
        .includes("elevated")
        ? "medium"
        : "high";
    return {
        id: row.sid,
        caseId: row.case_id,
        name: row.student_name ?? "",
        mssv: row.sid.slice(0, 8).toUpperCase(),
        email: row.email ?? "",
        problem: getProblemFromRisk(row.current_risk_status),
        summary: row.current_risk_status,
        severity,
        subject: "",
        body: "",
        lastContactedAt: null,
        status: fromBackendStatus(row.intervention_status),
        movedAt: now,
        draftJobId: null,
        draftSubject: row.draft_subject ?? null,
        draftBody: row.draft_body ?? null,
        appointmentAt: null,
        goals: [],
    };
}

const INTERVENTION_FILTER_OPTIONS: Array<{
    value: BackendInterventionStatus | "all";
    label: string;
}> = [
    { value: "all", label: "Tất cả trạng thái" },
    { value: "none", label: INTERVENTION_LABEL.none },
    { value: "notified", label: INTERVENTION_LABEL.notified },
    { value: "sent", label: INTERVENTION_LABEL.sent },
    { value: "booked", label: INTERVENTION_LABEL.booked },
    { value: "supporting", label: INTERVENTION_LABEL.supporting },
    { value: "resolved", label: INTERVENTION_LABEL.resolved },
    { value: "dismissed", label: INTERVENTION_LABEL.dismissed },
    { value: "expired", label: INTERVENTION_LABEL.expired },
];

const RISK_FILTER_OPTIONS: Array<{
    value: "all" | "critical" | "elevated" | "normal" | "unknown";
    label: string;
}> = [
    { value: "all", label: "Tất cả mức độ" },
    { value: "critical", label: RISK_LABEL_BY_KEY.critical },
    { value: "elevated", label: RISK_LABEL_BY_KEY.elevated },
    { value: "normal", label: RISK_LABEL_BY_KEY.normal },
    { value: "unknown", label: RISK_LABEL_BY_KEY.unknown },
];

export function CaseManagementBoard() {
    const { data: paged, isLoading } = useOpenCases();
    const rows = React.useMemo<TaskItem[]>(() => paged?.items ?? [], [paged]);
    const { dataset } = useDataset();

    const [search, setSearch] = React.useState("");
    const [statusFilter, setStatusFilter] = React.useState<
        BackendInterventionStatus | "all"
    >("all");
    const [riskFilter, setRiskFilter] = React.useState<
        "all" | "critical" | "elevated" | "normal" | "unknown"
    >("all");
    const [selectedCaseId, setSelectedCaseId] = React.useState<string | null>(null);

    const studentProfilesById = React.useMemo(() => {
        const map: Record<string, StudentRow | undefined> = {};
        for (const student of dataset?.students ?? []) {
            map[student.id] = student;
        }
        return map;
    }, [dataset?.students]);

    const filtered = React.useMemo(() => {
        const q = search.trim().toLowerCase();
        return rows.filter((r) => {
            const matchesQuery =
                !q ||
                (r.student_name ?? "").toLowerCase().includes(q) ||
                (r.email ?? "").toLowerCase().includes(q) ||
                r.sid.toLowerCase().includes(q);
            const matchesStatus =
                statusFilter === "all" || r.intervention_status === statusFilter;
            const matchesRisk =
                riskFilter === "all" || riskKey(r.current_risk_status) === riskFilter;
            return matchesQuery && matchesStatus && matchesRisk;
        });
    }, [rows, search, statusFilter, riskFilter]);

    const stats = React.useMemo(() => {
        const total = rows.length;
        const byRisk = { critical: 0, elevated: 0, normal: 0, unknown: 0 };
        const unassigned = rows.filter((r) => !r.assigned_to).length;
        const assigned = rows.filter((r) => !!r.assigned_to).length;
        for (const r of rows) {
            byRisk[riskKey(r.current_risk_status)]++;
        }
        return { total, unassigned, assigned, byRisk };
    }, [rows]);

    const selectedRow = React.useMemo(
        () =>
            selectedCaseId
                ? rows.find((r) => r.case_id === selectedCaseId) ?? null
                : null,
        [rows, selectedCaseId],
    );
    const selectedAlert = React.useMemo(
        () => (selectedRow ? toAlert(selectedRow) : null),
        [selectedRow],
    );

    return (
        <div className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <StatCard label="Tổng số case" value={stats.total} tone="primary" />
                <StatCard
                    label="Chưa phân công"
                    value={stats.unassigned}
                    tone="warning"
                />
                <StatCard
                    label="Nguy cấp"
                    value={stats.byRisk.critical}
                    tone="destructive"
                    icon={<AlertTriangle className="size-4" />}
                />
                <StatCard
                    label="Đã giao advisor"
                    value={stats.assigned}
                    tone="success"
                />
            </div>

            <Card className="overflow-hidden">
                <CardHeader className="gap-3 border-b border-border/60 bg-muted/20 pb-3">
                    <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                        <div>
                            <CardTitle className="text-base font-semibold">
                                Danh sách case
                            </CardTitle>
                            <p className="mt-1 text-xs text-muted-foreground">
                                Hiển thị {filtered.length} / {rows.length} case
                            </p>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                            <div className="relative">
                                <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                                <Input
                                    value={search}
                                    onChange={(e) => setSearch(e.target.value)}
                                    placeholder="Tìm sinh viên, email, MSSV..."
                                    className="h-9 w-64 pl-8"
                                />
                            </div>
                            <Select
                                value={statusFilter}
                                onValueChange={(v) =>
                                    setStatusFilter(
                                        v as BackendInterventionStatus | "all",
                                    )
                                }
                            >
                                <SelectTrigger className="h-9 w-44">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {INTERVENTION_FILTER_OPTIONS.map((o) => (
                                        <SelectItem key={o.value} value={o.value}>
                                            {o.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <Select
                                value={riskFilter}
                                onValueChange={(v) =>
                                    setRiskFilter(v as typeof riskFilter)
                                }
                            >
                                <SelectTrigger className="h-9 w-40">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {RISK_FILTER_OPTIONS.map((o) => (
                                        <SelectItem key={o.value} value={o.value}>
                                            {o.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="p-0">
                    <Table>
                        <TableHeader>
                            <TableRow className="bg-muted/30">
                                <TableHead className="px-4">Case ID</TableHead>
                                <TableHead>Sinh viên</TableHead>
                                <TableHead>Cố vấn phụ trách</TableHead>
                                <TableHead>Mức độ rủi ro</TableHead>
                                <TableHead>Trạng thái can thiệp</TableHead>
                                <TableHead className="text-right pr-4">
                                    Hành động
                                </TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {isLoading ? (
                                Array.from({ length: 5 }).map((_, i) => (
                                    <TableRow key={`skeleton-${i}`}>
                                        <TableCell className="px-4">
                                            <Skeleton className="h-4 w-24" />
                                        </TableCell>
                                        <TableCell>
                                            <div className="flex items-center gap-3">
                                                <Skeleton className="size-9 rounded-full" />
                                                <div className="flex flex-col gap-1">
                                                    <Skeleton className="h-4 w-32" />
                                                    <Skeleton className="h-3 w-44" />
                                                </div>
                                            </div>
                                        </TableCell>
                                        <TableCell>
                                            <Skeleton className="h-4 w-28" />
                                        </TableCell>
                                        <TableCell>
                                            <Skeleton className="h-5 w-20" />
                                        </TableCell>
                                        <TableCell>
                                            <Skeleton className="h-5 w-24" />
                                        </TableCell>
                                        <TableCell className="text-right pr-4">
                                            <Skeleton className="ml-auto h-8 w-20" />
                                        </TableCell>
                                    </TableRow>
                                ))
                            ) : filtered.length === 0 ? (
                                <TableRow>
                                    <TableCell
                                        colSpan={6}
                                        className="px-4 py-12 text-center"
                                    >
                                        <div className="flex flex-col items-center gap-2 text-muted-foreground">
                                            <Inbox className="size-8" />
                                            <p className="text-sm">
                                                {rows.length === 0
                                                    ? "Chưa có case nào."
                                                    : "Không có case nào khớp bộ lọc."}
                                            </p>
                                        </div>
                                    </TableCell>
                                </TableRow>
                            ) : (
                                filtered.map((row) => {
                                    const rKey = riskKey(row.current_risk_status);
                                    return (
                                        <TableRow
                                            key={row.case_id}
                                            className="cursor-pointer"
                                            onClick={() => setSelectedCaseId(row.case_id)}
                                        >
                                            <TableCell className="px-4 py-3 font-mono text-xs text-muted-foreground">
                                                {row.case_id.slice(0, 8)}
                                            </TableCell>
                                            <TableCell>
                                                <div className="flex items-center gap-3">
                                                    <Avatar className="size-9">
                                                        <AvatarFallback className="text-xs font-semibold">
                                                            {getInitials(row.student_name ?? "")}
                                                        </AvatarFallback>
                                                    </Avatar>
                                                    <div className="flex flex-col">
                                                        <span className="font-medium">
                                                            {row.student_name ?? "—"}
                                                        </span>
                                                        <span className="text-xs text-muted-foreground">
                                                            {row.email ?? ""}
                                                        </span>
                                                    </div>
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                {row.assigned_to ? (
                                                    <span className="text-sm">
                                                        {row.assigned_to}
                                                    </span>
                                                ) : (
                                                    <span className="text-xs italic text-muted-foreground">
                                                        Chưa giao
                                                    </span>
                                                )}
                                            </TableCell>
                                            <TableCell>
                                                <Badge
                                                    variant="outline"
                                                    className={cn(
                                                        "ring-1",
                                                        RISK_TONE_BY_KEY[rKey],
                                                    )}
                                                >
                                                    {RISK_LABEL_BY_KEY[rKey]}
                                                </Badge>
                                            </TableCell>
                                            <TableCell>
                                                <Badge
                                                    variant="outline"
                                                    className={cn(
                                                        "ring-1",
                                                        INTERVENTION_TONE[
                                                            row.intervention_status
                                                        ],
                                                    )}
                                                >
                                                    {
                                                        INTERVENTION_LABEL[
                                                            row.intervention_status
                                                        ]
                                                    }
                                                </Badge>
                                            </TableCell>
                                            <TableCell className="text-right pr-4">
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        setSelectedCaseId(row.case_id);
                                                    }}
                                                >
                                                    <Eye className="size-4" />
                                                    Xem
                                                </Button>
                                            </TableCell>
                                        </TableRow>
                                    );
                                })
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            <StudentDetailDrawer
                open={selectedCaseId !== null}
                onOpenChange={(open) => {
                    if (!open) setSelectedCaseId(null);
                }}
                alert={selectedAlert}
                studentProfile={
                    selectedRow ? studentProfilesById[selectedRow.sid] : undefined
                }
            />
        </div>
    );
}

function StatCard({
    label,
    value,
    tone,
    icon,
}: {
    label: string;
    value: number;
    tone: "primary" | "warning" | "destructive" | "success";
    icon?: React.ReactNode;
}) {
    const toneClass = {
        primary: "bg-primary/10 text-primary ring-primary/20",
        warning: "bg-warning/15 text-warning ring-warning/25",
        destructive: "bg-destructive/10 text-destructive ring-destructive/20",
        success: "bg-emerald-500/10 text-emerald-700 ring-emerald-500/25 dark:text-emerald-300",
    }[tone];

    return (
        <Card className="border-border/60">
            <CardContent className="flex items-center justify-between gap-3 p-4">
                <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        {label}
                    </p>
                    <p className="mt-1 font-serif text-2xl font-semibold">
                        {value}
                    </p>
                </div>
                <div
                    className={cn(
                        "grid size-10 place-items-center rounded-xl ring-1",
                        toneClass,
                    )}
                >
                    {icon ?? <span className="text-sm font-bold">{value}</span>}
                </div>
            </CardContent>
        </Card>
    );
}
