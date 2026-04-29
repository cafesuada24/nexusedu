"use client"

import { Loader2 } from "lucide-react"
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { useAdvisorsEngagement } from "@/hooks/use-advisors"

const config = {
  sent: { label: "Đã gửi", color: "var(--chart-1)" },
  drafted: { label: "Chờ duyệt", color: "var(--chart-2)" },
} satisfies ChartConfig

export function EngagementChart() {
  const { data, isLoading, error } = useAdvisorsEngagement()

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
        Chưa có dữ liệu tương tác.
      </div>
    )
  }

  // Sort data high to low based on total activity
  const sortedData = [...data].sort((a, b) => (b.sent + b.drafted) - (a.sent + a.drafted))

  return (
    <ChartContainer config={config} className="h-[280px] w-full">
      <BarChart data={sortedData} margin={{ left: 4, right: 8, top: 8 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} className="stroke-border/60" />
        <XAxis dataKey="faculty" tickLine={false} axisLine={false} tickMargin={8} />
        <YAxis tickLine={false} axisLine={false} tickMargin={8} width={28} />
        <ChartTooltip content={<ChartTooltipContent />} />
        <Bar
          dataKey="sent"
          stackId="a"
          fill="var(--color-sent)"
          radius={[0, 0, 6, 6]}
        />
        <Bar
          dataKey="drafted"
          stackId="a"
          fill="var(--color-drafted)"
          radius={[6, 6, 0, 0]}
        />
      </BarChart>
    </ChartContainer>
  )
}
