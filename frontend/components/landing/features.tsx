import {
    BrainCircuit,
    MailCheck,
    CalendarClock,
    LineChart,
    ShieldCheck,
    Users,
} from "lucide-react";

const features = [
    {
        icon: BrainCircuit,
        title: "AI Analysis",
        desc: "Mô hình máy học phân tích dữ liệu sinh viên để phát hiện nguy cơ bỏ học sớm.",
        color: "blue",
    },
    {
        icon: MailCheck,
        title: "HIL Emailing",
        desc: "Hệ thống email thông minh với sự kiểm soát của cố vấn trong mọi luồng.",
        color: "purple",
    },
    {
        icon: CalendarClock,
        title: "Smart Booking",
        desc: "Đặt lịch tư vấn thông minh, tự động đồng bộ hoá với Google Calendar.",
        color: "orange",
    },
    {
        icon: LineChart,
        title: "Dashboard",
        desc: "Trực quan hoá dữ liệu tỷ lệ giữ chân sinh viên cho nhà quản lý.",
        color: "blue",
    },
    {
        icon: ShieldCheck,
        title: "Privacy-first",
        desc: "Bảo mật dữ liệu tối đa với cơ chế phân quyền chi tiết.",
        color: "purple",
    },
    {
        icon: Users,
        title: "Đồng hành cố vấn",
        desc: "Hỗ trợ đội ngũ cố vấn theo dõi và chăm sóc sinh viên hiệu quả.",
        color: "orange",
    },
];

const colorMap: Record<string, string> = {
    blue: "bg-blue-200/40",
    purple: "bg-purple-200/40",
    orange: "bg-orange-200/40",
};

const iconGlowMap: Record<string, string> = {
    blue: "shadow-blue-500/10",
    purple: "shadow-purple-500/10",
    orange: "shadow-orange-500/10",
};

export function Features() {
    return (
        <section id="features" className="relative py-4">
            <div className="mx-auto w-full max-w-7xl px-4">
                <div className="mx-auto max-w-2xl text-center mb-16">
                    <h2 className="text-xl font-bold tracking-wide text-blue-600 dark:text-white uppercase">
                        TÍNH NĂNG CỐT LÕI
                    </h2>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {features.map((f) => (
                        <article
                            key={f.title}
                            className="group relative h-full p-[1px] rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-400 dark:from-blue-700 dark:to-cyan-600 transition-transform duration-300 hover:-translate-y-2 hover:scale-[1.02] hover:shadow-[0_8px_20px_rgba(56,189,248,0.06)]"
                        >
                            {/* Inner Card */}
                            <div className="h-full flex flex-col items-center text-center p-6 rounded-[14px] bg-white/60 dark:bg-slate-900/60 backdrop-blur-sm border border-white/20 dark:border-white/10">
                                {/* Subtle background glow */}
                                <div
                                    className={`absolute -inset-0.5 rounded-2xl ${colorMap[f.color]} blur-sm opacity-[0.06] group-hover:opacity-[0.14] transition-opacity duration-500`}
                                />

                                <div className="relative z-10 flex flex-col items-center">
                                    <div
                                        className={`relative flex size-12 items-center justify-center rounded-2xl bg-slate-50 dark:bg-slate-800 shadow-sm ${iconGlowMap[f.color]} mb-4 group-hover:-translate-y-1 transition-transform duration-300`}
                                    >
                                        <f.icon className="size-6 text-foreground dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors duration-300" />
                                    </div>

                                    <h3 className="text-lg font-bold text-foreground dark:text-white group-hover:opacity-100 transition-opacity">
                                        {f.title}
                                    </h3>

                                    <p className="mt-2 text-sm leading-relaxed text-muted-foreground dark:text-slate-300 group-hover:text-foreground dark:group-hover:text-white transition-colors duration-300">
                                        {f.desc}
                                    </p>
                                </div>
                            </div>
                        </article>
                    ))}
                </div>
            </div>
        </section>
    );
}
