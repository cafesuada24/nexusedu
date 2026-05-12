"use client"

import * as React from "react"
import { Loader2, AlertCircle } from "lucide-react"
import { TooltipProvider } from "@/components/ui/tooltip"
import { useScheduleQuery } from "@/hooks/use-schedule-query"
import { useAuth } from "@/hooks/use-auth"
import { totalWeeklyHours, type DayKey, DEFAULT_SCHEDULE } from "@/lib/schedule"
import { ScheduleStats } from "./schedule/schedule-stats"
import { WorkingHoursCard } from "./schedule/working-hours-card"
import { OverridesCard } from "./schedule/overrides-card"
import { BookingLinkCard } from "./schedule/booking-link-card"

export function ScheduleView() {
  const { schedule, setSchedule, isLoading, isMutating, isError } =
    useScheduleQuery()
  const { user } = useAuth()

  const bookingSlug = user?.email?.split("@")[0] || "advisor"
  const bookingUrl = `https://nexusedu.app/booking/${bookingSlug}`
  const displayUrl = `nexusedu.app/booking/${bookingSlug}`

  const weeklyHours = React.useMemo(
    () => totalWeeklyHours(schedule.week),
    [schedule.week],
  )

  const weeklyCapacity = React.useMemo(() => {
    const step = DEFAULT_SCHEDULE.duration + DEFAULT_SCHEDULE.buffer
    if (!step) return 0
    return Math.floor((weeklyHours * 60) / step)
  }, [weeklyHours])

  const upcomingOverrides = React.useMemo(
    () => schedule.overrides.slice(0, 4),
    [schedule.overrides],
  )

  const toggleDay = (key: DayKey, enabled: boolean) => {
    if (isMutating) return
    setSchedule((prev) => {
      const next = { ...prev.week }
      next[key] = { ...next[key], enabled }
      return { ...prev, week: next }
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
        <span className="ml-2 text-sm text-muted-foreground">
          Đang tải lịch làm việc…
        </span>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3">
        <AlertCircle className="size-5 text-destructive" />
        <p className="text-sm text-destructive">
          Không thể tải lịch làm việc. Vui lòng thử lại sau.
        </p>
      </div>
    )
  }

  return (
    <TooltipProvider delayDuration={150}>
      <div className="grid gap-6">
        <ScheduleStats
          weeklyHours={weeklyHours}
          weeklyCapacity={weeklyCapacity}
          duration={DEFAULT_SCHEDULE.duration}
        />

        <div className="grid gap-6 lg:grid-cols-3">
          <WorkingHoursCard
            week={schedule.week}
            onToggleDay={toggleDay}
            disabled={isMutating}
          />

          <div className="grid gap-6">
            <OverridesCard upcomingOverrides={upcomingOverrides} />

            <BookingLinkCard
              displayUrl={displayUrl}
              bookingUrl={bookingUrl}
            />
          </div>
        </div>
      </div>
    </TooltipProvider>
  )
}

