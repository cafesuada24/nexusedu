"use client"

import Link from "next/link"
import { Upload, LayoutDashboard, BellRing, ShieldAlert, BarChartHorizontal } from "lucide-react"
import { HeroDashboard } from "@/components/dashboard/hero-dashboard"
import { ThankYouNotes } from "@/components/dashboard/thank-you-notes"
import { AdminDashboard } from "@/components/dashboard/admin-dashboard"
import { AdminSummaryReport } from "@/components/dashboard/admin-summary-report"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/hooks/use-auth"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

export default function OverviewPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === "admin"

  return (
    <div className="flex w-full flex-1 flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className={cn(
            "grid size-10 place-items-center rounded-xl ring-1 shadow-sm",
            isAdmin 
              ? "bg-primary/10 text-primary ring-primary/20 shadow-primary/10" 
              : "bg-primary/10 text-primary ring-primary/20 shadow-primary/10"
          )}>
            {isAdmin ? <BarChartHorizontal className="size-5" /> : <LayoutDashboard className="size-5" />}
          </div>
          <div className="flex flex-col">
            <h1 className="font-serif text-2xl font-bold tracking-tight md:text-3xl">
              {isAdmin ? "Tổng quan Chiến lược" : "Tổng quan"}
            </h1>
            {isAdmin && (
              <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">
                Trung tâm Điều hành Ban giám hiệu
              </p>
            )}
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {isAdmin ? (
            <>
              <Button asChild size="sm" className="rounded-xl">
                <Link href="/dashboard/import">
                  <Upload className="size-4" />
                  Nhập CSV
                </Link>
              </Button>
            </>
          ) : (
            <>
              <Button asChild variant="destructive" size="sm" className="rounded-xl bg-red-600 hover:bg-red-700 text-white shadow-lg shadow-red-500/20 ring-red-500/50 border-none">
                <Link href="/dashboard/alerts" aria-label="Cảnh báo" className="flex items-center gap-2">
                  <BellRing className="size-4" />
                  Cảnh báo
                </Link>
              </Button>
            </>
          )}
        </div>
      </div>

      <div
        aria-hidden
        className={cn(
          "h-px w-full",
          isAdmin 
            ? "bg-gradient-to-r from-primary/60 via-primary/20 to-transparent"
            : "bg-gradient-to-r from-primary/40 via-primary/10 to-transparent"
        )}
      />

      {isAdmin ? (
        <>
          <AdminDashboard />
          <AdminSummaryReport />
        </>
      ) : (
        <>
          <HeroDashboard />
          <ThankYouNotes />
        </>
      )}
    </div>
  )
}
