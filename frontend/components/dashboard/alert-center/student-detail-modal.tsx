"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { type Alert } from "@/lib/alerts";
import { type StudentRow } from "@/lib/csv";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import {
    X,
    Calendar,
    MapPin,
    MessageSquareText,
    TrendingUp,
    TrendingDown,
    BrainCircuit,
    Info,
} from "lucide-react";
import { useStudent } from "@/hooks/use-student-query";

type StudentDetailModalProps = {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    alert: Alert | null;
    studentProfile?: StudentRow;
};

const mockLmsData = [
    { course: "Toán giải tích", prev: 3.2, current: 3.8 },
    { course: "Lập trình hướng đối tượng", prev: 3.5, current: 3.3 },
    { course: "Cấu trúc dữ liệu & Giải thuật", prev: 2.8, current: 3.4 },
    { course: "Cơ sở dữ liệu", prev: 3.0, current: 3.0 },
    { course: "Mạng máy tính", prev: 3.6, current: 3.2 },
];

const severityLabel: Record<Alert["severity"], string> = {
    high: "Nguy cơ cao",
    medium: "Nguy cơ vừa",
};

const severityTone: Record<Alert["severity"], string> = {
    high: "bg-destructive/10 text-destructive ring-destructive/20",
    medium: "bg-warning/15 text-warning ring-warning/25",
};

const TrendIndicator = ({
    prev,
    current,
}: {
    prev: number;
    current: number;
}) => {
    const diff = current - prev;
    if (diff > 0) {
        return (
            <div className="inline-flex items-center justify-center gap-1 text-emerald-600 font-medium">
                <TrendingUp className="size-3.5" />
                <span>+{diff.toFixed(1)}</span>
            </div>
        );
    }
    if (diff < 0) {
        return (
            <div className="inline-flex items-center justify-center gap-1 text-destructive font-medium">
                <TrendingDown className="size-3.5" />
                <span>{diff.toFixed(1)}</span>
            </div>
        );
    }
    return <span className="text-muted-foreground">—</span>;
};

export const StudentDetailModal = React.memo(function StudentDetailModal({
    open,
    onOpenChange,
    alert,
    studentProfile,
}: StudentDetailModalProps) {
    const { data: student, isLoading } = useStudent(
        alert?.id || undefined,
        open,
    );

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent
                showCloseButton={false}
                className="sm:max-w-5xl overflow-hidden rounded-xl border-border/60 bg-background p-0 shadow-2xl"
            >
                <DialogHeader className="flex flex-row items-center justify-between border-b border-border/60 p-6 pb-6 bg-white">
                    <DialogTitle className="text-2xl font-bold tracking-tight text-slate-900">
                        {student?.student_name ||
                            alert?.name ||
                            "Hồ sơ sinh viên"}
                    </DialogTitle>
                    <div className="flex items-center gap-6">
                        {alert && (
                            <div className="flex flex-col items-end gap-1">
                                <Badge
                                    variant="outline"
                                    className={`px-3 py-1 text-xs font-semibold ring-1 ${severityTone[alert.severity]}`}
                                >
                                    {severityLabel[alert.severity]}
                                </Badge>
                                {alert.summary &&
                                    alert.summary !==
                                        severityLabel[alert.severity] &&
                                    alert.summary !==
                                        (alert.severity === "high"
                                            ? "Critical"
                                            : "Elevated") && (
                                        <Badge
                                            variant="outline"
                                            className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground/70 px-2 py-0.5"
                                        >
                                            {alert.summary}
                                        </Badge>
                                    )}
                            </div>
                        )}

                        <button
                            onClick={() => onOpenChange(false)}
                            className="flex h-8 w-8 items-center justify-center rounded-full text-muted-foreground transition-all duration-200 hover:bg-gray-100 hover:text-slate-900 active:scale-95"
                            aria-label="Close"
                        >
                            <X className="h-4 w-4" />
                        </button>
                    </div>
                </DialogHeader>

                <ScrollArea className="max-h-[85vh] bg-slate-50/50 hide-scrollbar">
                    {alert ? (
                        <div className="flex flex-col gap-6 p-6">
                            <div className="grid grid-cols-10 gap-6">
                                {/* Left Column (4/10): SIS Profile */}
                                <div className="col-span-4 flex flex-col gap-6">
                                    <section className="flex flex-col h-full rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                                        <div className="mb-6 flex items-center justify-between">
                                            <h4 className="text-xs font-bold uppercase tracking-widest text-blue-600">
                                                SIS Profile
                                            </h4>
                                            <Badge
                                                variant="secondary"
                                                className="bg-blue-50 text-blue-700 hover:bg-blue-50"
                                            >
                                                Cơ bản
                                            </Badge>
                                        </div>
                                        <div className="overflow-hidden rounded-lg border border-slate-100">
                                            <div className="flex flex-col divide-y divide-slate-50 text-sm">
                                                <div className="flex items-center px-4 py-3">
                                                    <span className="w-32 shrink-0 text-[10px] font-bold uppercase text-slate-500">
                                                        Mã số sinh viên
                                                    </span>
                                                    <span className="font-mono font-semibold text-slate-900">
                                                        {alert.mssv}
                                                    </span>
                                                </div>
                                                <div className="flex items-center px-4 py-3">
                                                    <span className="w-32 shrink-0 text-[10px] font-bold uppercase text-slate-500">
                                                        Địa chỉ Email
                                                    </span>
                                                    <span className="font-semibold text-slate-900 truncate">
                                                        {isLoading ? (
                                                            <div className="h-4 w-32 bg-slate-100 animate-pulse rounded" />
                                                        ) : (
                                                            student?.email ||
                                                            alert.email ||
                                                            "—"
                                                        )}
                                                    </span>
                                                </div>
                                                <div className="flex items-center px-4 py-3">
                                                    <span className="w-32 shrink-0 text-[10px] font-bold uppercase text-slate-500">
                                                        Chuyên ngành
                                                    </span>
                                                    <span className="font-semibold text-slate-900">
                                                        {isLoading ? (
                                                            <div className="h-4 w-24 bg-slate-100 animate-pulse rounded" />
                                                        ) : (
                                                            student?.major ||
                                                            "Công nghệ Thông tin"
                                                        )}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                    </section>

                                    {/* Appointment Info Card if exists */}
                                    {alert.appointmentAt && (
                                        <section className="rounded-xl border border-emerald-100 bg-emerald-50/50 p-6 shadow-sm">
                                            <div className="flex items-center gap-2 mb-6">
                                                <div className="p-1.5 bg-emerald-100 rounded-lg text-emerald-600">
                                                    <Calendar className="size-4" />
                                                </div>
                                                <h4 className="text-xs font-bold uppercase tracking-widest text-emerald-600">
                                                    Lịch hẹn
                                                </h4>
                                            </div>
                                            <div className="grid gap-4 text-sm">
                                                <div className="flex flex-col gap-1 border-b border-emerald-100/50 pb-3">
                                                    <span className="text-[10px] font-bold uppercase text-emerald-700/60">
                                                        Thời gian
                                                    </span>
                                                    <span className="font-medium text-emerald-900">
                                                        {new Date(
                                                            alert.appointmentAt *
                                                                1000,
                                                        ).toLocaleString(
                                                            "vi-VN",
                                                            {
                                                                weekday: "long",
                                                                year: "numeric",
                                                                month: "long",
                                                                day: "numeric",
                                                                hour: "2-digit",
                                                                minute: "2-digit",
                                                            },
                                                        )}
                                                    </span>
                                                </div>
                                                <div className="flex flex-col gap-1">
                                                    <span className="text-[10px] font-bold uppercase text-emerald-700/60">
                                                        Hình thức
                                                    </span>
                                                    <span className="font-medium text-emerald-900">
                                                        {alert.meetingMethod ===
                                                        "online"
                                                            ? "Trực tuyến (Zoom/Meet)"
                                                            : "Trực tiếp tại văn phòng"}
                                                    </span>
                                                </div>
                                            </div>
                                        </section>
                                    )}
                                </div>

                                {/* Right Column (6/10): LMS Overview */}
                                <div className="col-span-6">
                                    <section className="h-full rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                                        <div className="mb-6 flex items-center justify-between">
                                            <h4 className="text-xs font-bold uppercase tracking-widest text-indigo-600">
                                                LMS Overview
                                            </h4>
                                            <div className="flex items-center gap-2 text-[10px] font-medium text-slate-400">
                                                <Info className="size-3" />
                                                Dữ liệu học kỳ 2023.2
                                            </div>
                                        </div>

                                        <div className="overflow-hidden rounded-lg border border-slate-100">
                                            <table className="w-full text-left text-sm">
                                                <thead className="bg-slate-50 text-slate-500 uppercase text-[10px] font-bold">
                                                    <tr>
                                                        <th className="px-4 py-3">
                                                            Học phần
                                                        </th>
                                                        <th className="px-4 py-3 text-center">
                                                            Điểm
                                                        </th>
                                                        <th className="px-4 py-3 text-center">
                                                            Trend
                                                        </th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-slate-50">
                                                    {mockLmsData.map(
                                                        (item, idx) => (
                                                            <tr
                                                                key={idx}
                                                                className="hover:bg-slate-50/50 transition-colors"
                                                            >
                                                                <td className="px-4 py-3 font-medium text-slate-700">
                                                                    {
                                                                        item.course
                                                                    }
                                                                </td>
                                                                <td className="px-4 py-3 text-center font-bold text-slate-900 font-mono">
                                                                    {item.current.toFixed(
                                                                        1,
                                                                    )}
                                                                </td>
                                                                <td className="px-4 py-3 text-center">
                                                                    <TrendIndicator
                                                                        prev={
                                                                            item.prev
                                                                        }
                                                                        current={
                                                                            item.current
                                                                        }
                                                                    />
                                                                </td>
                                                            </tr>
                                                        ),
                                                    )}
                                                </tbody>
                                            </table>
                                        </div>

                                        <div className="mt-6 grid grid-cols-2 gap-4">
                                            <div className="rounded-lg bg-slate-50 p-4 text-center ring-1 ring-slate-100 flex flex-col justify-center">
                                                <p className="text-[10px] font-bold uppercase text-slate-400 tracking-wider mb-1">
                                                    GPA
                                                </p>
                                                <div className="grid grid-cols-[1fr_auto_1fr] items-baseline w-full">
                                                    <div />
                                                    <p className="text-2xl font-black text-indigo-600">
                                                        3.4
                                                    </p>
                                                    <div className="flex justify-start pl-2">
                                                        <div className="flex items-center gap-0.5 text-xs font-bold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">
                                                            <TrendingUp className="size-3" />
                                                            +0.2
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="rounded-lg bg-slate-50 p-4 text-center ring-1 ring-slate-100 flex flex-col justify-center">
                                                <p className="text-[10px] font-bold uppercase text-slate-400 tracking-wider mb-1">
                                                    Hạng
                                                </p>
                                                <div className="grid grid-cols-[1fr_auto_1fr] items-baseline w-full">
                                                    <div />
                                                    <p className="text-2xl font-black text-slate-800">
                                                        15/40
                                                    </p>
                                                    <div className="flex justify-start pl-2">
                                                        <div className="flex items-center gap-0.5 text-xs font-bold text-destructive bg-destructive/10 px-1.5 py-0.5 rounded">
                                                            <TrendingDown className="size-3" />
                                                            -5
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </section>
                                </div>
                            </div>

                            {/* AI Overview Section (Full Width) */}
                            <section className="rounded-xl border border-purple-100 bg-gradient-to-br from-purple-50/50 to-indigo-50/30 p-6 shadow-sm">
                                <div className="mb-4 flex items-center gap-2">
                                    <div className="p-1.5 bg-purple-100 rounded-lg text-purple-600">
                                        <BrainCircuit className="size-4" />
                                    </div>
                                    <h4 className="text-xs font-bold uppercase tracking-widest text-purple-700">
                                        AI Insights & Recommendations
                                    </h4>
                                </div>
                                <div className="grid grid-cols-3 gap-6">
                                    <div className="col-span-2 space-y-4">
                                        <div className="rounded-lg bg-white/60 p-4 ring-1 ring-purple-100">
                                            <p className="text-sm font-semibold text-slate-900 mb-1">
                                                Phân tích rủi ro
                                            </p>
                                            <p className="text-sm text-slate-600 leading-relaxed">
                                                Sinh viên có dấu hiệu sụt giảm
                                                kết quả ở các môn chuyên ngành
                                                (Mạng máy tính, Lập trình). Tuy
                                                nhiên, các môn lý thuyết tính
                                                toán có sự cải thiện rõ rệt. Cần
                                                chú trọng hỗ trợ kỹ năng thực
                                                hành.
                                            </p>
                                        </div>
                                        <div className="flex gap-4">
                                            <Badge className="bg-indigo-100 text-indigo-700 hover:bg-indigo-100 border-indigo-200">
                                                Cần tư vấn môn chuyên ngành
                                            </Badge>
                                        </div>
                                    </div>
                                    <div className="space-y-3">
                                        <p className="text-[10px] font-bold uppercase text-purple-400">
                                            Khuyến nghị hành động
                                        </p>
                                        <ul className="space-y-2">
                                            {[
                                                "Đăng ký phụ đạo môn Mạng",
                                                "Gặp cố vấn học tập tuần 12",
                                                "Tham gia Lab thực hành bổ sung",
                                            ].map((action, i) => (
                                                <li
                                                    key={i}
                                                    className="flex items-start gap-2 text-xs text-slate-700"
                                                >
                                                    <div className="mt-1 size-1.5 rounded-full bg-purple-400 shrink-0" />
                                                    {action}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                </div>
                            </section>
                        </div>
                    ) : null}
                </ScrollArea>
            </DialogContent>
        </Dialog>
    );
});
