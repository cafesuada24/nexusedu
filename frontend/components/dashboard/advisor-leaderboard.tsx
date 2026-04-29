"use client"

import { Mail, CheckCircle2, Loader2 } from "lucide-react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { useAdvisorsLeaderboard } from "@/hooks/use-advisors"

export function AdvisorLeaderboard() {
  const { data: advisors, isLoading, error } = useAdvisorsLeaderboard("all_time")

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-destructive">
        Không thể tải dữ liệu bảng xếp hạng.
      </div>
    )
  }

  if (!advisors || advisors.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
        Chưa có dữ liệu hoạt động.
      </div>
    )
  }

  // Calculate rate and initials for each advisor, and sort by points
  const processedAdvisors = [...advisors]
    .sort((a, b) => b.total_points - a.total_points)
    .map((l, index) => {
      const initials = l.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
      
      const rate = l.sent_count > 0 
        ? Math.round((l.resolved_count / l.sent_count) * 100) 
        : 0

      return {
        ...l,
        rank: index + 1,
        initials,
        rate: Math.min(rate, 100), // Cap at 100% just in case
      }
    })

  return (
    <TooltipProvider delayDuration={150}>
      <ol className="divide-y divide-border">
        {processedAdvisors.map((l) => {
          return (
            <li
              key={l.advisor_id}
              className="flex flex-col gap-3 py-3 first:pt-0 last:pb-0 md:flex-row md:items-center"
            >
              <div className="flex items-center gap-3 md:w-72">
                <span
                  className="grid size-9 place-items-center rounded-xl bg-muted font-mono text-sm font-semibold text-muted-foreground ring-1 ring-border"
                  aria-label={`Số thứ tự ${l.rank}`}
                >
                  {l.rank}
                </span>
                <Avatar className="size-9">
                  <AvatarFallback className="bg-primary/10 text-primary text-xs font-semibold">
                    {l.initials}
                  </AvatarFallback>
                </Avatar>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold">{l.name}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    Cố vấn học tập
                  </p>
                </div>
              </div>

              <div className="flex-1">
                <div className="mb-1.5 flex items-center justify-between">
                  <span
                    className="font-mono text-xs font-semibold text-success"
                    aria-label="Tỷ lệ giải quyết"
                  >
                    {l.rate}%
                  </span>
                  <span className="text-[10px] text-muted-foreground uppercase font-medium">
                    {l.total_points} điểm
                  </span>
                </div>
                <Progress value={l.rate} className="h-1.5" />
              </div>

              <div className="flex gap-1.5 md:w-auto md:justify-end">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Badge
                      variant="outline"
                      className="gap-1 rounded-md font-mono text-[11px]"
                    >
                      <Mail className="size-3" />
                      {l.sent_count}
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent>{l.sent_count} email đã gửi</TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Badge
                      variant="secondary"
                      className="gap-1 rounded-md bg-success/15 font-mono text-[11px] text-success hover:bg-success/15"
                    >
                      <CheckCircle2 className="size-3" />
                      {l.resolved_count}
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent>{l.resolved_count} đã xử lý</TooltipContent>
                </Tooltip>
              </div>
            </li>
          )
        })}
      </ol>
    </TooltipProvider>
  )
}
