"use client"

import Link from "next/link"
import { Mail, MailCheck, Send, Sparkles } from "lucide-react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { describeProblem, type StudentRow } from "@/lib/csv"

type Props = {
  students: StudentRow[]
  limit?: number
}

function getInitials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .map((n) => n[0]?.toUpperCase() ?? "")
    .slice(-2)
    .join("")
}

export function PendingEmails({ students, limit = 6 }: Props) {
  // One email per high-risk student — khớp với số "Nguy cơ cao".
  const pending = students
    .filter((s) => s.severity === "high")
    .sort((a, b) => {
      // Chưa liên hệ xếp trước, rồi tới điểm TB thấp nhất.
      const ac = a.lastContactedAt ? 1 : 0
      const bc = b.lastContactedAt ? 1 : 0
      if (ac !== bc) return ac - bc
      return a.averageScore - b.averageScore
    })

  const total = pending.length
  const shown = pending.slice(0, limit)

  if (total === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border/60 bg-muted/30 p-6 text-center">
        <span className="mx-auto mb-2 grid size-10 place-items-center rounded-xl bg-primary/10 text-primary">
          <MailCheck className="size-5" />
        </span>
        <p className="text-sm font-medium">
          Không có email nào đang chờ gửi
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          Hiện không có sinh viên nào ở mức nguy cơ cao trong dữ liệu này.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <ul className="grid gap-2 sm:grid-cols-2">
        {shown.map((s) => (
          <li
            key={s.id}
            className="flex items-start gap-3 rounded-xl border border-border/60 bg-card p-3 transition-colors hover:border-primary/40 hover:bg-accent/40"
          >
            <Avatar className="size-9 shrink-0">
              <AvatarFallback className="bg-destructive/10 text-destructive text-xs font-semibold">
                {getInitials(s.name)}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{s.name}</p>
                  <p className="truncate font-mono text-[11px] text-muted-foreground">
                    {s.email || s.id}
                  </p>
                </div>
                <Badge
                  variant="secondary"
                  className="shrink-0 rounded-md bg-destructive/10 text-destructive hover:bg-destructive/10"
                >
                  {s.averageScore.toFixed(0)}
                </Badge>
              </div>
              <p className="mt-1 truncate text-xs text-muted-foreground">
                {describeProblem(s)}
              </p>
              <div className="mt-2 flex items-center gap-1.5">
                <Badge
                  variant="outline"
                  className="rounded-md border-primary/30 text-[10px] text-primary"
                >
                  <Sparkles className="size-2.5" />
                  AI draft sẵn
                </Badge>
                <Button
                  asChild
                  size="sm"
                  variant="ghost"
                  className="h-7 rounded-lg px-2 text-xs"
                >
                  <Link href="/dashboard/alerts">
                    <Send className="size-3" />
                    Soạn
                  </Link>
                </Button>
              </div>
            </div>
          </li>
        ))}
      </ul>

      {total > shown.length && (
        <div className="flex items-center justify-between rounded-xl border border-dashed border-border/60 bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <Mail className="size-3.5" />
            Còn {total - shown.length} email khác đang chờ gửi.
          </span>
          <Button
            asChild
            size="sm"
            variant="ghost"
            className="h-7 rounded-lg px-2 text-xs"
          >
            <Link href="/dashboard/alerts">Xem tất cả</Link>
          </Button>
        </div>
      )}
    </div>
  )
}
