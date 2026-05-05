import * as React from "react";
import {
    GraduationCap,
    BookOpen,
    TrendingDown,
    Send,
    CalendarCheck,
    Handshake,
    CheckCircle2,
    Sparkles,
} from "lucide-react";
import { problemLabels, type Problem } from "@/lib/csv";
import { type BackendInterventionStatus } from "@/lib/api";
import { type Goal } from "@/components/dashboard/goals-dialog";

export type CaseStatus =
    | "new"
    | "accepted"
    | "contacted"
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
    /** Tailwind classes cho dot và viền nhẹ ở header column. */
    accent: string;
    dotClass: string;
};

export const COLUMNS: ColumnDef[] = [
    {
        id: "new",
        title: "Mới",
        icon: Sparkles,
        accent: "text-destructive",
        dotClass: "bg-destructive",
    },
    {
        id: "accepted",
        title: "Accepted",
        icon: Sparkles,
        accent: "text-primary",
        dotClass: "bg-primary",
    },
    {
        id: "contacted",
        title: "Đã liên hệ",
        icon: Send,
        accent: "text-primary",
        dotClass: "bg-primary",
    },
    {
        id: "scheduled",
        title: "Đã đặt hẹn",
        icon: CalendarCheck,
        accent: "text-warning",
        dotClass: "bg-warning",
    },
    {
        id: "in_progress",
        title: "Đang hỗ trợ",
        icon: Handshake,
        accent: "text-foreground",
        dotClass: "bg-muted-foreground",
    },
    {
        id: "resolved",
        title: "Đã giải quyết",
        icon: CheckCircle2,
        accent: "text-success",
        dotClass: "bg-success",
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
            return "accepted";
        case "contacted":
            return "sent";
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
export function fromBackendStatus(s: BackendInterventionStatus): CaseStatus {
    switch (s) {
        case "accepted":
            return "accepted";
        case "sent":
            return "contacted";
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
