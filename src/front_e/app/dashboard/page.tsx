"use client";

import Link from "next/link";
import {
  Users,
  AlertTriangle,
  Clock,
  MailCheck,
  ArrowRight,
  Upload,
  FileSpreadsheet,
  RefreshCw,
  type LucideIcon,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { RiskTrendChart } from "@/components/dashboard/risk-trend-chart";
import { RecentAlerts } from "@/components/dashboard/recent-alerts";
import { OverviewEmptyState } from "@/components/dashboard/overview-empty-state";
import { useDataset, type Dataset } from "@/hooks/use-dataset";

type Stat = {
  label: string;
  value: string;
  hint: string;
  icon: LucideIcon;
  tone?: "default" | "destructive";
};

function buildStats(d: Dataset): Stat[] {
  // Defensive defaults in case stored dataset is missing numeric fields.
  const totalStudents =
    typeof d.totalStudents === "number" && Number.isFinite(d.totalStudents)
      ? d.totalStudents
      : 0;
  const totalTests =
    typeof d.totalTests === "number" && Number.isFinite(d.totalTests)
      ? d.totalTests
      : 0;
  const highRisk =
    typeof d.highRisk === "number" && Number.isFinite(d.highRisk)
      ? d.highRisk
      : 0;
  const draftEmails =
    typeof d.draftEmails === "number" && Number.isFinite(d.draftEmails)
      ? d.draftEmails
      : 0;
  const averageScore =
    typeof d.averageScore === "number" && Number.isFinite(d.averageScore)
      ? d.averageScore
      : 0;

  const highPct =
    totalStudents > 0 ? Math.round((highRisk / totalStudents) * 100) : 0;
  // Rough estimate: ~15 minutes saved per AI-drafted follow-up email.
  const savedHours = Math.round((draftEmails * 15) / 60);

  return [
    {
      label: "Tổng sinh viên",
      value: totalStudents.toLocaleString("vi-VN"),
      hint: `${totalTests.toLocaleString("vi-VN")} bài kiểm tra`,
      icon: Users,
    },
    {
      label: "Nguy cơ cao",
      value: highRisk.toLocaleString("vi-VN"),
      hint: `${highPct}% tổng số sinh viên`,
      icon: AlertTriangle,
      tone: highRisk > 0 ? "destructive" : "default",
    },
    {
      label: "Email cần gửi",
      value: draftEmails.toLocaleString("vi-VN"),
      hint: "chưa từng liên hệ",
      icon: MailCheck,
    },
    {
      label: "Điểm TB toàn lớp",
      value: averageScore.toFixed(2),
      hint: `${savedHours}h tiết kiệm dự kiến`,
      icon: Clock,
    },
  ];
}

function formatTimeAgo(iso: string) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "vừa xong";
  if (mins < 60) return `${mins} phút trước`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} giờ trước`;
  const days = Math.floor(hours / 24);
  return `${days} ngày trước`;
}

export default function OverviewPage() {
  const { dataset, isLoading } = useDataset();

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
      <div className="flex flex-col justify-between gap-3 md:flex-row md:items-end">
        <div>
          <h1 className="font-serif text-2xl font-bold tracking-tight md:text-3xl">
            Xin chào, TS. Lê Hà
          </h1>
          <div className="mt-1 text-sm text-muted-foreground">
            {isLoading ? (
              // Use a span to avoid block-level elements inside text containers,
              // but keep Skeleton visually similar. If Skeleton renders a div,
              // wrapping it in a span prevents illegal <div> inside <p>.
              <span className="inline-block align-middle">
                <Skeleton className="inline-block h-4 w-64 align-middle" />
              </span>
            ) : dataset ? (
              <>
                Tuần này có{" "}
                <span className="font-semibold text-foreground">
                  {dataset.highRisk}
                </span>{" "}
                sinh viên cần sự chú ý của bạn.
              </>
            ) : (
              "Hãy nhập danh sách sinh viên để bắt đầu theo dõi."
            )}
          </div>
        </div>
        <div className="flex gap-2">
          {dataset ? (
            <>
              <Button asChild variant="outline" className="rounded-xl">
                <Link href="/dashboard/import">
                  <Upload className="size-4" />
                  Tải CSV mới
                </Link>
              </Button>
              <Button asChild className="rounded-xl">
                <Link href="/dashboard/alerts">
                  Xem cảnh báo
                  <ArrowRight className="size-4" />
                </Link>
              </Button>
            </>
          ) : (
            <Button asChild className="rounded-xl">
              <Link href="/dashboard/import">
                <Upload className="size-4" />
                Nhập CSV ngay
              </Link>
            </Button>
          )}
        </div>
      </div>

      {isLoading ? (
        <OverviewSkeleton />
      ) : !dataset ? (
        <OverviewEmptyState />
      ) : (
        <>
          <Card className="rounded-2xl border-primary/20 bg-primary/5">
            <CardContent className="flex flex-col items-start justify-between gap-3 p-4 sm:flex-row sm:items-center">
              <div className="flex items-center gap-3">
                <span className="grid size-10 place-items-center rounded-xl bg-primary/15 text-primary">
                  <FileSpreadsheet className="size-5" />
                </span>
                <div>
                  <p className="text-sm font-medium">
                    Đang phân tích{" "}
                    <span className="font-mono">{dataset.fileName}</span>
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Cập nhật {formatTimeAgo(dataset.uploadedAt)} ·{" "}
                    {dataset.totalStudents.toLocaleString("vi-VN")} bản ghi ·{" "}
                    {dataset.sizeKB.toFixed(1)} KB
                  </p>
                </div>
              </div>
              <Button
                asChild
                variant="outline"
                size="sm"
                className="rounded-lg"
              >
                <Link href="/dashboard/import">
                  <RefreshCw className="size-3.5" />
                  Cập nhật dữ liệu
                </Link>
              </Button>
            </CardContent>
          </Card>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {buildStats(dataset).map((s) => (
              <Card
                key={s.label}
                className="rounded-2xl border-border/60 transition-shadow hover:shadow-md"
              >
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    {s.label}
                  </CardTitle>
                  <span
                    className={
                      s.tone === "destructive"
                        ? "grid size-9 place-items-center rounded-lg bg-destructive/10 text-destructive"
                        : "grid size-9 place-items-center rounded-lg bg-primary/10 text-primary"
                    }
                  >
                    <s.icon className="size-4" />
                  </span>
                </CardHeader>
                <CardContent>
                  <div className="font-serif text-3xl font-bold">{s.value}</div>
                  <div className="mt-1 flex items-center gap-1.5 text-xs">
                    <Badge
                      variant="secondary"
                      className="rounded-md bg-muted text-muted-foreground hover:bg-muted"
                    >
                      {s.hint}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="rounded-2xl border-border/60 lg:col-span-2">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="font-serif text-xl">
                      Phân bố sinh viên theo vấn đề
                    </CardTitle>
                    <CardDescription>
                      Dựa trên dữ liệu CSV đã nhập · có thể trùng (SV có nhiều
                      vấn đề)
                    </CardDescription>
                  </div>
                  <Badge
                    variant="outline"
                    className="rounded-md border-primary/30 text-primary"
                  >
                    {formatTimeAgo(dataset.uploadedAt)}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <RiskTrendChart problemCounts={dataset.problemCounts} />
              </CardContent>
            </Card>

            <Card className="rounded-2xl border-border/60">
              <CardHeader>
                <CardTitle className="font-serif text-xl">
                  Cảnh báo mới nhất
                </CardTitle>
                <CardDescription>
                  Top sinh viên nguy cơ trong file hiện tại
                </CardDescription>
              </CardHeader>
              <CardContent>
                <RecentAlerts students={dataset.students} />
                <Button
                  asChild
                  variant="ghost"
                  className="mt-2 w-full justify-center rounded-xl"
                >
                  <Link href="/dashboard/alerts">
                    Xem tất cả
                    <ArrowRight className="size-4" />
                  </Link>
                </Button>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

function OverviewSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-32 rounded-2xl" />
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Skeleton className="h-80 rounded-2xl lg:col-span-2" />
        <Skeleton className="h-80 rounded-2xl" />
      </div>
    </div>
  );
}
