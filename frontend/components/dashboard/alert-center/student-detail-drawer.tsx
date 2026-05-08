"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import {
    Drawer,
    DrawerContent,
    DrawerDescription,
    DrawerHeader,
    DrawerTitle,
} from "@/components/ui/drawer";
import { type Alert, relativeTime } from "@/lib/alerts";
import { type StudentRow } from "@/lib/csv";

type StudentDetailDrawerProps = {
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

export function StudentDetailDrawer({
    open,
    onOpenChange,
    alert,
    studentProfile,
}: StudentDetailDrawerProps) {
    const tests = React.useMemo(
        () =>
            [...(studentProfile?.tests ?? [])]
                .sort((a, b) => b.timestamp - a.timestamp)
                .slice(0, 8),
        [studentProfile],
    );

    return (
        <Drawer open={open} onOpenChange={onOpenChange} direction="right">
            <DrawerContent className="w-full border-border/60 bg-background/95 backdrop-blur sm:max-w-xl">
                <DrawerHeader className="border-b border-border/60">
                    <DrawerTitle className="text-base">
                        {alert ? alert.name : "Hồ sơ sinh viên"}
                    </DrawerTitle>
                    <DrawerDescription>
                        {alert ? `MSSV ${alert.mssv} · ${alert.email || "Chưa có email"}` : ""}
                    </DrawerDescription>
                </DrawerHeader>

                {alert ? (
                    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4">
                        <div className="flex flex-wrap items-center gap-2">
                            <Badge
                                variant="outline"
                                className={`ring-1 ${severityTone[alert.severity]}`}
                            >
                                {severityLabel[alert.severity]}
                            </Badge>
                            <Badge variant="outline" className="font-mono text-xs">
                                {alert.summary}
                            </Badge>
                            <Badge variant="secondary" className="text-xs">
                                Cập nhật {relativeTime(alert.movedAt)}
                            </Badge>
                        </div>

                        <section className="rounded-xl border border-border/60 bg-card/60 p-3">
                            <h4 className="text-sm font-semibold">SIS</h4>
                            <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
                                <p className="text-muted-foreground">MSSV</p>
                                <p className="font-mono">{alert.mssv}</p>
                                <p className="text-muted-foreground">Email</p>
                                <p className="truncate">{alert.email || "Chưa có"}</p>
                                <p className="text-muted-foreground">Năm học hiện tại</p>
                                <p>{studentProfile?.academicYear ?? "Chưa có"}</p>
                                <p className="text-muted-foreground">Lần liên hệ gần nhất</p>
                                <p>{formatUnix(studentProfile?.lastContactedAt ?? null)}</p>
                            </div>
                        </section>

                        <section className="rounded-xl border border-border/60 bg-card/60 p-3">
                            <h4 className="text-sm font-semibold">LMS</h4>
                            {studentProfile ? (
                                <>
                                    <div className="mt-2 grid grid-cols-3 gap-2">
                                        <div className="rounded-lg border border-border/60 bg-muted/30 p-2">
                                            <p className="text-xs text-muted-foreground">Điểm TB</p>
                                            <p className="font-semibold">
                                                {studentProfile.averageScore.toFixed(1)}
                                            </p>
                                        </div>
                                        <div className="rounded-lg border border-border/60 bg-muted/30 p-2">
                                            <p className="text-xs text-muted-foreground">Số bài kiểm tra</p>
                                            <p className="font-semibold">
                                                {studentProfile.tests.length}
                                            </p>
                                        </div>
                                        <div className="rounded-lg border border-border/60 bg-muted/30 p-2">
                                            <p className="text-xs text-muted-foreground">Bài dưới 50</p>
                                            <p className="font-semibold">
                                                {studentProfile.failedCount}
                                            </p>
                                        </div>
                                    </div>

                                    <div className="mt-3 space-y-2">
                                        {tests.map((test, idx) => (
                                            <div
                                                key={`${test.courseId}-${test.timestamp}-${idx}`}
                                                className="rounded-lg border border-border/60 bg-muted/20 p-2"
                                            >
                                                <p className="truncate text-sm font-medium">
                                                    {test.courseName || "Môn học chưa rõ"}
                                                </p>
                                                <p className="mt-1 text-xs text-muted-foreground">
                                                    Điểm {test.score.toFixed(1)} · HK {test.semester}/
                                                    Năm {test.academicYear}
                                                </p>
                                            </div>
                                        ))}
                                    </div>
                                </>
                            ) : (
                                <p className="mt-2 text-sm text-muted-foreground">
                                    Chưa có dữ liệu LMS/SIS chi tiết từ lần import gần nhất.
                                </p>
                            )}
                        </section>
                    </div>
                ) : null}
            </DrawerContent>
        </Drawer>
    );
}

