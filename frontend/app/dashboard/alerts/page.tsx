"use client";

import { AlertTriangle, BellRing, MailCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertCenter } from "@/components/dashboard/alert-center";
import { useDataset } from "@/hooks/use-dataset";

export default function AlertsPage() {
  const { dataset, isLoading } = useDataset();

  return (
    <div className="flex w-full flex-1 flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="grid size-10 place-items-center rounded-xl bg-destructive/10 text-destructive ring-1 ring-destructive/20 shadow-sm shadow-destructive/10">
          <BellRing className="size-5" />
        </div>
        <h1 className="font-serif text-2xl font-bold tracking-tight md:text-3xl">
          Trung tâm cảnh báo
        </h1>

        {/* Live metrics — sourced from the Analysis dataset so the two
            screens stay in sync. We expose both "Nguy cơ cao" and
            "Email cần gửi" instead of a single fixed count. */}
        {isLoading ? (
          <div className="ml-1 flex items-center gap-2">
            <Skeleton className="h-6 w-28 rounded-full" />
            <Skeleton className="h-6 w-32 rounded-full" />
          </div>
        ) : dataset ? (
          <div className="ml-1 flex flex-wrap items-center gap-2">
            <Badge
              variant="outline"
              className="gap-1.5 rounded-full border-destructive/25 bg-destructive/10 px-2.5 py-0.5 text-destructive hover:bg-destructive/15"
            >
              <AlertTriangle className="size-3.5" aria-hidden />
              <span className="font-mono tabular-nums">
                {dataset.highRisk.toLocaleString("vi-VN")}
              </span>
              <span className="hidden sm:inline">nguy cơ cao</span>
              <span className="sm:hidden">cao</span>
            </Badge>
            <Badge
              variant="outline"
              className="gap-1.5 rounded-full border-warning/25 bg-warning/10 px-2.5 py-0.5 text-warning hover:bg-warning/15"
            >
              <MailCheck className="size-3.5" aria-hidden />
              <span className="font-mono tabular-nums">
                {dataset.draftEmails.toLocaleString("vi-VN")}
              </span>
              <span className="hidden sm:inline">email cần gửi</span>
              <span className="sm:hidden">email</span>
            </Badge>
          </div>
        ) : null}
      </div>

      <div
        aria-hidden
        className="h-px w-full bg-gradient-to-r from-destructive/40 via-warning/30 to-transparent"
      />

      <AlertCenter />
    </div>
  );
}
