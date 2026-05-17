"use client"

import * as React from "react"
import Link from "next/link"
import {
    AlarmClock,
    ArrowRight,
    BellRing,
    LifeBuoy,
    MailOpen,
    RefreshCw,
    Trophy,
    Zap,
} from "lucide-react"
import {
    AnimatePresence,
    animate,
    motion,
    useMotionValue,
    useReducedMotion,
    type Variants,
} from "framer-motion"
import {
    Bar,
    BarChart,
    Cell,
    Line,
    LineChart,
    ResponsiveContainer,
    Tooltip as ReTooltip,
} from "recharts"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import { useAuth } from "@/hooks/use-auth"
import { useAdvisorDashboard } from "@/hooks/use-advisors"
import { type EmergencyDashboard } from "@/lib/api"
import { cn } from "@/lib/utils"

const MONTH_NAMES_VI = [
    "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6",
    "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12",
]

const containerVariants: Variants = {
    hidden: { opacity: 0 },
    show: {
        opacity: 1,
        transition: { staggerChildren: 0.08, delayChildren: 0.05 },
    },
}

const itemVariants: Variants = {
    hidden: { opacity: 0, y: 16 },
    show: {
        opacity: 1,
        y: 0,
        transition: { type: "spring", stiffness: 120, damping: 18 },
    },
}

/* ─── Animated counter ──────────────────────────────────────────────────── */

function useCountUp(target: number, duration = 1.2, decimals = 0) {
    const reduce = useReducedMotion()
    const mv = useMotionValue(0)
    const [display, setDisplay] = React.useState(() =>
        reduce ? target.toFixed(decimals) : "0"
    )

    React.useEffect(() => {
        if (reduce) {
            setDisplay(target.toFixed(decimals))
            return
        }
        const controls = animate(mv, target, {
            duration,
            ease: [0.16, 1, 0.3, 1],
            onUpdate: (v) => setDisplay(v.toFixed(decimals)),
        })
        return () => controls.stop()
    }, [target, duration, decimals, mv, reduce])

    return display
}

function CountUp({
    value,
    decimals = 0,
    suffix,
    className,
}: {
    value: number
    decimals?: number
    suffix?: string
    className?: string
}) {
    const display = useCountUp(value, 1.2, decimals)
    return (
        <span
            className={cn("tabular-nums", className)}
            aria-label={`${value.toFixed(decimals)}${suffix ?? ""}`}
        >
            {display}
            {suffix}
        </span>
    )
}

/* ─── Hero band ─────────────────────────────────────────────────────────── */

function HeroBand({ data }: { data: EmergencyDashboard }) {
    const { impact } = data
    const isTopThree =
        typeof impact.ranking_position === "number" &&
        impact.ranking_position > 0 &&
        impact.ranking_position <= 3

    const monthLabel = `${MONTH_NAMES_VI[impact.month - 1] ?? `Tháng ${impact.month}`}/${impact.year}`

    const chartData = impact.weekly_history.map((h) => ({ name: `W${h.week}`, xp: h.xp }))
    const maxXp = chartData.reduce((m, d) => Math.max(m, d.xp), 0)
    const peakWeek = chartData.length
        ? chartData.reduce((p, c) => (c.xp > p.xp ? c : p), chartData[0])
        : null

    return (
        <motion.div variants={itemVariants}>
            <Card className="stripe-primary relative overflow-hidden rounded-3xl border-primary/20 bg-gradient-to-br from-primary/15 via-primary/5 to-card">
                {/* Decorative blob */}
                <div
                    aria-hidden
                    className="pointer-events-none absolute -right-16 -top-16 size-64 rounded-full bg-primary/10 blur-3xl"
                />

                <CardContent className="relative grid gap-6 p-6 md:grid-cols-[1.45fr_1fr] md:p-8">
                    {/* LEFT: XP + chart */}
                    <div className="flex flex-col gap-5">
                        <div className="flex items-start justify-between gap-4">
                            <div className="flex flex-col gap-1.5">
                                <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary/80">
                                    Điểm tác động cá nhân
                                </span>
                                <div className="flex items-baseline gap-2">
                                    <CountUp
                                        value={impact.current_xp}
                                        className="font-serif text-5xl font-black leading-none text-primary md:text-6xl"
                                    />
                                    <span className="font-mono text-base font-bold text-primary/70">
                                        XP
                                    </span>
                                </div>
                                <p className="text-xs text-muted-foreground">
                                    {monthLabel} • Hiệu suất tích lũy
                                </p>
                            </div>

                            <span
                                className="grid size-12 shrink-0 place-items-center rounded-2xl bg-primary/10 text-primary ring-1 ring-primary/20"
                                aria-hidden
                            >
                                <Zap className="size-6" />
                            </span>
                        </div>

                        {chartData.length > 0 ? (
                            <div className="-mx-1 h-24 w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart
                                        data={chartData}
                                        margin={{ top: 6, right: 4, bottom: 0, left: 4 }}
                                    >
                                        <ReTooltip
                                            cursor={{ fill: "var(--color-primary)", opacity: 0.05 }}
                                            contentStyle={{
                                                borderRadius: 12,
                                                border: "1px solid var(--color-border)",
                                                background: "var(--color-popover)",
                                                fontSize: 12,
                                                padding: "6px 10px",
                                            }}
                                            labelStyle={{ fontWeight: 600 }}
                                            formatter={(v: number) => [`${v} XP`, "Điểm"]}
                                        />
                                        <Bar
                                            dataKey="xp"
                                            radius={[6, 6, 2, 2]}
                                            animationDuration={1400}
                                            animationEasing="ease-out"
                                        >
                                            {chartData.map((entry, i) => {
                                                const isLast = i === chartData.length - 1
                                                const isPeak = peakWeek?.name === entry.name
                                                return (
                                                    <Cell
                                                        key={entry.name}
                                                        fill="var(--color-primary)"
                                                        fillOpacity={
                                                            isLast ? 1 : isPeak ? 0.55 : 0.22
                                                        }
                                                    />
                                                )
                                            })}
                                        </Bar>
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        ) : (
                            <div className="flex h-24 items-center justify-center rounded-xl bg-muted/30 text-xs text-muted-foreground">
                                Chưa có dữ liệu tuần
                            </div>
                        )}

                        <div className="flex flex-wrap items-center gap-3 text-[11px] font-medium text-muted-foreground">
                            <span className="inline-flex items-center gap-1.5">
                                <span className="size-2 rounded-full bg-primary" />
                                Tuần hiện tại
                            </span>
                            {peakWeek && peakWeek.xp > 0 && peakWeek.name !== chartData.at(-1)?.name && (
                                <span className="inline-flex items-center gap-1.5">
                                    <span className="size-2 rounded-full bg-primary/55" />
                                    Đỉnh: {peakWeek.name} ({peakWeek.xp} XP)
                                </span>
                            )}
                            {maxXp > 0 && (
                                <span className="ml-auto font-mono text-muted-foreground/80">
                                    max {maxXp} XP/tuần
                                </span>
                            )}
                        </div>
                    </div>

                    {/* RIGHT: ranking + completion */}
                    <div className="flex flex-col gap-4 border-t border-primary/15 pt-5 md:border-l md:border-t-0 md:pl-6 md:pt-0">
                        <motion.div
                            animate={
                                isTopThree
                                    ? { rotate: [0, -3, 3, -2, 0] }
                                    : undefined
                            }
                            transition={{
                                repeat: Infinity,
                                duration: 2.4,
                                ease: "easeInOut",
                                repeatDelay: 2,
                            }}
                            className={cn(
                                "flex items-center gap-3 rounded-2xl p-4 ring-1",
                                isTopThree
                                    ? "bg-warning/10 ring-warning/30"
                                    : "bg-muted/40 ring-border/60"
                            )}
                        >
                            <span
                                className={cn(
                                    "grid size-11 place-items-center rounded-xl ring-1",
                                    isTopThree
                                        ? "bg-warning/20 text-warning ring-warning/30"
                                        : "bg-card text-muted-foreground ring-border"
                                )}
                            >
                                <Trophy className="size-5" />
                            </span>
                            <div className="min-w-0 flex-1">
                                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                                    Vị trí bảng xếp hạng
                                </p>
                                <p className="mt-0.5 font-serif text-2xl font-bold leading-none">
                                    {impact.ranking_position
                                        ? `Top ${impact.ranking_position}`
                                        : "—"}
                                </p>
                            </div>
                            {isTopThree && (
                                <Badge
                                    variant="outline"
                                    className="border-warning/30 bg-warning/10 text-[10px] font-bold uppercase tracking-wider text-warning"
                                >
                                    Xuất sắc
                                </Badge>
                            )}
                        </motion.div>

                        <div className="flex flex-col gap-2 rounded-2xl bg-card/60 p-4 ring-1 ring-border/60">
                            <div className="flex items-center justify-between gap-3">
                                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                                    Tỉ lệ hoàn thành tháng
                                </p>
                                <CountUp
                                    value={Math.round(impact.completion_rate * 100)}
                                    suffix="%"
                                    className="font-serif text-xl font-bold text-foreground"
                                />
                            </div>
                            <Progress
                                value={Math.min(100, Math.max(0, impact.completion_rate * 100))}
                                className="h-2 bg-primary/10"
                                indicatorClassName="bg-gradient-to-r from-primary to-primary/70"
                            />
                            <p className="text-[11px] text-muted-foreground">
                                {impact.completion_rate >= 0.8
                                    ? "Đang vượt tiến độ tháng này"
                                    : impact.completion_rate >= 0.5
                                        ? "Tiếp tục giữ nhịp can thiệp"
                                        : "Cần đẩy nhanh các ca đang mở"}
                            </p>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </motion.div>
    )
}

/* ─── KPI cards ─────────────────────────────────────────────────────────── */

function PriorityCard({ count }: { count: number }) {
    const hasQueue = count > 0
    return (
        <motion.div variants={itemVariants}>
            <Card
                className={cn(
                    "group relative h-full overflow-hidden rounded-2xl border transition-shadow hover:shadow-md",
                    hasQueue
                        ? "border-destructive/25 bg-destructive/5"
                        : "border-border bg-card"
                )}
            >
                <CardContent className="flex h-full flex-col gap-3 p-5">
                    <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                            <span
                                className={cn(
                                    "relative grid size-9 place-items-center rounded-xl ring-1",
                                    hasQueue
                                        ? "bg-destructive/10 text-destructive ring-destructive/20"
                                        : "bg-muted text-muted-foreground ring-border"
                                )}
                            >
                                <BellRing className="size-4" />
                                {hasQueue && (
                                    <span className="absolute -right-0.5 -top-0.5 flex size-2.5">
                                        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-destructive opacity-70" />
                                        <span className="relative inline-flex size-2.5 rounded-full bg-destructive" />
                                    </span>
                                )}
                            </span>
                            <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                                Hàng đợi ưu tiên
                            </span>
                        </div>
                    </div>

                    <div className="flex items-baseline gap-1.5">
                        <CountUp
                            value={count}
                            className={cn(
                                "font-serif text-4xl font-black leading-none",
                                hasQueue ? "text-destructive" : "text-foreground/60"
                            )}
                        />
                        <span className="text-xs font-medium text-muted-foreground">SV đang chờ</span>
                    </div>

                    <p className="text-[11px] text-muted-foreground">
                        {hasQueue
                            ? "Sinh viên rủi ro cao chưa được tiếp nhận."
                            : "Không có sinh viên nào đang chờ. Tốt lắm!"}
                    </p>

                    {hasQueue && (
                        <Button
                            asChild
                            size="sm"
                            variant="ghost"
                            className="mt-auto w-fit gap-1.5 rounded-lg px-2 text-xs font-semibold text-destructive hover:bg-destructive/10 hover:text-destructive"
                        >
                            <Link href="/dashboard/alerts">
                                Mở danh sách <ArrowRight className="size-3.5" />
                            </Link>
                        </Button>
                    )}
                </CardContent>
            </Card>
        </motion.div>
    )
}

function ResponseCard({ kpi }: { kpi: EmergencyDashboard["response_kpi"] }) {
    const pct = Math.round(kpi.within_kpi_rate * 100)
    const onTrack = kpi.within_kpi_rate >= 0.8
    const hasBreach = kpi.sla_breach_count > 0

    return (
        <motion.div variants={itemVariants}>
            <Card className="group relative h-full overflow-hidden rounded-2xl border bg-card transition-shadow hover:shadow-md">
                <CardContent className="flex h-full flex-col gap-3 p-5">
                    <div className="flex items-center gap-2">
                        <span
                            className={cn(
                                "relative grid size-9 place-items-center rounded-xl ring-1",
                                onTrack
                                    ? "bg-success/10 text-success ring-success/20"
                                    : "bg-warning/15 text-warning ring-warning/25"
                            )}
                        >
                            <AlarmClock className="size-4" />
                            {hasBreach && (
                                <span className="absolute -right-0.5 -top-0.5 flex size-2.5">
                                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-destructive opacity-70" />
                                    <span className="relative inline-flex size-2.5 rounded-full bg-destructive" />
                                </span>
                            )}
                        </span>
                        <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                            Thời gian phản hồi
                        </span>
                    </div>

                    <div className="flex items-baseline gap-1.5">
                        <CountUp
                            value={kpi.avg_response_hours}
                            decimals={1}
                            className={cn(
                                "font-serif text-4xl font-bold leading-none",
                                onTrack ? "text-success" : "text-warning"
                            )}
                        />
                        <span className="text-sm font-bold text-muted-foreground">giờ</span>
                        <span className="ml-1 font-mono text-[11px] text-muted-foreground/80">
                            mục tiêu &lt;{kpi.target_hours}h
                        </span>
                    </div>

                    <div className="flex flex-col gap-1.5">
                        <div className="flex items-center justify-between text-[10px] font-medium">
                            <span
                                className={cn(
                                    "font-mono font-semibold",
                                    onTrack ? "text-success" : "text-warning"
                                )}
                            >
                                {pct}% đạt KPI
                            </span>
                            <span className="text-muted-foreground">
                                {onTrack ? "Đúng nhịp" : "Cần cải thiện"}
                            </span>
                        </div>
                        <Progress
                            value={pct}
                            className="h-1.5"
                            indicatorClassName={cn(onTrack ? "bg-success" : "bg-warning")}
                        />
                    </div>

                    <p className={cn(
                        "mt-auto text-[11px]",
                        hasBreach ? "font-medium text-destructive" : "text-muted-foreground"
                    )}>
                        {hasBreach
                            ? `${kpi.sla_breach_count} ca đã quá hạn KPI`
                            : "Không có ca quá hạn"}
                    </p>
                </CardContent>
            </Card>
        </motion.div>
    )
}

function ActivationCard({
    activation,
    weeklyHistory,
}: {
    activation: number
    weeklyHistory: EmergencyDashboard["impact"]["weekly_history"]
}) {
    const pct = Math.round(activation * 100)
    const tip =
        activation >= 0.7
            ? "Tốc độ kích hoạt xuất sắc"
            : activation >= 0.4
                ? "Đang tăng trưởng ổn định"
                : "Cần đẩy mạnh phản hồi sớm"

    const sparkData = weeklyHistory.map((h) => ({ name: `W${h.week}`, v: h.xp }))

    return (
        <motion.div variants={itemVariants}>
            <Card className="group relative h-full overflow-hidden rounded-2xl border bg-card transition-shadow hover:shadow-md">
                <CardContent className="flex h-full flex-col gap-3 p-5">
                    <div className="flex items-center gap-2">
                        <span className="grid size-9 place-items-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/20">
                            <MailOpen className="size-4" />
                        </span>
                        <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                            Tỉ lệ kích hoạt
                        </span>
                    </div>

                    <div className="flex items-baseline gap-1.5">
                        <CountUp
                            value={pct}
                            suffix="%"
                            className="font-serif text-4xl font-bold leading-none text-primary"
                        />
                    </div>

                    {sparkData.length > 1 ? (
                        <div className="-mx-1 h-12 w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={sparkData} margin={{ top: 4, right: 4, bottom: 0, left: 4 }}>
                                    <Line
                                        type="monotone"
                                        dataKey="v"
                                        stroke="var(--color-primary)"
                                        strokeWidth={2}
                                        dot={false}
                                        animationDuration={1500}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    ) : (
                        <div className="h-12" />
                    )}

                    <p className="mt-auto text-[11px] text-muted-foreground">{tip}</p>
                </CardContent>
            </Card>
        </motion.div>
    )
}

function RecoveryCard({ recovery }: { recovery: EmergencyDashboard["recovery"] }) {
    const pct = Math.round(
        Math.min(1, Math.max(0, recovery.recovery_rate)) * 100
    )
    const avgDays = recovery.avg_recovery_days
    const showDays = Number.isFinite(avgDays) && avgDays > 0

    return (
        <motion.div variants={itemVariants}>
            <Card className="group relative h-full overflow-hidden rounded-2xl border bg-card transition-shadow hover:shadow-md">
                <CardContent className="flex h-full flex-col gap-3 p-5">
                    <div className="flex items-center gap-2">
                        <span className="grid size-9 place-items-center rounded-xl bg-success/10 text-success ring-1 ring-success/20">
                            <LifeBuoy className="size-4" />
                        </span>
                        <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                            Tỉ lệ ổn định
                        </span>
                    </div>

                    <div className="flex items-baseline gap-1.5">
                        <CountUp
                            value={pct}
                            suffix="%"
                            className="font-serif text-4xl font-bold leading-none text-success"
                        />
                    </div>

                    <div className="flex flex-col gap-1.5">
                        <div className="flex items-center justify-between text-[10px] font-medium">
                            <span className="font-mono font-semibold text-success">
                                {recovery.stabilized_students}/{recovery.total_risk_students} SV
                            </span>
                            <span className="text-muted-foreground">đã ổn định</span>
                        </div>
                        <Progress
                            value={pct}
                            className="h-1.5"
                            indicatorClassName="bg-success"
                        />
                    </div>

                    <p className="mt-auto text-[11px] text-muted-foreground">
                        {showDays
                            ? `⌀ ${avgDays.toFixed(1)} ngày để chuyển sang ổn định`
                            : "Chưa có ca nào hoàn tất chu trình ổn định"}
                    </p>
                </CardContent>
            </Card>
        </motion.div>
    )
}

/* ─── Skeleton / error ──────────────────────────────────────────────────── */

function OverviewSkeleton() {
    return (
        <section className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
                <Skeleton className="h-4 w-44" />
            </div>
            <Skeleton className="h-52 w-full rounded-3xl" />
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {Array.from({ length: 4 }).map((_, i) => (
                    <Skeleton key={i} className="h-44 rounded-2xl" />
                ))}
            </div>
        </section>
    )
}

function OverviewError({ onRetry }: { onRetry: () => void }) {
    return (
        <Card className="rounded-2xl border-destructive/20 bg-destructive/5">
            <CardContent className="flex items-center justify-between gap-4 p-5">
                <div className="flex flex-col gap-0.5">
                    <p className="text-sm font-semibold text-destructive">
                        Không thể tải hiệu suất cố vấn.
                    </p>
                    <p className="text-xs text-muted-foreground">
                        Endpoint <code className="font-mono">/advisors/me/dashboard</code> không phản hồi.
                    </p>
                </div>
                <Button
                    size="sm"
                    variant="outline"
                    onClick={onRetry}
                    className="gap-1.5 rounded-lg"
                >
                    <RefreshCw className="size-3.5" />
                    Thử lại
                </Button>
            </CardContent>
        </Card>
    )
}

/* ─── Main export ───────────────────────────────────────────────────────── */

export function AdvisorPerformanceOverview() {
    const { user } = useAuth()
    const { data, isLoading, isError, refetch } = useAdvisorDashboard()

    // Only advisors have a dashboard — admin/viewer users don't have advisor profiles.
    if (user && user.role !== "advisor") return null

    return (
        <AnimatePresence mode="wait">
            {isLoading ? (
                <motion.div
                    key="loading"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                >
                    <OverviewSkeleton />
                </motion.div>
            ) : isError || !data ? (
                <motion.div
                    key="error"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                >
                    <OverviewError onRetry={() => refetch()} />
                </motion.div>
            ) : (
                <motion.section
                    key="content"
                    variants={containerVariants}
                    initial="hidden"
                    animate="show"
                    className="flex flex-col gap-4"
                >
                    <motion.div
                        variants={itemVariants}
                        className="flex items-center justify-between gap-3"
                    >
                        <h2 className="text-[11px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
                            Hiệu suất cố vấn của bạn
                        </h2>
                        <span className="hidden text-[10px] text-muted-foreground/70 sm:inline">
                            Cập nhật mỗi 30 giây
                        </span>
                    </motion.div>

                    <HeroBand data={data} />

                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                        <PriorityCard count={data.priority_queue} />
                        <ResponseCard kpi={data.response_kpi} />
                        <ActivationCard
                            activation={data.activation}
                            weeklyHistory={data.impact.weekly_history}
                        />
                        <RecoveryCard recovery={data.recovery} />
                    </div>
                </motion.section>
            )}
        </AnimatePresence>
    )
}
