"use client";

import { Clock } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { ScheduleEditorSheet } from "@/components/dashboard/schedule-editor-sheet";
import { cn } from "@/lib/utils";
import {
  DAYS,
  DAY_ORDER,
  type WeekSchedule,
  type DayKey,
  convertUtcToUtc7,
} from "@/lib/schedule";

interface WorkingHoursCardProps {
  week: WeekSchedule;
  onToggleDay: (key: DayKey, enabled: boolean) => void;
  disabled?: boolean;
}

export function WorkingHoursCard({
  week,
  onToggleDay,
  disabled,
}: WorkingHoursCardProps) {
  return (
    <Card className="stripe-indigo rounded-2xl border-accent-indigo/15 bg-gradient-to-br from-accent-indigo/22 via-accent-indigo/10 to-card lg:col-span-2">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Clock className="size-4 text-primary" />
          Giờ làm việc (UTC+7)
        </CardTitle>
        <ScheduleEditorSheet />
      </CardHeader>
      <CardContent className="px-2 pb-2">
        <div className="flex flex-col overflow-hidden rounded-xl border border-border/60 bg-muted/30">
          {DAY_ORDER.map((key, index) => {
            const dayConfig = week[key];
            const dayInfo = DAYS.find((d) => d.key === key)!;
            const hasSlots = dayConfig.slots.length > 0;

            const timeDisplay = !dayConfig.enabled
              ? "Nghỉ"
              : !hasSlots
              ? "Trống"
              : dayConfig.slots
                  .map(
                    (s) =>
                      `${convertUtcToUtc7(s.from)} – ${convertUtcToUtc7(
                        s.to
                      )}`
                  )
                  .join(" · ");

            return (
              <div
                key={key}
                className={cn(
                  "flex items-center justify-between px-4 py-3 transition-colors hover:bg-muted/50",
                  index !== DAY_ORDER.length - 1 && "border-b border-border/40"
                )}
              >
                <div className="flex min-w-0 items-center gap-3">
                  <span
                    aria-hidden
                    className={cn(
                      "size-2 shrink-0 rounded-full",
                      dayConfig.enabled ? "bg-success" : "bg-muted-foreground/30"
                    )}
                  />
                  <div className="min-w-0">
                    <p className="text-sm font-medium">{dayInfo.long}</p>
                    <p
                      className={cn(
                        "font-mono text-[11px]",
                        dayConfig.enabled && hasSlots
                          ? "text-muted-foreground"
                          : "text-muted-foreground/60 italic"
                      )}
                    >
                      {timeDisplay}
                    </p>
                  </div>
                </div>
                <Switch
                  checked={dayConfig.enabled}
                  onCheckedChange={(v) => onToggleDay(key, v)}
                  disabled={disabled}
                />
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
