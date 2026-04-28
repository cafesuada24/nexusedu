import { Upload } from "lucide-react"
import { CsvUploader } from "@/components/dashboard/csv-uploader"
import { Badge } from "@/components/ui/badge"

export default function ImportPage() {
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
