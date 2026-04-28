import { LifeBuoy, MessageSquarePlus } from "lucide-react"
import { SupportView } from "@/components/dashboard/support-view"
import { Button } from "@/components/ui/button"

export default function SupportPage() {
  return (
    <div className="flex w-full flex-1 flex-col gap-6">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="grid size-10 place-items-center rounded-xl bg-accent-sky/10 text-accent-sky ring-1 ring-accent-sky/20 shadow-sm shadow-accent-sky/10">
            <LifeBuoy className="size-5" />
          </div>
          <h1 className="font-serif text-2xl font-bold tracking-tight md:text-3xl">
            Hỗ trợ
          </h1>
        </div>
        <Button size="sm" className="rounded-lg">
          <MessageSquarePlus className="size-4" />
          Gửi yêu cầu
        </Button>
      </div>
      <div
        aria-hidden
        className="h-px w-full bg-gradient-to-r from-accent-sky/40 via-primary/25 to-transparent"
      />
      <SupportView />
    </div>
  )
}
