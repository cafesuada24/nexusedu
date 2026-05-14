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
import { fromBackendStatus } from "@/lib/alerts"

const ACTIVATION_DATA = [
  { day: "M", value: 20 },
  { day: "T", value: 25 },
  { day: "W", value: 22 },
  { day: "T", value: 30 },
  { day: "F", value: 28 },
  { day: "S", value: 35 },
  { day: "S", value: 33 },
]

const XP_DATA = [
  { day: "M", value: 40 },
  { day: "T", value: 65 },
  { day: "W", value: 45 },
  { day: "T", value: 80 },
  { day: "F", value: 95 },
  { day: "S", value: 70 },
  { day: "S", value: 55 },
]

export function HeroDashboard() {
  const { data: alerts = [] } = useAlerts()

  const { rescueRate, rescueRateLabel } = React.useMemo(() => {
    const resolvedCount = alerts.filter(a => (a.intervention_status || "").toLowerCase() === "resolved").length
    const failedCount = alerts.filter(a => (a.intervention_status || "").toLowerCase() === "failed").length
    const totalClosed = resolvedCount + failedCount
    
    const rate = totalClosed === 0 ? 0 : (resolvedCount / totalClosed) * 100
    const label = `${resolvedCount}/${totalClosed} SV`
    
    return {
      rescueRate: rate.toFixed(1),
      rescueRateLabel: label
    }
  }, [alerts])

  const priorityCount = React.useMemo(() => {
    return alerts.filter((alert) => {
      // Logic: Only count alerts in the 'New' column that are also 'High Risk'
      // A case is truly 'new' only if it hasn't been assigned to an advisor yet.
      if ((alert.intervention_status || "").toLowerCase() === "dismissed") return false
      
      const baseStatus = fromBackendStatus(alert.intervention_status)
      const isNew = baseStatus === "new" && !alert.assigned_advisor_id
      
      const isHighRisk = !(alert.current_risk_status || "").toLowerCase().includes("elevated")
      
      return isNew && isHighRisk
    }).length
  }, [alerts])

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
                  <Timer className="size-6" />
                </div>
                <div className="flex flex-col">
                  <span className="text-xs font-bold tracking-widest text-success uppercase">THỜI GIAN PHẢN HỒI (KPI &lt; 4h)</span>
                  <div className="flex items-baseline gap-2">
                    <span className="font-serif text-4xl font-bold text-success">3.2</span>
                    <span className="text-xl font-bold text-success/80">giờ</span>
                  </div>
                </div>
              </div>
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between text-xs font-medium">
                  <span className="text-success">Tốc độ tuyệt vời</span>
                  <span className="text-muted-foreground">Mục tiêu: 4.0h</span>
                </div>
                <Progress value={80} className="h-2 bg-success/10" indicatorClassName="bg-success" />
              </div>
              <p className="text-xs text-muted-foreground italic">Đang đạt mục tiêu KPI. Giữ mức độ tương tác của sinh viên ở mức cao.</p>
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
                  <span className="font-serif text-3xl font-bold text-primary">35%</span>
                </div>
                <div className="flex items-center gap-1 text-[11px] font-bold text-success">
                  <TrendingUp className="size-3" />
                  +12%
                </div>
              </div>
              
              <div className="h-16 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={ACTIVATION_DATA}>
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
                <span className="font-serif text-3xl font-bold text-primary">{rescueRate}%</span>
              </div>
              
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between text-[10px] font-bold">
                  <span className="text-primary uppercase tracking-tighter">ĐÃ ĐẠT ỔN ĐỊNH</span>
                  <span className="text-muted-foreground">{rescueRateLabel}</span>
                </div>
                <Progress value={Number(rescueRate)} className="h-2.5 bg-primary/10" indicatorClassName="bg-primary shadow-[0_0_8px_rgba(37,99,235,0.3)]" />
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
                    <span className="font-serif text-3xl font-black text-warning">450</span>
                    <span className="text-xs font-bold text-warning/80">XP</span>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-0.5">
                  <span className="text-[10px] font-bold text-warning uppercase">Top 3</span>
                  <span className="text-[9px] text-muted-foreground">Bảng xếp hạng</span>
                </div>
              </div>

              <div className="h-16 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={XP_DATA}>
                    <Bar dataKey="value" radius={[2, 2, 0, 0]} animationDuration={2000}>
                      {XP_DATA.map((entry, index) => (
                        <Cell 
                          key={`cell-${index}`} 
                          fill={index === 4 ? "var(--color-warning)" : "var(--color-warning-foreground)"} 
                          fillOpacity={index === 4 ? 1 : 0.2} 
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="flex items-center justify-between border-t border-border/40 pt-2 text-[10px] font-medium">
                <span className="text-muted-foreground">Mục tiêu tuần: 500 XP</span>
                <span className="text-warning font-bold">90% Hoàn thành</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  )
}
