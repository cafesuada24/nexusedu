"use client"

import * as React from "react"
import { TooltipProvider } from "@/components/ui/tooltip"
import { useScheduleQuery } from "@/hooks/use-schedule-query"
import { useAuth } from "@/hooks/use-auth"
import { summarizeWeek, totalWeeklyHours, type DayKey } from "@/lib/schedule"
import { ScheduleStats } from "./schedule/schedule-stats"
import { WorkingHoursCard } from "./schedule/working-hours-card"
import { OverridesCard } from "./schedule/overrides-card"
import { BookingLinkCard } from "./schedule/booking-link-card"

export function ScheduleView() {
  const { schedule, setSchedule } = useScheduleQuery()
  const { user } = useAuth()

  const bookingSlug = user?.email?.split("@")[0] || "advisor"
  const bookingUrl = `https://nexusedu.app/booking/${bookingSlug}`
  const displayUrl = `nexusedu.app/booking/${bookingSlug}`

  const weekSummary = React.useMemo(
    () => summarizeWeek(schedule.week),
    [schedule.week],
  )

  const weeklyHours = React.useMemo(
    () => totalWeeklyHours(schedule.week),
    [schedule.week],
  )

  const weeklyCapacity = React.useMemo(() => {
    const step = schedule.duration + schedule.buffer
    if (!step) return 0
    return Math.floor((weeklyHours * 60) / step)
  }, [weeklyHours, schedule.duration, schedule.buffer])

  const upcomingOverrides = React.useMemo(
    () => schedule.overrides.slice(0, 4),
    [schedule.overrides],
  )

  const toggleGroup = (keys: DayKey[], enabled: boolean) => {
    setSchedule((prev) => {
      const next = { ...prev.week }
      keys.forEach((k) => {
        next[k] = { ...next[k], enabled }
      })
      return { ...prev, week: next }
    })
  }

  return (
    <TooltipProvider delayDuration={150}>
      <div className="grid gap-6">
        <ScheduleStats
          weeklyHours={weeklyHours}
          weeklyCapacity={weeklyCapacity}
          duration={schedule.duration}
          minNotice={schedule.minNotice}
        />

        <div className="grid gap-6 lg:grid-cols-3">
          <WorkingHoursCard
            weekSummary={weekSummary}
            onToggleGroup={toggleGroup}
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
