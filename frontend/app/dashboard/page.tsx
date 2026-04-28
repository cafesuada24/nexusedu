"use client"

import Link from "next/link"
import { ArrowRight, Upload, LineChart, BellRing, LayoutDashboard } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { SuccessCaseStudies } from "@/components/dashboard/success-case-studies"
import { useDataset } from "@/hooks/use-dataset"

export default function OverviewPage() {
  const { dataset, isLoading } = useDataset()

  return (
    <div className="flex w-full flex-1 flex-col gap-6">
      {/* Compact header — icon + counter pill, no greeting prose */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="grid size-10 place-items-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/20 shadow-sm shadow-primary/10">
            <LayoutDashboard className="size-5" />
          </div>
          <div className="flex items-center gap-2">
            <h1 className="font-serif text-2xl font-bold tracking-tight md:text-3xl">
              Tổng quan
            </h1>
            {isLoading ? (
              <Skeleton className="h-6 w-20 rounded-full" />
            ) : dataset ? (
              <Badge variant="secondary" className="rounded-full bg-primary/10 text-primary hover:bg-primary/10">
                {dataset.totalStudents.toLocaleString("vi-VN")} SV
              </Badge>
            ) : null}
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {dataset ? (
            <>
              <Button asChild variant="outline" size="sm" className="rounded-xl">
                <Link href="/dashboard/analysis" aria-label="Phân tích">
                  <LineChart className="size-4" />
                  <span className="hidden sm:inline">Phân tích</span>
                </Link>
              </Button>
              <Button asChild size="sm" className="rounded-xl">
                <Link href="/dashboard/alerts" aria-label="Cảnh báo">
                  <BellRing className="size-4" />
                  <span className="hidden sm:inline">Cảnh báo</span>
                  <ArrowRight className="size-4" />
                </Link>
              </Button>
            </>
          ) : (
            <Button asChild size="sm" className="rounded-xl">
              <Link href="/dashboard/import">
                <Upload className="size-4" />
                Nhập CSV
              </Link>
            </Button>
          )}
        </div>
      </div>

      <div className="page-divider w-full" aria-hidden />

      {!isLoading && !dataset && (
        <Card className="stripe-primary rounded-2xl border-dashed border-primary/30 bg-gradient-to-br from-primary/25 via-accent-sky/15 to-card">
          <CardContent className="flex items-center justify-between gap-3 p-4">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Upload className="size-4 text-primary" />
              Chưa có dữ liệu
            </div>
            <Button asChild size="sm" className="rounded-lg">
              <Link href="/dashboard/import">
                Nhập CSV
                <ArrowRight className="size-3.5" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      )}

      <SuccessCaseStudies />
    </div>
  )
}
