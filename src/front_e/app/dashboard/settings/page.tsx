import { Settings as SettingsIcon, Save } from "lucide-react"
import { PageHeader } from "@/components/dashboard/page-header"
import { SettingsView } from "@/components/dashboard/settings-view"
import { Button } from "@/components/ui/button"

export default function SettingsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Tài khoản & hệ thống"
        title="Cài đặt"
        description="Quản lý hồ sơ cá nhân, thông báo, quy tắc AI và tích hợp hệ thống cho vai trò cố vấn của bạn."
        icon={<SettingsIcon className="size-5" />}
        actions={
          <Button className="rounded-lg">
            <Save className="size-4" />
            Lưu thay đổi
          </Button>
        }
      />
      <SettingsView />
    </>
  )
}
