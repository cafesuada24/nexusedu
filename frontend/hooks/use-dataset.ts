"use client"

import * as React from "react"
import type { Problem, StudentRow } from "@/lib/csv"

export type Dataset = {
  fileName: string
  sizeKB: number
  uploadedAt: string // ISO

  totalStudents: number
  totalTests: number
  averageScore: number

  highRisk: number
  mediumRisk: number
  lowRisk: number
  /** Number of AI-drafted emails awaiting approval — one per high-risk student
   *  that has never been contacted (`last_send_email = None`). */
  draftEmails: number

  problemCounts: Record<Problem, number>
  /** Risk breakdown by academic_year. */
  yearRisk: Record<string, number>

  /** All parsed student rows — kept so UI can surface real names & scores. */
  students: StudentRow[]
  headers: string[]
}

const STORAGE_KEY = "nexusedu:dataset"
const EVENT_NAME = "nexusedu:dataset:change"

function readDataset(): Dataset | null {
  if (typeof window === "undefined") return null
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    return JSON.parse(raw) as Dataset
  } catch {
    return null
  }
}

function writeDataset(next: Dataset | null) {
  if (typeof window === "undefined") return
  try {
    if (next === null) {
      window.localStorage.removeItem(STORAGE_KEY)
    } else {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    }
  } catch {
    // localStorage can throw on quota exceeded — fall back to in-memory only.
  }
  window.dispatchEvent(new CustomEvent(EVENT_NAME))
}

/**
 * Client-only hook that exposes the currently imported dataset.
 * Returns `undefined` during hydration so consumers can avoid flashing
 * the empty state on first paint.
 */
export function useDataset() {
  const [dataset, setDatasetState] = React.useState<Dataset | null | undefined>(
    undefined,
  )

  React.useEffect(() => {
    setDatasetState(readDataset())

    const onChange = () => setDatasetState(readDataset())
    window.addEventListener(EVENT_NAME, onChange)
    window.addEventListener("storage", onChange)
    return () => {
      window.removeEventListener(EVENT_NAME, onChange)
      window.removeEventListener("storage", onChange)
    }
  }, [])

  const setDataset = React.useCallback((next: Dataset | null) => {
    writeDataset(next)
    setDatasetState(next)
  }, [])

  const clearDataset = React.useCallback(() => {
    writeDataset(null)
    setDatasetState(null)
  }, [])

  return { dataset, setDataset, clearDataset, isLoading: dataset === undefined }
}
