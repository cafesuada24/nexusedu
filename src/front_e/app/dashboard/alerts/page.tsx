"use client"

import { AlertCenter } from "@/components/dashboard/alert-center"
import { useDataset } from "@/hooks/use-dataset"
import { Skeleton } from "@/components/ui/skeleton"

export default function AlertsPage() {
  const { dataset, isLoading } = useDataset()

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
      <div className="flex flex-col justify-between gap-3 md:flex-row md:items-end">
        <div>
          <h1 className="font-serif text-2xl font-bold tracking-tight md:text-3xl">
            Alert Center · HIL
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {isLoading ? (
              <Skeleton className="inline-block h-4 w-72 align-middle" />
            ) : dataset ? (
              <>
                AI đã phát hiện{" "}
                <span className="font-semibold text-foreground">
                  {dataset.highRisk.toLocaleString("vi-VN")}
                </span>{" "}
                sinh viên nguy cơ cao cần gửi email. Xem bản nháp và quyết định gửi.
              </>
            ) : (
              "Hãy nhập file CSV điểm sinh viên để AI soạn sẵn email cảnh báo."
            )}
          </p>
        </div>
      </div>

      <AlertCenter />
    </div>
  )
}
