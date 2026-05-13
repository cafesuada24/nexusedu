"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { CalendarClock, Loader2 } from "lucide-react"
import { ScheduleView } from "@/components/dashboard/schedule-view"
import { useAuth } from "@/hooks/use-auth"

export default function SchedulePage() {
  const { user, loading } = useAuth()
  const router = useRouter()

  React.useEffect(() => {
    if (!loading && user && user.role === "admin") {
      router.replace("/dashboard")
    }
  }, [user, loading, router])

  if (loading || (user && user.role === "admin")) {
    return (
      <div className="flex min-h-[400px] w-full flex-col items-center justify-center gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-primary opacity-20" />
        <p className="text-sm font-medium text-muted-foreground animate-pulse">
          Đang xác thực quyền truy cập...
        </p>
      </div>
    )
  }

  return (
    <div className="flex w-full flex-1 flex-col gap-6">
      <div className="flex items-center gap-3">
        <div className="grid size-10 place-items-center rounded-xl bg-accent-indigo/10 text-accent-indigo ring-1 ring-accent-indigo/20 shadow-sm shadow-accent-indigo/10">
          <CalendarClock className="size-5" />
        </div>
        <h1 className="font-serif text-2xl font-bold tracking-tight md:text-3xl">
          Lịch làm việc
        </h1>
      </div>
      <div
        aria-hidden
        className="h-px w-full bg-gradient-to-r from-accent-indigo/40 via-primary/25 to-transparent"
      />
      <ScheduleView />
    </div>
  )
}
