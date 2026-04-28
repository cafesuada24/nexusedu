"use client";

import * as React from "react"
import { ChevronDown, ChevronsDown, ChevronsUp } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import {
  type Alert,
  type AlertStatus,
  type ColumnDef,
  PAGE_SIZE,
} from "@/lib/alerts"
import { KanbanCard } from "./kanban-card"

type KanbanColumnProps = {
  column: ColumnDef
  items: Alert[]
  totalInColumn: number
  isCollapsed: boolean
  isExpanded: boolean
  onToggleCollapse: (id: AlertStatus) => void
  onToggleExpand: (id: AlertStatus) => void
  onSend: (a: Alert) => void
  onEdit: (a: Alert) => void
  onRemove: (a: Alert) => void
  onMove: (id: string, status: AlertStatus, message?: string) => void
  onOpenGoals: (id: string) => void
}

export function KanbanColumn({
  column: col,
  items,
  totalInColumn,
  isCollapsed,
  isExpanded,
  onToggleCollapse,
  onToggleExpand,
  onSend,
  onEdit,
  onRemove,
  onMove,
  onOpenGoals,
}: KanbanColumnProps) {
  const ColIcon = col.icon

  return (
    <section
      role="listitem"
      className={cn(
        "flex min-w-0 flex-col rounded-2xl border border-border/60 bg-muted/30 transition-colors",
        isCollapsed && "bg-muted/20",
      )}
      aria-label={col.title}
    >
      <header className="flex items-center justify-between gap-2 border-b border-border/60 px-3 py-3">
        <div className="flex min-w-0 items-center gap-2.5">
          <span
            className={cn(
              "grid size-9 shrink-0 place-items-center rounded-lg bg-card ring-1 ring-border/60",
              col.accent,
            )}
            aria-hidden
          >
            <ColIcon className="size-[18px]" />
          </span>
          <p className="truncate text-base font-semibold">
            {col.title}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <Badge
            variant="outline"
            className="h-7 rounded-md bg-card px-2 font-mono text-sm"
          >
            {items.length}
            {items.length !== totalInColumn ? (
              <span className="ml-0.5 text-muted-foreground">
                /{totalInColumn}
              </span>
            ) : null}
          </Badge>
          <Button
            variant="ghost"
            size="icon"
            className="size-7 rounded-md text-muted-foreground hover:text-foreground"
            onClick={() => onToggleCollapse(col.id)}
            aria-label={
              isCollapsed
                ? `Mở rộng cột ${col.title}`
                : `Thu gọn cột ${col.title}`
            }
            aria-expanded={!isCollapsed}
          >
            <ChevronDown
              className={cn(
                "size-4 transition-transform",
                isCollapsed && "-rotate-90",
              )}
            />
          </Button>
        </div>
      </header>

      {isCollapsed ? null : (
        <div className="flex min-h-[140px] flex-col gap-2.5 p-2.5">
          {items.length === 0 ? (
            <div className="flex flex-1 items-center justify-center rounded-xl border border-dashed border-border/60 bg-card/40 p-6 text-center">
              <span
                aria-hidden
                className={cn(
                  "grid size-8 place-items-center rounded-lg bg-card opacity-60 ring-1 ring-border/60",
                  col.accent,
                )}
              >
                <ColIcon className="size-4" />
              </span>
            </div>
          ) : (
            <>
              {(isExpanded ? items : items.slice(0, PAGE_SIZE)).map((a) => (
                <KanbanCard
                  key={a.id}
                  alert={a}
                  onSend={() => onSend(a)}
                  onEdit={() => onEdit(a)}
                  onRemove={() => onRemove(a)}
                  onMove={(s, msg) => onMove(a.id, s, msg)}
                  onOpenGoals={() => onOpenGoals(a.id)}
                />
              ))}
              {items.length > PAGE_SIZE ? (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onToggleExpand(col.id)}
                  className="mt-1 h-10 w-full justify-center gap-2 rounded-lg text-sm font-medium text-muted-foreground hover:bg-card hover:text-foreground"
                  aria-expanded={isExpanded}
                >
                  {isExpanded ? (
                    <>
                      <ChevronsUp className="size-4" />
                      Thu gọn
                    </>
                  ) : (
                    <>
                      <ChevronsDown className="size-4" />
                      Xem thêm {items.length - PAGE_SIZE} thẻ
                    </>
                  )}
                </Button>
              ) : null}
            </>
          )}
        </div>
      )}
    </section>
  )
}
