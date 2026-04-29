"use client";

import { Clock } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { ScheduleEditorSheet } from "@/components/dashboard/schedule-editor-sheet";
import { cn } from "@/lib/utils";

interface WorkingHoursCardProps {
  weekSummary: Array<{
    keys: string[];
    label: string;
    hours: string;
    enabled: boolean;
  }>;
  onToggleGroup: (keys: any[], enabled: boolean) => void;
}

export function WorkingHoursCard({
  weekSummary,
  onToggleGroup,
}: WorkingHoursCardProps) {
  return (
    <Card className="stripe-indigo rounded-2xl border-accent-indigo/15 bg-gradient-to-br from-accent-indigo/22 via-accent-indigo/10 to-card lg:col-span-2">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Clock className="size-4 text-primary" />
          Giờ làm việc
        </CardTitle>
        <ScheduleEditorSheet />
      </CardHeader>
      <CardContent className="grid gap-2 text-sm">
        {weekSummary.map((group) => (
          <div
            key={group.keys.join("-")}
            className="flex items-center justify-between rounded-xl border border-border/60 bg-muted/30 px-4 py-3"
          >
            <div className="flex min-w-0 items-center gap-2.5">
              <span
                aria-hidden
                className={cn(
                  "size-2 rounded-full transition-colors",
                  group.enabled ? "bg-success" : "bg-muted-foreground/30"
                )}
              />
              <div className="min-w-0">
                <p className="font-medium">{group.label}</p>
                <p className="truncate font-mono text-[11px] text-muted-foreground">
                  {group.hours}
                </p>
              </div>
            </div>
            <Switch
              checked={group.enabled}
              onCheckedChange={(v) => onToggleGroup(group.keys, v)}
            />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
