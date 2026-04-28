"use client"

import Link from "next/link"
import {
  Upload,
  ArrowRight,
  LineChart,
} from "lucide-react"
import {
  Card,
  CardContent,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  TooltipProvider,
} from "@/components/ui/tooltip"

export default function AnalysisPage() {
  return (
    <TooltipProvider delayDuration={150}>
      <div className="flex w-full flex-1 flex-col gap-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-xl bg-accent-cyan/10 text-accent-cyan ring-1 ring-accent-cyan/20 shadow-sm shadow-accent-cyan/10">
              <LineChart className="size-5" />
            </div>
            <h1 className="font-serif text-2xl font-bold tracking-tight md:text-3xl">
              Phân tích
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <Button asChild size="sm" className="rounded-xl">
              <Link href="/dashboard/import">
                <Upload className="size-4" />
                Nhập CSV
              </Link>
            </Button>
            <Button asChild variant="outline" size="sm" className="rounded-xl">
              <Link href="/dashboard/alerts">
                Xem cảnh báo
                <ArrowRight className="size-4" />
              </Link>
            </Button>
          </div>
        </div>

        <div
          aria-hidden
          className="h-px w-full bg-gradient-to-r from-accent-cyan/40 via-primary/25 to-transparent"
        />

        <Card className="rounded-2xl border-dashed border-border/60">
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <div className="grid size-12 place-items-center rounded-xl bg-primary/10 text-primary">
              <LineChart className="size-6" />
            </div>
            <div className="max-w-md space-y-1">
              <h2 className="font-serif text-xl font-semibold">Sẵn sàng phân tích</h2>
              <p className="text-sm text-muted-foreground">
                Hệ thống đã được kết nối với máy chủ. Tải lên dữ liệu CSV mới để bắt đầu quá trình nhận diện rủi ro tự động.
              </p>
            </div>
            <div className="flex gap-2">
              <Button asChild className="rounded-xl">
                <Link href="/dashboard/import">Nhập dữ liệu</Link>
              </Button>
              <Button asChild variant="outline" className="rounded-xl">
                <Link href="/dashboard/alerts">Kiểm tra cảnh báo</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </TooltipProvider>
  )
}
