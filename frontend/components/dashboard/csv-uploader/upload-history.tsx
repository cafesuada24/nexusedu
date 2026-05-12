"use client";

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
        <li className="flex flex-col gap-3 px-4 py-3 md:flex-row md:items-center md:px-5">
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
                    {item.status === "error" && item.errorMessage
                        ? ` · ${item.errorMessage}`
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
        </li>
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
