import { Metadata } from "next";
import Link from "next/link";
import { Inter } from "next/font/google";
import { ArrowLeft, Heart, Zap, Users, ShieldCheck, GraduationCap, Target, Sparkles } from "lucide-react";

const inter = Inter({ subsets: ["latin", "vietnamese"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Về NexusEdu | Sứ mệnh của chúng tôi",
  description: "Chúng tôi tin rằng không một sinh viên nào nên bị bỏ lại phía sau trong kỷ nguyên số.",
};

export default function AboutPage() {
  return (
    <div className={`min-h-screen bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 ${inter.variable} font-sans transition-colors duration-300`}>
      {/* Hero Section with Ambient Glow */}
      <div className="relative overflow-hidden pt-12 pb-24 md:pt-20 md:pb-32">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-4xl h-96 bg-blue-400/20 dark:bg-blue-600/10 blur-[120px] rounded-full -z-10" />
        
        <div className="container mx-auto px-4 md:px-6 max-w-4xl">
          <Link href="/" className="inline-flex items-center text-sm text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors mb-12">
            <ArrowLeft size={16} className="mr-2" />
            Quay lại trang chủ
          </Link>

          <header className="text-center md:text-left">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 text-xs font-bold mb-6">
              <Sparkles size={14} />
              Sứ mệnh của chúng tôi
            </div>
            <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-slate-900 dark:text-white leading-tight mb-6">
              Sứ mệnh của NexusEdu
            </h1>
            <p className="text-slate-600 dark:text-slate-400 text-xl md:text-2xl font-medium leading-relaxed max-w-3xl">
              Chúng tôi tin rằng không một sinh viên nào nên bị bỏ lại phía sau trong kỷ nguyên số.
            </p>
          </header>
        </div>
      </div>

      <div className="container mx-auto px-4 md:px-6 max-w-4xl pb-24">
        <div className="grid gap-12">
          {/* Section 1: The Why */}
          <section className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 md:p-12 shadow-sm">
            <h2 className="text-3xl font-bold text-slate-900 dark:text-white mb-6 flex items-center gap-3">
              <GraduationCap className="text-blue-500" size={32} />
              Tại sao chúng tôi tồn tại?
            </h2>
            <div className="text-slate-600 dark:text-slate-400 text-lg font-medium leading-relaxed space-y-4">
              <p>
                Hiện nay, tỉ lệ sinh viên thôi học đang trở thành một thách thức lớn đối với nền giáo dục. Đội ngũ cố vấn học tập thường xuyên rơi vào tình trạng quá tải, khiến việc theo sát và hỗ trợ kịp thời cho từng cá nhân trở nên khó khăn.
              </p>
              <p>
                Khoảng cách giữa dữ liệu và hành động chăm sóc sinh viên chính là nơi NexusEdu ra đời để lấp đầy.
              </p>
            </div>
          </section>

          {/* Section 2: The What */}
          <section className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 md:p-12 shadow-sm">
            <h2 className="text-3xl font-bold text-slate-900 dark:text-white mb-6 flex items-center gap-3">
              <Zap className="text-amber-500" size={32} />
              Giải pháp AI Agents
            </h2>
            <p className="text-slate-600 dark:text-slate-400 text-lg font-medium leading-relaxed">
              NexusEdu không chỉ là một công cụ phân tích dữ liệu
              <strong className="mx-1 text-slate-900 dark:text-white font-bold">Big Data</strong>. 
              Chúng tôi xây dựng các
              <strong className="mx-1 text-slate-900 dark:text-white font-bold">AI Agents</strong>
              đóng vai trò như những người đồng hành thông minh, giúp kết nối tình thầy trò và hỗ trợ sinh viên đúng lúc dựa trên những bằng chứng thực tế từ hoạt động học tập.
            </p>
          </section>

          {/* Section 3: Core Values Grid */}
          <section>
            <h2 className="text-3xl font-bold text-slate-900 dark:text-white mb-10 text-center">Giá trị cốt lõi</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-8 text-center shadow-sm">
                <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-xl flex items-center justify-center mx-auto mb-6 text-blue-600 dark:text-blue-400">
                  <Target size={28} />
                </div>
                <h3 className="text-xl font-bold mb-4">Chính xác</h3>
                <p className="text-slate-500 dark:text-slate-400 font-medium">Mọi dự đoán đều dựa trên dữ liệu LMS thực tế, loại bỏ những nhận định cảm tính.</p>
              </div>
              
              <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-8 text-center shadow-sm">
                <div className="w-12 h-12 bg-amber-100 dark:bg-amber-900/30 rounded-xl flex items-center justify-center mx-auto mb-6 text-amber-600 dark:text-amber-400">
                  <Zap size={28} />
                </div>
                <h3 className="text-xl font-bold mb-4">Kịp thời</h3>
                <p className="text-slate-500 dark:text-slate-400 font-medium">Phát hiện sớm các dấu hiệu rủi ro ngay từ những tuần học đầu tiên.</p>
              </div>

              <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-8 text-center shadow-sm">
                <div className="w-12 h-12 bg-emerald-100 dark:bg-emerald-900/30 rounded-xl flex items-center justify-center mx-auto mb-6 text-emerald-600 dark:text-emerald-400">
                  <Heart size={28} />
                </div>
                <h3 className="text-xl font-bold mb-4">Thấu hiểu</h3>
                <p className="text-slate-500 dark:text-slate-400 font-medium">Đặt con người làm trung tâm, AI chỉ là công cụ để thấu hiểu sinh viên hơn.</p>
              </div>
            </div>
          </section>

          {/* Section 4: Team & Commitment */}
          <section className="text-center py-12 px-6 rounded-3xl bg-slate-50 dark:bg-slate-900/20 border border-slate-200 dark:border-slate-800">
            <div className="max-w-2xl mx-auto">
              <Users className="w-12 h-12 text-blue-500 mx-auto mb-6" />
              <h2 className="text-3xl font-bold text-slate-900 dark:text-white mb-6">Đội ngũ tâm huyết</h2>
              <p className="text-slate-600 dark:text-slate-400 text-lg font-medium leading-relaxed mb-10">
                NexusEdu được phát triển bởi đội ngũ kỹ sư tại 
                <strong className="mx-1 text-slate-900 dark:text-white font-bold">CTUT</strong>
                (Can Tho University of Technology), với mong muốn mang công nghệ AI phục vụ giáo dục nước nhà.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link 
                  href="/"
                  className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 px-8 rounded-2xl transition-all shadow-lg shadow-blue-500/20"
                >
                  Hãy cùng chúng tôi xây dựng một môi trường giáo dục tốt đẹp hơn
                </Link>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
