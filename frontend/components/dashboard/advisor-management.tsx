"use client"

import * as React from "react"
import {
    Activity,
    ArrowRight,
    CheckCircle2,
    Mail,
    TrendingUp,
    Users,
    Zap,
} from "lucide-react"
import {
    animate,
    motion,
    useMotionValue,
    useReducedMotion,
    type Variants,
} from "framer-motion"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip"
import { useAdvisorsLeaderboard } from "@/hooks/use-advisors"
import { cn } from "@/lib/utils"

/* ─── Demo fallback data ────────────────────────────────────────────────── */

const DEMO_ADVISORS = [
    { advisor_id: "demo-1", name: "Nguyễn Thị Hương", total_points: 847, actions_count: 31, sent_count: 24, resolved_count: 18 },
    { advisor_id: "demo-2", name: "Trần Minh Khoa",   total_points: 623, actions_count: 26, sent_count: 19, resolved_count: 13 },
    { advisor_id: "demo-3", name: "Lê Thị Lan Anh",   total_points: 541, actions_count: 22, sent_count: 17, resolved_count: 11 },
    { advisor_id: "demo-4", name: "Phạm Quốc Hùng",   total_points: 389, actions_count: 18, sent_count: 14, resolved_count:  8 },
    { advisor_id: "demo-5", name: "Đỗ Thị Mai Linh",  total_points: 274, actions_count: 14, sent_count: 11, resolved_count:  5 },
    { advisor_id: "demo-6", name: "Vũ Thanh Tùng",    total_points: 198, actions_count: 10, sent_count:  8, resolved_count:  3 },
]

/* ─── Types ─────────────────────────────────────────────────────────────── */

type TimeWindow = "weekly" | "monthly" | "semester" | "all_time"

const TIME_WINDOWS: { value: TimeWindow; label: string }[] = [
    { value: "weekly", label: "Tuần" },
    { value: "monthly", label: "Tháng" },
    { value: "semester", label: "Học kỳ" },
    { value: "all_time", label: "Tất cả" },
]

type ProcessedAdvisor = {
    advisor_id: string
    name: string
    initials: string
    total_points: number
    actions_count: number
    sent_count: number
    resolved_count: number
    rank: number
    resolve_rate: number
}

/* ─── Motion ────────────────────────────────────────────────────────────── */

const containerVariants: Variants = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.07 } },
}

const itemVariants: Variants = {
    hidden: { opacity: 0, y: 12 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 130, damping: 20 } },
}

/* ─── Animated counter ──────────────────────────────────────────────────── */

function useCountUp(target: number, duration = 0.9) {
    const reduce = useReducedMotion()
    const mv = useMotionValue(0)
    const [display, setDisplay] = React.useState(reduce ? String(target) : "0")

    React.useEffect(() => {
        if (reduce) { setDisplay(String(target)); return }
        const ctrl = animate(mv, target, {
            duration,
            ease: [0.16, 1, 0.3, 1],
            onUpdate: (v) => setDisplay(String(Math.round(v))),
        })
        return () => ctrl.stop()
    }, [target, duration, mv, reduce])

    return display
}

/* ─── Ring gauge — animated SVG donut ──────────────────────────────────── */

const RingGauge = React.memo(function RingGauge({
    value,
    size = 56,
    strokeWidth = 4.5,
    className,
}: {
    value: number
    size?: number
    strokeWidth?: number
    className?: string
}) {
    const reduce = useReducedMotion()
    const r = (size - strokeWidth * 2) / 2
    const cx = size / 2
    const cy = size / 2
    const circ = 2 * Math.PI * r
    const target = circ * (1 - Math.min(100, Math.max(0, value)) / 100)

    return (
        <div
            className={cn("relative shrink-0", className)}
            style={{ width: size, height: size }}
            aria-label={`${value}%`}
        >
            <svg width={size} height={size} className="-rotate-90" aria-hidden>
                {/* Track */}
                <circle
                    cx={cx} cy={cy} r={r}
                    fill="none"
                    strokeWidth={strokeWidth}
                    className="stroke-border/50"
                />
                {/* Fill */}
                <motion.circle
                    cx={cx} cy={cy} r={r}
                    fill="none"
                    strokeWidth={strokeWidth}
                    stroke="currentColor"
                    strokeLinecap="round"
                    strokeDasharray={circ}
                    initial={{ strokeDashoffset: reduce ? target : circ }}
                    animate={{ strokeDashoffset: target }}
                    transition={{
                        duration: reduce ? 0 : 1.3,
                        ease: [0.16, 1, 0.3, 1],
                        delay: 0.2,
                    }}
                />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
                <span className="font-mono text-[11px] font-bold leading-none">
                    {value}%
                </span>
            </div>
        </div>
    )
})

/* ─── Resolve rate color helper ─────────────────────────────────────────── */

function rateColor(rate: number, prefix: "text" | "bg" = "text") {
    if (rate >= 70) return prefix === "text" ? "text-emerald-600 dark:text-emerald-400" : "bg-emerald-500"
    if (rate >= 40) return prefix === "text" ? "text-amber-600 dark:text-amber-400" : "bg-amber-500"
    return prefix === "text" ? "text-slate-400 dark:text-slate-500" : "bg-slate-400"
}

/* ─── Stats band ─────────────────────────────────────────────────────────

   Single-surface tile grid — no individual cards, divider trick instead.
   ────────────────────────────────────────────────────────────────────── */

function StatsBand({
    totalAdvisors,
    totalSent,
    totalResolved,
    teamResolveRate,
}: {
    totalAdvisors: number
    totalSent: number
    totalResolved: number
    teamResolveRate: number
}) {
    const advisorsDisplay = useCountUp(totalAdvisors)
    const sentDisplay = useCountUp(totalSent)
    const resolvedDisplay = useCountUp(totalResolved)
    const rateDisplay = useCountUp(teamResolveRate)

    const stats = [
        {
            icon: Users,
            value: advisorsDisplay,
            label: "Cố vấn",
            sub: "đang hoạt động",
        },
        {
            icon: Mail,
            value: sentDisplay,
            label: "Email gửi",
            sub: "can thiệp",
        },
        {
            icon: CheckCircle2,
            value: resolvedDisplay,
            label: "Ca xử lý",
            sub: "thành công",
        },
        {
            icon: TrendingUp,
            value: `${rateDisplay}%`,
            label: "Resolve rate",
            sub: "trung bình nhóm",
        },
    ]

    return (
        <motion.div
            variants={itemVariants}
            className="grid grid-cols-2 overflow-hidden rounded-2xl ring-1 ring-border/60 sm:grid-cols-4"
            style={{ gap: "1px", background: "hsl(var(--border) / 0.4)" }}
        >
            {stats.map(({ icon: Icon, value, label, sub }) => (
                <div key={label} className="flex items-center gap-3 bg-card px-4 py-4">
                    <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-muted text-muted-foreground ring-1 ring-border/60">
                        <Icon className="size-3.5" />
                    </span>
                    <div className="min-w-0">
                        <p className="font-mono text-xl font-bold leading-none tracking-tight text-foreground">
                            {value}
                        </p>
                        <p className="mt-0.5 text-[11px] font-medium text-foreground/70">{label}</p>
                        <p className="text-[10px] text-muted-foreground">{sub}</p>
                    </div>
                </div>
            ))}
        </motion.div>
    )
}

/* ─── Podium card — top 3 ────────────────────────────────────────────────── */

const PODIUM_CONFIG = {
    1: {
        badge: "bg-amber-100 text-amber-700 ring-amber-300/60 dark:bg-amber-900/30 dark:text-amber-400 dark:ring-amber-700/40",
        card: "border-amber-200/70 bg-gradient-to-b from-amber-50/80 to-card dark:border-amber-700/30 dark:from-amber-900/15",
        blob: "bg-amber-300/20 dark:bg-amber-500/10",
        avatar: "ring-amber-300/60 dark:ring-amber-600/40",
        label: "Hạng nhất",
    },
    2: {
        badge: "bg-slate-100 text-slate-600 ring-slate-300/50 dark:bg-slate-700/40 dark:text-slate-300 dark:ring-slate-600/40",
        card: "border-slate-200/60 bg-gradient-to-b from-slate-50/70 to-card dark:border-slate-700/30 dark:from-slate-800/20",
        blob: "bg-slate-300/15 dark:bg-slate-500/8",
        avatar: "ring-slate-300/50 dark:ring-slate-600/40",
        label: "Hạng nhì",
    },
    3: {
        badge: "bg-orange-100 text-orange-700 ring-orange-300/50 dark:bg-orange-900/25 dark:text-orange-400 dark:ring-orange-700/35",
        card: "border-orange-200/60 bg-gradient-to-b from-orange-50/70 to-card dark:border-orange-700/30 dark:from-orange-900/12",
        blob: "bg-orange-300/15 dark:bg-orange-500/8",
        avatar: "ring-orange-300/50 dark:ring-orange-600/40",
        label: "Hạng ba",
    },
} as const

function PodiumCard({ a, delay }: { a: ProcessedAdvisor; delay: number }) {
    const cfg = PODIUM_CONFIG[a.rank as 1 | 2 | 3]
    const isFirst = a.rank === 1

    return (
        <motion.div
            variants={itemVariants}
            transition={{ delay }}
            className={cn(
                "relative overflow-hidden rounded-2xl border transition-shadow hover:shadow-lg",
                cfg.card,
            )}
        >
            {/* Decorative blur blob */}
            <div
                aria-hidden
                className={cn(
                    "pointer-events-none absolute -right-8 -top-8 size-36 rounded-full blur-3xl",
                    cfg.blob,
                )}
            />

            <div className="relative flex flex-col items-center gap-4 px-5 py-6">
                {/* Rank badge */}
                <span
                    className={cn(
                        "rounded-lg px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-widest ring-1",
                        cfg.badge,
                    )}
                >
                    {cfg.label}
                </span>

                {/* Avatar */}
                <Avatar
                    className={cn(
                        "ring-2",
                        cfg.avatar,
                        isFirst ? "size-14" : "size-12",
                    )}
                >
                    <AvatarFallback
                        className={cn(
                            "font-semibold",
                            isFirst ? "text-base" : "text-sm",
                            a.rank === 1
                                ? "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300"
                                : a.rank === 2
                                    ? "bg-slate-100 text-slate-700 dark:bg-slate-700/60 dark:text-slate-200"
                                    : "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300",
                        )}
                    >
                        {a.initials}
                    </AvatarFallback>
                </Avatar>

                {/* Name + XP */}
                <div className="flex flex-col items-center gap-1 text-center">
                    <p className="text-sm font-semibold leading-tight">{a.name}</p>
                    <p className="font-mono text-xs font-medium text-muted-foreground">
                        {a.total_points} XP
                    </p>
                </div>

                {/* Ring gauge */}
                <div className={rateColor(a.resolve_rate)}>
                    <RingGauge value={a.resolve_rate} size={isFirst ? 68 : 60} strokeWidth={5} />
                </div>
                <p className="text-[10px] font-medium text-muted-foreground">Resolve rate</p>

                {/* Stat chips */}
                <div className="flex w-full items-center justify-center gap-2">
                    <TooltipProvider delayDuration={100}>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <div className="flex items-center gap-1 rounded-lg bg-muted/50 px-2.5 py-1.5 ring-1 ring-border/50">
                                    <Mail className="size-3 text-muted-foreground" />
                                    <span className="font-mono text-[11px] font-semibold">{a.sent_count}</span>
                                </div>
                            </TooltipTrigger>
                            <TooltipContent>{a.sent_count} email đã gửi</TooltipContent>
                        </Tooltip>
                        <ArrowRight className="size-3 text-muted-foreground/40 shrink-0" />
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <div className={cn(
                                    "flex items-center gap-1 rounded-lg px-2.5 py-1.5 ring-1",
                                    a.resolved_count > 0
                                        ? "bg-emerald-50 text-emerald-700 ring-emerald-200/60 dark:bg-emerald-900/20 dark:text-emerald-400 dark:ring-emerald-700/30"
                                        : "bg-muted/50 ring-border/50 text-muted-foreground",
                                )}>
                                    <CheckCircle2 className="size-3" />
                                    <span className="font-mono text-[11px] font-semibold">{a.resolved_count}</span>
                                </div>
                            </TooltipTrigger>
                            <TooltipContent>{a.resolved_count} ca đã xử lý</TooltipContent>
                        </Tooltip>
                    </TooltipProvider>
                </div>

                {/* Actions count */}
                <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                    <Activity className="size-3" />
                    <span className="font-mono font-medium">{a.actions_count}</span>
                    <span>hành động</span>
                </div>
            </div>
        </motion.div>
    )
}

/* ─── Ghost podium slot — empty placeholder ─────────────────────────────── */

const GHOST_LABEL: Record<1 | 2 | 3, string> = {
    1: "Hạng nhất",
    2: "Hạng nhì",
    3: "Hạng ba",
}

function GhostPodiumCard({ rank }: { rank: 1 | 2 | 3 }) {
    return (
        <motion.div
            variants={itemVariants}
            className="flex flex-col items-center gap-4 rounded-2xl border border-dashed border-border/60 bg-muted/20 px-5 py-6 dark:bg-muted/10"
        >
            {/* Rank badge — muted */}
            <span className="rounded-lg bg-muted px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/50 ring-1 ring-border/50">
                {GHOST_LABEL[rank]}
            </span>

            {/* Avatar placeholder */}
            <div className="grid size-12 place-items-center rounded-full border-2 border-dashed border-border/50">
                <Users className="size-5 text-muted-foreground/25" />
            </div>

            {/* Name placeholder bars */}
            <div className="flex flex-col items-center gap-2">
                <div className="h-2.5 w-24 rounded-full bg-muted/60" />
                <div className="h-2 w-14 rounded-full bg-muted/40" />
            </div>

            {/* Ring placeholder — track only */}
            <div className="relative size-14" aria-hidden>
                <svg width={56} height={56} className="-rotate-90">
                    <circle
                        cx={28} cy={28} r={22}
                        fill="none"
                        strokeWidth={4.5}
                        className="stroke-border/40"
                        strokeDasharray="4 4"
                    />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                    <span className="font-mono text-[10px] text-muted-foreground/40">—</span>
                </div>
            </div>
            <p className="text-[10px] font-medium text-muted-foreground/40">Resolve rate</p>

            {/* Stat placeholder */}
            <p className="text-[11px] text-muted-foreground/50">Chưa có dữ liệu</p>
        </motion.div>
    )
}

/* ─── Leaderboard row — rank 4+ ─────────────────────────────────────────── */

function LeaderRow({ a }: { a: ProcessedAdvisor }) {
    return (
        <motion.li
            variants={itemVariants}
            className="group grid grid-cols-[2rem_1fr_auto] items-center gap-3 rounded-xl px-2 py-2.5 transition-colors hover:bg-muted/30 sm:grid-cols-[2rem_auto_1fr_auto_auto]"
        >
            {/* Rank */}
            <span className="font-mono text-xs font-bold text-muted-foreground/60 text-center">
                {a.rank}
            </span>

            {/* Avatar + name */}
            <div className="flex items-center gap-2.5 sm:w-48">
                <Avatar className="size-7 shrink-0">
                    <AvatarFallback className="bg-muted text-[10px] font-semibold text-muted-foreground">
                        {a.initials}
                    </AvatarFallback>
                </Avatar>
                <div className="min-w-0">
                    <p className="truncate text-xs font-semibold leading-none">{a.name}</p>
                    <p className="mt-0.5 font-mono text-[10px] text-muted-foreground">
                        {a.total_points} XP
                    </p>
                </div>
            </div>

            {/* Sent → Resolved — hidden on mobile, flex on sm+ */}
            <div className="hidden items-center gap-2 sm:flex">
                <TooltipProvider delayDuration={80}>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
                                <Mail className="size-3" />
                                <span className="font-mono font-medium">{a.sent_count}</span>
                            </div>
                        </TooltipTrigger>
                        <TooltipContent>{a.sent_count} email đã gửi</TooltipContent>
                    </Tooltip>

                    <ArrowRight className="size-3 text-muted-foreground/30" />

                    <Tooltip>
                        <TooltipTrigger asChild>
                            <div className={cn(
                                "flex items-center gap-1 text-[11px]",
                                a.resolved_count > 0 ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground/50",
                            )}>
                                <CheckCircle2 className="size-3" />
                                <span className="font-mono font-medium">{a.resolved_count}</span>
                            </div>
                        </TooltipTrigger>
                        <TooltipContent>{a.resolved_count} ca đã xử lý</TooltipContent>
                    </Tooltip>

                    <Tooltip>
                        <TooltipTrigger asChild>
                            <div className="ml-2 flex items-center gap-1 text-[10px] text-muted-foreground/60">
                                <Activity className="size-3" />
                                <span className="font-mono">{a.actions_count}</span>
                            </div>
                        </TooltipTrigger>
                        <TooltipContent>{a.actions_count} hành động</TooltipContent>
                    </Tooltip>
                </TooltipProvider>
            </div>

            {/* Sent/resolved on mobile only */}
            <div className="flex items-center gap-1.5 sm:hidden">
                <span className="font-mono text-[10px] text-muted-foreground">{a.sent_count}</span>
                <ArrowRight className="size-3 text-muted-foreground/30" />
                <span className={cn(
                    "font-mono text-[10px]",
                    a.resolved_count > 0 ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground",
                )}>
                    {a.resolved_count}
                </span>
            </div>

            {/* Ring gauge */}
            <div className={cn("shrink-0", rateColor(a.resolve_rate))}>
                <RingGauge value={a.resolve_rate} size={40} strokeWidth={3.5} />
            </div>
        </motion.li>
    )
}

/* ─── Empty / error / loading ───────────────────────────────────────────── */

function EmptyState() {
    return (
        <div className="flex flex-col items-center gap-2 py-14 text-center">
            <Users className="size-7 text-muted-foreground/30" />
            <p className="text-sm font-medium text-muted-foreground">
                Chưa có dữ liệu hoạt động trong khoảng thời gian này.
            </p>
        </div>
    )
}

function LoadingSkeleton() {
    return (
        <div className="flex flex-col gap-4">
            {/* Stats band */}
            <Skeleton className="h-[76px] rounded-2xl" />
            {/* Podium */}
            <div className="grid gap-3 sm:grid-cols-3">
                {[1, 0, 2].map((i) => <Skeleton key={i} className="h-72 rounded-2xl" />)}
            </div>
            {/* List */}
            <div className="flex flex-col gap-1 pt-1">
                {Array.from({ length: 4 }).map((_, i) => (
                    <Skeleton key={i} className="h-11 rounded-xl" />
                ))}
            </div>
        </div>
    )
}

/* ─── Main export ───────────────────────────────────────────────────────── */

export function AdvisorManagement() {
    const [timeWindow, setTimeWindow] = React.useState<TimeWindow>("all_time")
    const { data, isLoading, error } = useAdvisorsLeaderboard(timeWindow)

    const { processed, stats, isDemo } = React.useMemo(() => {
        const raw = (data?.items.length ?? 0) >= 3 ? data!.items : null
        const source = raw ?? DEMO_ADVISORS
        const isDemo = !raw

        const sorted = [...source].sort((a, b) => b.total_points - a.total_points)
        const processed: ProcessedAdvisor[] = sorted.map((item, i) => ({
            ...item,
            rank: i + 1,
            initials: item.name
                .split(/\s+/)
                .map((n) => n[0]?.toUpperCase() ?? "")
                .slice(-2)
                .join(""),
            resolve_rate:
                item.sent_count > 0
                    ? Math.min(100, Math.round((item.resolved_count / item.sent_count) * 100))
                    : 0,
        }))

        const totalSent = processed.reduce((s, a) => s + a.sent_count, 0)
        const totalResolved = processed.reduce((s, a) => s + a.resolved_count, 0)
        const teamResolveRate =
            totalSent > 0 ? Math.min(100, Math.round((totalResolved / totalSent) * 100)) : 0

        return {
            processed,
            isDemo,
            stats: {
                totalAdvisors: isDemo ? processed.length : (data?.metadata.total_count ?? processed.length),
                totalSent,
                totalResolved,
                teamResolveRate,
            },
        }
    }, [data])

    const podium = processed.slice(0, 3)
    const rest = processed.slice(3)

    if (isLoading) return <LoadingSkeleton />

    if (error) {
        return (
            <div className="flex flex-col items-center gap-2 py-12 text-center">
                <p className="text-sm text-destructive">Không thể tải dữ liệu cố vấn.</p>
            </div>
        )
    }

    return (
        <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="show"
            className="flex flex-col gap-4"
        >
            {/* Stats band */}
            {stats && (
                <StatsBand
                    totalAdvisors={stats.totalAdvisors}
                    totalSent={stats.totalSent}
                    totalResolved={stats.totalResolved}
                    teamResolveRate={stats.teamResolveRate}
                />
            )}

            {/* Leaderboard card */}
            <motion.div variants={itemVariants}>
                <Card className="rounded-2xl border-border/60 bg-card shadow-sm">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                        <CardTitle className="flex items-center gap-2 text-base font-semibold tracking-tight">
                            <span className="grid size-7 place-items-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/20">
                                <Zap className="size-3.5" />
                            </span>
                            Bảng xếp hạng cố vấn
                            {isDemo && (
                                <Badge
                                    variant="outline"
                                    className="rounded-md border-dashed border-muted-foreground/30 text-[10px] font-medium text-muted-foreground/60"
                                >
                                    Demo
                                </Badge>
                            )}
                        </CardTitle>

                        <Tabs value={timeWindow} onValueChange={(v) => setTimeWindow(v as TimeWindow)}>
                            <TabsList className="h-8">
                                {TIME_WINDOWS.map(({ value, label }) => (
                                    <TabsTrigger key={value} value={value} className="h-6 px-2.5 text-[11px]">
                                        {label}
                                    </TabsTrigger>
                                ))}
                            </TabsList>
                        </Tabs>
                    </CardHeader>

                    <CardContent className="flex flex-col gap-4">
                        {/* Podium — always 3 slots; empty ranks show ghost card */}
                        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                            {/* Desktop order: rank2 | rank1 | rank3 — mobile: rank1 first */}
                            <div className="order-2 sm:order-1">
                                {podium[1]
                                    ? <PodiumCard a={podium[1]} delay={0.08} />
                                    : <GhostPodiumCard rank={2} />}
                            </div>
                            <div className="order-1 sm:order-2">
                                {podium[0]
                                    ? <PodiumCard a={podium[0]} delay={0} />
                                    : <GhostPodiumCard rank={1} />}
                            </div>
                            <div className="order-3 sm:order-3">
                                {podium[2]
                                    ? <PodiumCard a={podium[2]} delay={0.16} />
                                    : <GhostPodiumCard rank={3} />}
                            </div>
                        </div>

                        {/* Rest of leaderboard — rank 4+ */}
                        {rest.length > 0 && (
                            <div>
                                <div className="mb-2 flex items-center gap-3">
                                    <div className="h-px flex-1 bg-border/50" />
                                    <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/50">
                                        Xếp hạng còn lại
                                    </span>
                                    <div className="h-px flex-1 bg-border/50" />
                                </div>
                                <ol className="flex flex-col divide-y divide-border/40">
                                    {rest.map((a) => (
                                        <LeaderRow key={a.advisor_id} a={a} />
                                    ))}
                                </ol>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </motion.div>
        </motion.div>
    )
}
