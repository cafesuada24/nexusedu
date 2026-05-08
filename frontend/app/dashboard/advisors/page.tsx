"use client"

import { Users } from "lucide-react"
import { AdvisorManagement } from "@/components/dashboard/advisor-management"

export default function AdvisorsPage() {
  return (
    <div className="flex w-full flex-1 flex-col gap-6">
      <div className="flex items-center gap-3">
        <div className="grid size-10 place-items-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/20 shadow-sm shadow-primary/10">
          <Users className="size-5" />
        </div>
        <div className="flex flex-col">
          <h1 className="font-serif text-2xl font-bold tracking-tight md:text-3xl">
            Quản lý cố vấn
          </h1>
          <p className="text-sm text-muted-foreground">
            Tổng quan hiệu suất và tải trọng của cố vấn học tập
          </p>
        </div>
      </div>

      <div
        aria-hidden
        className="h-px w-full bg-gradient-to-r from-primary/40 via-primary/10 to-transparent"
      />

      <AdvisorManagement />
    </div>
  )
}
