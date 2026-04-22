import { CsvUploader } from "@/components/dashboard/csv-uploader"

export default function ImportPage() {
  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <div>
        <h1 className="font-serif text-2xl font-bold tracking-tight md:text-3xl">
          Nhập danh sách sinh viên
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Tải lên bảng điểm, điểm danh hoặc trạng thái học phí (định dạng
          .CSV) để AI phân tích nguy cơ.
        </p>
      </div>

      <CsvUploader />
    </div>
  )
}
