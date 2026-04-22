"use client"

import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts"
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"

const data = [
  { week: "T1", financial: 40, grades: 24, absence: 18 },
  { week: "T2", financial: 38, grades: 28, absence: 22 },
  { week: "T3", financial: 42, grades: 30, absence: 26 },
  { week: "T4", financial: 36, grades: 34, absence: 30 },
  { week: "T5", financial: 34, grades: 38, absence: 28 },
  { week: "T6", financial: 30, grades: 36, absence: 32 },
  { week: "T7", financial: 28, grades: 40, absence: 30 },
  { week: "T8", financial: 26, grades: 38, absence: 34 },
  { week: "T9", financial: 30, grades: 34, absence: 36 },
  { week: "T10", financial: 24, grades: 30, absence: 30 },
  { week: "T11", financial: 22, grades: 26, absence: 28 },
  { week: "T12", financial: 18, grades: 22, absence: 24 },
]

const config = {
  financial: { label: "Học phí", color: "var(--chart-1)" },
  grades: { label: "Điểm số", color: "var(--chart-2)" },
  absence: { label: "Vắng học", color: "var(--chart-4)" },
} satisfies ChartConfig

export function RiskTrendChart() {
  return (
    <ChartContainer config={config} className="h-[280px] w-full">
      <AreaChart data={data} margin={{ left: 4, right: 8, top: 8 }}>
        <defs>
          <linearGradient id="g-financial" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-financial)" stopOpacity={0.35} />
            <stop offset="100%" stopColor="var(--color-financial)" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="g-grades" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-grades)" stopOpacity={0.3} />
            <stop offset="100%" stopColor="var(--color-grades)" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="g-absence" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-absence)" stopOpacity={0.3} />
            <stop offset="100%" stopColor="var(--color-absence)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" vertical={false} className="stroke-border/60" />
        <XAxis
          dataKey="week"
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          className="text-xs"
        />
        <YAxis tickLine={false} axisLine={false} tickMargin={8} width={28} />
        <ChartTooltip content={<ChartTooltipContent />} />
        <ChartLegend content={<ChartLegendContent />} />
        <Area
          type="monotone"
          dataKey="financial"
          stroke="var(--color-financial)"
          fill="url(#g-financial)"
          strokeWidth={2}
        />
        <Area
          type="monotone"
          dataKey="grades"
          stroke="var(--color-grades)"
          fill="url(#g-grades)"
          strokeWidth={2}
        />
        <Area
          type="monotone"
          dataKey="absence"
          stroke="var(--color-absence)"
          fill="url(#g-absence)"
          strokeWidth={2}
        />
      </AreaChart>
    </ChartContainer>
  )
}
