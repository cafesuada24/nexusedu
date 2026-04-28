"use client"

import { BookOpen, GraduationCap, TrendingDown } from "lucide-react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { describeProblem, type Problem, type StudentRow } from "@/lib/csv"

type Props = {
  students: StudentRow[]
  limit?: number
}

const iconFor: Record<Problem, typeof BookOpen> = {
  failed_final: GraduationCap,
  failed_midterm: BookOpen,
  low_average: TrendingDown,
}

const toneFor: Record<Problem, string> = {
  failed_final: "bg-destructive/10 text-destructive",
  failed_midterm: "bg-warning/15 text-warning",
  low_average: "bg-primary/10 text-primary",
}

function getInitials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .map((n) => n[0]?.toUpperCase() ?? "")
    .slice(-2)
    .join("")
}

export function RecentAlerts({ students, limit = 4 }: Props) {
  const ranked = [...students]
    .filter((s) => s.severity !== "low")
    .sort((a, b) => {
      const sev = (s: StudentRow["severity"]) => (s === "high" ? 2 : 1)
      if (sev(b.severity) !== sev(a.severity)) {
        return sev(b.severity) - sev(a.severity)
      }
      // Lower average score = more urgent.
      return a.averageScore - b.averageScore
    })
    .slice(0, limit)

  if (ranked.length === 0) {
    return (
      <div className="grid place-items-center gap-2 rounded-xl border border-dashed border-border/60 bg-muted/30 p-6 text-center">
        <span className="grid size-9 place-items-center rounded-lg bg-success/10 text-success">
          <GraduationCap className="size-4" />
        </span>
        <p className="text-xs text-muted-foreground">An toàn</p>
      </div>
    )
  }

  return (
    <ul className="space-y-2">
      {ranked.map((s) => {
        const main: Problem = s.problems[0] ?? "low_average"
        const Icon = iconFor[main]
        return (
          <li
            key={s.id}
            className="flex items-center gap-3 rounded-xl border border-border/60 bg-card p-3 transition-colors hover:bg-accent/50"
          >
            <Avatar className="size-9">
              <AvatarFallback className="bg-primary/10 text-primary text-xs font-semibold">
                {getInitials(s.name)}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{s.name}</p>
              <p className="truncate text-xs text-muted-foreground">
                {describeProblem(s)}
              </p>
            </div>
            <Badge
              variant="secondary"
              className={`${toneFor[main]} rounded-md hover:${toneFor[main]}`}
            >
              <Icon className="size-3" />
            </Badge>
          </li>
        )
      })}
    </ul>
  )
}
