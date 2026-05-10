"use client";

import * as React from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import { Logo } from "@/components/logo";
import { Button, buttonVariants } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { cn } from "@/lib/utils";

const links = [
    { href: "#features", label: "Tính năng" },
    { href: "#how", label: "Cách hoạt động" },
    { href: "#metrics", label: "Hiệu quả" },
];

export function SiteHeader() {
    const [open, setOpen] = React.useState(false);
    const [scrolled, setScrolled] = React.useState(false);

    React.useEffect(() => {
        let ticking = false;
        const onScroll = () => {
            if (ticking) return;
            ticking = true;
            window.requestAnimationFrame(() => {
                setScrolled(window.scrollY > 8);
                ticking = false;
            });
        };

        onScroll();
        window.addEventListener("scroll", onScroll, { passive: true });
        return () => window.removeEventListener("scroll", onScroll);
    }, []);

    return (
        <header
            className={cn(
                "sticky top-0 z-50 w-full transition-all duration-300",
                scrolled
                    ? "border-b border-slate-200/80 bg-white/80 shadow-sm backdrop-blur-md dark:border-slate-800 dark:bg-slate-950/80"
                    : "border-b border-transparent bg-transparent shadow-none backdrop-blur-0",
            )}
        >
            <div className="mx-auto flex h-20 w-full max-w-7xl items-center justify-between px-4 md:px-6">
                <div className="w-fit flex-none">
                    <Logo
                        priority
                        onClick={() =>
                            window.scrollTo({ top: 0, behavior: "smooth" })
                        }
                    />
                </div>

                <nav
                    className="hidden items-center gap-1 md:flex"
                    aria-label="Điều hướng chính"
                >
                    {links.map((l) => (
                        <button
                            key={l.href}
                            onClick={(e) => {
                                e.preventDefault();
                                const element = document.querySelector(l.href);
                                if (element) {
                                    element.scrollIntoView({
                                        behavior: "smooth",
                                    });
                                }
                            }}
                            className="rounded-lg px-3 py-2 text-base font-medium text-slate-600 transition-colors hover:bg-accent hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800/70 dark:hover:text-slate-100"
                        >
                            {l.label}
                        </button>
                    ))}
                </nav>

                <div className="flex items-center gap-2">
                    <Link
                        href="/login"
                        className={cn(
                            buttonVariants({
                                variant: "ghost",
                                size: "default",
                            }),
                            "hidden rounded-xl px-4 md:inline-flex text-primary font-semibold shadow-[0_0_15px_rgba(59,130,246,0.3)] transition-shadow duration-300 hover:shadow-[0_0_20px_rgba(59,130,246,0.5)]",
                        )}
                    >
                        Đăng nhập
                    </Link>
                    <ThemeToggle />
                    <Button
                        variant="ghost"
                        size="icon"
                        className="rounded-xl text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100 md:hidden"
                        onClick={() => setOpen((v) => !v)}
                        aria-label="Mở menu"
                        aria-expanded={open}
                    >
                        {open ? (
                            <X className="size-5" />
                        ) : (
                            <Menu className="size-5" />
                        )}
                    </Button>
                </div>
            </div>

            {open && (
                <div className="border-t border-slate-200/80 bg-white/90 backdrop-blur-md dark:border-slate-800 dark:bg-slate-950/90 md:hidden">
                    <nav
                        className="mx-auto flex max-w-7xl flex-col gap-1 p-4"
                        aria-label="Điều hướng di động"
                    >
                        {links.map((l) => (
                            <button
                                key={l.href}
                                onClick={() => {
                                    setOpen(false);
                                    const element = document.querySelector(
                                        l.href,
                                    );
                                    if (element) {
                                        element.scrollIntoView({
                                            behavior: "smooth",
                                        });
                                    }
                                }}
                                className="rounded-lg px-3 py-2.5 text-left text-sm font-medium text-slate-600 hover:bg-accent hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800/70 dark:hover:text-slate-100"
                            >
                                {l.label}
                            </button>
                        ))}
                        <div className="mt-2 flex flex-col gap-2">
                            <Link
                                href="/login"
                                className={cn(
                                    buttonVariants({
                                        variant: "outline",
                                        size: "default",
                                    }),
                                    "w-full rounded-xl text-primary font-semibold",
                                )}
                            >
                                Đăng nhập
                            </Link>
                        </div>
                    </nav>
                </div>
            )}
        </header>
    );
}
