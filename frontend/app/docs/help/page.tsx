import { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, HelpCircle, BookOpen, MessageSquare, Mail, Database, UserCheck, Zap } from "lucide-react";

export const metadata: Metadata = {
  title: "Trung tâm hỗ trợ | NexusEdu",
  description: "Tìm kiếm câu trả lời hoặc liên hệ với đội ngũ kỹ thuật của chúng tôi để được hỗ trợ tốt nhất.",
};

const FAQItem = ({ question, answer }: { question: string, answer: React.ReactNode }) => (
  <div className="border-b border-slate-200 dark:border-slate-800 py-6 last:border-0">
    <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2 flex items-start gap-2">
      <HelpCircle className="w-5 h-5 text-blue-500 mt-0.5 shrink-0" />
      {question}
    </h3>
    <div className="text-slate-600 dark:text-slate-400 font-medium leading-relaxed pl-7">
      {answer}
    </div>
  </div>
);

export default function HelpPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans transition-colors duration-300">
      <div className="container mx-auto py-12 px-4 md:px-6 max-w-4xl">
        <Link href="/" className="inline-flex items-center text-sm text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors mb-8">
          <ArrowLeft size={16} className="mr-2" />
          Quay lại trang chủ
        </Link>

        <header className="mb-16">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-slate-900 dark:text-white leading-tight">
            Trung tâm hỗ trợ
          </h1>
          <p className="mt-4 text-slate-500 dark:text-slate-400 text-lg max-w-2xl font-medium leading-relaxed">
            Tìm kiếm câu trả lời hoặc liên hệ với đội ngũ kỹ thuật của chúng tôi để được hỗ trợ tốt nhất.
          </p>
        </header>

        <div className="space-y-16">
          {/* Section 1: Categories */}
          <section>
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-8 flex items-center gap-2">
              <BookOpen className="w-6 h-6 text-blue-500" />
              Danh mục hỗ trợ
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
                <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg w-fit mb-4">
                  <Zap className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                </div>
                <h3 className="text-lg font-semibold mb-2">Bắt đầu</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">Hướng dẫn nhanh cho Cố vấn mới tham gia hệ thống.</p>
              </div>
              <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
                <div className="p-2 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg w-fit mb-4">
                  <Database className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
                </div>
                <h3 className="text-lg font-semibold mb-2">Quản lý dữ liệu</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">Cách xử lý file CSV và khắc phục các lỗi upload thường gặp.</p>
              </div>
              <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
                <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg w-fit mb-4">
                  <UserCheck className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                </div>
                <h3 className="text-lg font-semibold mb-2">Tài khoản</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">Bảo mật thông tin cá nhân và phân quyền trong Workspace.</p>
              </div>
            </div>
          </section>

          {/* Section 2: FAQs */}
          <section className="bg-slate-50 dark:bg-slate-900/20 border border-slate-200 dark:border-slate-800 rounded-2xl p-8">
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-8 flex items-center gap-2">
              <MessageSquare className="w-6 h-6 text-blue-500" />
              Câu hỏi thường gặp
            </h2>
            <div className="divide-y divide-slate-200 dark:divide-slate-800">
              <FAQItem 
                question="Làm thế nào để AI dự đoán chính xác hơn?" 
                answer={
                  <span>
                    Để AI đạt độ chính xác cao nhất, bạn cần cung cấp đủ dữ liệu
                    <strong className="mx-1 text-slate-900 dark:text-white font-bold">LMS</strong>
                    tối thiểu trong vòng
                    <strong className="mx-1 text-slate-900 dark:text-white font-bold">4 tuần</strong>
                    học tập của sinh viên.
                  </span>
                }
              />
              <FAQItem 
                question="Dữ liệu có được cập nhật thời gian thực không?" 
                answer="Có, tất cả các chỉ số và dự đoán sẽ được cập nhật ngay sau khi bạn upload file CSV mới nhất vào hệ thống."
              />
              <FAQItem 
                question="Tôi phải làm gì nếu hệ thống báo lỗi định dạng?" 
                answer={
                  <span>
                    Vui lòng kiểm tra lại file của bạn đã tuân thủ chuẩn
                    <strong className="mx-1 text-slate-900 dark:text-white font-bold">UTF-8</strong>
                    và định dạng thời gian
                    <strong className="mx-1 text-slate-900 dark:text-white font-bold">ISO 8601</strong>
                    tại trang
                    <Link href="/docs/csv-import" className="text-blue-600 dark:text-blue-400 hover:underline mx-1">Hướng dẫn CSV</Link>.
                  </span>
                }
              />
            </div>
          </section>

          {/* Section 3: Contact */}
          <section className="bg-blue-600 dark:bg-blue-700 rounded-2xl p-8 text-white shadow-lg">
            <div className="flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="space-y-2 text-center md:text-left">
                <h2 className="text-2xl font-bold flex items-center justify-center md:justify-start gap-2">
                  <Mail className="w-6 h-6" />
                  Liên hệ hỗ trợ kỹ thuật
                </h2>
                <p className="text-blue-100 font-medium">Đội ngũ của chúng tôi luôn sẵn sàng giải đáp mọi thắc mắc của bạn.</p>
                <div className="text-lg font-bold mt-4">support@nexusedu.io</div>
              </div>
              <button className="bg-white text-blue-600 hover:bg-blue-50 transition-colors px-8 py-3 rounded-xl font-bold text-sm shadow-sm whitespace-nowrap">
                Gửi yêu cầu hỗ trợ
              </button>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
