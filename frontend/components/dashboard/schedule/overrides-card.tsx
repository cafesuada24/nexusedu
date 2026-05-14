"use client";

import { CalendarX, Clock } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface OverridesCardProps {
  upcomingOverrides: Array<{
    id: string;
    type: string;
    date: string;
    note: string;
  }>;
}

export function OverridesCard({ upcomingOverrides }: OverridesCardProps) {
  return (
    <Card className="stripe-warning rounded-2xl border-warning/20 bg-gradient-to-br from-warning/22 via-warning/10 to-card">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <CalendarX className="size-4 text-warning" />
          Ngày nghỉ
        </CardTitle>
      </CardHeader>
      <CardContent className="grid gap-2">
        {upcomingOverrides.length === 0 ? (
          <div className="grid place-items-center gap-1.5 rounded-lg border border-dashed border-border/60 px-3 py-5">
            <span className="grid size-8 place-items-center rounded-lg bg-muted text-muted-foreground">
              <CalendarX className="size-3.5" />
            </span>
          </div>
        ) : (
          upcomingOverrides.map((o) => (
            <div
              key={o.id}
              className="flex items-start gap-3 rounded-lg border border-border/60 bg-muted/30 px-3 py-2.5"
            >
              <div
                className={cn(
                  "grid size-8 shrink-0 place-items-center rounded-lg ring-1",
                  o.type === "off"
                    ? "bg-destructive/10 text-destructive ring-destructive/20"
                    : "bg-warning/15 text-warning ring-warning/25"
                )}
              >
                {o.type === "off" ? (
                  <CalendarX className="size-4" />
                ) : (
                  <Clock className="size-4" />
                )}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="font-mono text-xs font-medium">{o.date}</p>
                  <Badge
                    variant={o.type === "off" ? "destructive" : "secondary"}
                    className="rounded-full px-1.5 py-0 text-[10px] font-normal"
                  >
                    {o.type === "off" ? "Nghỉ" : "Riêng"}
                  </Badge>
                </div>
                <p className="mt-0.5 truncate text-xs text-muted-foreground">
                  {o.note}
                </p>
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
