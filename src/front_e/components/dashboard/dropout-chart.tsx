"use client"

import { Line, LineChart, CartesianGrid, XAxis, YAxis } from "recharts"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"

const data = [
  { month: "T9", baseline: 78, current: 82 },
  { month: "T10", baseline: 79, current: 84 },
  { month: "T11", baseline: 80, current: 86 },
  { month: "T12", baseline: 81, current: 87 },
  { month: "T1", baseline: 81, current: 88 },
  { month: "T2", baseline: 82, current: 90 },
  { month: "T3", baseline: 82, current: 91 },
  { month: "T4", baseline: 83, current: 92 },
]

const config = {
  current: { label: "Sau NexusEdu", color: "var(--chart-1)" },
  baseline: { label: "Trước NexusEdu", color: "var(--chart-3)" },
} satisfies ChartConfig

export function DropoutChart() {
  return (
    <ChartContainer config={config} className="h-[280px] w-full">
      <LineChart data={data} margin={{ left: 4, right: 8, top: 8 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} className="stroke-border/60" />
        <XAxis dataKey="month" tickLine={false} axisLine={false} tickMargin={8} />
        <YAxis
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          domain={[70, 100]}
          width={32}
          tickFormatter={(v) => `${v}%`}
        />
        <ChartTooltip content={<ChartTooltipContent />} />
        <Line
          dataKey="baseline"
          stroke="var(--color-baseline)"
          strokeWidth={2}
          strokeDasharray="5 5"
          dot={false}
        />
        <Line
          dataKey="current"
          stroke="var(--color-current)"
          strokeWidth={3}
          dot={{ r: 3, strokeWidth: 0, fill: "var(--color-current)" }}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ChartContainer>
  )
}
