"use client"

import * as React from "react"

export type Dataset = {
  fileName: string
  sizeKB: number
  uploadedAt: string // ISO
  totalStudents: number
  highRisk: number
  draftEmails: number
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
  if (next === null) {
    window.localStorage.removeItem(STORAGE_KEY)
  } else {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
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
