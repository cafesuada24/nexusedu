"use client"

import { Bar, BarChart, CartesianGrid, LabelList, XAxis, YAxis } from "recharts"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import type { Problem } from "@/lib/csv"

type Props = {
  problemCounts: Record<Problem, number>
}

const config = {
  count: { label: "Sinh viên", color: "var(--chart-1)" },
  failed_final: { label: "Rớt cuối kỳ", color: "var(--chart-1)" },
  failed_midterm: { label: "Rớt giữa kỳ", color: "var(--chart-2)" },
  low_average: { label: "Điểm TB thấp", color: "var(--chart-4)" },
} satisfies ChartConfig

export function RiskTrendChart({ problemCounts }: Props) {
  const data = [
    {
      key: "failed_final" as const,
      label: "Rớt cuối kỳ",
      count: problemCounts.failed_final,
      fill: "var(--color-failed_final)",
    },
    {
      key: "failed_midterm" as const,
      label: "Rớt giữa kỳ",
      count: problemCounts.failed_midterm,
      fill: "var(--color-failed_midterm)",
    },
    {
      key: "low_average" as const,
      label: "Điểm TB thấp",
      count: problemCounts.low_average,
      fill: "var(--color-low_average)",
    },
  ]

  const total = data.reduce((s, d) => s + d.count, 0)

  if (total === 0) {
    return (
      <div className="grid h-[280px] place-items-center rounded-xl border border-dashed border-border/60 bg-muted/30 text-center">
        <div className="max-w-xs px-4">
          <p className="font-serif text-base font-semibold">
            Chưa phát hiện vấn đề nào
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Tất cả sinh viên trong file hiện đang ở mức an toàn theo ngưỡng mặc
            định.
          </p>
        </div>
      </div>
    )
  }

  return (
    <ChartContainer config={config} className="h-[280px] w-full">
      <BarChart
        data={data}
        margin={{ left: 4, right: 8, top: 16, bottom: 4 }}
      >
        <CartesianGrid
          strokeDasharray="3 3"
          vertical={false}
          className="stroke-border/60"
        />
        <XAxis
          dataKey="label"
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          className="text-xs"
        />
        <YAxis
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          width={32}
          allowDecimals={false}
        />
        <ChartTooltip
          content={
            <ChartTooltipContent
              labelKey="label"
              formatter={(value) => [`${value} sinh viên`, ""]}
            />
          }
        />
        <Bar dataKey="count" radius={[8, 8, 0, 0]} maxBarSize={80}>
          <LabelList
            dataKey="count"
            position="top"
            className="fill-foreground text-xs font-medium"
          />
        </Bar>
      </BarChart>
    </ChartContainer>
  )
}
