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
  BrainCircuit
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
import { cn } from "@/lib/utils"

const ACADEMIC_IMPACT_DATA = [
  { name: "GPA", before: 2.1, after: 3.2 },
  { name: "Điểm chuyên cần", before: 65, after: 88 },
  { name: "Tỷ lệ nộp bài", before: 45, after: 75 },
]

const RISK_DISTRIBUTION_DATA = [
  { name: "Nghỉ học nhiều", value: 45, color: "#2563eb" },
  { name: "Điểm thấp", value: 35, color: "#60a5fa" },
  { name: "Lý do khác", value: 20, color: "#93c5fd" },
]

const RECOVERY_TREND_DATA = [
  { month: "Jan", rate: 58 },
  { month: "Feb", rate: 62 },
  { month: "Mar", rate: 65 },
  { month: "Apr", rate: 72 },
  { month: "May", rate: 78 },
  { month: "Jun", rate: 82 },
]

export function AdminDashboard() {
  return (
    <div className="flex flex-col gap-6">
      {/* 1. Strategic Pulse (Top Row) */}
      <section className="flex flex-col gap-4">
        <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground/80">
          Strategic Pulse
        </h2>
        <div className="grid gap-4 md:grid-cols-2">
          {/* Card 1: Overall Recovery Rate */}
          <Card className="relative overflow-hidden border-primary/20 bg-primary/5 transition-all hover:shadow-md">
            <CardContent className="flex flex-col gap-4 p-6">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="grid size-12 place-items-center rounded-2xl bg-primary/10 text-primary ring-1 ring-primary/20">
                    <ShieldCheck className="size-6" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-xs font-bold tracking-widest text-primary uppercase">Overall Recovery Rate</span>
                    <div className="flex items-baseline gap-2">
                      <span className="font-serif text-5xl font-black text-primary">82%</span>
                      <div className="flex items-center gap-1 text-sm font-bold text-success">
                        <TrendingUp className="size-4" />
                        +4%
                      </div>
                    </div>
                  </div>
                </div>
                <div className="h-16 w-32">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={RECOVERY_TREND_DATA}>
                      <Line 
                        type="monotone" 
                        dataKey="rate" 
                        stroke="var(--color-primary)" 
                        strokeWidth={2} 
                        dot={false} 
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between text-[11px] font-medium text-muted-foreground">
                  <span>Vs Last Semester</span>
                  <span>Target: 85%</span>
                </div>
                <Progress value={82} className="h-2 bg-primary/10" indicatorClassName="bg-primary" />
              </div>
              <p className="text-xs text-muted-foreground">
                Formula: (Stable Students / Total At-Risk). Significant growth in technical departments.
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
                  <span className="text-xs font-bold tracking-widest text-success uppercase">School-wide Lead Time</span>
                  <div className="flex items-baseline gap-2">
                    <span className="font-serif text-5xl font-black text-success">3.8</span>
                    <span className="text-xl font-bold text-success/80">hours</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4 rounded-xl border border-success/20 bg-white/50 p-3 dark:bg-slate-900/40">
                <div className="flex-1 space-y-1">
                  <div className="flex items-center justify-between text-xs font-bold">
                    <span className="text-success uppercase">KPI Performance</span>
                    <span className="text-success">&lt; 4.0h</span>
                  </div>
                  <Progress value={92} className="h-1.5 bg-success/10" indicatorClassName="bg-success" />
                </div>
                <div className="text-right">
                  <p className="text-[10px] font-bold text-muted-foreground uppercase">Compliance</p>
                  <p className="text-lg font-black text-success leading-none">92%</p>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                Maintaining sub-4h response ensures critical intervention during peak exam weeks.
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* 2. Impact Results (Middle Row) */}
      <section className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground/80">
            Strategic Impact
          </h2>
          <div className="flex items-center gap-2">
            <div className="size-2 rounded-full bg-success animate-pulse" />
            <span className="text-[10px] font-bold text-success uppercase tracking-tighter">Live System Data</span>
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {/* Card 3: Student Activation Rate */}
          <Card className="stripe-primary overflow-hidden border-primary/10 bg-white transition-all hover:shadow-md dark:bg-slate-900/40">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 font-serif text-sm">
                <BrainCircuit className="size-4 text-primary" />
                Nudge Activation Rate
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-black text-primary">42%</span>
                <span className="text-xs font-bold text-success">+5.2% vs baseline</span>
              </div>
              <div className="space-y-3">
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-[10px] font-bold uppercase">
                    <span>AI Engagement</span>
                    <span>High</span>
                  </div>
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
                      <div 
                        key={i} 
                        className={cn(
                          "h-1.5 flex-1 rounded-full",
                          i <= 6 ? "bg-primary" : "bg-primary/10"
                        )} 
                      />
                    ))}
                  </div>
                </div>
                <p className="text-[11px] leading-relaxed text-muted-foreground">
                  Effectiveness of AI-generated content across the system. % of students respond after automated Nudge.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Card 4: Academic Impact Score */}
          <Card className="stripe-primary overflow-hidden border-primary/10 bg-white transition-all hover:shadow-md dark:bg-slate-900/40">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 font-serif text-sm">
                <BarChart3 className="size-4 text-primary" />
                Academic Impact Score
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              <div className="h-[120px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={ACADEMIC_IMPACT_DATA} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                    <XAxis dataKey="name" fontSize={9} axisLine={false} tickLine={false} />
                    <Tooltip 
                      contentStyle={{ fontSize: '10px', borderRadius: '8px' }}
                      cursor={{ fill: 'var(--color-primary)', fillOpacity: 0.05 }}
                    />
                    <Bar dataKey="before" fill="#94a3b8" radius={[2, 2, 0, 0]} barSize={12} />
                    <Bar dataKey="after" fill="var(--color-primary)" radius={[2, 2, 0, 0]} barSize={12} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="flex items-center justify-center gap-4 text-[10px] font-bold uppercase">
                <div className="flex items-center gap-1.5">
                  <div className="size-2 rounded-sm bg-slate-400" />
                  <span className="text-muted-foreground">Before</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="size-2 rounded-sm bg-primary" />
                  <span className="text-primary">After</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Card 5: Risk Distribution */}
          <Card className="stripe-primary overflow-hidden border-primary/10 bg-white transition-all hover:shadow-md dark:bg-slate-900/40">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 font-serif text-sm">
                <PieChartIcon className="size-4 text-primary" />
                Risk Distribution
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <div className="h-[120px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={RISK_DISTRIBUTION_DATA}
                      cx="50%"
                      cy="50%"
                      innerRadius={30}
                      outerRadius={50}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {RISK_DISTRIBUTION_DATA.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ fontSize: '10px', borderRadius: '8px' }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {RISK_DISTRIBUTION_DATA.map((item) => (
                  <div key={item.name} className="flex items-center gap-2">
                    <div className="size-2 shrink-0 rounded-full" style={{ backgroundColor: item.color }} />
                    <span className="truncate text-[10px] font-medium text-muted-foreground">{item.name}</span>
                    <span className="ml-auto text-[10px] font-bold">{item.value}%</span>
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
