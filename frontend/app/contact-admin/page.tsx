"use client";

import Link from "next/link";
import { Inter } from "next/font/google";
import { ArrowLeft, ShieldCheck, UserPlus, Mail, Building2, ChevronRight, Info } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";

const inter = Inter({ subsets: ["latin", "vietnamese"], variable: "--font-inter" });

export default function ContactAdminPage() {
  return (
    <div className={`hero-gradient min-h-screen bg-background dark:bg-slate-950 text-slate-900 dark:text-slate-100 ${inter.variable} font-sans transition-colors duration-300 flex flex-col`}>
      <header className="relative z-10 mx-auto flex w-full max-w-7xl items-center justify-between px-4 py-5 md:px-6">
        <Link
          href="/login"
          className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground dark:text-slate-300 dark:hover:text-slate-100"
        >
          <ArrowLeft className="size-4" />
          Quay lại đăng nhập
        </Link>
        <ThemeToggle />
      </header>

      <main className="relative z-10 flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-2xl">
          <div className="text-center mb-12">
            <div className="inline-flex items-center justify-center p-4 bg-blue-100 dark:bg-blue-900/20 rounded-full mb-6 text-blue-600 dark:text-blue-400">
              <ShieldCheck size={48} strokeWidth={1.5} className="opacity-80" />
            </div>
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-slate-900 dark:text-white mb-4">
              Yêu cầu cấp quyền truy cập
            </h1>
            <p className="text-slate-500 dark:text-slate-400 text-lg font-medium leading-relaxed">
              Hệ thống
              <strong className="mx-1 text-slate-900 dark:text-white font-bold">NexusEdu</strong>
              hiện chỉ dành riêng cho Cố vấn học tập và Giảng viên được ủy quyền thông qua hệ thống đăng nhập tập trung
              <strong className="mx-1 text-slate-900 dark:text-white font-bold">SSO</strong>
              của từng trường.
            </p>
          </div>

          <div className="grid gap-6">
            {/* Card 1: Registration Procedure */}
            <section className="bg-white/80 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 shadow-sm backdrop-blur-sm">
              <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
                <UserPlus size={20} className="text-blue-500" />
                Quy trình đăng ký
              </h2>
              <div className="space-y-6">
                {[
                  "Liên hệ với Phòng Đào tạo hoặc Quản trị viên hệ thống tại đơn vị của bạn.",
                  "Cung cấp Email công vụ do nhà trường cấp (Email Workspace) và thông tin định danh cán bộ.",
                  "Chờ xác nhận kích hoạt tài khoản qua Email Workspace."
                ].map((step, i) => (
                  <div key={i} className="flex gap-4">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-sm font-bold text-slate-500 dark:text-slate-400">
                      {i + 1}
                    </div>
                    <p className="text-slate-600 dark:text-slate-300 font-medium leading-relaxed pt-1">
                      {step}
                    </p>
                  </div>
                ))}
              </div>
            </section>

            {/* Card 2: Support Information */}
            <section className="bg-white/80 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 shadow-sm backdrop-blur-sm">
              <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
                <Building2 size={20} className="text-blue-500" />
                Liên hệ Quản trị viên tại trường
              </h2>
              <div className="space-y-6">
                <p className="text-slate-600 dark:text-slate-300 font-medium leading-relaxed">
                  Vui lòng liên hệ với bộ phận CNTT hoặc Phòng Đào tạo tại đơn vị của bạn để được cấp quyền truy cập hệ thống.
                </p>
                
                <div className="flex items-start gap-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-2xl border border-blue-100 dark:border-blue-500/20">
                  <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg text-blue-600 dark:text-blue-400 shrink-0">
                    <Info size={20} />
                  </div>
                  <p className="text-sm text-blue-800 dark:text-blue-300 font-medium leading-relaxed">
                    Thông tin về quản trị viên và đầu mối liên hệ thường được cung cấp trong cổng thông tin nội bộ của nhà trường.
                  </p>
                </div>
              </div>
            </section>

            <Link 
              href="/login"
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 px-8 rounded-2xl transition-all shadow-lg shadow-blue-500/20 flex items-center justify-center gap-2 group"
            >
              Quay lại trang Đăng nhập
              <ChevronRight size={18} className="group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>
        </div>
      </main>
      
      <footer className="py-6 text-center text-xs text-muted-foreground/60">
        © {new Date().getFullYear()} NexusEdu. Bảo mật dữ liệu nội bộ.
      </footer>
    </div>
  );
}
