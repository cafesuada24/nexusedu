"use client"

import { Loader2 } from "lucide-react"
import { Line, LineChart, CartesianGrid, XAxis, YAxis } from "recharts"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { useRetentionTrend } from "@/hooks/use-metrics"

const config = {
  current: { label: "Sau NexusEdu", color: "var(--chart-1)" },
  baseline: { label: "Trước NexusEdu", color: "var(--chart-3)" },
} satisfies ChartConfig

export function DropoutChart() {
  const { data, isLoading, error } = useRetentionTrend()

  if (isLoading) {
    return (
      <div className="flex h-[280px] w-full items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-[280px] w-full items-center justify-center text-sm text-destructive">
        Không thể tải dữ liệu biểu đồ.
      </div>
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className="flex h-[280px] w-full items-center justify-center text-sm text-muted-foreground">
        Chưa có dữ liệu xu hướng.
      </div>
    )
  }

  return (
    <ChartContainer config={config} className="h-[280px] w-full">
      <LineChart data={data} margin={{ left: 4, right: 8, top: 8 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} className="stroke-border/60" />
        <XAxis dataKey="month" tickLine={false} axisLine={false} tickMargin={8} />
        <YAxis
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          domain={[0, 100]}
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
