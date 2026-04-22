import { LifeBuoy, MessageSquarePlus } from "lucide-react"
import { PageHeader } from "@/components/dashboard/page-header"
import { SupportView } from "@/components/dashboard/support-view"
import { Button } from "@/components/ui/button"

export default function SupportPage() {
  return (
    <>
      <PageHeader
        eyebrow="Trợ giúp & tài liệu"
        title="Trung tâm hỗ trợ"
        description="Tìm câu trả lời nhanh, xem hướng dẫn sử dụng hoặc liên hệ đội ngũ NexusEdu. Đội hỗ trợ trả lời trong vòng 2 giờ làm việc."
        icon={<LifeBuoy className="size-5" />}
        actions={
          <Button className="rounded-lg">
            <MessageSquarePlus className="size-4" />
            Gửi yêu cầu mới
          </Button>
        }
      />
      <SupportView />
    </>
  )
}
