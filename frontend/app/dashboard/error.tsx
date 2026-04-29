"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { AlertCircle, RotateCcw } from "lucide-react";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center p-6 text-center">
      <div className="flex h-20 w-20 items-center justify-center rounded-full bg-destructive/10 text-destructive">
        <AlertCircle className="h-10 w-10" />
      </div>
      <h2 className="mt-6 text-2xl font-bold">Đã xảy ra lỗi</h2>
      <p className="mt-2 text-muted-foreground max-w-md">
        Không thể tải dữ liệu dashboard. Điều này có thể do lỗi kết nối hoặc phiên làm việc đã hết hạn.
      </p>
      <div className="mt-8 flex gap-4">
        <Button onClick={() => reset()} className="gap-2">
          <RotateCcw className="h-4 w-4" />
          Thử lại
        </Button>
        <Button variant="outline" onClick={() => window.location.href = "/"}>
          Quay lại trang chủ
        </Button>
      </div>
    </div>
  );
}
