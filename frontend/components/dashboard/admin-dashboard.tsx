"use client"

import * as React from "react"
import { 
  TrendingUp, 
  BarChart3, 
  PieChart as PieChartIcon, 
  Activity,
  Timer,
  ShieldCheck,
  ChevronRight,
  TrendingDown,
  BrainCircuit,
  Clock
} from "lucide-react"
import { motion } from "framer-motion"
import { 
  LineChart, 
  Line, 
  BarChart, 
  Bar, 
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { useAdminDashboard } from "@/hooks/use-admin-dashboard"

const COLORS = ["#2563eb", "#60a5fa", "#93c5fd", "#bfdbfe", "#dbeafe"]

export function AdminDashboard() {
  const { data: dashboardData, isLoading, error, isError } = useAdminDashboard()

  React.useEffect(() => {
    if (dashboardData) {
      console.log("AdminDashboard Data:", dashboardData)
    }
  }, [dashboardData])

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <section className="flex flex-col gap-4">
          <Skeleton className="h-4 w-32" />
          <div className="grid gap-4 md:grid-cols-2">
            <Skeleton className="h-[200px] rounded-2xl" />
            <Skeleton className="h-[200px] rounded-2xl" />
          </div>
        </section>
        <section className="flex flex-col gap-4">
          <Skeleton className="h-4 w-32" />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Skeleton className="h-[180px] rounded-2xl" />
            <Skeleton className="h-[180px] rounded-2xl" />
            <Skeleton className="h-[180px] rounded-2xl" />
          </div>
        </section>
      </div>
    )
  }

  if (isError) {
    return (
      <Card className="border-destructive/20 bg-destructive/5 p-8 text-center">
        <p className="text-sm font-medium text-destructive">Không thể tải dữ liệu dashboard: {error instanceof Error ? error.message : "Lỗi không xác định"}</p>
      </Card>
    )
  }

  if (!dashboardData) return null

  const {
    recovery = { recovery_rate: 0, stabilized_students: 0, total_at_risk_students: 0 },
    lead_time = { avg_lead_time_hours: 0, target_hours: 4, within_target_rate: 0 },
    nudge_activation = { activation_rate: 0, total_nudges_sent: 0, responses_received: 0 },
    academic_impact = { 
      avg_gpa_before: 0, avg_gpa_after: 0, impact_score: 0
    },
    risk_distribution = [],
    generated_at = new Date().toISOString()
  } = dashboardData

  const recoveryRate = ((recovery.recovery_rate || 0) * 100).toFixed(1)
  const activationRate = ((nudge_activation.activation_rate || 0) * 100).toFixed(0)
  const complianceRate = ((lead_time.within_target_rate || 0) * 100).toFixed(0)

  const academicImpactData = [
    { name: "GPA Avg", before: academic_impact.avg_gpa_before || 0, after: academic_impact.avg_gpa_after || 0 },
  ]

  const riskDistributionData = (risk_distribution || []).map((item, idx) => ({
    name: item.label || "N/A",
    value: item.count || 0,
    percentage: item.percentage || 0,
    color: COLORS[idx % COLORS.length]
  }))

  return (
    <div className="flex flex-col gap-6">
      {/* 1. Nhịp độ Chiến lược (Top Row) */}
      <section className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground/80">
            Nhịp độ Chiến lược
          </h2>
          <div className="flex items-center gap-1.5 text-[10px] font-medium text-muted-foreground">
            <Clock className="size-3" />
            Cập nhật: {generated_at ? new Date(generated_at).toLocaleString('vi-VN') : 'Vừa xong'}
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {/* Card 1: Tỷ lệ Phục hồi Tổng thể */}
          <Card className="relative overflow-hidden border-primary/20 bg-primary/5 transition-all hover:shadow-md">
            <CardContent className="flex flex-col gap-4 p-6">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="grid size-12 place-items-center rounded-2xl bg-primary/10 text-primary ring-1 ring-primary/20">
                    <ShieldCheck className="size-6" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-xs font-bold tracking-widest text-primary uppercase">Tỷ lệ Phục hồi Tổng thể</span>
                    <div className="flex items-baseline gap-2">
                      <span className="font-serif text-5xl font-black text-primary">{recoveryRate}%</span>
                      <div className="flex items-center gap-1 text-sm font-bold text-success">
                        <TrendingUp className="size-4" />
                        Trực tiếp
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between text-[11px] font-medium text-muted-foreground">
                  <span>{recovery.stabilized_students || 0} / {recovery.total_at_risk_students || 0} SV ổn định</span>
                  <span>Mục tiêu: 85%</span>
                </div>
                <Progress value={(recovery.recovery_rate || 0) * 100} className="h-2 bg-primary/10" indicatorClassName="bg-primary" />
              </div>
              <p className="text-xs text-muted-foreground">
                Công thức: (Sinh viên ổn định / Tổng số rủi ro). Tăng trưởng đáng kể ở các khoa kỹ thuật.
              </p>
            </CardContent>
          </Card>

          {/* Card 2: Average Intervention Lead-Time */}
          <Card className="relative overflow-hidden border-success/20 bg-success/5 transition-all hover:shadow-md">
            <CardContent className="flex flex-col gap-4 p-6">
              <div className="flex items-center gap-3">
                <div className="grid size-12 place-items-center rounded-2xl bg-success/10 text-success ring-1 ring-success/20">
                  <Timer className="size-6" />
                </div>
                <div className="flex flex-col">
                  <span className="text-xs font-bold tracking-widest text-success uppercase">Thời gian Phản hồi Toàn trường</span>
                  <div className="flex items-baseline gap-2">
                    <span className="font-serif text-5xl font-black text-success">{(lead_time.avg_lead_time_hours || 0).toFixed(1)}</span>
                    <span className="text-xl font-bold text-success/80">giờ</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4 rounded-xl border border-success/20 bg-white/50 p-3 dark:bg-slate-900/40">
                <div className="flex-1 space-y-1">
                  <div className="flex items-center justify-between text-xs font-bold">
                    <span className="text-success uppercase">Hiệu suất KPI</span>
                    <span className="text-success">&lt; {lead_time.target_hours || 4}h</span>
                  </div>
                  <Progress value={(lead_time.within_target_rate || 0) * 100} className="h-1.5 bg-success/10" indicatorClassName="bg-success" />
                </div>
                <div className="text-right">
                  <p className="text-[10px] font-bold text-muted-foreground uppercase">Mức độ Tuân thủ</p>
                  <p className="text-lg font-black text-success leading-none">{complianceRate}%</p>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                Duy trì phản hồi dưới {lead_time.target_hours || 4}h đảm bảo can thiệp kịp thời trong các tuần thi cao điểm.
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* 2. Tác động Chiến lược (Middle Row) */}
      <section className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground/80">
            Tác động Chiến lược
          </h2>
          <div className="flex items-center gap-2">
            <div className="size-2 rounded-full bg-success animate-pulse" />
            <span className="text-[10px] font-bold text-success uppercase tracking-tighter">Dữ liệu Hệ thống Trực tiếp</span>
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {/* Card 3: Student Activation Rate */}
          <Card className="stripe-primary overflow-hidden border-primary/10 bg-white transition-all hover:shadow-md dark:bg-slate-900/40">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 font-serif text-sm">
                <BrainCircuit className="size-4 text-primary" />
                Tỷ lệ Kích hoạt Nhắc nhở
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-black text-primary">{activationRate}%</span>
                <span className="text-xs font-bold text-success">{nudge_activation.responses_received || 0} / {nudge_activation.total_nudges_sent || 0} phản hồi</span>
              </div>
              <div className="space-y-3">
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-[10px] font-bold uppercase">
                    <span>Mức độ Tương tác AI</span>
                    <span>{Number(activationRate) > 40 ? "Cao" : "Bình thường"}</span>
                  </div>
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
                      <div 
                        key={i} 
                        className={cn(
                          "h-1.5 flex-1 rounded-full",
                          i <= Math.round((Number(activationRate) / 100) * 8) ? "bg-primary" : "bg-primary/10"
                        )} 
                      />
                    ))}
                  </div>
                </div>
                <p className="text-[11px] leading-relaxed text-muted-foreground">
                  Hiệu quả của nội dung do AI tạo ra trên toàn hệ thống. % sinh viên phản hồi sau Nhắc nhở tự động.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Card 4: Academic Impact Score */}
          <Card className="stripe-primary overflow-hidden border-primary/10 bg-white transition-all hover:shadow-md dark:bg-slate-900/40">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center justify-between font-serif text-sm">
                <div className="flex items-center gap-2">
                  <BarChart3 className="size-4 text-primary" />
                  Tác động Học thuật
                </div>
                {academic_impact.impact_score !== undefined && (
                  <Badge variant="outline" className="rounded-md bg-primary/5 text-primary border-primary/20 text-[10px] px-1.5 py-0 h-5">
                    Tác động: {academic_impact.impact_score}
                  </Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              <div className="h-[120px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={academicImpactData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                    <XAxis dataKey="name" fontSize={9} axisLine={false} tickLine={false} />
                    <Tooltip 
                      contentStyle={{ fontSize: '10px', borderRadius: '8px' }}
                      cursor={{ fill: 'var(--color-primary)', fillOpacity: 0.05 }}
                    />
                    <Bar dataKey="before" fill="#94a3b8" radius={[2, 2, 0, 0]} barSize={24} />
                    <Bar dataKey="after" fill="var(--color-primary)" radius={[2, 2, 0, 0]} barSize={24} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="flex items-center justify-center gap-4 text-[10px] font-bold uppercase">
                <div className="flex items-center gap-1.5">
                  <div className="size-2 rounded-sm bg-slate-400" />
                  <span className="text-muted-foreground">Trước (GPA)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="size-2 rounded-sm bg-primary" />
                  <span className="text-primary">Sau (GPA)</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Card 5: Risk Distribution */}
          <Card className="stripe-primary overflow-hidden border-primary/10 bg-white transition-all hover:shadow-md dark:bg-slate-900/40">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 font-serif text-sm">
                <PieChartIcon className="size-4 text-primary" />
                Phân bổ Rủi ro
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <div className="h-[120px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={riskDistributionData}
                      cx="50%"
                      cy="50%"
                      innerRadius={30}
                      outerRadius={50}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {riskDistributionData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{ fontSize: '10px', borderRadius: '8px' }}
                      formatter={(value, name, props: any) => [`${value} SV (${props.payload.percentage || 0}%)`, name]}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="grid grid-cols-2 gap-x-2 gap-y-1">
                {riskDistributionData.map((item) => (
                  <div key={item.name} className="flex items-center gap-1.5 overflow-hidden">
                    <div className="size-2 shrink-0 rounded-full" style={{ backgroundColor: item.color }} />
                    <span className="truncate text-[10px] font-medium text-muted-foreground">{item.name}</span>
                    <span className="ml-auto text-[10px] font-bold">{item.percentage}%</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  )
}
