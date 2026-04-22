"use client"

import * as React from "react"
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  Sparkles,
  ShieldCheck,
  Rows3,
  X,
} from "lucide-react"
import { toast } from "sonner"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { cn } from "@/lib/utils"
import { useDataset } from "@/hooks/use-dataset"

type Stage = "idle" | "uploading" | "analyzing" | "done"

export function CsvUploader() {
  const { dataset, setDataset, clearDataset } = useDataset()
  const [stage, setStage] = React.useState<Stage>("idle")
  const [fileName, setFileName] = React.useState<string | null>(null)
  const [fileSizeKB, setFileSizeKB] = React.useState<number>(0)
  const [progress, setProgress] = React.useState(0)
  const [dragging, setDragging] = React.useState(false)
  const inputRef = React.useRef<HTMLInputElement>(null)

  // Restore the "done" view when a dataset already exists (e.g. after
  // navigating away and coming back to the Import page).
  React.useEffect(() => {
    if (dataset && stage === "idle") {
      setStage("done")
      setFileName(dataset.fileName)
      setFileSizeKB(dataset.sizeKB)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataset])

  const reset = () => {
    setStage("idle")
    setFileName(null)
    setFileSizeKB(0)
    setProgress(0)
    clearDataset()
  }

  const handleFile = (f: File) => {
    if (!f.name.toLowerCase().endsWith(".csv")) {
      toast.error("Vui lòng tải file .CSV")
      return
    }
    setFileName(f.name)
    setFileSizeKB(Number((f.size / 1024).toFixed(1)))
    setStage("uploading")
    setProgress(0)

    const tick = setInterval(() => {
      setProgress((p) => {
        if (p >= 100) {
          clearInterval(tick)
          setStage("analyzing")
          setTimeout(() => {
            setStage("done")
            setDataset({
              fileName: f.name,
              sizeKB: Number((f.size / 1024).toFixed(1)),
              uploadedAt: new Date().toISOString(),
              totalStudents: 2184,
              highRisk: 128,
              draftEmails: 23,
            })
            toast.success("Phân tích hoàn tất — đã phát hiện 128 sinh viên nguy cơ")
          }, 1400)
          return 100
        }
        return p + 8
      })
    }, 120)
  }

  if (stage === "idle") {
    return (
      <Card className="rounded-2xl border-border/60">
        <CardContent className="p-0">
          <div
            onDragOver={(e) => {
              e.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDragging(false)
              const f = e.dataTransfer.files?.[0]
              if (f) handleFile(f)
            }}
            className={cn(
              "relative overflow-hidden rounded-2xl border-2 border-dashed p-8 transition-colors md:p-12",
              dragging
                ? "border-primary bg-primary/5"
                : "border-border/70 bg-muted/30",
            )}
          >
            <Empty className="border-0 bg-transparent">
              <EmptyHeader>
                <EmptyMedia variant="icon" className="bg-primary/10 text-primary">
                  <UploadCloud className="size-7" />
                </EmptyMedia>
                <EmptyTitle className="font-serif text-xl">
                  Kéo thả file CSV vào đây
                </EmptyTitle>
                <EmptyDescription className="max-w-md">
                  Hoặc chọn file từ máy của bạn. Hỗ trợ bảng điểm, điểm danh,
                  trạng thái học phí. Dung lượng tối đa 20MB.
                </EmptyDescription>
              </EmptyHeader>
              <EmptyContent>
                <input
                  ref={inputRef}
                  type="file"
                  accept=".csv,text/csv"
                  className="sr-only"
                  onChange={(e) => {
                    const f = e.target.files?.[0]
                    if (f) handleFile(f)
                  }}
                />
                <Button
                  size="lg"
                  className="rounded-xl"
                  onClick={() => inputRef.current?.click()}
                >
                  <UploadCloud className="size-4" />
                  Tải lên danh sách sinh viên (.CSV)
                </Button>
                <p className="text-xs text-muted-foreground">
                  Hoặc dùng{" "}
                  <button className="font-medium text-primary hover:underline">
                    mẫu CSV của chúng tôi
                  </button>
                </p>
              </EmptyContent>
            </Empty>
          </div>

          <div className="grid gap-4 border-t border-border/60 p-6 md:grid-cols-3 md:p-8">
            <Tip
              icon={<ShieldCheck className="size-4" />}
              title="Bảo mật"
              desc="Mã hoá end-to-end. Dữ liệu không rời khỏi máy chủ trường."
            />
            <Tip
              icon={<Rows3 className="size-4" />}
              title="Linh hoạt cột"
              desc="Tự động nhận diện MSSV, điểm, trạng thái học phí."
            />
            <Tip
              icon={<Sparkles className="size-4" />}
              title="Phân tích AI"
              desc="Phát hiện nguy cơ chỉ trong vài giây sau khi tải."
            />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="rounded-2xl border-border/60">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <span className="grid size-11 place-items-center rounded-xl bg-primary/10 text-primary">
              <FileSpreadsheet className="size-5" />
            </span>
            <div>
              <CardTitle className="font-serif">
                {fileName ?? "students.csv"}
              </CardTitle>
              <CardDescription>
                {stage === "uploading" && "Đang tải lên..."}
                {stage === "analyzing" && "AI đang phân tích nguy cơ..."}
                {stage === "done" &&
                  "Hoàn tất — đã phát hiện 128 sinh viên nguy cơ."}
              </CardDescription>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="rounded-lg"
            onClick={reset}
            aria-label="Huỷ"
          >
            <X className="size-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {(stage === "uploading" || stage === "analyzing") && (
          <>
            <Progress value={stage === "analyzing" ? 100 : progress} />
            <p className="text-xs text-muted-foreground">
              {stage === "analyzing"
                ? "Đang quét mô hình rủi ro qua 2,184 bản ghi..."
                : `${progress}% · ${fileSizeKB.toFixed(1)} KB`}
            </p>
          </>
        )}

        {stage === "done" && (
          <div className="grid gap-3 rounded-xl border border-success/30 bg-success/10 p-4 sm:grid-cols-3">
            <Stat label="Sinh viên" value="2,184" />
            <Stat label="Nguy cơ cao" value="128" tone="destructive" />
            <Stat label="Email dự thảo" value="23" tone="primary" />
          </div>
        )}

        <div className="flex flex-wrap gap-2 pt-2">
          <Button
            disabled={stage !== "done"}
            className="rounded-xl"
            asChild
          >
            <a href="/dashboard/alerts">
              <CheckCircle2 className="size-4" />
              Tới Alert Center
            </a>
          </Button>
          <Button variant="outline" className="rounded-xl" onClick={reset}>
            Tải file khác
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function Tip({
  icon,
  title,
  desc,
}: {
  icon: React.ReactNode
  title: string
  desc: string
}) {
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 grid size-8 place-items-center rounded-lg bg-primary/10 text-primary">
        {icon}
      </span>
      <div>
        <p className="text-sm font-semibold">{title}</p>
        <p className="text-xs text-muted-foreground">{desc}</p>
      </div>
    </div>
  )
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string
  value: string
  tone?: "destructive" | "primary"
}) {
  const colorMap = {
    destructive: "text-destructive",
    primary: "text-primary",
  }
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p
        className={cn(
          "font-serif text-2xl font-bold",
          tone ? colorMap[tone] : "text-foreground",
        )}
      >
        {value}
      </p>
    </div>
  )
}
