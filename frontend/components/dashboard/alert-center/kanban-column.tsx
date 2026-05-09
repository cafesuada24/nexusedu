"use client";

import * as React from "react"
import { ChevronDown, ChevronsDown, ChevronsUp } from "lucide-react"
import { AnimatePresence, motion } from "framer-motion"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import {
  type Alert,
  type CaseStatus,
  type ColumnDef,
  PAGE_SIZE,
} from "@/lib/alerts"
import { type StudentRow } from "@/lib/csv"
import { KanbanCard } from "./kanban-card"

type KanbanColumnProps = {
  column: ColumnDef
  items: Alert[]
  totalInColumn: number
  highlightedAlertId?: string | null
  isActivated?: boolean
  isCollapsed: boolean
  isExpanded: boolean
  onToggleCollapse: (id: CaseStatus) => void
  onToggleExpand: (id: CaseStatus) => void
  onViewDetails: (a: Alert) => void
  onEditEmail: (a: Alert) => void
  onGenerateDraft: (a: Alert) => void
  onSendEmail: (a: Alert) => void
  onMove: (a: Alert, status: CaseStatus, message?: string) => void
  onOpenGoals: (id: string) => void
  studentProfilesById: Record<string, StudentRow | undefined>
  aiDraftingById: Record<string, boolean>
  aiDraftErrorById: Record<string, string>
  aiDraftReadyById: Record<string, boolean>
  acceptingCaseById: Record<string, boolean>
}

export function KanbanColumn({
  column: col,
  items,
  totalInColumn,
  highlightedAlertId,
  isActivated,
  isCollapsed,
  isExpanded,
  onToggleCollapse,
  onToggleExpand,
  onViewDetails,
  onEditEmail,
  onGenerateDraft,
  onSendEmail,
  onMove,
  onOpenGoals,
  studentProfilesById,
  aiDraftingById,
  aiDraftErrorById,
  aiDraftReadyById,
  acceptingCaseById,
}: KanbanColumnProps) {
  const ColIcon = col.icon

  return (
    <section
      role="listitem"
      className={cn(
        "flex min-w-[380px] w-[380px] shrink-0 basis-[380px] flex-col rounded-2xl border border-border/60 border-t-4 transition-all duration-300 dark:border-slate-800",
        col.containerTone,
        col.topBorderTone,
        isCollapsed ? "h-auto" : "h-full",
        isCollapsed && "opacity-95",
        isActivated && col.columnHighlightTone,
      )}
      aria-label={col.title}
    >
      <header
        className={cn(
          "flex items-center justify-between gap-2 border-b border-border/50 px-3 py-3 dark:border-slate-800 dark:bg-slate-950",
          col.headerTone,
        )}
      >
        <div className="flex min-w-0 items-center gap-2.5">
          <span
            className={cn(
              "grid size-9 shrink-0 place-items-center rounded-lg ring-1",
              col.iconContainerTone,
              col.accent,
            )}
            aria-hidden
          >
            <ColIcon className="size-[18px]" />
          </span>
          <p className={cn("truncate text-base font-semibold", col.accent)}>
            {col.title}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <Badge
            variant="outline"
            className="h-7 rounded-md border-border/50 bg-white/85 px-2 font-mono text-sm text-slate-800 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
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
        <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-y-auto p-2.5 hide-scrollbar">
          {items.length === 0 ? (
            <div className="flex flex-1 items-center justify-center rounded-xl border border-dashed border-border/60 bg-white/45 p-6 text-center dark:border-slate-800 dark:bg-black/20">
              <span
                aria-hidden
                className={cn(
                  "grid size-8 place-items-center rounded-lg opacity-35 ring-1 dark:opacity-20",
                  col.iconContainerTone,
                  col.accent,
                )}
              >
                <ColIcon className="size-4" />
              </span>
            </div>
          ) : (
            <>
              <AnimatePresence initial={false}>
                {(isExpanded ? items : items.slice(0, PAGE_SIZE)).map((a) => (
                  <motion.div
                    key={a.id}
                    layout
                    layoutId={`alert-card-${a.id}`}
                    initial={{ opacity: 0.7, scale: 0.98 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.98 }}
                    transition={{ duration: 0.2, ease: "easeOut" }}
                  >
                    <KanbanCard
                      alert={a}
                      isHighlighted={highlightedAlertId === a.id}
                      highlightTone={col.cardHighlightTone}
                      onViewDetails={() => onViewDetails(a)}
                      onEditEmail={() => onEditEmail(a)}
                      onGenerateDraft={() => onGenerateDraft(a)}
                      onSendEmail={() => onSendEmail(a)}
                      onMove={(s, msg) => onMove(a, s, msg)}
                      onOpenGoals={() => onOpenGoals(a.id)}
                      studentProfile={studentProfilesById[a.id]}
                      isAiDrafting={Boolean(aiDraftingById[a.id])}
                      aiDraftError={aiDraftErrorById[a.id]}
                      isAiDraftReady={Boolean(aiDraftReadyById[a.id])}
                      isAcceptingCase={Boolean(acceptingCaseById[a.id])}
                    />
                  </motion.div>
                ))}
              </AnimatePresence>
              {items.length > PAGE_SIZE ? (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onToggleExpand(col.id)}
                  className="mt-1 h-10 w-full justify-center gap-2 rounded-lg text-sm font-medium text-muted-foreground hover:bg-card hover:text-foreground dark:hover:bg-slate-900 dark:hover:text-slate-100"
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
