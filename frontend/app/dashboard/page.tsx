"use client"

import Link from "next/link"
import { Upload, LayoutDashboard, BellRing } from "lucide-react"
import { SuccessCaseStudies } from "@/components/dashboard/success-case-studies"
import { Button } from "@/components/ui/button"

export default function OverviewPage() {
  return (
    <div className="flex w-full flex-1 flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="grid size-10 place-items-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/20 shadow-sm shadow-primary/10">
            <LayoutDashboard className="size-5" />
          </div>
          <div className="flex items-center gap-2">
            <h1 className="font-serif text-2xl font-bold tracking-tight md:text-3xl">
              Tổng quan
            </h1>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline" size="sm" className="rounded-xl">
            <Link href="/dashboard/alerts" aria-label="Cảnh báo">
              <BellRing className="size-4" />
              Cảnh báo
            </Link>
          </Button>
          <Button asChild size="sm" className="rounded-xl">
            <Link href="/dashboard/import">
              <Upload className="size-4" />
              Nhập CSV
            </Link>
          </Button>
        </div>
      </div>

      <div
        aria-hidden
        className="h-px w-full bg-gradient-to-r from-primary/40 via-primary/10 to-transparent"
      />

      <SuccessCaseStudies />
    </div>
  )
}
