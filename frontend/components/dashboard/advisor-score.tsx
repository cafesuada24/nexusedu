"use client"

import * as React from "react"
import { Trophy } from "lucide-react"
import { useQuery } from "@tanstack/react-query"
import { fetchAdvisorPoints } from "@/lib/api"
import { useAuth } from "@/hooks/use-auth"
import { cn } from "@/lib/utils"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface AdvisorScoreProps {
  className?: string
}

export function AdvisorScore({ className }: AdvisorScoreProps) {
  const { user } = useAuth()
  const isAdvisor = user?.role === "advisor"

  const { data, isLoading, error } = useQuery({
    queryKey: ["advisor-points"],
    queryFn: fetchAdvisorPoints,
    refetchInterval: 30000, // Refresh every 30 seconds
    enabled: isAdvisor,
  })

  if (!isAdvisor) return null

  if (isLoading) {
    return (
      <div className={cn("flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted/50 animate-pulse", className)}>
        <div className="size-4 rounded-full bg-muted" />
        <div className="w-8 h-4 rounded bg-muted" />
      </div>
    )
  }

  if (error) return null

  const points = data?.points ?? 0

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={cn(
              "group flex items-center gap-2 px-3 py-1.5 rounded-full",
              "bg-primary/10 text-primary border border-primary/20",
              "transition-all duration-300 hover:bg-primary/20 hover:scale-105 cursor-default",
              className
            )}
          >
            <Trophy className="size-4 transition-transform group-hover:rotate-12" />
            <span className="text-sm font-bold tracking-tight">
              {points.toLocaleString()}
            </span>
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="max-w-xs text-xs bg-white text-gray-900 border border-gray-200 shadow-md">
          <p className="font-semibold mb-1">Điểm cố vấn</p>
          <p className="text-muted-foreground">
            Điểm thưởng tích lũy từ các hoạt động can thiệp và hỗ trợ sinh viên.
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
