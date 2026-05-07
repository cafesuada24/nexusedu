"use client";

import { Clock, Users, CalendarClock, type LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type StatTone = "primary" | "success" | "warning";

const TONE_CLASSES: Record<StatTone, string> = {
  primary: "bg-primary/10 text-primary ring-1 ring-primary/15",
  success: "bg-success/10 text-success ring-1 ring-success/15",
  warning: "bg-warning/15 text-warning ring-1 ring-warning/20",
};

const STAT_CARD_CLASSES: Record<StatTone, string> = {
  primary: "stripe-primary border-primary/15 bg-gradient-to-br from-primary/18 via-primary/8 to-card",
  success: "stripe-success border-success/15 bg-gradient-to-br from-success/18 via-success/8 to-card",
  warning: "stripe-warning border-warning/20 bg-gradient-to-br from-warning/22 via-warning/10 to-card",
};

interface ScheduleStatsProps {
  weeklyHours: number;
  weeklyCapacity: number;
  duration: number;
}

export function ScheduleStats({
  weeklyHours,
  weeklyCapacity,
  duration,
}: ScheduleStatsProps) {
  const stats: Array<{
    label: string;
    value: string;
    icon: LucideIcon;
    tone: StatTone;
  }> = [
    {
      label: "Giờ/tuần",
      value: weeklyHours.toFixed(1),
      icon: Clock,
      tone: "primary",
    },
    {
      label: "Sức chứa",
      value: `~${weeklyCapacity}`,
      icon: Users,
      tone: "success",
    },
    {
      label: "Phút/cuộc",
      value: `${duration}`,
      icon: CalendarClock,
      tone: "warning",
    },
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {stats.map((s) => (
        <Card
          key={s.label}
          className={cn(
            "rounded-2xl transition-shadow hover:shadow-md",
            STAT_CARD_CLASSES[s.tone]
          )}
        >
          <CardContent className="flex items-center gap-3 p-4">
            <div
              className={cn(
                "grid size-11 place-items-center rounded-xl",
                TONE_CLASSES[s.tone]
              )}
            >
              <s.icon className="size-5" />
            </div>
            <div className="min-w-0">
              <p className="font-serif text-xl font-bold leading-none tabular-nums">
                {s.value}
              </p>
              <p className="mt-1 truncate text-xs text-muted-foreground">
                {s.label}
              </p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
