"use client";

import * as React from "react";
import {
    UploadCloud,
    FileSpreadsheet,
    CheckCircle2,
    Plus,
    Loader2,
    Link2,
} from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useUploads, type UploadItem } from "@/hooks/use-uploads";
import {
    analyzeCsv,
    csvToLMSRecords,
    csvToSISRecords,
    mergeCsv,
    LMS_SAMPLE_CSV,
    SIS_SAMPLE_CSV,
} from "@/lib/csv";

import { ingestData, updateUserSettings } from "@/lib/api";
import { type SourceKey } from "@/lib/constants";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query-keys";
import { Dropzone, HintLine, type StagedMap } from "./csv-uploader/dropzone";
import { UploadHistoryRow } from "./csv-uploader/upload-history";

import { useAuth } from "@/hooks/use-auth";

export function CsvUploader() {
    const { user } = useAuth();
    const { uploads, addUpload, updateUpload, removeUpload } = useUploads();
    const queryClient = useQueryClient();

    const [staged, setStaged] = React.useState<StagedMap>({});
    const [draggingOver, setDraggingOver] = React.useState<SourceKey | null>(
        null,
    );
    const [confirming, setConfirming] = React.useState(false);

    const isAdmin = user?.role === "admin";

    const stageFile = React.useCallback(
        (file: File, source: SourceKey) => {
            if (!isAdmin) {
                toast.error("Bạn không có quyền thực hiện thao tác này");
                return;
            }
            if (!file.name.toLowerCase().endsWith(".csv")) {
                toast.error("Vui lòng tải file .CSV");
                return;
            }
            const reader = new FileReader();
            reader.onerror = () => {
                toast.error("Không đọc được file");
            };
            reader.onload = () => {
                const text =
                    typeof reader.result === "string" ? reader.result : "";
                setStaged((prev) => ({
                    ...prev,
                    [source]: {
                        file,
                        text,
                        sizeKB: Number((file.size / 1024).toFixed(1)),
                    },
                }));
                toast.success(`Đã nạp file ${source}`, {
                    description: file.name,
                });
            };
            reader.readAsText(file);
        },
        [isAdmin],
    );

    const removeStaged = (source: SourceKey) => {
        setStaged((prev) => {
            const next = { ...prev };
            delete next[source];
            return next;
        });
    };

    const lmsStaged = staged.LMS;
    const sisStaged = staged.SIS;
    const bothReady = Boolean(lmsStaged && sisStaged);

    const handleConfirm = async () => {
        if (!isAdmin) {
            toast.error("Chỉ Quản trị viên mới có quyền nhập dữ liệu");
            return;
        }
        if (!lmsStaged || !sisStaged || confirming) return;
        setConfirming(true);

        const id = `up_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
        const item: UploadItem = {
            id,
            status: "processing",
            uploadedAt: new Date().toISOString(),
            files: {
                LMS: {
                    fileName: lmsStaged.file.name,
                    sizeKB: lmsStaged.sizeKB,
                },
                SIS: {
                    fileName: sisStaged.file.name,
                    sizeKB: sisStaged.sizeKB,
                },
            },
        };
        addUpload(item);

        // Reset zones immediately so the user can stage the next pair.
        setStaged({});

        // Small delay so the "Đang xử lý" pill is briefly visible.
        await new Promise((r) => setTimeout(r, 800));

        try {
            const merged = mergeCsv(lmsStaged.text, sisStaged.text);
            const result = analyzeCsv(merged);
            if (result.totalStudents === 0) {
                updateUpload(id, {
                    status: "error",
                    errorMessage:
                        "Bộ dữ liệu không có dòng hợp lệ (thiếu cột sid hoặc score).",
                });
                toast.error("Bộ dữ liệu không có dữ liệu hợp lệ");
                setConfirming(false);
                return;
            }

            // Push the raw rows to the backend as structured sources.
            const lmsRecords = csvToLMSRecords(lmsStaged.text);
            const sisRecords = csvToSISRecords(sisStaged.text);

            const dataSources: any[] = [];
            if (sisRecords.length > 0) {
                dataSources.push({ source_type: "sis", records: sisRecords });
            }
            if (lmsRecords.length > 0) {
                dataSources.push({ source_type: "lms", records: lmsRecords });
            }

            if (dataSources.length > 0) {
                try {
                    console.log("[CSV] Submitting data sources:", {
                        sourceCount: dataSources.length,
                        sources: dataSources.map(s => ({
                            type: s.source_type,
                            recordCount: s.records.length,
                        })),
                        totalRecords: dataSources.reduce((sum, s) => sum + s.records.length, 0),
                    });

                    await updateUserSettings({ auto_draft_enabled: false });
                    const ingestResponse = (await ingestData(dataSources)) as any;
                    console.log("[CSV] /data/ingest response:", ingestResponse);

                    // Invalidate alerts query so the Alert Center reflects the new data
                    queryClient.invalidateQueries({
                        queryKey: queryKeys.alerts.list(),
                    });

                    updateUpload(id, {
                        jobId: ingestResponse.job_id,
                        totalStudents: result.totalStudents,
                        totalTests: result.totalTests,
                        highRisk: result.highRisk,
                    });
                    toast.success("Hồ sơ đã được gửi", {
                        description: `Đang xử lý ${result.totalStudents.toLocaleString(
                            "vi-VN",
                        )} sinh viên trong nền.`,
                    });
                } catch (err: any) {
                    console.error("[CSV] /data/ingest failed with error:", {
                        message: err.message,
                        detail: err.detail,
                        stack: err.stack,
                    });

                    let errorMessage =
                        err.message || "Không thể đồng bộ với máy chủ.";
                    if (err.detail) {
                        if (Array.isArray(err.detail)) {
                            errorMessage = err.detail
                                .map((d: any) => d.msg || d.message)
                                .join(", ");
                        } else {
                            errorMessage =
                                typeof err.detail === "string"
                                    ? err.detail
                                    : JSON.stringify(err.detail);
                        }
                    }

                    updateUpload(id, {
                        status: "error",
                        errorMessage,
                    });
                    toast.error("Đồng bộ thất bại", {
                        description: errorMessage,
                    });
                }
            }
        } catch (err: any) {
            console.error("[v0] CSV analyze failed", err);
            updateUpload(id, {
                status: "error",
                errorMessage:
                    err.message ||
                    "Không thể phân tích bộ hồ sơ. Hãy kiểm tra định dạng.",
            });
            toast.error("Phân tích thất bại");
        } finally {
            setConfirming(false);
        }
    };

    const handleDelete = (item: UploadItem) => {
        removeUpload(item.id);
        toast.message("Đã xóa khỏi danh sách", {
            description: `${item.files.LMS.fileName} + ${item.files.SIS.fileName}`,
        });
    };

    const useSampleForBoth = () => {
        const lmsFile = new File([LMS_SAMPLE_CSV], "nexusedu-lms-sample.csv", {
            type: "text/csv",
        });
        const sisFile = new File([SIS_SAMPLE_CSV], "nexusedu-sis-sample.csv", {
            type: "text/csv",
        });
        stageFile(lmsFile, "LMS");
        stageFile(sisFile, "SIS");
    };

    const ordered = React.useMemo(() => [...uploads].reverse(), [uploads]);

    if (!isAdmin) {
        return (
            <Card className="border-dashed border-red-200 bg-red-50/30">
                <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                    <div className="mb-4 rounded-full bg-red-100 p-3">
                        <CheckCircle2 className="size-6 text-red-600" />
                    </div>
                    <h3 className="text-lg font-medium text-red-900">
                        Quyền truy cập bị từ chối
                    </h3>
                    <p className="max-w-xs text-sm text-red-600/80">
                        Bạn đang đăng nhập với vai trò{" "}
                        <strong>{user?.role || "viewer"}</strong>. Chỉ Quản trị
                        viên mới có quyền nhập dữ liệu CSV vào hệ thống.
                    </p>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="flex flex-col gap-6">
            <div
                aria-hidden
                className="h-px w-full bg-gradient-to-r from-accent-sky/40 via-primary/25 to-transparent"
            />

            {/* Paired LMS + SIS upload */}
            <Card className="stripe-sky rounded-2xl border-accent-sky/15 bg-gradient-to-br from-accent-sky/22 via-accent-sky/10 to-card">
                <CardContent className="p-4 md:p-6">
                    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                            <UploadCloud className="size-4 text-primary" />
                            <p className="text-sm font-semibold">LMS + SIS</p>
                        </div>
                        <button
                            type="button"
                            onClick={useSampleForBoth}
                            className="text-xs font-medium text-primary hover:underline"
                        >
                            Dữ liệu mẫu
                        </button>
                    </div>

                    {/* Two parallel dropzones with a chained link icon between them */}
                    <div className="grid items-stretch gap-3 md:grid-cols-[1fr_auto_1fr]">
                        <Dropzone
                            source="LMS"
                            staged={lmsStaged}
                            dragging={draggingOver === "LMS"}
                            onDragEnter={() => setDraggingOver("LMS")}
                            onDragLeave={() => setDraggingOver(null)}
                            onFile={(f) => stageFile(f, "LMS")}
                            onClear={() => removeStaged("LMS")}
                            disabled={confirming}
                        />

                        {/* Chain link visual between the two zones */}
                        <div className="relative flex items-center justify-center md:px-1">
                            <div
                                aria-hidden
                                className="absolute inset-x-0 top-1/2 hidden h-px -translate-y-1/2 bg-gradient-to-r from-primary/30 via-border to-warning/30 md:block"
                            />
                            <div
                                className={cn(
                                    "relative grid size-9 place-items-center rounded-full border bg-card transition-colors",
                                    bothReady
                                        ? "border-primary/60 text-primary ring-2 ring-primary/20"
                                        : "border-border/60 text-muted-foreground",
                                )}
                                aria-label="LMS và SIS phải đi cùng nhau"
                            >
                                <Link2 className="size-4" />
                            </div>
                        </div>

                        <Dropzone
                            source="SIS"
                            staged={sisStaged}
                            dragging={draggingOver === "SIS"}
                            onDragEnter={() => setDraggingOver("SIS")}
                            onDragLeave={() => setDraggingOver(null)}
                            onFile={(f) => stageFile(f, "SIS")}
                            onClear={() => removeStaged("SIS")}
                            disabled={confirming}
                        />
                    </div>

                    {/* Hint + Confirm row */}
                    <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                        <HintLine staged={staged} />
                        <Button
                            type="button"
                            size="sm"
                            onClick={handleConfirm}
                            disabled={!bothReady || confirming}
                            className={cn(
                                "rounded-xl gap-1.5 transition-all",
                                bothReady && !confirming
                                    ? "bg-primary text-primary-foreground shadow-sm shadow-primary/20 hover:bg-primary/90"
                                    : "",
                            )}
                            aria-label="Xác nhận bộ hồ sơ"
                        >
                            {confirming ? (
                                <Loader2 className="size-4 animate-spin" />
                            ) : (
                                <Plus className="size-4" />
                            )}
                            Xác nhận bộ hồ sơ
                        </Button>
                    </div>
                </CardContent>
            </Card>

            {/* File registry */}
            <Card className="stripe-cyan rounded-2xl border-accent-cyan/15 bg-gradient-to-br from-accent-cyan/22 via-accent-cyan/10 to-card">
                <CardContent className="p-0">
                    <header className="flex items-center justify-between gap-3 border-b border-border/60 px-4 py-3 md:px-5">
                        <div className="flex items-center gap-2">
                            <FileSpreadsheet className="size-4 text-muted-foreground" />
                            <p className="text-sm font-semibold">Lịch sử</p>
                        </div>
                        {uploads.length > 0 && (
                            <div className="flex items-center gap-2 text-xs">
                                <Badge
                                    variant="outline"
                                    className="rounded-md font-mono"
                                >
                                    {uploads.length}
                                </Badge>
                                <Badge
                                    variant="secondary"
                                    className="rounded-md bg-success/10 font-mono text-success hover:bg-success/10"
                                >
                                    <CheckCircle2 className="size-3" />
                                    {
                                        uploads.filter(
                                            (u) => u.status === "ready",
                                        ).length
                                    }
                                </Badge>
                            </div>
                        )}
                    </header>

                    {uploads.length === 0 ? (
                        <div className="px-4 py-8 text-center md:px-6">
                            <div className="mx-auto grid size-10 place-items-center rounded-xl bg-muted text-muted-foreground">
                                <FileSpreadsheet className="size-4" />
                            </div>
                        </div>
                    ) : (
                        <ul className="divide-y divide-border/60">
                            {ordered.map((item) => (
                                <UploadHistoryRow
                                    key={item.id}
                                    item={item}
                                    onDelete={() => handleDelete(item)}
                                />
                            ))}
                        </ul>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
