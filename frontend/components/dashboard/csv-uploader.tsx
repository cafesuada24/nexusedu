"use client";

import * as React from "react";
import {
    UploadCloud,
    CheckCircle2,
    Plus,
    Loader2,
    Link2,
    AlertCircle,
    X,
    FileSpreadsheet,
} from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
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

import { useAuth } from "@/hooks/use-auth";

type LMSRecord = ReturnType<typeof csvToLMSRecords>[number];
type SISRecord = ReturnType<typeof csvToSISRecords>[number];

type UploadedContent = {
    lmsName: string;
    sisName: string;
    lmsRecords: LMSRecord[];
    sisRecords: SISRecord[];
};

type InflightStatus =
    | { kind: "idle" }
    | { kind: "processing"; lmsName: string; sisName: string }
    | { kind: "ready"; totalStudents: number; highRisk: number }
    | { kind: "error"; message: string };

const PREVIEW_LIMIT = 100;

function extractErrorMessage(err: unknown): string {
    const e = err as { message?: string; detail?: unknown };
    if (e?.detail) {
        if (Array.isArray(e.detail)) {
            return e.detail
                .map((d: { msg?: string; message?: string }) => d.msg || d.message)
                .filter(Boolean)
                .join(", ");
        }
        if (typeof e.detail === "string") return e.detail;
        return JSON.stringify(e.detail);
    }
    return e?.message || "Không thể đồng bộ với máy chủ.";
}

// Strip SQLAlchemy/SQLite noise so the inline error card stays readable.
function cleanupErrorMessage(raw: string): string {
    if (!raw) return "Đồng bộ thất bại";
    let core = raw.replace(/^Đồng bộ dữ liệu thất bại:\s*/, "");
    core = core.replace(/\s*\[SQL:[\s\S]*$/, "");
    core = core.replace(/^\(\w+\.\w+Error\)\s*/, "");
    return core.trim() || "Đồng bộ thất bại";
}

export function CsvUploader() {
    const { user } = useAuth();
    const queryClient = useQueryClient();

    const [staged, setStaged] = React.useState<StagedMap>({});
    const [draggingOver, setDraggingOver] = React.useState<SourceKey | null>(
        null,
    );
    const [confirming, setConfirming] = React.useState(false);
    const [inflight, setInflight] = React.useState<InflightStatus>({
        kind: "idle",
    });
    const [uploaded, setUploaded] = React.useState<UploadedContent | null>(
        null,
    );
    const [selectedSource, setSelectedSource] = React.useState<SourceKey>("LMS");

    const isAdmin = user?.role === "admin";

    // Auto-hide the success card after a short delay.
    React.useEffect(() => {
        if (inflight.kind !== "ready") return;
        const handle = window.setTimeout(
            () => setInflight({ kind: "idle" }),
            5000,
        );
        return () => window.clearTimeout(handle);
    }, [inflight]);

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

        const lmsName = lmsStaged.file.name;
        const sisName = sisStaged.file.name;
        const lmsText = lmsStaged.text;
        const sisText = sisStaged.text;

        setConfirming(true);
        setInflight({ kind: "processing", lmsName, sisName });

        // Reset zones immediately so the user can stage the next pair.
        setStaged({});

        try {
            const merged = mergeCsv(lmsText, sisText);
            const result = analyzeCsv(merged);
            if (result.totalStudents === 0) {
                const message =
                    "Bộ dữ liệu không có dòng hợp lệ (thiếu cột sid hoặc score).";
                setInflight({ kind: "error", message });
                toast.error("Bộ dữ liệu không có dữ liệu hợp lệ");
                return;
            }

            const lmsRecords = csvToLMSRecords(lmsText);
            const sisRecords = csvToSISRecords(sisText);

            const dataSources: {
                source_type: "sis" | "lms" | "custom";
                records: unknown[];
            }[] = [];
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

            await updateUserSettings({ auto_draft_enabled: false });
            await ingestData(dataSources);

            queryClient.invalidateQueries({
                queryKey: queryKeys.alerts.list(),
            });
            queryClient.invalidateQueries({
                queryKey: queryKeys.cases.all,
            });

            setUploaded({ lmsName, sisName, lmsRecords, sisRecords });

            setInflight({
                kind: "ready",
                totalStudents: result.totalStudents,
                highRisk: result.highRisk,
            });
            toast.success("Đã đồng bộ với máy chủ", {
                description: `${result.totalStudents.toLocaleString(
                    "vi-VN",
                )} sinh viên đã được cập nhật hệ thống.`,
            });
        } catch (err) {
            const message = cleanupErrorMessage(extractErrorMessage(err));
            setInflight({ kind: "error", message });
            toast.error("Đồng bộ thất bại", { description: message });
        } finally {
            setConfirming(false);
        }
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

            <InflightCard
                state={inflight}
                onDismiss={() => setInflight({ kind: "idle" })}
            />

            {uploaded ? (
                <>
                    <Tabs
                        value={selectedSource}
                        onValueChange={(v) =>
                            setSelectedSource(v as SourceKey)
                        }
                    >
                        <TabsList className="grid w-full grid-cols-2 md:w-auto md:inline-grid">
                            <TabsTrigger value="LMS" className="gap-1.5">
                                LMS
                                <span className="text-[10.5px] text-muted-foreground">
                                    {uploaded.lmsRecords.length.toLocaleString(
                                        "vi-VN",
                                    )}
                                </span>
                            </TabsTrigger>
                            <TabsTrigger value="SIS" className="gap-1.5">
                                SIS
                                <span className="text-[10.5px] text-muted-foreground">
                                    {uploaded.sisRecords.length.toLocaleString(
                                        "vi-VN",
                                    )}
                                </span>
                            </TabsTrigger>
                        </TabsList>
                    </Tabs>

                    {selectedSource === "LMS" ? (
                        <UploadedFileCard
                            title="Nội dung file LMS"
                            fileName={uploaded.lmsName}
                            rows={uploaded.lmsRecords}
                            columns={LMS_COLUMNS}
                        />
                    ) : (
                        <UploadedFileCard
                            title="Nội dung file SIS"
                            fileName={uploaded.sisName}
                            rows={uploaded.sisRecords}
                            columns={SIS_COLUMNS}
                        />
                    )}
                </>
            ) : (
                <Card className="rounded-2xl border-dashed border-border/60 bg-muted/20">
                    <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
                        <div className="grid size-10 place-items-center rounded-xl bg-muted text-muted-foreground">
                            <FileSpreadsheet className="size-4" />
                        </div>
                        <p className="text-sm text-muted-foreground">
                            Chưa có file nào được nhập — hãy upload bộ CSV để
                            xem nội dung.
                        </p>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}

function InflightCard({
    state,
    onDismiss,
}: {
    state: InflightStatus;
    onDismiss: () => void;
}) {
    if (state.kind === "idle") return null;

    if (state.kind === "processing") {
        return (
            <Card className="rounded-2xl border-border/60 bg-muted/30">
                <CardContent className="flex items-center gap-3 p-4">
                    <Loader2 className="size-4 shrink-0 animate-spin text-muted-foreground" />
                    <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium">Đang xử lý...</p>
                        <p className="truncate text-xs text-muted-foreground">
                            {state.lmsName} + {state.sisName}
                        </p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    if (state.kind === "ready") {
        return (
            <Card className="rounded-2xl border-success/30 bg-success/5">
                <CardContent className="flex items-center gap-3 p-4">
                    <CheckCircle2 className="size-4 shrink-0 text-success" />
                    <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-success">
                            Đã đồng bộ thành công
                        </p>
                        <p className="text-xs text-muted-foreground">
                            {state.totalStudents.toLocaleString("vi-VN")} sinh
                            viên · {state.highRisk.toLocaleString("vi-VN")} nguy
                            cơ cao
                        </p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="rounded-2xl border-destructive/30 bg-destructive/5">
            <CardContent className="flex items-start gap-3 p-4">
                <AlertCircle className="mt-0.5 size-4 shrink-0 text-destructive" />
                <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-destructive">
                        Đồng bộ thất bại
                    </p>
                    <p className="break-words text-xs text-muted-foreground">
                        {state.message}
                    </p>
                </div>
                <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="size-7 shrink-0 rounded-lg text-muted-foreground hover:text-destructive"
                    onClick={onDismiss}
                    aria-label="Đóng"
                >
                    <X className="size-4" />
                </Button>
            </CardContent>
        </Card>
    );
}

type Column<T> = {
    key: string;
    label: string;
    render: (row: T) => React.ReactNode;
    className?: string;
};

const LMS_COLUMNS: Column<LMSRecord>[] = [
    {
        key: "sid",
        label: "SID",
        render: (r) => <span className="font-mono text-xs">{r.sid}</span>,
    },
    {
        key: "course_id",
        label: "Mã môn",
        render: (r) => <span className="font-mono text-xs">{r.course_id || "—"}</span>,
    },
    {
        key: "course_name",
        label: "Tên môn",
        render: (r) => r.course_name || "—",
    },
    {
        key: "test_type",
        label: "Loại bài",
        render: (r) => r.test_type || "—",
    },
    {
        key: "score",
        label: "Điểm",
        className: "text-right",
        render: (r) => (
            <span className="font-mono text-xs">{r.score}</span>
        ),
    },
    {
        key: "academic_year",
        label: "Năm",
        render: (r) => r.academic_year || "—",
    },
    {
        key: "semester",
        label: "HK",
        render: (r) => r.semester || "—",
    },
    {
        key: "week",
        label: "Tuần",
        render: (r) => r.week ?? "—",
    },
    {
        key: "timestamp",
        label: "Thời gian",
        render: (r) =>
            r.timestamp
                ? new Date(r.timestamp).toLocaleString("vi-VN", {
                      hour12: false,
                  })
                : "—",
    },
];

const SIS_COLUMNS: Column<SISRecord>[] = [
    {
        key: "sid",
        label: "SID",
        render: (r) => <span className="font-mono text-xs">{r.sid}</span>,
    },
    {
        key: "student_name",
        label: "Tên sinh viên",
        render: (r) => r.student_name || "—",
    },
    {
        key: "email",
        label: "Email",
        className: "max-w-[200px] truncate",
        render: (r) => r.email || "—",
    },
    {
        key: "major",
        label: "Ngành",
        render: (r) => r.major || "—",
    },
    {
        key: "current_risk_status",
        label: "Risk",
        render: (r) => r.current_risk_status || "—",
    },
    {
        key: "intervention_status",
        label: "Trạng thái can thiệp",
        render: (r) => r.intervention_status || "—",
    },
    {
        key: "last_notified_timestamp",
        label: "Thông báo gần nhất",
        render: (r) =>
            r.last_notified_timestamp
                ? new Date(r.last_notified_timestamp).toLocaleString("vi-VN", {
                      hour12: false,
                  })
                : "—",
    },
    {
        key: "last_notified_satisfaction",
        label: "Hài lòng",
        render: (r) => r.last_notified_satisfaction ?? "—",
    },
];

function UploadedFileCard<T>({
    title,
    fileName,
    rows,
    columns,
}: {
    title: string;
    fileName: string;
    rows: T[];
    columns: Column<T>[];
}) {
    const preview = rows.slice(0, PREVIEW_LIMIT);
    const truncated = rows.length > PREVIEW_LIMIT;

    return (
        <Card className="stripe-cyan rounded-2xl border-accent-cyan/15 bg-gradient-to-br from-accent-cyan/22 via-accent-cyan/10 to-card">
            <CardContent className="p-0">
                <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 px-4 py-3 md:px-5">
                    <div className="flex min-w-0 items-center gap-2">
                        <FileSpreadsheet className="size-4 shrink-0 text-muted-foreground" />
                        <div className="min-w-0">
                            <p className="text-sm font-semibold">{title}</p>
                            <p className="truncate text-[11px] text-muted-foreground">
                                {fileName}
                            </p>
                        </div>
                    </div>
                    <Badge
                        variant="outline"
                        className="rounded-md font-mono text-xs"
                    >
                        {rows.length.toLocaleString("vi-VN")} dòng
                        {truncated
                            ? ` · hiển thị ${PREVIEW_LIMIT.toLocaleString(
                                  "vi-VN",
                              )} đầu`
                            : ""}
                    </Badge>
                </header>

                {rows.length === 0 ? (
                    <div className="px-4 py-8 text-center text-sm text-muted-foreground md:px-6">
                        File không có dòng hợp lệ.
                    </div>
                ) : (
                    <div className="max-h-[480px] overflow-auto">
                        <Table>
                            <TableHeader className="sticky top-0 z-10 bg-card/95 backdrop-blur">
                                <TableRow>
                                    {columns.map((c) => (
                                        <TableHead
                                            key={c.key}
                                            className={c.className}
                                        >
                                            {c.label}
                                        </TableHead>
                                    ))}
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {preview.map((row, idx) => (
                                    <TableRow key={idx}>
                                        {columns.map((c) => (
                                            <TableCell
                                                key={c.key}
                                                className={c.className}
                                            >
                                                {c.render(row)}
                                            </TableCell>
                                        ))}
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
