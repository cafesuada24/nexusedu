"use client";

import * as React from "react";
import Link from "next/link";
import {
    Sparkles,
    Send,
    RotateCcw,
    CalendarDays,
    ExternalLink,
    Mail,
    User,
    BookOpen,
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

import { type Alert } from "@/lib/alerts";

type Props = {
    alert: Alert | null;
    onClose: () => void;
    onSave: (a: Alert) => void;
};

export function EmailEditorSheet({ alert, onClose, onSave }: Props) {
    // Only poll for draft status while there's an active draft job. If there's no
    // job, rely on the alert's stored draft fields to avoid excess requests.
    const { data: draft } = useDraftStatus(alert?.draftJobId ? alert.id : null);
    const [subject, setSubject] = React.useState("");
    const [body, setBody] = React.useState("");

    // Initial load or background completion
    React.useEffect(() => {
        if (alert) {
            // If we don't have a body yet, but the background draft just finished, use it
            const currentSubject =
                subject ||
                alert.subject ||
                alert.draftSubject ||
                draft?.subject ||
                "";
            const currentBody =
                body || alert.body || alert.draftBody || draft?.body || "";

            if (!subject && currentSubject) setSubject(currentSubject);
            if (!body && currentBody) setBody(currentBody);
        }
    }, [alert, draft, subject, body]);

    const reset = () => {
        if (draft?.body) {
            setSubject(draft.subject || "");
            setBody(draft.body);
        } else if (alert) {
            setSubject(alert.draftSubject || "");
            setBody(alert.draftBody || "");
        }
    };

    const isGenerating =
        draft?.is_generating ?? (!!alert?.draftJobId && !alert?.draftBody);

    const bookingUrl = alert
        ? `/booking/le-ha?sid=${alert.id}`
        : "/booking/le-ha";
    const displayUrl = alert
        ? `nexusedu.app/booking/le-ha?sid=${alert.id}`
        : "nexusedu.app/booking/le-ha";

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
                                    Soạn thảo Email
                                </SheetTitle>
                                <SheetDescription>
                                    Gửi thông điệp hỗ trợ tới sinh viên
                                </SheetDescription>
                            </div>
                        </div>
                        <Badge
                            variant="secondary"
                            className={cn(
                                "rounded-md px-2.5 py-0.5 text-xs font-medium",
                                isGenerating
                                    ? "bg-primary/15 text-primary"
                                    : body
                                      ? "bg-success/15 text-success"
                                      : "bg-muted text-muted-foreground",
                            )}
                        >
                            <Sparkles className="mr-1 size-3" />
                            {isGenerating
                                ? "AI đang soạn..."
                                : body
                                  ? "Bản nháp đã sẵn sàng"
                                  : "Chưa có bản nháp"}
                        </Badge>
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
                                className="text-sm font-semibold"
                            >
                                Tiêu đề Email
                            </Label>
                            <Input
                                id="subject"
                                value={subject}
                                onChange={(e) => setSubject(e.target.value)}
                                placeholder="VD: Trao đổi về tình hình học tập học kỳ này"
                                className="h-11 rounded-xl border-border/60 focus-visible:ring-primary/20"
                            />
                        </div>

                        <div className="grid gap-3">
                            <div className="flex items-center justify-between">
                                <Label
                                    htmlFor="body"
                                    className="text-sm font-semibold"
                                >
                                    Nội dung chi tiết
                                </Label>
                                <span className="text-[11px] text-muted-foreground">
                                    {body.split(/\s+/).filter(Boolean).length}{" "}
                                    từ
                                </span>
                            </div>
                            <Textarea
                                id="body"
                                value={body}
                                onChange={(e) => setBody(e.target.value)}
                                placeholder={
                                    isGenerating
                                        ? "Hệ thống đang phân tích kết quả học tập để soạn thư hỗ trợ phù hợp..."
                                        : "Nhập nội dung email tại đây..."
                                }
                                className="min-h-[400px] resize-none rounded-2xl border-border/60 p-4 font-sans text-base leading-relaxed focus-visible:ring-primary/20"
                            />
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
                        className="h-11 rounded-xl bg-primary px-8 font-semibold shadow-lg shadow-primary/20 hover:bg-primary/90"
                        onClick={() => {
                            if (!alert) return;
                            const fullUrl = `https://${displayUrl}`;
                            const finalBody = body.includes(displayUrl)
                                ? body
                                : `${body}\n\n---\nBạn có thể đặt lịch hẹn tư vấn tại đây: ${fullUrl}`;
                            onSave({ ...alert, subject, body: finalBody });
                        }}
                    >
                        <Send className="mr-2 size-4" />
                        Lưu & Sẵn sàng gửi
                    </Button>
                </SheetFooter>
            </SheetContent>
        </Sheet>
    );
}
