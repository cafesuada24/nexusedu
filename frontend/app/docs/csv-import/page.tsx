import { Metadata } from "next";
import Link from "next/link";
import { memo } from "react";
import { SampleCSVBlock } from "@/components/landing/sample-csv-block";
import { ArrowLeft } from "lucide-react";

export const metadata: Metadata = {
  title: "Hướng dẫn CSV | NexusEdu",
  description: "Hướng dẫn cấu trúc file CSV cho hệ thống NexusEdu",
};

const TypeBadge = memo(({ type }: { type: string }) => {
  const colors = {
    UUID: "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-500/30",
    String: "bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-500/30",
    Float: "bg-purple-100 text-purple-700 border-purple-200 dark:bg-purple-900/30 dark:text-purple-300 dark:border-purple-500/30",
    Integer: "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700",
    DateTime: "bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-500/30",
  };
  const color = colors[type as keyof typeof colors] || "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700";
  return <span className={`px-2 py-0.5 rounded border text-[10px] font-semibold uppercase tracking-wide ${color}`}>{type}</span>;
});
TypeBadge.displayName = "TypeBadge";

const DataTable = memo(({ fields }: { fields: { field: string; type: string; desc: string }[] }) => (
  <div className="overflow-hidden rounded-lg border border-slate-200 dark:border-slate-800">
    <table className="w-full text-sm text-left">
      <thead className="bg-slate-50 dark:bg-slate-900">
        <tr>
          <th className="px-6 py-3 font-semibold text-slate-700 dark:text-slate-300">Trường dữ liệu</th>
          <th className="px-6 py-3 font-semibold text-slate-700 dark:text-slate-300">Kiểu</th>
          <th className="px-6 py-3 font-semibold text-slate-700 dark:text-slate-300">Mô tả</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
        {fields.map((row) => (
          <tr key={row.field} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
            <td className={`px-6 py-3 text-xs text-slate-700 dark:text-slate-200 font-mono`}>{row.field}</td>
            <td className="px-6 py-3"><TypeBadge type={row.type} /></td>
            <td className="px-6 py-3 text-slate-500 dark:text-slate-400 font-medium leading-relaxed">{row.desc}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
));
DataTable.displayName = "DataTable";

export default function CSVGuidePage() {
  const lmsSample = `activity_id,sid,course_id,course_name,test_type,score,timestamp,academic_year,semester,week
d079df0e-bbdd-472c-9544-51b188a40d35,35bd9e50-f8fd-4a19-8e4e-30ab0302e8f6,C106,Software Engineering,Final,67.0,2022-05-14T10:51:08Z,1,1,1`;

  const sisSample = `sid,student_name,email,major,current_risk_status,intervention_status,last_notified_timestamp,last_notified_satisfaction
35bd9e50-f8fd-4a19-8e4e-30ab0302e8f6,Student 0,student_0@university.edu,Computer Science,Normal,none,1970-01-01T00:00:00Z,0`;

  const lmsFields = [
    { field: "activity_id", type: "UUID", desc: "Định danh duy nhất của hoạt động" },
    { field: "sid", type: "UUID", desc: "Mã sinh viên" },
    { field: "course_id", type: "String", desc: "Mã môn học" },
    { field: "course_name", type: "String", desc: "Tên môn học" },
    { field: "test_type", type: "String", desc: "Loại kiểm tra" },
    { field: "score", type: "Float", desc: "Điểm số" },
    { field: "timestamp", type: "DateTime", desc: "Thời gian diễn ra (ISO 8601)" },
    { field: "academic_year", type: "Integer", desc: "Năm học" },
    { field: "semester", type: "Integer", desc: "Học kỳ" },
    { field: "week", type: "Integer", desc: "Tuần học" },
  ];

  const sisFields = [
    { field: "sid", type: "UUID", desc: "Mã sinh viên" },
    { field: "student_name", type: "String", desc: "Họ và tên" },
    { field: "email", type: "String", desc: "Địa chỉ email" },
    { field: "major", type: "String", desc: "Ngành học" },
    { field: "current_risk_status", type: "String", desc: "Trạng thái rủi ro" },
    { field: "intervention_status", type: "String", desc: "Trạng thái hỗ trợ" },
    { field: "last_notified_timestamp", type: "DateTime", desc: "Thời gian thông báo gần nhất" },
    { field: "last_notified_satisfaction", type: "Integer", desc: "Mức độ hài lòng gần nhất" },
  ];

  return (
    <div className="min-h-screen bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans transition-colors duration-300">
      <div className="container mx-auto py-12 px-4 md:px-6 max-w-5xl">
        <Link href="/" className="inline-flex items-center text-sm text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors mb-8">
          <ArrowLeft size={16} className="mr-2" />
          Quay lại trang chủ
        </Link>

        <header className="mb-16">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-slate-900 dark:text-white leading-tight">
            Hướng dẫn cấu trúc file CSV
          </h1>
          <p className="mt-4 text-slate-500 dark:text-slate-400 text-lg max-w-2xl font-medium leading-relaxed">
            Để đảm bảo AI có thể phân tích và dự đoán chính xác tỉ lệ sinh viên thôi học, 
            vui lòng định dạng dữ liệu của bạn theo các mẫu dưới đây.
          </p>
        </header>

        <div className="space-y-12">
          <section className="bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-xl p-6 md:p-8">
            <h2 className="text-2xl font-semibold text-slate-900 dark:text-white">Dữ liệu LMS</h2>
            <p className="mt-2 text-slate-500 dark:text-slate-400 mb-8 font-medium">Chứa thông tin về hoạt động học tập, điểm số và tiến độ của sinh viên.</p>
            <DataTable fields={lmsFields} />
            <div className={`mt-6 font-mono`}>
              <SampleCSVBlock title="lms_data.csv" data={lmsSample} filename="lms_data.csv" />
            </div>
          </section>

          <section className="bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-xl p-6 md:p-8">
            <h2 className="text-2xl font-semibold text-slate-900 dark:text-white">Dữ liệu SIS</h2>
            <p className="mt-2 text-slate-500 dark:text-slate-400 mb-8 font-medium">Chứa thông tin cá nhân và tình trạng quản lý của sinh viên.</p>
            <DataTable fields={sisFields} />
            <div className={`mt-6 font-mono`}>
              <SampleCSVBlock title="sis_data.csv" data={sisSample} filename="sis_data.csv" />
            </div>
          </section>

          <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 p-8">
            <h3 className="font-semibold text-lg text-slate-900 dark:text-white flex items-center">
              <span className="w-1 h-6 bg-blue-500 rounded-full mr-3" />
              Lưu ý quan trọng
            </h3>
            <ul className="mt-4 list-none text-sm text-slate-500 dark:text-slate-400 space-y-3 font-medium">
              <li className="flex items-start">
                <span className="mr-2">⚡</span>
                <span>
                  File CSV phải được lưu với định dạng
                  <strong className="mx-1 text-slate-900 dark:text-white font-bold">UTF-8</strong>
                  để tránh lỗi hiển thị tiếng Việt.
                </span>
              </li>
              <li className="flex items-start">
                <span className="mr-2">⚡</span>
                <span>
                  Các trường thời gian (timestamp) phải tuân thủ định dạng
                  <strong className="ml-1 text-slate-900 dark:text-white font-bold">ISO 8601</strong>.
                </span>
              </li>
            </ul>
          </section>
        </div>
      </div>
    </div>
  );
}
