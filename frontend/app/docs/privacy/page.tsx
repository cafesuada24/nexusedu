import { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, Shield, Lock, Eye, Server } from "lucide-react";

export const metadata: Metadata = {
  title: "Bảo mật và Quyền riêng tư | NexusEdu",
  description: "Cam kết của chúng tôi trong việc bảo vệ dữ liệu sinh viên và tuân thủ các tiêu chuẩn bảo mật cao nhất.",
};

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans transition-colors duration-300">
      <div className="container mx-auto py-12 px-4 md:px-6 max-w-4xl">
        <Link href="/" className="inline-flex items-center text-sm text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors mb-8">
          <ArrowLeft size={16} className="mr-2" />
          Quay lại trang chủ
        </Link>

        <header className="mb-16">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-slate-900 dark:text-white leading-tight">
            Bảo mật và Quyền riêng tư dữ liệu
          </h1>
          <p className="mt-4 text-slate-500 dark:text-slate-400 text-lg max-w-2xl font-medium leading-relaxed">
            Cam kết của chúng tôi trong việc bảo vệ dữ liệu sinh viên và tuân thủ các tiêu chuẩn bảo mật cao nhất.
          </p>
        </header>

        <div className="grid gap-8">
          {/* Section 1: Encryption */}
          <section className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-xl p-6 md:p-8 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                <Lock className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              </div>
              <h2 className="text-2xl font-semibold text-slate-900 dark:text-white">Mã hóa dữ liệu</h2>
            </div>
            <div className="text-slate-600 dark:text-slate-400 font-medium leading-relaxed space-y-4">
              <p>
                Tất cả dữ liệu trong hệ thống NexusEdu được bảo vệ bởi các thuật toán mã hóa tiên tiến nhất. Chúng tôi sử dụng tiêu chuẩn
                <strong className="mx-1 text-slate-900 dark:text-white font-bold">AES-256</strong>
                để mã hóa dữ liệu ở trạng thái nghỉ (at rest) và giao thức
                <strong className="mx-1 text-slate-900 dark:text-white font-bold">TLS 1.3</strong>
                để bảo mật dữ liệu khi đang truyền tải qua mạng.
              </p>
              <div className="inline-flex items-center px-4 py-2 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-100 dark:border-emerald-500/30 rounded-lg text-emerald-700 dark:text-emerald-400 text-sm font-bold">
                ⚡ Dữ liệu của bạn luôn được mã hóa đầu cuối.
              </div>
            </div>
          </section>

          {/* Section 2: Compliance */}
          <section className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-xl p-6 md:p-8 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                <Shield className="w-6 h-6 text-purple-600 dark:text-purple-400" />
              </div>
              <h2 className="text-2xl font-semibold text-slate-900 dark:text-white">Tuân thủ tiêu chuẩn</h2>
            </div>
            <p className="text-slate-600 dark:text-slate-400 font-medium leading-relaxed">
              NexusEdu tuân thủ nghiêm ngặt các quy định quốc tế và nội địa về bảo vệ dữ liệu giáo dục. Hệ thống hỗ trợ tích hợp đăng nhập một lần
              <strong className="mx-1 text-slate-900 dark:text-white font-bold">SSO</strong>
              và các giao thức xác thực bảo mật nội bộ, đảm bảo chỉ những người dùng hợp lệ mới có thể truy cập vào hệ thống.
            </p>
          </section>

          {/* Section 3: Access Control */}
          <section className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-xl p-6 md:p-8 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
                <Eye className="w-6 h-6 text-amber-600 dark:text-amber-400" />
              </div>
              <h2 className="text-2xl font-semibold text-slate-900 dark:text-white">Quyền hạn truy cập</h2>
            </div>
            <p className="text-slate-600 dark:text-slate-400 font-medium leading-relaxed">
              Chúng tôi áp dụng mô hình kiểm soát truy cập dựa trên vai trò
              <strong className="mx-1 text-slate-900 dark:text-white font-bold">Role-based Access Control</strong>
              một cách chặt chẽ. Chỉ những Cố vấn học tập được chỉ định trực tiếp mới có quyền xem và quản lý dữ liệu của các sinh viên thuộc phạm vi phụ trách của họ.
            </p>
          </section>

          {/* Section 4: Data Residency */}
          <section className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-xl p-6 md:p-8 shadow-sm">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-slate-100 dark:bg-slate-800 rounded-lg">
                <Server className="w-6 h-6 text-slate-600 dark:text-slate-400" />
              </div>
              <h2 className="text-2xl font-semibold text-slate-900 dark:text-white">Lưu trữ dữ liệu</h2>
            </div>
            <p className="text-slate-600 dark:text-slate-400 font-medium leading-relaxed">
              Chính sách
              <strong className="mx-1 text-slate-900 dark:text-white font-bold">Data Residency</strong>
              của chúng tôi đảm bảo rằng dữ liệu sinh viên không bao giờ rời khỏi máy chủ được ủy quyền của nhà trường hoặc các khu vực lưu trữ đã được phê duyệt, đảm bảo toàn vẹn dữ liệu tuyệt đối.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
