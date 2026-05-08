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
import { X } from "lucide-react";

type StudentDetailModalProps = {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    alert: Alert | null;
    studentProfile?: StudentRow;
};

const severityLabel: Record<Alert["severity"], string> = {
    high: "Nguy cơ cao",
    medium: "Nguy cơ vừa",
};

const severityTone: Record<Alert["severity"], string> = {
    high: "bg-destructive/10 text-destructive ring-destructive/20",
    medium: "bg-warning/15 text-warning ring-warning/25",
};

function formatUnix(seconds: number | null): string {
    if (!seconds) return "Chưa có";
    return new Date(seconds * 1000).toLocaleString("vi-VN");
}

export const StudentDetailModal = React.memo(function StudentDetailModal({
    open,
    onOpenChange,
    alert,
    studentProfile,
}: StudentDetailModalProps) {
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent showCloseButton={false} className="max-w-4xl overflow-hidden rounded-xl border-border/60 bg-background p-0 shadow-2xl">
                <DialogHeader className="flex flex-row items-center justify-between border-b border-border/60 p-6 pb-6 bg-white">
                    <DialogTitle className="text-2xl font-bold tracking-tight text-slate-900">
                        {alert ? alert.name : "Hồ sơ sinh viên"}
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
                                    alert.summary !== severityLabel[alert.severity] &&
                                    alert.summary !== (alert.severity === "high" ? "Critical" : "Elevated") && (
                                        <Badge variant="outline" className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground/70 px-2 py-0.5">
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

                <ScrollArea className="max-h-[75vh] bg-slate-50 hide-scrollbar">
                    {alert ? (
                        <div className="flex flex-col gap-8 p-8">
                            {/* SIS Profile Card */}
                            <section className="rounded-xl border border-slate-100 bg-white p-8 shadow-sm">
                                <h4 className="mb-8 text-xs font-bold uppercase tracking-widest text-blue-600">
                                    SIS Profile
                                </h4>
                                <div className="grid gap-5 text-sm">
                                    <div className="grid grid-cols-[30%_1fr] items-center border-b border-border/10 pb-4">
                                        <span className="text-gray-500">Mã số sinh viên</span>
                                        <span className="font-mono font-medium text-gray-900 text-right">{alert.mssv}</span>
                                    </div>
                                    <div className="grid grid-cols-[30%_1fr] items-center border-b border-border/10 pb-4">
                                        <span className="text-gray-500">Địa chỉ Email</span>
                                        <span className="font-medium text-gray-900 text-right">{alert.email || "—"}</span>
                                    </div>
                                    <div className="grid grid-cols-[30%_1fr] items-center border-b border-border/10 pb-4">
                                        <span className="text-gray-500">Năm học hiện tại</span>
                                        <span className="font-medium text-gray-900 text-right">{studentProfile?.academicYear ?? "—"}</span>
                                    </div>
                                    <div className="grid grid-cols-[30%_1fr] items-center">
                                        <span className="text-gray-500">Lần liên hệ gần nhất</span>
                                        <span className="font-medium text-gray-900 text-right">{formatUnix(studentProfile?.lastContactedAt ?? null)}</span>
                                    </div>
                                </div>
                            </section>

                            {/* LMS Overview Card */}
                            <section className="rounded-xl border border-slate-100 bg-white p-8 shadow-sm">
                                <h4 className="mb-8 text-xs font-bold uppercase tracking-widest text-indigo-600">
                                    LMS Overview
                                </h4>
                                {studentProfile ? (
                                    <div className="flex flex-col justify-between">
                                        <div className="grid grid-cols-3 gap-8 mb-8">
                                            <div className="flex flex-col items-center rounded-xl bg-slate-50/50 p-5 text-center ring-1 ring-border/5">
                                                <p className="text-[10px] font-bold uppercase text-gray-400 tracking-wider">GPA</p>
                                                <p className="mt-1 text-2xl font-black text-primary">
                                                    {studentProfile.averageScore.toFixed(1)}
                                                </p>
                                            </div>
                                            <div className="flex flex-col items-center rounded-xl bg-slate-50/50 p-5 text-center ring-1 ring-border/5">
                                                <p className="text-[10px] font-bold uppercase text-gray-400 tracking-wider">Tests</p>
                                                <p className="mt-1 text-2xl font-black text-gray-900">
                                                    {studentProfile.tests.length}
                                                </p>
                                            </div>
                                            <div className="flex flex-col items-center rounded-xl bg-slate-50/50 p-5 text-center ring-1 ring-border/5">
                                                <p className="text-[10px] font-bold uppercase text-gray-400 tracking-wider">Fail</p>
                                                <p className="mt-1 text-2xl font-black text-destructive">
                                                    {studentProfile.failedCount}
                                                </p>
                                            </div>
                                        </div>
                                        <p className="text-xs text-muted-foreground leading-relaxed italic">
                                            * Dữ liệu được tổng hợp từ kết quả học tập trong học kỳ hiện tại.
                                        </p>
                                    </div>
                                ) : (
                                    <div className="flex h-40 items-center justify-center rounded-xl border-2 border-dashed border-gray-100 bg-slate-50/20">
                                        <p className="text-sm text-muted-foreground italic text-center">
                                            Chưa có dữ liệu LMS đồng bộ.
                                        </p>
                                    </div>
                                )}
                            </section>
                        </div>
                    ) : null}
                </ScrollArea>
            </DialogContent>
        </Dialog>
    );
});
