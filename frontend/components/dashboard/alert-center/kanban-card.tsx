"use client";

import * as React from "react"
import {
  MoreHorizontal,
  Pencil,
  Trash2,
  Target,
  Sparkles,
  Clock,
  Send,
  CalendarCheck,
  Handshake,
  CheckCircle2,
  ArrowRight,
  RotateCcw,
  Loader2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn } from "@/lib/utils"
import { useDraftStatus } from "@/hooks/use-alerts"
import {
  type Alert,
  type AlertStatus,
  problemMeta,
  COLUMNS,
  getInitials,
  formatAppointment,

  relativeTime,
} from "@/lib/alerts"

type KanbanCardProps = {
  alert: Alert
  onSend: (updated: Alert) => void
  onEdit: () => void
  onRemove: () => void
  onMove: (status: AlertStatus, message?: string) => void
  onOpenGoals: () => void
}

export function KanbanCard({
  alert: a,
  onSend,
  onEdit,
  onRemove,
  onMove,
  onOpenGoals,
}: KanbanCardProps) {
  const { data: draft } = useDraftStatus(a.id)

  const meta = problemMeta[a.problem]
  const ProblemIcon = meta.icon
  const goalsTotal = a.goals.length
  const goalsDone = a.goals.filter((g) => g.done).length
  const goalsPct =
    goalsTotal === 0 ? 0 : Math.round((goalsDone / goalsTotal) * 100)
  const hasOverdue = a.goals.some(
    (g) =>
      !g.done &&
      g.deadline !== null &&
      new Date(g.deadline).getTime() < new Date().setHours(0, 0, 0, 0),
  )

  const isGenerating = draft?.is_generating ?? (!draft?.body)
  const draftBody = isGenerating
    ? ""
    : (draft?.body || '')



  return (
    <article className="group rounded-xl border border-border/60 bg-card p-4 shadow-sm transition-all hover:border-primary/30 hover:shadow-md">
      <div className="flex items-start gap-3">
        <Avatar className="size-12 shrink-0">
          <AvatarFallback className="bg-primary/10 text-primary text-sm font-semibold">
            {getInitials(a.name)}
          </AvatarFallback>
        </Avatar>
        <div className="min-w-0 flex-1">
          <p className="truncate text-base font-semibold leading-tight">
            {a.name}
          </p>
          <p className="mt-0.5 truncate font-mono text-xs text-muted-foreground">
            {a.email || `MSSV ${a.mssv}`}
          </p>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="size-9 shrink-0 rounded-lg text-muted-foreground hover:text-foreground"
              aria-label="Tuỳ chọn thẻ"
            >
              <MoreHorizontal className="size-5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-52 rounded-xl">
            <DropdownMenuLabel className="text-xs text-muted-foreground">
              Chuyển trạng thái
            </DropdownMenuLabel>
            {COLUMNS.filter((c) => c.id !== a.status).map((c) => {
              const Icon = c.icon
              return (
                <DropdownMenuItem
                  key={c.id}
                  onClick={() =>
                    onMove(c.id, `Đã chuyển ${a.name} → ${c.title}`)
                  }
                  className="gap-2"
                >
                  <Icon className={cn("size-4", c.accent)} />
                  {c.title}
                </DropdownMenuItem>
              )
            })}
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onOpenGoals} className="gap-2">
              <Target className="size-4 text-primary" />
              {goalsTotal > 0 ? (
                <span>
                  Mục tiêu{" "}
                  <span className="font-mono text-muted-foreground">
                    ({goalsDone}/{goalsTotal})
                  </span>
                </span>
              ) : (
                "Đặt mục tiêu"
              )}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={onEdit} className="gap-2">
              <Pencil className="size-4" />
              Chỉnh sửa email
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={onRemove}
              className="gap-2 text-destructive focus:text-destructive"
            >
              <Trash2 className="size-4" />
              Xoá thẻ
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <Badge
        variant="outline"
        className={cn(
          "mt-3 max-w-full gap-1.5 rounded-md border-transparent px-2 py-1 text-[13px] ring-1",
          meta.tone,
        )}
      >
        <ProblemIcon className="size-3.5" />
        <span className="truncate">{a.summary}</span>
      </Badge>

      {goalsTotal > 0 ? (
        <button
          type="button"
          onClick={onOpenGoals}
          className="mt-3 flex w-full items-center gap-2.5 rounded-lg border border-border/60 bg-muted/40 px-2.5 py-2 text-left transition-colors hover:border-primary/30 hover:bg-primary/5"
          aria-label={`Xem ${goalsTotal} mục tiêu của ${a.name}`}
        >
          <Target
            className={cn(
              "size-4 shrink-0",
              hasOverdue ? "text-destructive" : "text-primary",
            )}
          />
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between text-xs font-medium">
              <span className="text-foreground">
                Mục tiêu{" "}
                <span className="font-mono text-muted-foreground">
                  {goalsDone}/{goalsTotal}
                </span>
              </span>
              <span
                className={cn(
                  "font-mono",
                  hasOverdue ? "text-destructive" : "text-muted-foreground",
                )}
              >
                {hasOverdue ? "Quá hạn" : `${goalsPct}%`}
              </span>
            </div>
            <div
              className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-border/60"
              role="progressbar"
              aria-valuenow={goalsPct}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div
                className={cn(
                  "h-full rounded-full transition-[width] duration-300",
                  hasOverdue ? "bg-destructive" : "bg-success",
                )}
                style={{ width: `${goalsPct}%` }}
              />
            </div>
          </div>
        </button>
      ) : null}

      {a.status === "new" ? (
        <div className="mt-3 flex flex-col gap-2">
          {isGenerating ? (
            <Badge
              variant="outline"
              className="w-fit gap-1.5 rounded-md border-transparent bg-muted px-2 py-1 text-xs font-medium text-muted-foreground ring-1 ring-border"
            >
              <Loader2 className="size-3.5 animate-spin" />
              Đang soạn thảo AI...
            </Badge>
          ) : draftBody ? (
            <div className="flex items-center justify-between">
              <Badge
                variant="outline"
                className="w-fit gap-1.5 rounded-md border-transparent bg-primary/10 px-2 py-1 text-xs font-medium text-primary ring-1 ring-primary/20"
              >
                <Sparkles className="size-3.5" />
                Bản nháp AI sẵn sàng
              </Badge>
            </div>
          ) : null}

          <div
            className={cn(
              "rounded-lg border border-border/40 bg-muted/20 p-2.5 transition-all",
              !isGenerating && draftBody && "cursor-pointer hover:bg-muted/40"
            )}
            onClick={!isGenerating && draftBody ? onEdit : undefined}
          >
            <p className={cn(
              "text-[13px] leading-relaxed text-muted-foreground",
              isGenerating ? "italic" : "line-clamp-3"
            )}>
              {isGenerating
                ? "Hệ thống đang phân tích kết quả học tập để soạn thư hỗ trợ phù hợp..."
                : draftBody || "Chưa có bản nháp email. Nhấn Sửa để soạn thảo."}
            </p>
          </div>
        </div>
      ) : a.status === "scheduled" && a.appointmentAt ? (
        <p className="mt-3 flex items-center gap-1.5 text-[13px] font-medium text-warning">
          <Clock className="size-3.5" />
          Hẹn {formatAppointment(a.appointmentAt)}
        </p>
      ) : (
        <p className="mt-3 text-[13px] text-muted-foreground">
          Cập nhật {relativeTime(a.movedAt)}
        </p>
      )}

      <CardActions
        alert={{ ...a, body: draftBody }}
        onSend={(updated: Alert) => onSend(updated)}
        onEdit={onEdit}
        onMove={onMove}
        onOpenGoals={onOpenGoals}
        isGenerating={isGenerating}
      />
    </article>
  )
}

function CardActions({
  alert: a,
  onSend,
  onEdit,
  onMove,
  onOpenGoals,
  isGenerating,
}: {
  alert: Alert
  onSend: (updated: Alert) => void
  onEdit: () => void
  onMove: (status: AlertStatus, message?: string) => void
  onOpenGoals: () => void
  isGenerating?: boolean
}) {
  const hasGoals = a.goals.length > 0
  if (a.status === "new") {
    return (
      <div className="mt-3 flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="h-10 flex-1 rounded-lg text-sm font-medium"
          onClick={onEdit}
          disabled={isGenerating}
        >
          <Pencil className="size-4" />
          Sửa
        </Button>
        <Button
          size="sm"
          className="h-10 flex-1 rounded-lg text-sm font-medium"
          onClick={() => onSend(a)}
          disabled={!a.email || isGenerating}
          title={!a.email ? "Sinh viên chưa có email trong CSV" : undefined}
        >
          <Send className="size-4" />
          Gửi ngay
        </Button>
      </div>
    )
  }

  if (a.status === "contacted") {
    return (
      <div className="mt-3 flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="h-10 flex-1 rounded-lg text-sm font-medium"
          onClick={() =>
            onMove("scheduled", `${a.name} đã chọn khung giờ họp`)
          }
        >
          <CalendarCheck className="size-4" />
          Đã đặt hẹn
        </Button>
        <Button
          size="sm"
          variant="ghost"
          className="h-10 w-10 shrink-0 rounded-lg"
          onClick={() =>
            onMove("in_progress", `Bắt đầu hỗ trợ ${a.name}`)
          }
          aria-label="Chuyển sang Đang hỗ trợ"
        >
          <ArrowRight className="size-4" />
        </Button>
      </div>
    )
  }

  if (a.status === "scheduled") {
    return (
      <div className="mt-3 flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="h-10 w-10 shrink-0 rounded-lg"
          onClick={onOpenGoals}
          aria-label={hasGoals ? "Xem mục tiêu" : "Đặt mục tiêu"}
          title={hasGoals ? "Xem mục tiêu" : "Đặt mục tiêu"}
        >
          <Target className="size-4" />
        </Button>
        <Button
          size="sm"
          className="h-10 flex-1 rounded-lg text-sm font-medium"
          onClick={() => onMove("in_progress", `Bắt đầu hỗ trợ ${a.name}`)}
        >
          <Handshake className="size-4" />
          Bắt đầu hỗ trợ
        </Button>
      </div>
    )
  }

  if (a.status === "in_progress") {
    return (
      <div className="mt-3 flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="h-10 flex-1 rounded-lg text-sm font-medium"
          onClick={onOpenGoals}
        >
          <Target className="size-4" />
          {hasGoals ? "Mục tiêu" : "Đặt mục tiêu"}
        </Button>
        <Button
          size="sm"
          className="h-10 flex-1 rounded-lg text-sm font-medium"
          onClick={() => onMove("resolved", `Đã đóng case của ${a.name}`)}
        >
          <CheckCircle2 className="size-4" />
          Giải quyết
        </Button>
      </div>
    )
  }

  // resolved
  return (
    <Button
      variant="outline"
      size="sm"
      className="mt-3 h-10 w-full rounded-lg text-sm font-medium"
      onClick={() => onMove("in_progress", `Mở lại case của ${a.name}`)}
    >
      <RotateCcw className="size-4" />
      Mở lại case
    </Button>
  )
}
