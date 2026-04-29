"use client"

import * as React from "react"
import { Mail, Inbox } from "lucide-react"
import { toast } from "sonner"
import {
  Card,
  CardContent,
  CardHeader,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { EmailEditorSheet } from "@/components/dashboard/email-editor-sheet"
import { GoalsDialog, type Goal } from "@/components/dashboard/goals-dialog"
import { type Problem } from "@/lib/csv"
import { sendNudge } from "@/lib/api"
import { useAlerts, useUpdateAlertStatus } from "@/hooks/use-alerts"
import {
  type Alert,
  type AlertStatus,
  problemMeta,
  COLUMNS,
  pickRandomAppointment,
  fromBackendStatus,
  toBackendStatus,
} from "@/lib/alerts"
import { AlertSearch } from "./alert-center/alert-search"
import { KanbanColumn } from "./alert-center/kanban-column"

export function AlertCenter() {
  const [problemFilter, setProblemFilter] = React.useState<"all" | Problem>(
    "all",
  )
  const [query, setQuery] = React.useState("")
  const [editing, setEditing] = React.useState<Alert | null>(null)
  const [goalsTargetId, setGoalsTargetId] = React.useState<string | null>(null)

  // Use TanStack Query hooks
  const { data: remoteAlerts = [], isLoading } = useAlerts()
  const { mutate: updateStatus } = useUpdateAlertStatus()

  // Internal state for goals and hidden alerts (not yet persisted in backend)
  const [localAlertState, setLocalAlertState] = React.useState<Record<string, { goals: Goal[], hidden: boolean }>>({})

  // Map remote alerts to local Alert interface
  const alerts = React.useMemo(() => {
    const now = Math.floor(Date.now() / 1000)

    const getProblemFromStatus = (status: string): Problem => {
      const s = status.toLowerCase()
      if (s.includes("final")) return "failed_final"
      if (s.includes("midterm") || s.includes("critical")) return "failed_midterm"
      return "low_average"
    }

    return remoteAlerts
      .filter(r => !localAlertState[r.sid]?.hidden)
      .map((r) => ({
        id: r.sid,
        name: r.student_name,
        mssv: r.sid.slice(0, 8).toUpperCase(),
        email: r.email,
        problem: getProblemFromStatus(r.current_risk_status),
        summary: r.current_risk_status,
        severity: "high" as const,
        subject: r.draft_subject || "",
        body: r.draft_body || "",
        lastContactedAt: null,
        status: fromBackendStatus(r.intervention_status),
        movedAt: now,
        draftJobId: r.draft_job_id,
        draftSubject: r.draft_subject,
        draftBody: r.draft_body,
        appointmentAt: r.intervention_status === "booked" ? pickRandomAppointment() : null,
        goals: localAlertState[r.sid]?.goals || [],
      }))
  }, [remoteAlerts, localAlertState])

  const [collapsedCols, setCollapsedCols] = React.useState<
    Record<AlertStatus, boolean>
  >({
    new: false,
    contacted: false,
    scheduled: false,
    in_progress: false,
    resolved: false,
  })

  const toggleCollapse = (id: AlertStatus) =>
    setCollapsedCols((prev) => ({ ...prev, [id]: !prev[id] }))

  const [expandedCols, setExpandedCols] = React.useState<
    Record<AlertStatus, boolean>
  >({
    new: false,
    contacted: false,
    scheduled: false,
    in_progress: false,
    resolved: false,
  })

  const toggleExpand = (id: AlertStatus) =>
    setExpandedCols((prev) => ({ ...prev, [id]: !prev[id] }))

  const filteredAlerts = React.useMemo(() => {
    const q = query.trim().toLowerCase()
    return alerts.filter((a) => {
      const matchesProblem =
        problemFilter === "all" || a.problem === problemFilter
      const matchesQuery =
        !q ||
        a.name.toLowerCase().includes(q) ||
        a.mssv.toLowerCase().includes(q) ||
        a.email.toLowerCase().includes(q) ||
        a.summary.toLowerCase().includes(q)
      return matchesProblem && matchesQuery
    })
  }, [alerts, problemFilter, query])

  const grouped = React.useMemo(() => {
    const map: Record<AlertStatus, Alert[]> = {
      new: [],
      contacted: [],
      scheduled: [],
      in_progress: [],
      resolved: [],
    }
    for (const a of filteredAlerts) map[a.status].push(a)
    map.scheduled.sort((a, b) => {
      const ta = a.appointmentAt ?? Number.POSITIVE_INFINITY
      const tb = b.appointmentAt ?? Number.POSITIVE_INFINITY
      return ta - tb
    })
    return map
  }, [filteredAlerts])

  const totalCounts = React.useMemo(() => {
    const map: Record<AlertStatus, number> = {
      new: 0,
      contacted: 0,
      scheduled: 0,
      in_progress: 0,
      resolved: 0,
    }
    for (const a of alerts) map[a.status]++
    return map
  }, [alerts])

  const problemCounts = React.useMemo(() => {
    const counts: Record<Problem, number> = {
      failed_final: 0,
      failed_midterm: 0,
      low_average: 0,
    }
    for (const a of alerts) {
      counts[a.problem]++
    }
    return counts
  }, [alerts])

  const moveTo = (id: string, status: AlertStatus, message?: string) => {
    updateStatus(
      { sid: id, status: toBackendStatus(status) },
      {
        onSuccess: () => {
          if (message) toast.success(message)
        },
      },
    )
  }

  const send = async (a: Alert) => {
    if (!a.body) {
      toast.error("Chưa có nội dung email. Hãy nhấn Sửa để tạo bản nháp.")
      return
    }
    const toastId = toast.loading("Đang gửi email...")
    try {
      await sendNudge(a.id, { body: a.body })
      moveTo(
        a.id,
        "contacted",
        `Đã gửi email tới ${a.name}`,
      )
      toast.dismiss(toastId)
    } catch (err) {
      toast.error("Không thể gửi email", { id: toastId })
    }
  }

  const remove = (a: Alert) => {
    setLocalAlertState(prev => ({
      ...prev,
      [a.id]: { ...prev[a.id], hidden: true }
    }))
    toast.message(`Đã ẩn cảnh báo của ${a.name}`)
  }

  const saveEdit = (updated: Alert) => {
    setEditing(null)
    send(updated)
  }

  const addGoal = (
    alertId: string,
    title: string,
    deadline: string | null,
  ) => {
    const newGoal: Goal = {
      id: `g_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`,
      title,
      deadline,
      done: false,
      createdAt: Math.floor(Date.now() / 1000),
    }
    setLocalAlertState(prev => ({
      ...prev,
      [alertId]: {
        ...prev[alertId],
        goals: [...(prev[alertId]?.goals || []), newGoal]
      }
    }))
    toast.success("Đã thêm mục tiêu mới")
  }

  const toggleGoal = (alertId: string, goalId: string) => {
    setLocalAlertState(prev => ({
      ...prev,
      [alertId]: {
        ...prev[alertId],
        goals: (prev[alertId]?.goals || []).map((g) =>
          g.id === goalId ? { ...g, done: !g.done } : g
        ),
      }
    }))
  }

  const removeGoal = (alertId: string, goalId: string) => {
    setLocalAlertState(prev => ({
      ...prev,
      [alertId]: {
        ...prev[alertId],
        goals: (prev[alertId]?.goals || []).filter((g) => g.id !== goalId),
      }
    }))
  }

  const goalsTarget = React.useMemo(
    () => (goalsTargetId ? alerts.find((a) => a.id === goalsTargetId) : null),
    [alerts, goalsTargetId],
  )

  if (isLoading) {
    return (
      <Card className="rounded-2xl border-border/60">
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-72" />
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          {[0, 1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-72 rounded-2xl" />
          ))}
        </CardContent>
      </Card>
    )
  }

  return (
    <>
      <div className="flex flex-col gap-3">
        <AlertSearch 
          query={query}
          onQueryChange={setQuery}
          problemFilter={problemFilter}
          onProblemFilterChange={setProblemFilter}
          totalAlerts={alerts.length}
          problemCounts={problemCounts}
        />

        <div
          className="grid gap-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5"
          role="list"
        >
          {COLUMNS.map((col) => (
            <KanbanColumn 
              key={col.id}
              column={col}
              items={grouped[col.id]}
              totalInColumn={totalCounts[col.id]}
              isCollapsed={collapsedCols[col.id]}
              isExpanded={expandedCols[col.id]}
              onToggleCollapse={toggleCollapse}
              onToggleExpand={toggleExpand}
              onSend={send}
              onEdit={(a) => setEditing(a)}
              onRemove={remove}
              onMove={moveTo}
              onOpenGoals={(id) => setGoalsTargetId(id)}
            />
          ))}
        </div>

        {alerts.length === 0 && (
          <Card className="rounded-2xl border-dashed border-border/60">
            <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
              <Inbox className="size-10 text-muted-foreground" />
              <p className="font-serif text-lg font-semibold">
                Không có cảnh báo
              </p>
            </CardContent>
          </Card>
        )}

        {alerts.length > 0 && filteredAlerts.length === 0 && (
          <Card className="rounded-2xl border-dashed border-border/60">
            <CardContent className="flex flex-col items-center gap-2 py-8 text-center">
              <Mail className="size-8 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                Không có kết quả phù hợp.
              </p>
            </CardContent>
          </Card>
        )}
      </div>

      <EmailEditorSheet
        alert={editing}
        onClose={() => setEditing(null)}
        onSave={saveEdit}
      />

      <GoalsDialog
        alert={
          goalsTarget
            ? {
                id: goalsTarget.id,
                name: goalsTarget.name,
                problem: goalsTarget.problem,
                problemLabel: problemMeta[goalsTarget.problem].label,
                problemTone: problemMeta[goalsTarget.problem].tone,
                problemIcon: problemMeta[goalsTarget.problem].icon,
                goals: goalsTarget.goals,
              }
            : null
        }
        onClose={() => setGoalsTargetId(null)}
        onAdd={addGoal}
        onToggle={toggleGoal}
        onRemove={removeGoal}
      />
    </>
  )
}
