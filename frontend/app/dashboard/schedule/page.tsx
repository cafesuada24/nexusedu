import { CalendarClock } from "lucide-react"
import { ScheduleView } from "@/components/dashboard/schedule-view"

export default function SchedulePage() {
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
