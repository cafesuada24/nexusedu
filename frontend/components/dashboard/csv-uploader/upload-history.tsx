"use client";

import * as React from "react";
import {
    Link2,
    Trash2,
    CheckCircle2,
    Loader2,
    AlertCircle,
    ArrowRight,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { SOURCE_META, type SourceKey } from "@/lib/constants";
import { type UploadItem, type UploadStatus } from "@/hooks/use-uploads";

export function UploadHistoryRow({
    item,
    onDelete,
}: {
    item: UploadItem;
    onDelete: () => void;
}) {
    const lms = item.files.LMS;
    const sis = item.files.SIS;
    return (
        <li className="flex flex-col gap-2 px-4 py-3 md:px-5">
            <div className="flex flex-col gap-3 md:flex-row md:items-center">
                <div className="flex min-w-0 flex-1 flex-col gap-2 md:flex-row md:items-center md:gap-4">
                    <SourceFilePill source="LMS" file={lms} />
                    <Link2
                        aria-hidden
                        className="hidden size-3.5 shrink-0 text-muted-foreground md:block"
                    />
                    <SourceFilePill source="SIS" file={sis} />
                </div>

                <div className="flex shrink-0 flex-wrap items-center gap-2 self-end md:self-center">
                    <p className="text-[11px] text-muted-foreground">
                        {new Date(item.uploadedAt).toLocaleString("vi-VN", {
                            hour12: false,
                        })}
                        {item.status === "ready" && item.totalStudents
                            ? ` · ${item.totalStudents.toLocaleString("vi-VN")} SV · ${
                                  item.highRisk ?? 0
                              } nguy cơ cao`
                            : null}
                    </p>
                    <StatusBadge status={item.status} />
                    {item.status === "ready" ? (
                        <Button
                            asChild
                            variant="ghost"
                            size="sm"
                            className="rounded-lg text-xs"
                        >
                            <a href="/dashboard/cases">
                                Tới quản lý case
                                <ArrowRight className="size-3.5" />
                            </a>
                        </Button>
                    ) : null}
                    <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="size-8 rounded-lg text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                        onClick={onDelete}
                        aria-label="Xóa bộ hồ sơ"
                    >
                        <Trash2 className="size-4" />
                    </Button>
                </div>
            </div>

            {item.status === "error" && item.errorMessage ? (
                <UploadErrorDetails raw={item.errorMessage} />
            ) : null}
        </li>
    );
}

const COLUMN_LABELS: Record<string, string> = {
    intervention_status: "trạng thái can thiệp",
    sid: "mã sinh viên (SID)",
    email: "email",
    student_name: "tên sinh viên",
    major: "ngành học",
    current_risk_status: "trạng thái nguy cơ",
    last_notified_timestamp: "thời gian thông báo gần nhất",
    last_notified_satisfaction: "mức độ hài lòng gần nhất",
};

// Strips SQLAlchemy/SQLite noise from backend error strings and maps the most
// common DB constraint failures to Vietnamese summaries. Falls back to the raw
// core message when the pattern is unknown.
function formatIngestError(raw: string): {
    summary: string;
    hasDetails: boolean;
} {
    if (!raw) return { summary: "Đồng bộ thất bại", hasDetails: false };

    let core = raw.replace(/^Đồng bộ dữ liệu thất bại:\s*/, "");
    core = core.replace(/\s*\[SQL:[\s\S]*$/, "");
    core = core.replace(/^\(\w+\.\w+Error\)\s*/, "");
    core = core.trim();

    const hasDetails = raw.trim() !== core;

    const notNull = core.match(/NOT NULL constraint failed:\s*\w+\.(\w+)/);
    if (notNull) {
        const label = COLUMN_LABELS[notNull[1]] ?? notNull[1];
        return {
            summary: `Thiếu dữ liệu bắt buộc ở cột "${label}". Vui lòng kiểm tra lại file CSV.`,
            hasDetails,
        };
    }

    const unique = core.match(/UNIQUE constraint failed:\s*\w+\.(\w+)/);
    if (unique) {
        const label = COLUMN_LABELS[unique[1]] ?? unique[1];
        return {
            summary: `Giá trị "${label}" bị trùng trong dữ liệu nhập.`,
            hasDetails,
        };
    }

    if (/FOREIGN KEY constraint failed/i.test(core)) {
        return {
            summary: "Dữ liệu tham chiếu đến bản ghi không tồn tại.",
            hasDetails,
        };
    }

    if (/CHECK constraint failed/i.test(core)) {
        return {
            summary: "Một giá trị không thỏa mãn ràng buộc dữ liệu.",
            hasDetails,
        };
    }

    return { summary: core || "Đồng bộ thất bại", hasDetails };
}

function UploadErrorDetails({ raw }: { raw: string }) {
    const { summary, hasDetails } = formatIngestError(raw);
    const [expanded, setExpanded] = React.useState(false);

    return (
        <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 dark:border-destructive/40 dark:bg-destructive/10">
            <AlertCircle className="mt-0.5 size-3.5 shrink-0 text-destructive" />
            <div className="min-w-0 flex-1">
                <p className="text-[12px] font-medium text-destructive">
                    {summary}
                </p>
                {hasDetails ? (
                    <>
                        <button
                            type="button"
                            onClick={() => setExpanded((v) => !v)}
                            className="mt-1 text-[11px] text-muted-foreground underline-offset-2 hover:underline"
                        >
                            {expanded ? "Ẩn chi tiết kỹ thuật" : "Xem chi tiết kỹ thuật"}
                        </button>
                        {expanded ? (
                            <pre className="mt-1.5 max-h-40 overflow-auto whitespace-pre-wrap break-all rounded-md bg-background/60 p-2 font-mono text-[10.5px] leading-relaxed text-muted-foreground">
                                {raw}
                            </pre>
                        ) : null}
                    </>
                ) : null}
            </div>
        </div>
    );
}

export function SourceFilePill({
    source,
    file,
}: {
    source: SourceKey;
    file: { fileName: string; sizeKB: number };
}) {
    const meta = SOURCE_META[source];
    const Icon = meta.icon;
    return (
        <div className="flex min-w-0 items-center gap-2.5">
            <span
                className={cn(
                    "grid size-9 shrink-0 place-items-center rounded-xl",
                    meta.iconClass,
                )}
            >
                <Icon className="size-4" />
            </span>
            <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                    <Badge
                        variant="outline"
                        className={cn(
                            "shrink-0 rounded-md px-1.5 py-0 text-[10.5px] font-semibold",
                            meta.badgeClass,
                        )}
                    >
                        {source}
                    </Badge>
                    <p className="truncate text-[13px] font-medium">
                        {file.fileName}
                    </p>
                </div>
                <p className="text-[11px] text-muted-foreground">
                    {file.sizeKB.toFixed(1)} KB
                </p>
            </div>
        </div>
    );
}

export function StatusBadge({ status }: { status: UploadStatus }) {
    if (status === "processing") {
        return (
            <Badge className="gap-1 rounded-md border-transparent bg-warning/15 px-1.5 py-0.5 text-[10.5px] font-medium text-warning ring-1 ring-warning/25 hover:bg-warning/15">
                <Loader2 className="size-3 animate-spin" />
                Đang xử lý
            </Badge>
        );
    }
    if (status === "ready") {
        return (
            <Badge className="gap-1 rounded-md border-transparent bg-success/15 px-1.5 py-0.5 text-[10.5px] font-medium text-success ring-1 ring-success/25 hover:bg-success/15">
                <CheckCircle2 className="size-3" />
                Sẵn sàng
            </Badge>
        );
    }
    return (
        <Badge
            variant="destructive"
            className="gap-1 rounded-md px-1.5 py-0.5 text-[10.5px]"
        >
            <AlertCircle className="size-3" />
            Lỗi
        </Badge>
    );
}
