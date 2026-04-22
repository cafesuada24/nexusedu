"use client"

import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"

const data = [
  { faculty: "CNTT", sent: 148, drafted: 52 },
  { faculty: "Kinh tế", sent: 112, drafted: 38 },
  { faculty: "Cơ khí", sent: 88, drafted: 24 },
  { faculty: "Ngoại ngữ", sent: 74, drafted: 20 },
  { faculty: "Xây dựng", sent: 62, drafted: 18 },
  { faculty: "Kiến trúc", sent: 54, drafted: 14 },
]

const config = {
  sent: { label: "Đã gửi", color: "var(--chart-1)" },
  drafted: { label: "Chờ duyệt", color: "var(--chart-2)" },
} satisfies ChartConfig

export function EngagementChart() {
  return (
    <ChartContainer config={config} className="h-[280px] w-full">
      <BarChart data={data} margin={{ left: 4, right: 8, top: 8 }}>
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
