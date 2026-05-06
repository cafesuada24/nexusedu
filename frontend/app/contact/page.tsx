"use client";

import { useState } from "react";
import Link from "next/link";
import { Inter } from "next/font/google";
import { ArrowLeft, Mail, Clock, Send, Copy, Check } from "lucide-react";

const inter = Inter({ subsets: ["latin", "vietnamese"], variable: "--font-inter" });

export default function ContactPage() {
  const [copied, setCopied] = useState(false);

  const copyEmail = () => {
    navigator.clipboard.writeText("contact@nexusedu.io");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`min-h-screen bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 ${inter.variable} font-sans transition-colors duration-300`}>
      {/* Ambient Background Glow */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-400/10 dark:bg-blue-600/5 blur-[100px] rounded-full" />
        <div className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-400/10 dark:bg-indigo-600/5 blur-[100px] rounded-full" />
      </div>

      <div className="container relative mx-auto py-12 px-4 md:px-6 max-w-2xl">
        <Link href="/" className="inline-flex items-center text-sm text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors mb-8">
          <ArrowLeft size={16} className="mr-2" />
          Quay lại trang chủ
        </Link>

        <header className="mb-12 text-center md:text-left">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-slate-900 dark:text-white leading-tight">
            Liên hệ với chúng tôi
          </h1>
          <p className="mt-4 text-slate-500 dark:text-slate-400 text-lg font-medium leading-relaxed">
            Đội ngũ
            <strong className="mx-1 text-slate-900 dark:text-white font-bold">NexusEdu</strong>
            luôn sẵn sàng lắng nghe ý kiến đóng góp và hỗ trợ giải đáp mọi thắc mắc của bạn.
          </p>
        </header>

        <div className="space-y-8">
          {/* Section 1: Contact Details */}
          <section className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 shadow-sm">
            <h2 className="text-xl font-bold mb-8 text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-4">Thông tin liên lạc</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="flex items-start gap-4">
                <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-xl text-blue-600 dark:text-blue-400 shrink-0">
                  <Mail size={24} />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Email</h3>
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-bold truncate">contact@nexusedu.io</span>
                    <button 
                      onClick={copyEmail}
                      className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors text-slate-400 hover:text-blue-500 shrink-0"
                      title="Sao chép email"
                    >
                      {copied ? <Check size={16} className="text-emerald-500" /> : <Copy size={16} />}
                    </button>
                  </div>
                </div>
              </div>

              <div className="flex items-start gap-4">
                <div className="p-3 bg-amber-100 dark:bg-amber-900/30 rounded-xl text-amber-600 dark:text-amber-400 shrink-0">
                  <Clock size={24} />
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Thời gian làm việc</h3>
                  <p className="font-bold">Thứ 2 - Thứ 6 (8:00 - 17:00)</p>
                </div>
              </div>
            </div>
          </section>

          {/* Section 2: Contact Form */}
          <section className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 shadow-sm">
            <h2 className="text-xl font-bold mb-8 text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-4">Gửi tin nhắn nhanh</h2>
            <form className="space-y-6" onSubmit={(e) => e.preventDefault()}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label htmlFor="name" className="text-sm font-bold text-slate-500 dark:text-slate-400 ml-1">Họ tên</label>
                  <input 
                    type="text" 
                    id="name"
                    placeholder="Nguyễn Văn A"
                    className="w-full px-4 py-3 rounded-xl bg-transparent border border-slate-200 dark:border-slate-800 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none transition-all placeholder:text-slate-400 dark:placeholder:text-slate-600 font-medium"
                  />
                </div>
                <div className="space-y-2">
                  <label htmlFor="email" className="text-sm font-bold text-slate-500 dark:text-slate-400 ml-1">Email công việc</label>
                  <input 
                    type="email" 
                    id="email"
                    placeholder="name@university.edu"
                    className="w-full px-4 py-3 rounded-xl bg-transparent border border-slate-200 dark:border-slate-800 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none transition-all placeholder:text-slate-400 dark:placeholder:text-slate-600 font-medium"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label htmlFor="message" className="text-sm font-bold text-slate-500 dark:text-slate-400 ml-1">Nội dung tin nhắn</label>
                <textarea 
                  id="message"
                  rows={4}
                  placeholder="Hãy cho chúng tôi biết bạn đang cần hỗ trợ điều gì..."
                  className="w-full px-4 py-3 rounded-xl bg-transparent border border-slate-200 dark:border-slate-800 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none transition-all placeholder:text-slate-400 dark:placeholder:text-slate-600 font-medium resize-none"
                />
              </div>
              <button 
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 px-8 rounded-2xl transition-all shadow-lg shadow-blue-500/20 flex items-center justify-center gap-2 group"
              >
                Gửi tin nhắn
                <Send size={18} className="group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
              </button>
            </form>
          </section>
        </div>
      </div>
    </div>
  );
}
