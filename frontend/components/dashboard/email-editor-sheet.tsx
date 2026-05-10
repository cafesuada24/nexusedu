"use client";

import * as React from "react";
import Link from "next/link";
import {
    Sparkles,
    Send,
    RotateCcw,
    Loader2,
    CalendarDays,
    ExternalLink,
    Mail,
    User,
    BookOpen,
    Check,
} from "lucide-react";
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetFooter,
    SheetHeader,
    SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { useDraftStatus } from "@/hooks/use-alerts";
import { useDebounce } from "@/hooks/use-debounce";
import { updateEmailDraft } from "@/lib/api";

import { type Alert } from "@/lib/alerts";

type Props = {
    alert: Alert | null;
    onClose: () => void;
    onSave: (a: Alert) => void;
    onGenerateDraft: () => void;
    isAiDrafting?: boolean;
};

export function EmailEditorSheet({ alert, onClose, onSave, onGenerateDraft, isAiDrafting }: Props) {
    // Poll draft status using caseId (activeCaseId is not populated in alert mapping).
    const {
        data: draft,
        isFetching,
        isError,
    } = useDraftStatus(alert?.caseId);
    const [subject, setSubject] = React.useState("");
    const [body, setBody] = React.useState("");
    const [currentAlertId, setCurrentAlertId] = React.useState<string | null>(null);
    const [lastIncomingBody, setLastIncomingBody] = React.useState<string | null>(null);
    const [isSaving, setIsSaving] = React.useState(false);
    const [showSavedStatus, setShowSavedStatus] = React.useState(false);
    const [localSent, setLocalSent] = React.useState(false);

    const isSent = alert?.interventionStatus === "sent" || localSent;

    // Initial load or background completion
    React.useEffect(() => {
        if (!alert) {
            if (currentAlertId !== null) {
                setCurrentAlertId(null);
                setLastIncomingBody(null);
                setLocalSent(false);
            }
            return;
        }

        const incomingSubject = alert.draftSubject || draft?.subject || alert.subject || "";
        const incomingBody = alert.draftBody || draft?.body || alert.body || "";

        if (alert.id !== currentAlertId) {
            // New student opened - force override state with their specific data
            setSubject(incomingSubject);
            setBody(incomingBody);
            setCurrentAlertId(alert.id);
            setLastIncomingBody(incomingBody);
        } else {
            // Same student.
            // If a new AI draft just arrived, force overwrite manual input.
            if (incomingBody && incomingBody !== lastIncomingBody) {
                setSubject(incomingSubject);
                setBody(incomingBody);
                setLastIncomingBody(incomingBody);
            } else {
                // Otherwise, only fill in if fields are currently empty
                if (!subject && incomingSubject) setSubject(incomingSubject);
                if (!body && incomingBody) setBody(incomingBody);
            }
        }
    }, [alert, draft, subject, body, currentAlertId, lastIncomingBody]);

    // Auto-save logic
    const debouncedSubject = useDebounce(subject, 1000);
    const debouncedBody = useDebounce(body, 1000);

    React.useEffect(() => {
        const performAutoSave = async () => {
            if (!alert?.caseId || isSent || localSent) return;

            // Only save if content has actually changed from what we last received/saved
            // and we aren't currently generating
            if (isGenerating) return;

            // Don't auto-save if content is exactly what we got from the server initially
            const incomingSubject = alert.draftSubject || draft?.subject || alert.subject || "";
            const incomingBody = alert.draftBody || draft?.body || alert.body || "";
            
            if (debouncedSubject === incomingSubject && debouncedBody === incomingBody) {
                return;
            }

            // Guard: Backend rejects empty drafts
            if (!debouncedSubject.trim() || !debouncedBody.trim()) {
                return;
            }

            try {
                setIsSaving(true);
                setShowSavedStatus(false);

                // Final check before API call to minimize race condition with "Send" button
                if (localSent || alert?.interventionStatus === "sent") {
                    setIsSaving(false);
                    return;
                }

                await updateEmailDraft(alert.caseId, {
                    subject: debouncedSubject,
                    body: debouncedBody,
                });
                setShowSavedStatus(true);
                setTimeout(() => setShowSavedStatus(false), 2000);
            } catch (err: any) {
                // If it's a "sent" error, it means we hit a race condition with the final send.
                // We can ignore this as the final content was already sent by handleSendEmail.
                if (err.message?.includes("is sent")) {
                    return;
                }
                console.error("[EmailEditor] Auto-save failed:", err);
            } finally {
                setIsSaving(false);
            }
        };

        performAutoSave();
    }, [debouncedSubject, debouncedBody, alert?.caseId, isSent]);

    const reset = () => {
        if (draft?.body) {
            setSubject(draft.subject || "");
            setBody(draft.body);
        } else if (alert) {
            setSubject(alert.draftSubject || "");
            setBody(alert.draftBody || "");
        }
    };

    // Prefer the 5s draft poll over the stale 10s alert poll for generating state.
    const isGenerating =
        isAiDrafting ||
        (draft !== undefined ? !!draft?.is_generating : !!alert?.isGenerating) ||
        (isFetching && !!alert?.draftJobId && !alert?.draftBody && !isError);

    const isDev = process.env.NODE_ENV === "development";
    const baseDomain = isDev ? "localhost:3000" : "nexusedu.app";
    const protocol = isDev ? "http" : "https";

    const bookingUrl = alert
        ? `/booking?cid=${alert.caseId}`
        : "/booking";
    const displayUrl = alert
        ? `${baseDomain}/booking?cid=${alert.caseId}`
        : `${baseDomain}/booking`;

    return (
        <Sheet open={!!alert} onOpenChange={(o) => !o && onClose()}>
            <SheetContent className="flex h-full max-h-screen w-full flex-col gap-0 overflow-hidden p-0 sm:max-w-[700px]">
                <SheetHeader className="px-6 pt-6">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <div className="grid size-9 place-items-center rounded-xl bg-primary/10 text-primary">
                                <Mail className="size-5" />
                            </div>
                            <div>
                                <SheetTitle className="font-serif text-xl">
                                    {isSent ? "Nội dung Email (Chỉ đọc)" : "Soạn thảo Email"}
                                </SheetTitle>
                                <SheetDescription>
                                    {isSent ? "Email đã được gửi cho sinh viên" : "Gửi thông điệp hỗ trợ tới sinh viên"}
                                </SheetDescription>
                            </div>
                        </div>
                        <div className="flex items-center gap-3">
                            {isSaving ? (
                                <span className="flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground animate-in fade-in duration-300">
                                    <Loader2 className="size-3 animate-spin" />
                                    Đang lưu...
                                </span>
                            ) : showSavedStatus ? (
                                <span className="flex items-center gap-1.5 text-[11px] font-medium text-emerald-600 animate-in fade-in duration-300">
                                    <Check className="size-3" />
                                    Đã lưu
                                </span>
                            ) : null}
                            <Badge
                                variant="secondary"
                                className={cn(
                                    "rounded-md px-2.5 py-0.5 text-xs font-medium",
                                    isSent 
                                        ? "bg-success/15 text-success"
                                        : isGenerating
                                          ? "bg-primary/15 text-primary"
                                          : body
                                            ? "bg-success/15 text-success"
                                            : "bg-muted text-muted-foreground",
                                )}
                            >
                                {isSent ? (
                                    <>
                                        <Send className="mr-1 size-3" />
                                        Đã gửi
                                    </>
                                ) : (
                                    <>
                                        <Sparkles className="mr-1 size-3" />
                                        {isGenerating
                                            ? "AI đang soạn..."
                                            : body
                                              ? "Bản nháp đã sẵn sàng"
                                              : "Chưa có bản nháp"}
                                    </>
                                )}
                            </Badge>
                        </div>
                    </div>
                </SheetHeader>

                <div className="px-6 py-4">
                    <Separator />
                </div>

                <ScrollArea className="flex-1 overflow-y-auto px-6">
                    <div className="grid gap-6 py-6">
                        {/* Student Info Summary */}
                        <div className="flex flex-wrap items-center gap-4 rounded-2xl border border-border/60 bg-muted/30 p-4">
                            <div className="flex items-center gap-2">
                                <User className="size-4 text-muted-foreground" />
                                <span className="text-sm font-medium">
                                    {alert?.name}
                                </span>
                            </div>
                            <Separator orientation="vertical" className="h-4" />
                            <div className="flex items-center gap-2">
                                <span className="text-xs font-mono text-muted-foreground">
                                    MSSV: {alert?.mssv}
                                </span>
                            </div>
                            <Separator orientation="vertical" className="h-4" />
                            <div className="flex items-center gap-2">
                                <BookOpen className="size-4 text-muted-foreground" />
                                <span className="text-xs text-muted-foreground">
                                    {alert?.summary}
                                </span>
                            </div>
                        </div>

                        <div className="grid gap-3">
                            <Label
                                htmlFor="subject"
                                className="text-sm font-semibold text-foreground/70"
                            >
                                Tiêu đề Email
                            </Label>
                            <Input
                                id="subject"
                                value={subject}
                                onChange={(e) => setSubject(e.target.value)}
                                readOnly={isSent}
                                placeholder="VD: Trao đổi về tình hình học tập học kỳ này"
                                className={cn(
                                    "h-11 rounded-xl border-border/60 focus-visible:ring-primary/20",
                                    isSent && "cursor-default focus-visible:ring-0"
                                )}
                            />
                        </div>

                        <div className="grid gap-3">
                            <div className="flex items-center justify-between">
                                <Label
                                    htmlFor="body"
                                    className="text-sm font-semibold text-foreground/70"
                                >
                                    Nội dung chi tiết
                                </Label>
                                <div className="flex items-center gap-2">
                                    {!isSent && (
                                        <Button
                                            type="button"
                                            size="sm"
                                            variant={body ? "ghost" : "secondary"}
                                            disabled={isGenerating}
                                            onClick={onGenerateDraft}
                                            className={cn(
                                                "h-7 gap-1.5 px-2 text-[11px] font-medium",
                                                !body && "bg-indigo-50 text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-900/30 dark:text-indigo-300",
                                            )}
                                        >
                                            {isGenerating ? (
                                                <>
                                                    <Loader2 className="size-3 animate-spin" />
                                                    AI đang soạn...
                                                </>
                                            ) : (
                                                <>
                                                    <Sparkles className="size-3" />
                                                    {body ? "Tạo lại bằng AI" : "Tạo nội dung AI"}
                                                </>
                                            )}
                                        </Button>
                                    )}
                                    <span className="text-[11px] text-muted-foreground">
                                        {body.split(/\s+/).filter(Boolean).length}{" "}
                                        từ
                                    </span>
                                </div>
                            </div>
                            <Textarea
                                id="body"
                                value={body}
                                onChange={(e) => setBody(e.target.value)}
                                readOnly={isSent}
                                placeholder={
                                    isGenerating
                                        ? "Hệ thống đang phân tích kết quả học tập để soạn thư hỗ trợ phù hợp..."
                                        : "Nhập nội dung email tại đây..."
                                }
                                className={cn(
                                    "min-h-[400px] resize-none rounded-2xl border-border/60 p-4 font-sans text-base leading-relaxed focus-visible:ring-primary/20",
                                    isSent && "cursor-default focus-visible:ring-0"
                                )}
                            />
                            {!isSent && (
                                <div className="flex items-center justify-between rounded-lg bg-muted/50 px-3 py-2">
                                    <p className="text-[11px] text-muted-foreground italic">
                                        Mẹo: Nên bắt đầu bằng lời hỏi thăm chân
                                        thành trước khi đề cập đến kết quả học tập.
                                    </p>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={reset}
                                        className="h-7 gap-1.5 px-2 text-[11px] font-medium hover:bg-primary/10 hover:text-primary"
                                    >
                                        <RotateCcw className="size-3" />
                                        Khôi phục AI
                                    </Button>
                                </div>
                            )}
                        </div>

                        <div className="rounded-2xl border border-primary/20 bg-primary/5 p-5">
                            <div className="flex items-start gap-4">
                                <div className="mt-1 grid size-10 shrink-0 place-items-center rounded-xl bg-primary/20 text-primary">
                                    <CalendarDays className="size-5" />
                                </div>
                                <div className="flex-1 space-y-1">
                                    <p className="font-semibold text-primary">
                                        Đính kèm liên kết đặt lịch
                                    </p>
                                    <p className="text-sm leading-snug text-muted-foreground">
                                        Sinh viên sẽ nhận được liên kết này để
                                        chủ động chọn lịch hẹn tư vấn với bạn.
                                    </p>
                                    <div className="pt-2">
                                        <Link
                                            href={bookingUrl}
                                            target="_blank"
                                            className="inline-flex items-center gap-2 rounded-lg bg-white px-3 py-1.5 text-xs font-mono font-medium text-primary shadow-sm ring-1 ring-primary/20 hover:bg-primary/5"
                                        >
                                            {displayUrl}
                                            <ExternalLink className="size-3" />
                                        </Link>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </ScrollArea>

                <div className="px-6 py-4">
                    <Separator />
                </div>

                <SheetFooter className="mt-0 gap-3 px-6 pb-6 sm:justify-end">
                    <Button
                        variant="outline"
                        className="h-11 rounded-xl px-6"
                        onClick={onClose}
                    >
                        Đóng
                    </Button>
                    <Button
                        disabled={isSent || isGenerating || !body.trim()}
                        className={cn(
                            "h-11 rounded-xl px-8 font-semibold shadow-lg transition-all",
                            isSent 
                                ? "bg-muted text-muted-foreground cursor-not-allowed shadow-none" 
                                : "bg-primary text-primary-foreground shadow-primary/20 hover:bg-primary/90"
                        )}
                        onClick={() => {
                            if (!alert) return;
                            setLocalSent(true);
                            const fullUrl = `${protocol}://${displayUrl}`;
                            const finalBody = body.includes(displayUrl)
                                ? body
                                : `${body}\n\n---\nBạn có thể đặt lịch hẹn tư vấn tại đây: ${fullUrl}`;
                            onSave({ ...alert, subject, body: finalBody });
                        }}
                    >
                        {isSent ? (
                            <>
                                <Send className="mr-2 size-4" />
                                Đã được gửi
                            </>
                        ) : (
                            <>
                                <Send className="mr-2 size-4" />
                                Lưu & Sẵn sàng gửi
                            </>
                        )}
                    </Button>
                </SheetFooter>
            </SheetContent>
        </Sheet>
    );
}
