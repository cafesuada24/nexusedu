import Link from "next/link"
import { ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"

export function Cta() {
  return (
    <section className="relative border-t border-border/60 bg-muted/30 py-20 md:py-28">
      <div className="mx-auto w-full max-w-4xl px-4 text-center md:px-6">
        <h2 className="text-balance font-serif text-3xl font-black tracking-tight md:text-5xl">
          Sẵn sàng để không một sinh viên nào bị bỏ lại phía sau?
        </h2>
        <p className="mt-5 text-pretty text-muted-foreground md:text-lg">
          Bắt đầu với danh sách sinh viên của bạn chỉ trong 2 phút — không cần
          thẻ tín dụng.
        </p>
        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Button asChild size="lg" className="h-12 rounded-xl px-6 text-base">
            <Link href="/dashboard">
              Dùng thử NexusEdu
              <ArrowRight className="size-4" />
            </Link>
          </Button>
          <Button
            asChild
            size="lg"
            variant="outline"
            className="h-12 rounded-xl px-6 text-base"
          >
            <Link href="/login">Đăng nhập với Workspace</Link>
          </Button>
        </div>
      </div>
    </section>
  )
}
