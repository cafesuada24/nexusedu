"use client";

import * as React from "react";
import { ChevronLeft, ChevronRight, Mail, Inbox } from "lucide-react";
import { LayoutGroup } from "framer-motion";
import { toast } from "sonner";
import { z } from "zod";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { GoalsDialog, type Goal } from "@/components/dashboard/goals-dialog";
import { type Problem, type StudentRow } from "@/lib/csv";
import {
    fetchStudentCases,
    generateAiDraftForAlert,
    ingestData,
    sendNudge,
} from "@/lib/api";
import { useAlerts, useUpdateAlertStatus } from "@/hooks/use-alerts";
import { useSocketEvent } from "@/hooks/use-socket";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query-keys";
import { useDataset } from "@/hooks/use-dataset";
import { cn } from "@/lib/utils";
import {
    type Alert,
    type CaseStatus,
    problemMeta,
    COLUMNS,
    pickRandomAppointment,
    fromBackendStatus,
    toBackendStatus,
} from "@/lib/alerts";
import { AlertSearch } from "./alert-center/alert-search";
import { KanbanColumn } from "./alert-center/kanban-column";
import { StudentDetailModal } from "./alert-center/student-detail-modal";
import { EmailEditorSheet } from "./email-editor-sheet";

export function AlertCenter() {
    const boardScrollRef = React.useRef<HTMLDivElement | null>(null);
    const [problemFilter, setProblemFilter] = React.useState<"all" | Problem>(
        "all",
    );
    const [query, setQuery] = React.useState("");
    const [goalsTargetId, setGoalsTargetId] = React.useState<string | null>(
        null,
    );
    const [detailsTargetId, setDetailsTargetId] = React.useState<string | null>(
        null,
    );
    const [emailTargetId, setEmailTargetId] = React.useState<string | null>(
        null,
    );
    const [requestedDraftById, setRequestedDraftById] = React.useState<
        Record<string, boolean>
    >({});
    const [aiDraftingById, setAiDraftingById] = React.useState<
        Record<string, boolean>
    >({});
    const [aiDraftErrorById, setAiDraftErrorById] = React.useState<
        Record<string, string>
    >({});
    const [aiDraftReadyById, setAiDraftReadyById] = React.useState<
        Record<string, boolean>
    >({});
    const [acceptingCaseById, setAcceptingCaseById] = React.useState<
        Record<string, boolean>
    >({});
    const [hiddenAlerts, setHiddenAlerts] = React.useState<Set<string>>(
        new Set(),
    );
    const [recentlyMoved, setRecentlyMoved] = React.useState<{
        alertId: string;
        status: CaseStatus;
    } | null>(null);
    const [canScrollLeft, setCanScrollLeft] = React.useState(false);
    const [canScrollRight, setCanScrollRight] = React.useState(false);
    const { dataset } = useDataset();

    const { data: remoteAlerts = [], isLoading } = useAlerts();
    const { mutate: updateStatus } = useUpdateAlertStatus();
    const queryClient = useQueryClient();

    useSocketEvent<{ sid: string; date: string; slot: string }>(
        "new_appointment",
        (data) => {
            queryClient.setQueryData(
                queryKeys.alerts.list(),
                (old: any[] | undefined) => {
                    if (!old) return [];
                    return old.map((alert) =>
                        alert.sid === data.sid
                            ? { ...alert, intervention_status: "booked" }
                            : alert,
                    );
                },
            );

            toast.success(`Sinh viên ${data.sid} vừa đặt lịch hẹn!`, {
                description: `Thời gian: ${data.date} lúc ${data.slot}`,
            });
        },
    );

    const [localAlertState, setLocalAlertState] = React.useState<
        Record<string, { goals: Goal[] }>
    >({});

    React.useEffect(() => {
        const saved = localStorage.getItem("alert-goals-state");
        if (saved) {
            try {
                setLocalAlertState(JSON.parse(saved));
            } catch (e) {
                console.error("Failed to parse goal state", e);
            }
        }
    }, []);

    React.useEffect(() => {
        localStorage.setItem(
            "alert-goals-state",
            JSON.stringify(localAlertState),
        );
    }, [localAlertState]);

    const alerts = React.useMemo(() => {
        const now = Math.floor(Date.now() / 1000);

        const getProblemFromStatus = (status: string): Problem => {
            const s = (status || "").toLowerCase();
            if (s.includes("final")) return "failed_final";
            if (s.includes("midterm") || s.includes("critical"))
                return "failed_midterm";
            return "low_average";
        };

        return remoteAlerts
            .filter(
                (r) =>
                    (r.intervention_status || "").toLowerCase() !== "dismissed",
            )
            .filter((r) => !hiddenAlerts.has(r.sid || ""))
            .map((r) => {
                const baseStatus = fromBackendStatus(r.intervention_status);
                // If it's in /cases/assigned (has advisor) but still 'notified', it should be in 'accepted' column
                const status =
                    baseStatus === "new" && r.assigned_advisor_id
                        ? "accepted"
                        : baseStatus;

                return {
                    id: r.sid || `missing-${Math.random()}`,
                    caseId: r.case_id || r.active_case_id || null,
                    name: r.student_name || "Unknown Student",
                    mssv: (r.sid || "").slice(0, 8).toUpperCase() || "N/A",
                    email: r.email || "",
                    problem: getProblemFromStatus(r.current_risk_status || ""),
                    summary: r.current_risk_status || "Unknown risk",
                    severity: (r.current_risk_status || "")
                        .toLowerCase()
                        .includes("elevated")
                        ? ("medium" as const)
                        : ("high" as const),
                    subject: "",
                    body: "",
                    lastContactedAt: null,
                    status: status,
                    movedAt: now,
                    draftJobId: null,
                    draftSubject: r.draft_subject || null,
                    draftBody: r.draft_body || null,
                    isGenerating:
                        r.is_generating || r.draft_status === "generating",
                    appointmentAt:
                        (r.intervention_status || "").toLowerCase() === "booked"
                            ? pickRandomAppointment()
                            : null,
                    goals: localAlertState[r.sid]?.goals || [],
                };
            });
    }, [remoteAlerts, localAlertState, hiddenAlerts]);

    const [collapsedCols, setCollapsedCols] = React.useState<
        Record<CaseStatus, boolean>
    >({
        new: false,
        accepted: false,
        contacted: false,
        scheduled: false,
        in_progress: false,
        resolved: false,
    });

    const toggleCollapse = (id: CaseStatus) =>
        setCollapsedCols((prev) => ({ ...prev, [id]: !prev[id] }));

    const [expandedCols, setExpandedCols] = React.useState<
        Record<CaseStatus, boolean>
    >({
        new: false,
        accepted: false,
        contacted: false,
        scheduled: false,
        in_progress: false,
        resolved: false,
    });

    const toggleExpand = (id: CaseStatus) =>
        setExpandedCols((prev) => ({ ...prev, [id]: !prev[id] }));

    const filteredAlerts = React.useMemo(() => {
        const q = query.trim().toLowerCase();
        return alerts.filter((a) => {
            const matchesProblem =
                problemFilter === "all" || a.problem === problemFilter;
            const matchesQuery =
                !q ||
                a.name.toLowerCase().includes(q) ||
                a.mssv.toLowerCase().includes(q) ||
                a.email.toLowerCase().includes(q) ||
                a.summary.toLowerCase().includes(q);
            return matchesProblem && matchesQuery;
        });
    }, [alerts, problemFilter, query]);

    const grouped = React.useMemo(() => {
        const map: Record<CaseStatus, Alert[]> = {
            new: [],
            accepted: [],
            contacted: [],
            scheduled: [],
            in_progress: [],
            resolved: [],
        };
        for (const a of filteredAlerts) map[a.status].push(a);
        map.scheduled.sort((a, b) => {
            const ta = a.appointmentAt ?? Number.POSITIVE_INFINITY;
            const tb = b.appointmentAt ?? Number.POSITIVE_INFINITY;
            return ta - tb;
        });
        return map;
    }, [filteredAlerts]);

    const totalCounts = React.useMemo(() => {
        const map: Record<CaseStatus, number> = {
            new: 0,
            accepted: 0,
            contacted: 0,
            scheduled: 0,
            in_progress: 0,
            resolved: 0,
        };
        for (const a of alerts) map[a.status]++;
        return map;
    }, [alerts]);

    const problemCounts = React.useMemo(() => {
        const counts: Record<Problem, number> = {
            failed_final: 0,
            failed_midterm: 0,
            low_average: 0,
        };
        for (const a of alerts) {
            counts[a.problem]++;
        }
        return counts;
    }, [alerts]);

    const isAcceptedAiProcessing = React.useMemo(
        () => grouped.accepted.some((a) => Boolean(aiDraftingById[a.id])),
        [grouped, aiDraftingById],
    );

    const markRecentlyMoved = React.useCallback(
        (alertId: string, status: CaseStatus) => {
            setRecentlyMoved({ alertId, status });
        },
        [],
    );

    React.useEffect(() => {
        if (!recentlyMoved) return;
        const timeoutId = window.setTimeout(() => {
            setRecentlyMoved(null);
        }, 3200);
        return () => window.clearTimeout(timeoutId);
    }, [recentlyMoved]);

    const resolveCaseIdForAlert = (a: Alert): string | null =>
        a.caseId || a.activeCaseId || null;

    const handleGenerateDraft = async (a: Alert) => {
        const caseId = resolveCaseIdForAlert(a);
        if (!caseId) {
            toast.error("Không tìm thấy mã case", {
                description: "Vui lòng thử tải lại trang hoặc nhận lại ca.",
            });
            return;
        }

        setAiDraftingById((prev) => ({ ...prev, [a.id]: true }));
        setAiDraftErrorById((prev) => {
            if (!prev[a.id]) return prev;
            const next = { ...prev };
            delete next[a.id];
            return next;
        });

        try {
            await generateAiDraftForAlert(a.id, caseId);
            setRequestedDraftById((prev) => ({ ...prev, [a.id]: true }));
            setAiDraftReadyById((prev) => ({ ...prev, [a.id]: true }));
            toast.success("Bản nháp đã sẵn sàng", {
                description: "AI đã soạn xong nội dung email hỗ trợ.",
            });
        } catch (err: any) {
            const draftError = String(err?.message || err || "");
            setAiDraftErrorById((prev) => ({
                ...prev,
                [a.id]: draftError || "Không thể tạo bản nháp AI.",
            }));
            toast.error("Không thể tạo nội dung email", {
                description: draftError,
            });
        } finally {
            setAiDraftingById((prev) => {
                const next = { ...prev };
                delete next[a.id];
                return next;
            });
        }
    };

    const handleSaveEmail = (a: Alert) => {
        // When we save from the editor, we effectively "contact" the student
        moveTo(a, "contacted", "Đã lưu bản thảo và sẵn sàng gửi");
        setEmailTargetId(null);
    };

    const moveTo = async (a: Alert, status: CaseStatus, message: string) => {
        const sid = a.id;
        let caseId = resolveCaseIdForAlert(a);

        // --- UPSERT LOGIC (Ghost Case Prevention) ---
        // If we're accepting a student who doesn't have an active case record yet,
        // we must force the backend to create one via a minimal SIS data ingestion.
        if (status === "accepted" && !caseId) {
            const profile = studentProfilesById[sid];
            if (profile) {
                console.log(
                    "[AlertCenter] Triggering 'Upsert' for ghost student:",
                    sid,
                );
                try {
                    await ingestData([
                        {
                            source_type: "sis",
                            records: [
                                {
                                    sid: profile.id,
                                    student_name: profile.name,
                                    email: profile.email,
                                    major: profile.major || "Unknown",
                                    current_risk_status:
                                        a.severity === "high"
                                            ? "Critical"
                                            : "Elevated",
                                    intervention_status: "new",
                                },
                            ],
                        },
                    ]);

                    // Refresh alerts to get the newly created case ID
                    await queryClient.invalidateQueries({
                        queryKey: queryKeys.alerts.list(),
                    });
                    // Small wait to allow the refetch and the zipping logic in useAlerts to settle
                    await new Promise((r) => setTimeout(r, 1000));

                    // Look up the newly resolved case ID from the freshly fetched data
                    const latestData = queryClient.getQueryData<any[]>(
                        queryKeys.alerts.list(),
                    );
                    const latestAlert = latestData?.find(
                        (la) => la.sid === sid,
                    );
                    caseId = latestAlert?.active_case_id || null;
                } catch (err) {
                    console.error("[AlertCenter] Upsert failed:", err);
                }
            }
        }
        if (status === "accepted") {
            if (!z.string().uuid().safeParse(sid).success) {
                toast.error("Mã sinh viên không hợp lệ", {
                    description:
                        "Không thể nhận case vì student_id không phải UUID hợp lệ.",
                });
                return;
            }

            setAcceptingCaseById((prev) => ({ ...prev, [a.id]: true }));
            setAiDraftErrorById((prev) => {
                if (!prev[a.id]) return prev;
                const next = { ...prev };
                delete next[a.id];
                return next;
            });
            setAiDraftReadyById((prev) => {
                if (!prev[a.id]) return prev;
                const next = { ...prev };
                delete next[a.id];
                return next;
            });

            updateStatus(
                {
                    case_id: caseId || sid,
                    status: toBackendStatus(status),
                    sid,
                    isAccept: true,
                },
                {
                    onSuccess: async () => {
                        markRecentlyMoved(a.id, status);
                        // Manual trigger removed - AI draft is now triggered by Advisor
                    },
                    onError: () => {
                        setAcceptingCaseById((prev) => {
                            const next = { ...prev };
                            delete next[a.id];
                            return next;
                        });
                    },
                    onSettled: () => {
                        setAcceptingCaseById((prev) => {
                            const next = { ...prev };
                            delete next[a.id];
                            return next;
                        });
                    },
                },
            );
            return;
        }

        // "contacted" transition uses POST /email/send (no generic PATCH /status endpoint)
        if (status === "contacted") {
            if (!caseId) {
                toast.error("Không tìm thấy mã case", {
                    description: "Vui lòng tải lại danh sách và thử lại.",
                    action: {
                        label: "Tải lại",
                        onClick: () =>
                            queryClient.invalidateQueries({
                                queryKey: queryKeys.alerts.list(),
                            }),
                    },
                });
                return;
            }
            try {
                await sendNudge(caseId, {
                    body: a.body || a.draftBody || "",
                });
                markRecentlyMoved(a.id, status);
                setEmailTargetId(null);
                if (message) toast.success(message);
                queryClient.invalidateQueries({
                    queryKey: queryKeys.alerts.list(),
                });
            } catch (err: any) {
                toast.error("Không thể gửi email", {
                    description: err.message,
                });
            }
            return;
        }

        if (!caseId) {
            // Non-accept transitions without a case are treated as a ghost case
            toast.error("Không tìm thấy hồ sơ case (Ghost Case)", {
                description:
                    "Sinh viên chưa có case trong hệ thống. Vui lòng thử 'Tiếp nhận ca' trước.",
                action: {
                    label: "Tải lại",
                    onClick: () =>
                        queryClient.invalidateQueries({
                            queryKey: queryKeys.alerts.list(),
                        }),
                },
            });
            return;
        }

        updateStatus(
            { case_id: caseId, status: toBackendStatus(status), sid },
            {
                onSuccess: () => {
                    markRecentlyMoved(a.id, status);
                    if (message) toast.success(message);
                },
            },
        );
    };

    const handleGetProfile = React.useCallback((a: Alert) => {
        setDetailsTargetId(a.id);
    }, []);

    const addGoal = (
        alertId: string,
        title: string,
        deadline: string | null,
    ) => {
        const newGoal: Goal = {
            id: `g_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`,
            title,
            deadline,
            done: false,
            createdAt: Math.floor(Date.now() / 1000),
        };
        setLocalAlertState((prev) => ({
            ...prev,
            [alertId]: {
                ...prev[alertId],
                goals: [...(prev[alertId]?.goals || []), newGoal],
            },
        }));
        toast.success("Đã thêm mục tiêu mới");
    };

    const toggleGoal = (alertId: string, goalId: string) => {
        setLocalAlertState((prev) => ({
            ...prev,
            [alertId]: {
                ...prev[alertId],
                goals: (prev[alertId]?.goals || []).map((g) =>
                    g.id === goalId ? { ...g, done: !g.done } : g,
                ),
            },
        }));
    };

    const removeGoal = (alertId: string, goalId: string) => {
        setLocalAlertState((prev) => ({
            ...prev,
            [alertId]: {
                ...prev[alertId],
                goals: (prev[alertId]?.goals || []).filter(
                    (g) => g.id !== goalId,
                ),
            },
        }));
    };

    const goalsTarget = React.useMemo(
        () =>
            goalsTargetId ? alerts.find((a) => a.id === goalsTargetId) : null,
        [alerts, goalsTargetId],
    );
    const detailsTarget = React.useMemo(
        () =>
            detailsTargetId
                ? alerts.find((a) => a.id === detailsTargetId)
                : null,
        [alerts, detailsTargetId],
    );
    const studentProfilesById = React.useMemo(() => {
        const map: Record<string, StudentRow | undefined> = {};
        for (const student of dataset?.students ?? []) {
            map[student.id] = student;
        }
        return map;
    }, [dataset?.students]);

    const updateScrollButtons = React.useCallback(() => {
        const el = boardScrollRef.current;
        if (!el) return;
        const maxLeft = Math.max(0, el.scrollWidth - el.clientWidth);
        setCanScrollLeft(el.scrollLeft > 4);
        setCanScrollRight(maxLeft - el.scrollLeft > 4);
    }, []);

    React.useEffect(() => {
        const el = boardScrollRef.current;
        if (!el) return;

        const handleScroll = () => updateScrollButtons();
        const handleResize = () => updateScrollButtons();

        updateScrollButtons();
        el.addEventListener("scroll", handleScroll, { passive: true });
        window.addEventListener("resize", handleResize);

        const resizeObserver = new ResizeObserver(() => updateScrollButtons());
        resizeObserver.observe(el);

        return () => {
            el.removeEventListener("scroll", handleScroll);
            window.removeEventListener("resize", handleResize);
            resizeObserver.disconnect();
        };
    }, [updateScrollButtons, grouped, collapsedCols, expandedCols]);

    const getScrollStep = React.useCallback(() => {
        const el = boardScrollRef.current;
        if (!el) return 400;
        const firstColumn = el.firstElementChild as HTMLElement | null;
        const firstColumnWidth =
            firstColumn?.getBoundingClientRect().width ?? 380;
        const styles = window.getComputedStyle(el);
        const gap =
            Number.parseFloat(styles.columnGap || styles.gap || "0") || 0;
        return Math.round(firstColumnWidth + gap);
    }, []);

    const scrollBoardBy = (direction: "left" | "right") => {
        const el = boardScrollRef.current;
        if (!el) return;
        const step = getScrollStep();
        const left = direction === "left" ? -step : step;
        el.scrollBy({ left, behavior: "smooth" });
    };

    if (isLoading) {
        return (
            <Card className="rounded-2xl border-border/60">
                <CardHeader>
                    <Skeleton className="h-6 w-48" />
                    <Skeleton className="h-4 w-72" />
                </CardHeader>
                <CardContent className="grid gap-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
                    {[0, 1, 2, 3, 4].map((i) => (
                        <Skeleton key={i} className="h-72 rounded-2xl" />
                    ))}
                </CardContent>
            </Card>
        );
    }

    return (
        <>
            <div className="flex min-h-0 min-w-0 max-w-full flex-1 flex-col gap-3 overflow-hidden">
                <AlertSearch
                    query={query}
                    onQueryChange={setQuery}
                    problemFilter={problemFilter}
                    onProblemFilterChange={setProblemFilter}
                    totalAlerts={alerts.length}
                    problemCounts={problemCounts}
                />

                <LayoutGroup id="alert-board">
                    <div className="relative min-h-0 w-full max-w-full flex-1 overflow-hidden">
                        <div
                            ref={boardScrollRef}
                            className="hide-scrollbar flex h-full min-w-0 w-full max-w-full items-stretch gap-3 overflow-x-auto overflow-y-hidden bg-transparent pb-1 [-webkit-overflow-scrolling:touch]"
                            role="list"
                        >
                            {COLUMNS.map((col) => (
                                <KanbanColumn
                                    key={col.id}
                                    column={col}
                                    items={grouped[col.id]}
                                    totalInColumn={totalCounts[col.id]}
                                    highlightedAlertId={
                                        recentlyMoved?.status === col.id
                                            ? recentlyMoved.alertId
                                            : null
                                    }
                                    isActivated={
                                        recentlyMoved?.status === col.id
                                    }
                                    isCollapsed={collapsedCols[col.id]}
                                    isExpanded={expandedCols[col.id]}
                                    onToggleCollapse={toggleCollapse}
                                    onToggleExpand={toggleExpand}
                                    onViewDetails={handleGetProfile}
                                    onEditEmail={(a) => setEmailTargetId(a.id)}
                                    onGenerateDraft={handleGenerateDraft}
                                    onMove={moveTo}
                                    onOpenGoals={(id) => setGoalsTargetId(id)}
                                    studentProfilesById={studentProfilesById}
                                    aiDraftingById={Object.fromEntries(
                                        Object.entries(aiDraftingById).concat(
                                            filteredAlerts
                                                .filter((a) => a.isGenerating)
                                                .map((a) => [a.id, true]),
                                        ),
                                    )}
                                    aiDraftErrorById={aiDraftErrorById}
                                    aiDraftReadyById={aiDraftReadyById}
                                    acceptingCaseById={acceptingCaseById}
                                />
                            ))}
                        </div>
                    </div>
                </LayoutGroup>

                <Button
                    type="button"
                    variant="ghost"
                    onClick={() => scrollBoardBy("left")}
                    className={cn(
                        "fixed left-2 top-1/2 z-[100] h-12 w-12 -translate-y-1/2 rounded-full border border-white/20 bg-blue-600/90 text-white shadow-xl shadow-blue-500/40 backdrop-blur-md transition-all duration-200 hover:scale-110 hover:bg-blue-700 hover:opacity-100 hover:shadow-[0_0_18px_rgba(37,99,235,0.45)] dark:bg-blue-500/90 dark:hover:bg-blue-600 md:left-[260px]",
                        canScrollLeft
                            ? "opacity-95"
                            : "pointer-events-none opacity-0",
                        isAcceptedAiProcessing &&
                            "animate-pulse ring-2 ring-blue-300/70 shadow-[0_0_24px_rgba(59,130,246,0.35)] dark:ring-cyan-400/55 dark:shadow-[0_0_24px_rgba(56,189,248,0.35)]",
                    )}
                    aria-label="Cuộn sang trái"
                >
                    <ChevronLeft className="size-6 text-white" />
                </Button>

                <Button
                    type="button"
                    variant="ghost"
                    onClick={() => scrollBoardBy("right")}
                    className={cn(
                        "fixed right-5 top-1/2 z-[100] h-12 w-12 -translate-y-1/2 rounded-full border border-white/20 bg-blue-600/90 text-white shadow-xl shadow-blue-500/40 backdrop-blur-md transition-all duration-200 hover:scale-110 hover:bg-blue-700 hover:opacity-100 hover:shadow-[0_0_18px_rgba(37,99,235,0.45)] dark:bg-blue-500/90 dark:hover:bg-blue-600",
                        canScrollRight
                            ? "opacity-95"
                            : "pointer-events-none opacity-0",
                        isAcceptedAiProcessing &&
                            "animate-pulse ring-2 ring-blue-300/70 shadow-[0_0_24px_rgba(59,130,246,0.35)] dark:ring-cyan-400/55 dark:shadow-[0_0_24px_rgba(56,189,248,0.35)]",
                    )}
                    aria-label="Cuộn sang phải"
                >
                    <ChevronRight className="size-6 text-white" />
                </Button>

                {alerts.length === 0 && (
                    <Card className="rounded-2xl border-dashed border-border/60">
                        <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
                            <Inbox className="size-10 text-muted-foreground" />
                            <p className="font-serif text-lg font-semibold">
                                Không có cảnh báo
                            </p>
                        </CardContent>
                    </Card>
                )}

                {alerts.length > 0 && filteredAlerts.length === 0 && (
                    <Card className="rounded-2xl border-dashed border-border/60">
                        <CardContent className="flex flex-col items-center gap-2 py-8 text-center">
                            <Mail className="size-8 text-muted-foreground" />
                            <p className="text-sm text-muted-foreground">
                                Không có kết quả phù hợp.
                            </p>
                        </CardContent>
                    </Card>
                )}
            </div>

            <StudentDetailModal
                open={detailsTargetId !== null}
                onOpenChange={(open) => {
                    if (!open) setDetailsTargetId(null);
                }}
                alert={detailsTarget ?? null}
                studentProfile={
                    detailsTarget
                        ? studentProfilesById[detailsTarget.id]
                        : undefined
                }
            />

            <EmailEditorSheet
                alert={
                    emailTargetId
                        ? alerts.find((a) => a.id === emailTargetId) ?? null
                        : null
                }
                onClose={() => setEmailTargetId(null)}
                onSave={handleSaveEmail}
                onGenerateDraft={() => {
                    const a = emailTargetId
                        ? alerts.find((al) => al.id === emailTargetId) ?? null
                        : null;
                    if (a) handleGenerateDraft(a);
                }}
                isAiDrafting={
                    emailTargetId ? !!aiDraftingById[emailTargetId] : false
                }
            />

            <GoalsDialog
                alert={
                    goalsTarget
                        ? {
                              id: goalsTarget.id,
                              name: goalsTarget.name,
                              problem: goalsTarget.problem,
                              problemLabel:
                                  problemMeta[goalsTarget.problem].label,
                              problemTone:
                                  problemMeta[goalsTarget.problem].tone,
                              problemIcon:
                                  problemMeta[goalsTarget.problem].icon,
                              goals: goalsTarget.goals,
                          }
                        : null
                }
                onClose={() => setGoalsTargetId(null)}
                onAdd={addGoal}
                onToggle={toggleGoal}
                onRemove={removeGoal}
            />
        </>
    );
}
