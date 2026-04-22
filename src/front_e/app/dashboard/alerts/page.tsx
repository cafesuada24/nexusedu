import { AlertCenter } from "@/components/dashboard/alert-center"

export default function AlertsPage() {
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
      <div className="flex flex-col justify-between gap-3 md:flex-row md:items-end">
        <div>
          <h1 className="font-serif text-2xl font-bold tracking-tight md:text-3xl">
            Alert Center · HIL
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            AI đã phát hiện{" "}
            <span className="font-semibold text-foreground">128</span> sinh
            viên có nguy cơ. Xem bản nháp email và quyết định gửi.
          </p>
        </div>
      </div>

      <AlertCenter />
    </div>
  )
}
