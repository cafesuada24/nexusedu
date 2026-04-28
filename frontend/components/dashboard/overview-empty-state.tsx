import Link from "next/link"
import {
  Upload,
  FileSpreadsheet,
  Sparkles,
  ShieldCheck,
  ArrowRight,
  Database,
} from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"

export function OverviewEmptyState() {
  return (
    <div className="flex flex-col gap-6">
      <Card className="overflow-hidden rounded-2xl border-dashed border-primary/30 bg-gradient-to-br from-primary/5 via-background to-background">
        <CardContent className="p-6 md:p-10">
          <Empty className="border-0 bg-transparent">
            <EmptyHeader>
              <EmptyMedia
                variant="icon"
                className="size-14 bg-primary/10 text-primary"
              >
                <Database className="size-7" />
              </EmptyMedia>
              <EmptyTitle className="font-serif text-2xl">
                Chưa có dữ liệu sinh viên
              </EmptyTitle>
              <EmptyDescription className="max-w-xl text-pretty">
                Tổng quan sẽ hiển thị ngay sau khi bạn nhập danh sách sinh viên từ
                hệ thống quản lý học vụ. Hệ thống cần ít nhất một file CSV để AI có
                thể phát hiện sinh viên có nguy cơ và soạn email dự thảo.
              </EmptyDescription>
            </EmptyHeader>
            <EmptyContent>
              <div className="flex flex-wrap items-center justify-center gap-2">
                <Button asChild size="lg" className="rounded-xl">
                  <Link href="/dashboard/import">
                    <Upload className="size-4" />
                    Nhập CSV ngay
                  </Link>
                </Button>
                <Button
                  asChild
                  size="lg"
                  variant="outline"
                  className="rounded-xl"
                >
                  <Link href="/dashboard/support">
                    Xem hướng dẫn
                    <ArrowRight className="size-4" />
                  </Link>
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Hỗ trợ file .CSV xuất từ Moodle, Microsoft Teams, bảng điểm thủ công.
              </p>
            </EmptyContent>
          </Empty>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        <StepCard
          step={1}
          icon={<FileSpreadsheet className="size-5" />}
          title="Tải file CSV"
          desc="Kéo thả danh sách sinh viên vào thẻ “Nhập CSV”. Hỗ trợ điểm, điểm danh, học phí."
        />
        <StepCard
          step={2}
          icon={<Sparkles className="size-5" />}
          title="AI phân tích"
          desc="Hệ thống quét rủi ro học tập, tâm lý, tài chính và xếp hạng sinh viên theo mức ưu tiên."
        />
        <StepCard
          step={3}
          icon={<ShieldCheck className="size-5" />}
          title="Bạn duyệt & gửi"
          desc="Xem gợi ý email cá nhân hoá, chỉnh sửa và bấm duyệt trước khi gửi tới sinh viên."
        />
      </div>
    </div>
  )
}

function StepCard({
  step,
  icon,
  title,
  desc,
}: {
  step: number
  icon: React.ReactNode
  title: string
  desc: string
}) {
  return (
    <Card className="rounded-2xl border-border/60">
      <CardContent className="flex gap-3 p-5">
        <div className="flex flex-col items-center gap-1">
          <span className="grid size-10 place-items-center rounded-xl bg-primary/10 text-primary">
            {icon}
          </span>
          <span className="font-mono text-xs text-muted-foreground">
            {`0${step}`}
          </span>
        </div>
        <div className="flex-1">
          <p className="font-serif text-base font-semibold">{title}</p>
          <p className="mt-1 text-sm text-muted-foreground">{desc}</p>
        </div>
      </CardContent>
    </Card>
  )
}
