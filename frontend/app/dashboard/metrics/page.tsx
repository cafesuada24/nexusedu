import {
  TrendingDown,
  Users,
  HandHeart,
  Target,
  BarChart3,
  type LucideIcon,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { DropoutChart } from "@/components/dashboard/dropout-chart";
import { EngagementChart } from "@/components/dashboard/engagement-chart";
import { AdvisorLeaderboard } from "@/components/dashboard/advisor-leaderboard";
import { cn } from "@/lib/utils";

type KpiTone = "primary" | "success" | "warning" | "destructive";

const KPI_TONES: Record<
  KpiTone,
  { tile: string; value: string; delta: string; card: string; stripe: string }
> = {
  primary: {
    tile: "bg-primary/10 text-primary ring-1 ring-primary/15",
    value: "text-foreground",
    delta: "text-primary",
    card: "border-primary/15 bg-gradient-to-br from-primary/20 via-primary/8 to-card",
    stripe: "stripe-primary",
  },
  success: {
    tile: "bg-success/10 text-success ring-1 ring-success/15",
    value: "text-success",
    delta: "text-success",
    card: "border-success/15 bg-gradient-to-br from-success/20 via-success/8 to-card",
    stripe: "stripe-success",
  },
  warning: {
    tile: "bg-warning/15 text-warning ring-1 ring-warning/20",
    value: "text-foreground",
    delta: "text-warning",
    card: "border-warning/20 bg-gradient-to-br from-warning/22 via-warning/10 to-card",
    stripe: "stripe-warning",
  },
  destructive: {
    tile: "bg-destructive/10 text-destructive ring-1 ring-destructive/15",
    value: "text-destructive",
    delta: "text-destructive",
    card: "border-destructive/15 bg-gradient-to-br from-destructive/20 via-destructive/8 to-card",
    stripe: "stripe-destructive",
  },
};

const kpis: Array<{
  label: string;
  value: string;
  delta: string;
  icon: LucideIcon;
  tone: KpiTone;
  positive: boolean;
}> = [
  {
    label: "Giữ chân SV",
    value: "87.4%",
    delta: "+4.1%",
    icon: Target,
    tone: "success",
    positive: true,
  },
  {
    label: "Đã can thiệp",
    value: "1,284",
    delta: "+312",
    icon: Users,
    tone: "primary",
    positive: true,
  },
  {
    label: "Cố vấn",
    value: "92%",
    delta: "+6%",
    icon: HandHeart,
    tone: "primary",
    positive: true,
  },
  {
    label: "Bỏ học",
    value: "2.1%",
    delta: "−0.8%",
    icon: TrendingDown,
    tone: "destructive",
    positive: true,
  },
];

export default function MetricsPage() {
  return (
    <div className="flex w-full flex-1 flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="grid size-10 place-items-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/20 shadow-sm shadow-primary/10">
            <BarChart3 className="size-5" />
          </div>
          <h1 className="font-serif text-2xl font-bold tracking-tight md:text-3xl">
            Báo cáo BGH
          </h1>
        </div>
        <Badge variant="outline" className="rounded-md font-mono text-[11px]">
          HK2 · 2025–2026
        </Badge>
      </div>

      {/* KPI tiles */}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {kpis.map((k) => {
          const tone = KPI_TONES[k.tone];
          return (
            <Card
              key={k.label}
              className={cn(
                "rounded-2xl transition-shadow hover:shadow-md",
                tone.card,
                tone.stripe,
              )}
            >
              <CardContent className="flex items-center gap-3 p-4">
                <span
                  className={cn(
                    "grid size-11 shrink-0 place-items-center rounded-xl",
                    tone.tile,
                  )}
                >
                  <k.icon className="size-5" />
                </span>
                <div className="min-w-0 flex-1">
                  <div
                    className={cn(
                      "font-serif text-2xl font-bold leading-none tabular-nums",
                      tone.value,
                    )}
                  >
                    {k.value}
                  </div>
                  <div className="mt-1 flex items-center gap-1.5 text-xs">
                    <span className="truncate text-muted-foreground">
                      {k.label}
                    </span>
                    <span
                      className={cn(
                        "ml-auto shrink-0 font-mono font-semibold",
                        tone.delta,
                      )}
                    >
                      {k.delta}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div
        aria-hidden
        className="h-px w-full bg-gradient-to-r from-primary/40 via-success/25 to-transparent"
      />

      {/* Charts */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="stripe-success rounded-2xl border-success/15 bg-gradient-to-br from-success/18 via-success/8 to-card">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 font-serif text-lg">
              <span className="grid size-7 place-items-center rounded-lg bg-success/10 text-success ring-1 ring-success/15">
                <Target className="size-3.5" />
              </span>
              Giữ chân
            </CardTitle>
          </CardHeader>
          <CardContent>
            <DropoutChart />
          </CardContent>
        </Card>

        <Card className="stripe-primary rounded-2xl border-primary/15 bg-gradient-to-br from-primary/18 via-primary/8 to-card">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 font-serif text-lg">
              <span className="grid size-7 place-items-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/15">
                <HandHeart className="size-3.5" />
              </span>
              Cố vấn tham gia
            </CardTitle>
          </CardHeader>
          <CardContent>
            <EngagementChart />
          </CardContent>
        </Card>
      </div>

      <Card className="stripe-warning rounded-2xl border-warning/20 bg-gradient-to-br from-warning/22 via-warning/10 to-card">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 font-serif text-lg">
            <span className="grid size-7 place-items-center rounded-lg bg-warning/15 text-warning ring-1 ring-warning/20">
              <HandHeart className="size-3.5" />
            </span>
            Hoạt động cố vấn
          </CardTitle>
        </CardHeader>
        <CardContent>
          <AdvisorLeaderboard />
        </CardContent>
      </Card>
    </div>
  );
}
