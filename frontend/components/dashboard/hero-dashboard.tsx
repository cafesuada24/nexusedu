"use client"

import * as React from "react"
import { 
  BellRing, 
  Timer, 
  MailOpen, 
  LifeBuoy, 
  Trophy, 
  ArrowRight,
  TrendingUp
} from "lucide-react"
import { motion } from "framer-motion"
import { 
  LineChart, 
  Line, 
  BarChart, 
  Bar, 
  ResponsiveContainer,
  Cell
} from "recharts"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"
import Link from "next/link"
import { useAlerts } from "@/hooks/use-alerts"
import { useAdvisorDashboard } from "@/hooks/use-advisors"
import { fromBackendStatus } from "@/lib/alerts"

export function HeroDashboard() {
  const { data: alerts = [] } = useAlerts()
  const { 
    data: dashboard, 
    isLoading: isDashboardLoading, 
    isError: isDashboardError 
  } = useAdvisorDashboard()

  const priorityCount = React.useMemo(() => {
    return alerts.filter((alert) => {
      // A student belongs in the Priority Queue if they are at CRITICAL Risk
      // AND their case is still "Waiting for intervention" (New or Accepted).
      if ((alert.intervention_status || "").toLowerCase() === "dismissed") return false
      
      const baseStatus = fromBackendStatus(alert.intervention_status)
      const isWaiting = baseStatus === "new" || baseStatus === "accepted"
      
      const risk = (alert.current_risk_status || "").toLowerCase()
      const isCritical = risk.includes("critical")
      
      return isWaiting && isCritical
    }).length
  }, [alerts])

  const activationChartData = React.useMemo(() => {
    if (!dashboard?.impact?.weekly_history) return []
    return dashboard.impact.weekly_history.map(h => ({
      day: `W${h.week}`,
      value: h.xp // Or activation specific data if backend had it, but for now we use XP or mock trend
    }))
  }, [dashboard])

  const xpChartData = React.useMemo(() => {
    if (!dashboard?.impact?.weekly_history) return []
    return dashboard.impact.weekly_history.map(h => ({
      day: `W${h.week}`,
      value: h.xp
    }))
  }, [dashboard])

  if (isDashboardLoading) {
    return (
      <div className="flex h-48 w-full items-center justify-center">
        <div className="flex flex-col items-center gap-2">
          <div className="size-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-sm text-muted-foreground">Đang tải dữ liệu...</p>
        </div>
      </div>
    )
  }

  if (isDashboardError || !dashboard) {
    return (
      <Card className="border-destructive/20 bg-destructive/5">
        <CardContent className="flex flex-col items-center gap-2 p-6">
          <p className="text-sm font-medium text-destructive">Không thể tải dữ liệu dashboard.</p>
          <Button variant="outline" size="sm" onClick={() => window.location.reload()}>
            Thử lại
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      {/* 1. The Urgent Pulse Section */}
      <section className="flex flex-col gap-4">
        <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground/80">
          SINH VIÊN KHẨN CẤP
        </h2>
        <div className="grid gap-4 md:grid-cols-2">
          {/* Card 1: Priority Queue */}
          <Card className="relative overflow-hidden border-warning/20 bg-warning/5 transition-all hover:shadow-md">
            <div className="absolute top-0 right-0 p-4 opacity-10">
              <BellRing className="size-24 text-destructive rotate-12" />
            </div>
            <CardContent className="flex flex-col gap-4 p-6">
              <div className="flex items-center gap-3">
                <motion.div
                  animate={{ 
                    rotate: [0, -10, 10, -10, 10, 0],
                  }}
                  transition={{ 
                    repeat: Infinity, 
                    duration: 1.5,
                    repeatDelay: 2
                  }}
                  className="grid size-12 place-items-center rounded-2xl bg-destructive/10 text-destructive ring-1 ring-destructive/20"
                >
                  <BellRing className="size-6" />
                </motion.div>
                <div className="flex flex-col">
                  <span className="text-xs font-bold tracking-widest text-destructive uppercase">HÀNG ĐỢI ƯU TIÊN</span>
                  <div className="flex items-baseline gap-2">
                    <span className="font-serif text-5xl font-black text-destructive">
                      {priorityCount}
                    </span>
                    <span className="text-sm font-medium text-destructive/80 italic">Sinh viên đang chờ</span>
                  </div>
                </div>
              </div>
              <p className="text-sm text-muted-foreground">Sinh viên có nguy cơ chưa được xử lý. Phát hiện mức độ khẩn cấp cao.</p>
              <Button asChild size="sm" className="w-fit rounded-xl bg-destructive hover:bg-destructive/90 text-white shadow-lg shadow-destructive/20">
                <Link href="/dashboard/alerts" className="flex items-center gap-2">
                  Mở danh sách <ArrowRight className="size-4" />
                </Link>
              </Button>
            </CardContent>
          </Card>

          {/* Card 2: Response Lead-Time */}
          <Card className="relative overflow-hidden border-success/20 bg-success/5 transition-all hover:shadow-md">
            <CardContent className="flex flex-col gap-4 p-6">
              <div className="flex items-center gap-3">
                <div className="grid size-12 place-items-center rounded-2xl bg-success/10 text-success ring-1 ring-success/20">
                  <div className="relative">
                    <Timer className="size-6" />
                    {dashboard.response_kpi.sla_breach_count > 0 && (
                      <span className="absolute -top-1 -right-1 flex size-3">
                        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-destructive opacity-75"></span>
                        <span className="relative inline-flex size-3 rounded-full bg-destructive"></span>
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex flex-col">
                  <span className="text-xs font-bold tracking-widest text-success uppercase">THỜI GIAN PHẢN HỒI (KPI &lt; 4h)</span>
                  <div className="flex items-baseline gap-2">
                    <span className="font-serif text-4xl font-bold text-success">
                      {dashboard.response_kpi.avg_response_hours.toFixed(1)}
                    </span>
                    <span className="text-xl font-bold text-success/80">giờ</span>
                  </div>
                </div>
              </div>
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between text-xs font-medium">
                  <span className={cn(
                    dashboard.response_kpi.within_kpi_rate >= 0.8 ? "text-success" : "text-warning"
                  )}>
                    {dashboard.response_kpi.within_kpi_rate >= 0.8 ? "Tốc độ tuyệt vời" : "Cần cải thiện"}
                  </span>
                  <span className="text-muted-foreground">Mục tiêu: {dashboard.response_kpi.target_hours.toFixed(1)}h</span>
                </div>
                <Progress 
                  value={dashboard.response_kpi.within_kpi_rate * 100} 
                  className="h-2 bg-success/10" 
                  indicatorClassName={cn(
                    dashboard.response_kpi.within_kpi_rate >= 0.8 ? "bg-success" : "bg-warning"
                  )} 
                />
              </div>
              <p className="text-xs text-muted-foreground italic">
                {dashboard.response_kpi.sla_breach_count > 0 
                  ? `Có ${dashboard.response_kpi.sla_breach_count} trường hợp quá hạn KPI.`
                  : "Đang đạt mục tiêu KPI. Giữ mức độ tương tác của sinh viên ở mức cao."}
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* 2. Business Core Metrics Section */}
      <section className="flex flex-col gap-4">
        <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground/80">
          KẾT QUẢ TÁC ĐỘNG
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {/* Card 3: Activation Rate */}
          <Card className="stripe-primary overflow-hidden border-primary/15 bg-white transition-all hover:shadow-md dark:bg-slate-900/40">
            <CardContent className="flex flex-col gap-4 p-5">
              <div className="flex items-start justify-between">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <div className="grid size-8 place-items-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/20">
                      <MailOpen className="size-4" />
                    </div>
                    <span className="text-[11px] font-bold uppercase tracking-tight text-muted-foreground">TỶ LỆ KÍCH HOẠT</span>
                  </div>
                  <span className="font-serif text-3xl font-bold text-primary">
                    {Math.round(dashboard.activation * 100)}%
                  </span>
                </div>
              </div>
              
              <div className="h-16 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={activationChartData}>
                    <Line 
                      type="monotone" 
                      dataKey="value" 
                      stroke="var(--color-primary)" 
                      strokeWidth={2.5} 
                      dot={false}
                      animationDuration={1500}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              
              <p className="text-[11px] text-muted-foreground">
                Lịch hẹn được đặt trong vòng 48 giờ sau khi nhắc nhở.
              </p>
            </CardContent>
          </Card>

          {/* Card 4: Recovery Rate */}
          <Card className="stripe-primary overflow-hidden border-primary/15 bg-white transition-all hover:shadow-md dark:bg-slate-900/40">
            <CardContent className="flex flex-col gap-4 p-5">
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <div className="grid size-8 place-items-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/20">
                    <LifeBuoy className="size-4" />
                  </div>
                  <span className="text-[11px] font-bold uppercase tracking-tight text-muted-foreground">TỶ LỆ GIẢI CỨU</span>
                </div>
                <span className="font-serif text-3xl font-bold text-primary">
                  {Math.round(dashboard.recovery.recovery_rate * 100)}%
                </span>
              </div>
              
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between text-[10px] font-bold">
                  <span className="text-primary uppercase tracking-tighter">ĐÃ ĐẠT ỔN ĐỊNH</span>
                  <span className="text-muted-foreground">
                    {dashboard.recovery.stabilized_students}/{dashboard.recovery.total_risk_students} SV
                  </span>
                </div>
                <Progress 
                  value={dashboard.recovery.recovery_rate * 100} 
                  className="h-2.5 bg-primary/10" 
                  indicatorClassName="bg-primary shadow-[0_0_8px_rgba(37,99,235,0.3)]" 
                />
              </div>
              
              <p className="text-[11px] text-muted-foreground">
                Đã chuyển sang trạng thái Ổn định sau khi can thiệp.
              </p>
            </CardContent>
          </Card>

          {/* Card 5: Impact Points */}
          <Card className="stripe-warning overflow-hidden border-warning/20 bg-white transition-all hover:shadow-md dark:bg-slate-900/40">
            <CardContent className="flex flex-col gap-4 p-5">
              <div className="flex items-start justify-between">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <div className="grid size-8 place-items-center rounded-lg bg-warning/15 text-warning ring-1 ring-warning/20">
                      <Trophy className="size-4" />
                    </div>
                    <span className="text-[11px] font-bold uppercase tracking-tight text-muted-foreground">ĐIỂM TÁC ĐỘNG (XP)</span>
                  </div>
                  <div className="flex items-baseline gap-1">
                    <span className="font-serif text-3xl font-black text-warning">
                      {dashboard.impact.current_xp}
                    </span>
                    <span className="text-xs font-bold text-warning/80">XP</span>
                  </div>
                </div>
                {dashboard.impact.ranking_position && (
                  <div className="flex flex-col items-end gap-0.5">
                    <span className="text-[10px] font-bold text-warning uppercase">Top {dashboard.impact.ranking_position}</span>
                    <span className="text-[9px] text-muted-foreground">Bảng xếp hạng</span>
                  </div>
                )}
              </div>

              <div className="h-16 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={xpChartData}>
                    <Bar dataKey="value" radius={[2, 2, 0, 0]} animationDuration={2000}>
                      {xpChartData.map((entry, index) => (
                        <Cell 
                          key={`cell-${index}`} 
                          fill={index === xpChartData.length - 1 ? "var(--color-warning)" : "var(--color-warning-foreground)"} 
                          fillOpacity={index === xpChartData.length - 1 ? 1 : 0.2} 
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="flex items-center justify-between border-t border-border/40 pt-2 text-[10px] font-medium">
                <span className="text-muted-foreground">Tháng {dashboard.impact.month}/{dashboard.impact.year}</span>
                <span className="text-warning font-bold">{Math.round(dashboard.impact.completion_rate * 100)}% Hoàn thành</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  )
}
