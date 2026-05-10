"use client";

import * as React from "react";
import {
    Target,
    Clock,
    CalendarCheck,
    Handshake,
    CheckCircle2,
    Info,
    Loader2,
    Mail,
    Send,
    AlertCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

import { cn } from "@/lib/utils";
import { type StudentRow } from "@/lib/csv";
import {
    type Alert,
    type CaseStatus,
    problemMeta,
    COLUMNS,
    getInitials,
    formatAppointment,
    relativeTime,
} from "@/lib/alerts";

type KanbanCardProps = {
    alert: Alert;
    isHighlighted?: boolean;
    highlightTone?: string;
    onViewDetails: () => void;
    onEditEmail: () => void;
    onGenerateDraft: () => void;
    onSendEmail: () => void;
    onMove: (status: CaseStatus, message?: string) => void;
    onOpenGoals: () => void;
    studentProfile?: StudentRow;
    isAiDrafting?: boolean;
    aiDraftError?: string;
    isAiDraftReady?: boolean;
    isAcceptingCase?: boolean;
};

function KanbanCardInner({
    alert: a,
    isHighlighted,
    highlightTone,
    onViewDetails,
    onEditEmail,
    onGenerateDraft,
    onSendEmail,
    onMove,
    onOpenGoals,
    studentProfile,
    isAiDrafting,
    aiDraftError,
    isAiDraftReady,
    isAcceptingCase,
}: KanbanCardProps) {
    const meta = problemMeta[a.problem];
    const ProblemIcon = meta.icon;
    const goalsTotal = a.goals.length;
    const goalsDone = a.goals.filter((g) => g.done).length;
    const goalsPct =
        goalsTotal === 0 ? 0 : Math.round((goalsDone / goalsTotal) * 100);
    const hasOverdue = a.goals.some(
        (g) =>
            !g.done &&
            g.deadline !== null &&
            new Date(g.deadline).getTime() < new Date().setHours(0, 0, 0, 0),
    );
    const severityLabel = a.severity === "high" ? "Nguy cơ cao" : "Nguy cơ vừa";
    const severityTone =
        a.severity === "high"
            ? "bg-destructive/10 text-destructive ring-destructive/20"
            : "bg-warning/15 text-warning ring-warning/25";

    const isEmailSent =
        a.status === "accepted" && a.interventionStatus === "sent";
    const isAwaitingFeedback =
        a.interventionStatus === "pending_review";
    const hasStudentConcern = isAwaitingFeedback && Boolean(a.studentConcern);

    return (
        <article
            className={cn(
                "group rounded-xl border border-border/60 bg-card p-4 shadow-sm transition-all duration-300 hover:border-primary/30 hover:shadow-md dark:border-slate-700 dark:bg-slate-900 dark:hover:border-slate-500",
                isHighlighted && highlightTone,
                isEmailSent &&
                    "border-success/40 bg-success/5 dark:border-success/40 dark:bg-success/10",
                isAwaitingFeedback &&
                    !hasStudentConcern &&
                    "border-amber-300/60 bg-amber-50/40 dark:border-amber-400/40 dark:bg-amber-500/10",
                hasStudentConcern &&
                    "border-destructive/40 bg-destructive/5 dark:border-destructive/40 dark:bg-destructive/10",
            )}
        >
            <div className="flex items-start gap-3">
                <Avatar className="size-12 shrink-0">
                    <AvatarFallback className="bg-primary/10 text-primary text-sm font-semibold">
                        {getInitials(a.name)}
                    </AvatarFallback>
                </Avatar>
                <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                        <p className="truncate text-base font-semibold leading-tight">
                            {a.name}
                        </p>
                        {isEmailSent && (
                            <div 
                                className="flex size-5 shrink-0 items-center justify-center rounded-full bg-success/20 text-success"
                                title="Đã được gửi"
                            >
                                <CheckCircle2 className="size-3.5" />
                            </div>
                        )}
                    </div>
                    <p className="mt-0.5 truncate font-mono text-xs text-muted-foreground">
                        {a.email || `MSSV ${a.mssv}`}
                    </p>
                </div>

            </div>

            <div className="mt-3 flex flex-wrap items-center gap-2">
                <Badge
                    variant="outline"
                    className={cn(
                        "gap-1.5 rounded-md border-transparent px-2 py-1 text-[13px] ring-1",
                        severityTone,
                    )}
                >
                    {severityLabel}
                </Badge>
                {a.summary &&
                    a.summary !== severityLabel &&
                    a.summary !==
                        (a.severity === "high" ? "Critical" : "Elevated") && (
                        <Badge
                            variant="outline"
                            className={cn(
                                "max-w-full gap-1.5 rounded-md border-transparent px-2 py-1 text-[13px] ring-1",
                                meta.tone,
                            )}
                        >
                            <ProblemIcon className="size-3.5" />
                            <span className="truncate">{a.summary}</span>
                        </Badge>
                    )}
            </div>

            {goalsTotal > 0 ? (
                <button
                    type="button"
                    onClick={onOpenGoals}
                    className="mt-3 flex w-full items-center gap-2.5 rounded-lg border border-border/60 bg-muted/40 px-2.5 py-2 text-left transition-colors hover:border-primary/30 hover:bg-primary/5"
                    aria-label={`Xem ${goalsTotal} mục tiêu của ${a.name}`}
                >
                    <Target
                        className={cn(
                            "size-4 shrink-0",
                            hasOverdue ? "text-destructive" : "text-primary",
                        )}
                    />
                    <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between text-xs font-medium">
                            <span className="text-foreground">
                                Mục tiêu{" "}
                                <span className="font-mono text-muted-foreground">
                                    {goalsDone}/{goalsTotal}
                                </span>
                            </span>
                            <span
                                className={cn(
                                    "font-mono",
                                    hasOverdue
                                        ? "text-destructive"
                                        : "text-muted-foreground",
                                )}
                            >
                                {hasOverdue ? "Quá hạn" : `${goalsPct}%`}
                            </span>
                        </div>
                        <div
                            className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-border/60"
                            role="progressbar"
                            aria-valuenow={goalsPct}
                            aria-valuemin={0}
                            aria-valuemax={100}
                        >
                            <div
                                className={cn(
                                    "h-full rounded-full transition-[width] duration-300",
                                    hasOverdue ? "bg-destructive" : "bg-success",
                                )}
                                style={{ width: `${goalsPct}%` }}
                            />
                        </div>
                    </div>
                </button>
            ) : null}

            {a.status === "scheduled" && a.appointmentAt ? (
                <p className="mt-3 flex items-center gap-1.5 text-[13px] font-medium text-warning">
                    <Clock className="size-3.5" />
                    Hẹn {formatAppointment(a.appointmentAt)}
                </p>
            ) : a.status === "accepted" && isAiDrafting ? (
                <p className="mt-3 flex items-center gap-1.5 text-[13px] text-muted-foreground">
                    <Loader2 className="size-3.5 animate-spin" />
                    AI đang soạn thảo bản thảo...
                </p>
            ) : a.status === "accepted" && aiDraftError ? (
                <p className="mt-3 text-[13px] text-destructive">{aiDraftError}</p>
            ) : isEmailSent ? (
                <p className="mt-3 text-[13px] text-success font-medium">
                    Đã được gửi.
                </p>
            ) : a.status === "accepted" && (isAiDraftReady || a.draftSubject) ? (
                <p className="mt-3 text-[13px] text-success">
                    Bản nháp đã sẵn sàng.
                </p>
            ) : a.status !== "new" ? (
                <p className="mt-3 text-[13px] text-muted-foreground">
                    Cập nhật {relativeTime(a.movedAt)}
                </p>
            ) : null}

            <CardActions
                alert={a}
                onViewDetails={onViewDetails}
                onEditEmail={onEditEmail}
                onGenerateDraft={onGenerateDraft}
                onSendEmail={onSendEmail}
                onMove={onMove}
                onOpenGoals={onOpenGoals}
                studentProfile={studentProfile}
                isAiDrafting={isAiDrafting}
                isAcceptingCase={isAcceptingCase}
                isEmailSent={isEmailSent}
                isAwaitingFeedback={isAwaitingFeedback}
            />
        </article>
    );
}

export const KanbanCard = React.memo(KanbanCardInner);

function CardActions({
    alert: a,
    onViewDetails,
    onEditEmail,
    onGenerateDraft,
    onSendEmail,
    onMove,
    onOpenGoals,
    studentProfile,
    isAiDrafting,
    isAcceptingCase,
    isEmailSent,
    isAwaitingFeedback,
}: {
    alert: Alert;
    onViewDetails: () => void;
    onEditEmail: () => void;
    onGenerateDraft: () => void;
    onSendEmail: () => void;
    onMove: (status: CaseStatus, message?: string) => void;
    onOpenGoals: () => void;
    studentProfile?: StudentRow;
    isAiDrafting?: boolean;
    isAcceptingCase?: boolean;
    isEmailSent?: boolean;
    isAwaitingFeedback?: boolean;
}) {
    const hasGoals = a.goals.length > 0;
    const isActuallyDrafting = isAiDrafting || a.isGenerating;

    if (a.status === "new") {
        return (
            <div className="mt-3 flex flex-col gap-2">
                <Button
                    variant="ghost"
                    size="sm"
                    disabled={isAcceptingCase}
                    className="h-10 w-full justify-start rounded-lg border border-border/60 text-sm font-medium"
                    onClick={onViewDetails}
                >
                    <Info className="size-4" />
                    Xem hồ sơ
                </Button>
                <Button
                    size="sm"
                    disabled={isAcceptingCase}
                    className="h-10 w-full rounded-lg text-sm font-medium"
                    onClick={() => {
                        if (window.confirm(`Bạn có chắc chắn muốn tiếp nhận ca của ${a.name}?`)) {
                            onMove("accepted", `Đã nhận ca của ${a.name}`);
                        }
                    }}
                >
                    {isAcceptingCase ? (
                        <>
                            AI đang soạn thảo...
                        </>
                    ) : (
                        <>
                            <Handshake className="size-4" />
                            Tiếp nhận ca
                        </>
                    )}
                </Button>
                {!studentProfile ? (
                    <p className="text-[12px] text-muted-foreground">
                        Chưa có dữ liệu LMS/SIS chi tiết cho sinh viên này.
                    </p>
                ) : null}
            </div>
        );
    }

    if (a.status === "accepted") {
        return (
            <div className="mt-3">
                <Button
                    size="sm"
                    className="h-10 w-full rounded-lg text-sm font-medium"
                    onClick={onEditEmail}
                >
                    <Mail className="size-4" />
                    Nội dung Email
                </Button>
            </div>
        );
    }

    if (a.status === "scheduled") {
        return (
            <div className="mt-3 flex items-center gap-2">
                <Button
                    variant="outline"
                    size="sm"
                    className="h-10 w-10 shrink-0 rounded-lg"
                    onClick={onOpenGoals}
                    aria-label={hasGoals ? "Xem mục tiêu" : "Đặt mục tiêu"}
                    title={hasGoals ? "Xem mục tiêu" : "Đặt mục tiêu"}
                >
                    <Target className="size-4" />
                </Button>
                <Button
                    size="sm"
                    className="h-10 flex-1 rounded-lg text-sm font-medium"
                    onClick={() => {
                        if (window.confirm(`Bạn có chắc chắn muốn bắt đầu hỗ trợ ${a.name}?`)) {
                            onMove("in_progress", `Bắt đầu hỗ trợ ${a.name}`);
                        }
                    }}
                >
                    <Handshake className="size-4" />
                    Bắt đầu hỗ trợ
                </Button>
            </div>
        );
    }

    if (a.status === "in_progress") {
        return (
            <div className="mt-3 flex items-center gap-2">
                <Button
                    variant="outline"
                    size="sm"
                    className="h-10 flex-1 rounded-lg text-sm font-medium"
                    onClick={onOpenGoals}
                >
                    <Target className="size-4" />
                    {hasGoals ? "Mục tiêu" : "Đặt mục tiêu"}
                </Button>
                <Button
                    size="sm"
                    className="h-10 flex-1 rounded-lg text-sm font-medium"
                    onClick={() => {
                        if (window.confirm(`Bạn có chắc chắn muốn giải quyết và đóng ca của ${a.name}?`)) {
                            onMove("resolved", `Đã đóng case của ${a.name}`);
                        }
                    }}
                >
                    <CheckCircle2 className="size-4" />
                    Giải quyết
                </Button>
            </div>
        );
    }

    // resolved column — 2 sub-states (awaiting student confirmation vs confirmed)
    if (isAwaitingFeedback) {
        const concern = a.studentConcern;
        if (concern) {
            return (
                <div className="mt-3">
                    <div className="flex items-start gap-2 rounded-lg border border-destructive/40 bg-destructive/5 px-3 py-2.5 dark:border-destructive/40 dark:bg-destructive/10">
                        <AlertCircle className="mt-0.5 size-4 shrink-0 text-destructive" />
                        <div className="min-w-0 flex-1">
                            <p className="text-[13px] font-medium text-destructive">
                                Sinh viên báo chưa giải quyết
                            </p>
                            <p className="mt-0.5 line-clamp-2 text-[12px] text-destructive/85">
                                “{concern.comment}”
                            </p>
                            <p className="mt-1 text-[11px] text-muted-foreground">
                                {relativeTime(concern.submittedAt)}
                            </p>
                        </div>
                    </div>
                </div>
            );
        }
        return (
            <div className="mt-3">
                <div className="flex items-center gap-2 rounded-lg border border-amber-300/60 bg-amber-50/60 px-3 py-2.5 dark:border-amber-400/40 dark:bg-amber-500/10">
                    <Clock className="size-4 shrink-0 text-amber-600 dark:text-amber-400" />
                    <div className="min-w-0">
                        <p className="text-[13px] font-medium text-amber-800 dark:text-amber-300">
                            Chờ sinh viên xác nhận
                        </p>
                        <p className="text-[11px] text-amber-600/80 dark:text-amber-400/70">
                            Đã chuyển · {relativeTime(a.movedAt)}
                        </p>
                    </div>
                </div>
            </div>
        );
    }
    return (
        <p className="mt-3 text-[12px] italic text-success">
            ✓ Đã giải quyết xong · {relativeTime(a.movedAt)}
        </p>
    );
}
