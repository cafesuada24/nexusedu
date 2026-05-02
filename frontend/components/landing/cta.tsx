import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export function Cta() {
    return (
        <section className="relative border-t border-border/60 bg-muted/30 dark:bg-slate-900/80 py-20 md:py-28 transition-colors duration-300">
            <div className="mx-auto w-full max-w-4xl px-4 text-center md:px-6">
                <h2 className="text-balance font-serif text-3xl font-black tracking-tight md:text-5xl dark:text-white">
                    Sẵn sàng để không một sinh viên nào bị bỏ lại phía sau?
                </h2>
                <p className="mt-5 text-pretty text-muted-foreground dark:text-slate-300 md:text-lg">
                    Bắt đầu với danh sách sinh viên của bạn chỉ trong 2 phút —
                    không cần thẻ tín dụng.
                </p>
                <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
                    <Button
                        asChild
                        size="lg"
                        className="h-12 rounded-xl px-6 text-base transition-transform duration-200 ease-out hover:scale-[1.03] hover:shadow-md group"
                    >
                        <Link href="/login">
                            Dùng thử NexusEdu
                            <ArrowRight className="size-4 ml-1 transition-transform duration-300 group-hover:translate-x-1" />
                        </Link>
                    </Button>
                    <Button
                        asChild
                        size="lg"
                        variant="outline"
                        className="h-12 rounded-xl px-6 text-base transition-transform transition-shadow duration-200 ease-out hover:-translate-y-1 hover:shadow-md hover:border-slate-300 dark:bg-slate-800 dark:text-white dark:border-white/20 hover:dark:bg-slate-700"
                    >
                        <Link href="/login">Đăng nhập với Workspace</Link>
                    </Button>
                </div>
            </div>
        </section>
    );
}
