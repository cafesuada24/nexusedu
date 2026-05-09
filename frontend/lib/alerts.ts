import * as React from "react";
import {
    GraduationCap,
    BookOpen,
    TrendingDown,
    CalendarCheck,
    Handshake,
    CheckCircle2,
    Sparkles,
    BellDot,
} from "lucide-react";
import { problemLabels, type Problem } from "@/lib/csv";
import { type BackendInterventionStatus } from "@/lib/api";
import { type Goal } from "@/components/dashboard/goals-dialog";

export type CaseStatus =
    | "new"
    | "accepted"
    | "scheduled"
    | "in_progress"
    | "resolved";

export type Alert = {
    id: string;
    caseId: string | null;
    name: string;
    mssv: string;
    email: string;
    problem: Problem;
    summary: string;
    severity: "high" | "medium";
    subject: string;
    body: string;
    /** 0 = chưa từng liên hệ, >0 = đã liên hệ (Unix seconds). */
    lastContactedAt: number | null;
    status: CaseStatus;
    /** Khi thẻ chuyển cột gần nhất — dùng để hiển thị thời gian. */
    movedAt: number;
    draftJobId?: string | null;
    draftSubject?: string | null;
    draftBody?: string | null;
    isGenerating?: boolean;
    activeCaseId?: string | null;
    /** Raw backend intervention status (e.g. "sent", "booked"). Used to
     *  distinguish SENT (email đã gửi) from ACCEPTED inside the same column. */
    interventionStatus?: string | null;
    /** Thời gian cuộc hẹn (Unix seconds) — chỉ có khi đã đặt hẹn. */
    appointmentAt: number | null;
    /** Danh sách mục tiêu can thiệp. */
    goals: Goal[];
};

export const problemMeta: Record<
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
};

export type ColumnDef = {
    id: CaseStatus;
    title: string;
    icon: React.ElementType;
    /** Tailwind classes cho icon, điểm nhấn và màu theo trạng thái. */
    accent: string;
    dotClass: string;
    containerTone: string;
    headerTone: string;
    topBorderTone: string;
    iconContainerTone: string;
    cardHighlightTone: string;
    columnHighlightTone: string;
};

export const COLUMNS: ColumnDef[] = [
    {
        id: "new",
        title: "Mới",
        icon: BellDot,
        accent: "text-red-600 dark:text-red-300",
        dotClass: "bg-red-500",
        containerTone: "bg-red-50/60 dark:bg-slate-900/40",
        headerTone: "bg-red-50/85",
        topBorderTone: "border-t-red-500",
        iconContainerTone: "bg-red-100 ring-red-200/70 dark:bg-red-500/10 dark:ring-red-400/30",
        cardHighlightTone:
            "border-red-300 bg-red-50/60 ring-1 ring-red-200/70 shadow-[0_10px_24px_-16px_rgba(220,38,38,0.65)] dark:border-red-400/45 dark:bg-red-500/10 dark:ring-red-400/30",
        columnHighlightTone:
            "ring-2 ring-red-200/80 shadow-[0_0_0_1px_rgba(248,113,113,0.22)] dark:ring-red-400/35 dark:shadow-[0_0_0_1px_rgba(248,113,113,0.18)]",
    },
    {
        id: "accepted",
        title: "Đã chấp nhận",
        icon: Sparkles,
        accent: "text-blue-600 dark:text-blue-300",
        dotClass: "bg-blue-500",
        containerTone: "bg-blue-50/60 dark:bg-slate-900/40",
        headerTone: "bg-blue-50/85",
        topBorderTone: "border-t-blue-500",
        iconContainerTone: "bg-blue-100 ring-blue-200/70 dark:bg-blue-500/10 dark:ring-blue-400/30",
        cardHighlightTone:
            "border-blue-300 bg-blue-50/60 ring-1 ring-blue-200/70 shadow-[0_10px_24px_-16px_rgba(37,99,235,0.6)] dark:border-blue-400/45 dark:bg-blue-500/10 dark:ring-blue-400/30",
        columnHighlightTone:
            "ring-2 ring-blue-200/80 shadow-[0_0_0_1px_rgba(96,165,250,0.2)] dark:ring-blue-400/35 dark:shadow-[0_0_0_1px_rgba(96,165,250,0.16)]",
    },
    {
        id: "scheduled",
        title: "Đã đặt hẹn",
        icon: CalendarCheck,
        accent: "text-green-600 dark:text-green-300",
        dotClass: "bg-green-500",
        containerTone: "bg-green-50/60 dark:bg-slate-900/40",
        headerTone: "bg-green-50/85",
        topBorderTone: "border-t-green-500",
        iconContainerTone: "bg-green-100 ring-green-200/70 dark:bg-green-500/10 dark:ring-green-400/30",
        cardHighlightTone:
            "border-green-300 bg-green-50/60 ring-1 ring-green-200/70 shadow-[0_10px_24px_-16px_rgba(22,163,74,0.58)] dark:border-green-400/45 dark:bg-green-500/10 dark:ring-green-400/30",
        columnHighlightTone:
            "ring-2 ring-green-200/80 shadow-[0_0_0_1px_rgba(74,222,128,0.2)] dark:ring-green-400/35 dark:shadow-[0_0_0_1px_rgba(74,222,128,0.16)]",
    },
    {
        id: "in_progress",
        title: "Đang hỗ trợ",
        icon: Handshake,
        accent: "text-foreground",
        dotClass: "bg-muted-foreground",
        containerTone: "bg-muted/30 dark:bg-slate-900/40",
        headerTone: "bg-muted/45",
        topBorderTone: "border-t-slate-400",
        iconContainerTone: "bg-card ring-border/70 dark:bg-slate-800/70 dark:ring-slate-700/70",
        cardHighlightTone:
            "border-slate-300 bg-slate-50/70 ring-1 ring-slate-200/70 shadow-[0_10px_24px_-16px_rgba(100,116,139,0.45)] dark:border-slate-500/40 dark:bg-slate-800/60 dark:ring-slate-500/30",
        columnHighlightTone:
            "ring-2 ring-slate-200/80 shadow-[0_0_0_1px_rgba(148,163,184,0.2)] dark:ring-slate-500/35 dark:shadow-[0_0_0_1px_rgba(148,163,184,0.16)]",
    },
    {
        id: "resolved",
        title: "Đã giải quyết",
        icon: CheckCircle2,
        accent: "text-success dark:text-emerald-300",
        dotClass: "bg-success",
        containerTone: "bg-success/10 dark:bg-slate-900/40",
        headerTone: "bg-success/15",
        topBorderTone: "border-t-emerald-500",
        iconContainerTone: "bg-emerald-100 ring-emerald-200/70 dark:bg-emerald-500/10 dark:ring-emerald-400/30",
        cardHighlightTone:
            "border-emerald-300 bg-emerald-50/60 ring-1 ring-emerald-200/70 shadow-[0_10px_24px_-16px_rgba(5,150,105,0.52)] dark:border-emerald-400/45 dark:bg-emerald-500/10 dark:ring-emerald-400/30",
        columnHighlightTone:
            "ring-2 ring-emerald-200/80 shadow-[0_0_0_1px_rgba(110,231,183,0.2)] dark:ring-emerald-400/35 dark:shadow-[0_0_0_1px_rgba(110,231,183,0.16)]",
    },
];

export function getInitials(name: string) {
    return name
        .split(/\s+/)
        .filter(Boolean)
        .map((n) => n[0]?.toUpperCase() ?? "")
        .slice(-2)
        .join("");
}

export function firstName(name: string) {
    const parts = name.trim().split(/\s+/);
    return parts[parts.length - 1] || name;
}

export function relativeTime(seconds: number): string {
    const diff = Math.floor(Date.now() / 1000) - seconds;
    if (diff < 60) return "vừa xong";
    if (diff < 3600) return `${Math.floor(diff / 60)} phút trước`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} giờ trước`;
    return `${Math.floor(diff / 86400)} ngày trước`;
}

/** Bốc một mốc giờ hợp lý trong giờ làm việc 1–7 ngày tới. */
export function pickRandomAppointment(): number {
    const now = Date.now();
    const dayOffset = 1 + Math.floor(Math.random() * 7); // 1..7 ngày
    const hour = 8 + Math.floor(Math.random() * 9); // 8..16
    const minute = Math.random() < 0.5 ? 0 : 30;
    const d = new Date(now + dayOffset * 86400 * 1000);
    d.setHours(hour, minute, 0, 0);
    return Math.floor(d.getTime() / 1000);
}

const APPOINTMENT_FORMATTER = new Intl.DateTimeFormat("vi-VN", {
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
});

export function formatAppointment(seconds: number): string {
    return APPOINTMENT_FORMATTER.format(new Date(seconds * 1000));
}

/** Bỏ dòng chào, lấy đoạn nội dung đầu của email AI để preview. */
export function getEmailPreview(body: string): string {
    const blocks = body
        .split(/\n\s*\n/)
        .map((b) => b.trim())
        .filter(Boolean);
    // bỏ qua "Chào ..." nếu có
    const firstContent = blocks.find((b) => !/^chào\b/i.test(b)) ?? blocks[0];
    return (firstContent ?? body).replace(/\s+/g, " ");
}

/**
 * Translate the local Kanban column to the backend `intervention_status`
 * enum. This is the value persisted by `PATCH /cases/{case_id}/status`.
 */
export function toBackendStatus(s: CaseStatus): BackendInterventionStatus {
    switch (s) {
        case "new":
            return "notified";
        case "accepted":
            return "notified";
        case "scheduled":
            return "booked";
        case "in_progress":
            return "supporting";
        case "resolved":
            return "resolved";
    }
}

/**
 * Translate the backend status returned by `GET /alerts` to the local
 * column id. `none` and `expired` both fold into "new" — the PD should
 * see them together at the top of the funnel for re-engagement.
 */
export function fromBackendStatus(s: BackendInterventionStatus | string | null | undefined): CaseStatus {
    const status = (s || "none").toLowerCase();
    switch (status) {
        case "sent":
            // Email đã gửi nhưng chưa đặt lịch — vẫn coi là "Đã chấp nhận"
            // (card sẽ hiển thị indicator riêng để phân biệt với accepted thuần).
            return "accepted";
        case "booked":
            return "scheduled";
        case "supporting":
            return "in_progress";
        case "resolved":
            return "resolved";
        case "notified":
        case "none":
        case "expired":
        default:
            return "new";
    }
}

export const PAGE_SIZE = 5;
