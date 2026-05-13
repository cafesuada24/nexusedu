"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { Upload } from "lucide-react"
import { CsvUploader } from "@/components/dashboard/csv-uploader"
import { Badge } from "@/components/ui/badge"
import { useAuth } from "@/hooks/use-auth"

export default function ImportPage() {
  const router = useRouter()
  const { user, loading } = useAuth()

  React.useEffect(() => {
    if (!loading && user?.role !== "admin") {
      router.replace("/dashboard")
    }
  }, [user, loading, router])

  if (loading || user?.role !== "admin") {
    return null
  }

  return (
    <div className="flex w-full flex-1 flex-col gap-6">
      <div className="flex items-center gap-3">
        <div className="grid size-10 place-items-center rounded-xl bg-accent-sky/10 text-accent-sky ring-1 ring-accent-sky/20 shadow-sm shadow-accent-sky/10">
          <Upload className="size-5" />
        </div>
        <h1 className="font-serif text-2xl font-bold tracking-tight md:text-3xl">
          Nhập CSV
        </h1>
        <Badge variant="outline" className="ml-auto rounded-md font-mono text-[11px]">
          LMS · SIS
        </Badge>
      </div>

      <CsvUploader />
    </div>
  )
}
