import {
  TrendingDown,
  Users,
  HandHeart,
  Target,
} from "lucide-react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { DropoutChart } from "@/components/dashboard/dropout-chart"
import { EngagementChart } from "@/components/dashboard/engagement-chart"
import { AdvisorLeaderboard } from "@/components/dashboard/advisor-leaderboard"

const kpis = [
  {
    label: "Dropout Prevention Rate",
    value: "87.4%",
    delta: "+4.1%",
    trend: "up",
    icon: Target,
    hint: "so với kỳ trước",
  },
  {
    label: "Sinh viên được can thiệp",
    value: "1,284",
    delta: "+312",
    trend: "up",
    icon: Users,
    hint: "trong 30 ngày",
  },
  {
    label: "Advisor Engagement",
    value: "92%",
    delta: "+6%",
    trend: "up",
    icon: HandHeart,
    hint: "tham gia HIL tuần này",
  },
  {
    label: "Tỷ lệ bỏ học",
    value: "2.1%",
    delta: "−0.8%",
    trend: "down",
    icon: TrendingDown,
    hint: "giảm toàn trường",
  },
]

export default function MetricsPage() {
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
      <div className="flex flex-col justify-between gap-3 md:flex-row md:items-end">
        <div>
          <h1 className="font-serif text-2xl font-bold tracking-tight md:text-3xl">
            BGH Dashboard
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Bức tranh tổng thể về hiệu quả chương trình đồng hành sinh viên.
          </p>
        </div>
        <Badge variant="outline" className="w-fit rounded-md">
          Học kỳ 2 · 2025–2026
        </Badge>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpis.map((k) => (
          <Card
            key={k.label}
            className="rounded-2xl border-border/60 transition-shadow hover:shadow-md"
          >
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {k.label}
              </CardTitle>
              <span className="grid size-9 place-items-center rounded-lg bg-primary/10 text-primary">
                <k.icon className="size-4" />
              </span>
            </CardHeader>
            <CardContent>
              <div className="font-serif text-3xl font-bold">{k.value}</div>
              <p className="mt-1 text-xs">
                <span
                  className={
                    k.trend === "up"
                      ? "font-semibold text-success"
                      : "font-semibold text-success"
                  }
                >
                  {k.delta}
                </span>{" "}
                <span className="text-muted-foreground">{k.hint}</span>
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="rounded-2xl border-border/60">
          <CardHeader>
            <CardTitle className="font-serif text-xl">
              Dropout Prevention Rate
            </CardTitle>
            <CardDescription>Tỷ lệ giữ chân theo tháng</CardDescription>
          </CardHeader>
          <CardContent>
            <DropoutChart />
          </CardContent>
        </Card>

        <Card className="rounded-2xl border-border/60">
          <CardHeader>
            <CardTitle className="font-serif text-xl">
              Advisor Engagement
            </CardTitle>
            <CardDescription>Số email HIL gửi / tuần theo khoa</CardDescription>
          </CardHeader>
          <CardContent>
            <EngagementChart />
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-2xl border-border/60">
        <CardHeader>
          <CardTitle className="font-serif text-xl">
            Cố vấn năng động nhất
          </CardTitle>
          <CardDescription>
            Ghi nhận những thầy cô đã dành nhiều thời gian cho sinh viên.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AdvisorLeaderboard />
        </CardContent>
      </Card>
    </div>
  )
}
