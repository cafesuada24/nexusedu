"use client"

import * as React from "react"

export type SourceKey = "LMS" | "SIS"
export type UploadStatus = "processing" | "ready" | "error"

export type UploadFileMeta = {
  fileName: string
  sizeKB: number
}

/**
 * One row in the file registry corresponds to a paired dataset (both
 * an LMS file and a SIS file). We require both before analysis runs.
 */
export type UploadItem = {
  id: string
  status: UploadStatus
  uploadedAt: string
  files: Record<SourceKey, UploadFileMeta>
  totalStudents?: number
  totalTests?: number
  highRisk?: number
  errorMessage?: string
}

const STORAGE_KEY = "nexusedu:uploads:v2"
const EVENT_NAME = "nexusedu:uploads:change"

function readUploads(): UploadItem[] {
  if (typeof window === "undefined") return []
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? (parsed as UploadItem[]) : []
  } catch {
    return []
  }
}

function writeUploads(next: UploadItem[]) {
  if (typeof window === "undefined") return
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch {
    // localStorage can throw on quota exceeded — ignore.
  }
  window.dispatchEvent(new CustomEvent(EVENT_NAME))
}

/**
 * Client-only hook that exposes the registry of uploaded source files.
 * Each record is a paired LMS+SIS bundle that has been confirmed by
 * the PD. Multiple consumers stay in sync via a custom window event.
 */
export function useUploads() {
  const [uploads, setUploadsState] = React.useState<UploadItem[]>([])

  React.useEffect(() => {
    setUploadsState(readUploads())

    const onChange = () => setUploadsState(readUploads())
    window.addEventListener(EVENT_NAME, onChange)
    window.addEventListener("storage", onChange)
    return () => {
      window.removeEventListener(EVENT_NAME, onChange)
      window.removeEventListener("storage", onChange)
    }
  }, [])

  const addUpload = React.useCallback((item: UploadItem) => {
    const next = [...readUploads(), item]
    writeUploads(next)
    setUploadsState(next)
  }, [])

  const updateUpload = React.useCallback(
    (id: string, patch: Partial<UploadItem>) => {
      const next = readUploads().map((u) =>
        u.id === id ? { ...u, ...patch } : u,
      )
      writeUploads(next)
      setUploadsState(next)
    },
    [],
  )

  const removeUpload = React.useCallback((id: string) => {
    const next = readUploads().filter((u) => u.id !== id)
    writeUploads(next)
    setUploadsState(next)
  }, [])

  const clearUploads = React.useCallback(() => {
    writeUploads([])
    setUploadsState([])
  }, [])

  return { uploads, addUpload, updateUpload, removeUpload, clearUploads }
}
