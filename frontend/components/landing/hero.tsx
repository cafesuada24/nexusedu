"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { ArrowRight, Sparkles, ShieldCheck, Users } from "lucide-react";
import { Button } from "@/components/ui/button";

// Stable texts for the typewriter to avoid restarting on parent re-renders
const HERO_TYPEWRITER_TEXTS = [
    "AI phát hiện sớm",
    "Kết nối kịp thời",
    "Giữ chân học sinh",
];

function Typewriter({
    texts,
    delay = 100,
    period = 2000,
}: {
    texts: string[];
    delay?: number;
    period?: number;
}) {
    const [index, setIndex] = useState(0);
    const [displayText, setDisplayText] = useState("");
    const [isDeleting, setIsDeleting] = useState(false);

    useEffect(() => {
        let timeout: ReturnType<typeof setTimeout>;
        const currentText = texts[index % texts.length];

        if (isDeleting) {
            timeout = setTimeout(() => {
                setDisplayText((prev) => prev.slice(0, -1));
            }, delay / 2);
        } else {
            timeout = setTimeout(() => {
                setDisplayText(currentText.slice(0, displayText.length + 1));
            }, delay);
        }

        if (!isDeleting && displayText === currentText) {
            timeout = setTimeout(() => setIsDeleting(true), period);
        } else if (isDeleting && displayText === "") {
            setIsDeleting(false);
            setIndex((prev) => prev + 1);
        }

        return () => clearTimeout(timeout);
    }, [displayText, isDeleting, index, texts, delay, period]);

    return (
        <span className="inline-block min-h-[1.2em]">
            {displayText}
            <span className="ml-1 inline-block w-0.5 h-[1em] bg-blue-600 animate-pulse align-middle" />
        </span>
    );
}

export function Hero() {
    return (
        <section className="hero-gradient relative overflow-hidden">
            {/* Removed heavy masked overlay to reduce paint cost */}

            <div className="relative mx-auto w-full max-w-7xl px-4 pt-16 pb-20 md:px-6 md:pt-24 md:pb-28">
                <div className="mx-auto max-w-3xl text-center">
                    <h1 className="text-balance font-serif text-6xl font-extrabold tracking-tight md:text-9xl leading-tight">
                        <span className="bg-gradient-to-r from-[#1e40af] via-[#3b82f6] to-[#fb923c] bg-clip-text text-transparent transition-opacity duration-200 ease-out">
                            NexusEdu
                        </span>
                    </h1>

                    <div className="mt-8 min-h-[4rem] text-pretty text-2xl font-bold tracking-tight text-muted-foreground md:text-4xl">
                        <Typewriter texts={HERO_TYPEWRITER_TEXTS} />
                    </div>

                    <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
                        <Button
                            asChild
                            size="lg"
                            className="h-12 rounded-xl px-6 text-base transition-transform duration-200 ease-out hover:scale-[1.03] hover:shadow-md group"
                        >
                            <Link href="/login">
                                Bắt đầu với NexusEdu
                                <ArrowRight className="size-4 ml-1 transition-transform duration-300 group-hover:translate-x-1" />
                            </Link>
                        </Button>
                        <Button
                            asChild
                            size="lg"
                            variant="outline"
                            className="h-12 rounded-xl px-6 text-base transition-transform transition-shadow duration-200 ease-out hover:-translate-y-1 hover:shadow-md hover:shadow-gray-200/50 dark:hover:bg-white/5"
                        >
                            <Link href="#features">Xem tính năng</Link>
                        </Button>
                    </div>
                </div>
            </div>
        </section>
    );
}

function Stat({
    icon,
    value,
    label,
}: {
    icon: React.ReactNode;
    value: string;
    label: string;
}) {
    return (
        <div className="rounded-xl border border-border/60 bg-card/60 p-3">
            <dt className="flex items-center gap-2 text-xs text-muted-foreground">
                <span className="grid size-6 place-items-center rounded-md bg-primary/10 text-primary">
                    {icon}
                </span>
                {label}
            </dt>
            <dd className="mt-1 font-serif text-2xl font-bold text-foreground">
                {value}
            </dd>
        </div>
    );
}

function HeroMock() {
    return (
        <div className="grid gap-4 p-4 md:grid-cols-3 md:p-6">
            <div className="rounded-xl border border-border/60 bg-background/60 p-4">
                <p className="text-xs font-medium text-muted-foreground">
                    Sinh viên nguy cơ
                </p>
                <p className="mt-1 font-serif text-2xl font-bold">128</p>
                <div className="mt-3 h-16 rounded-md bg-gradient-to-t from-primary/20 to-primary/5" />
            </div>
            <div className="rounded-xl border border-border/60 bg-background/60 p-4">
                <p className="text-xs font-medium text-muted-foreground">
                    Email chờ duyệt
                </p>
                <p className="mt-1 font-serif text-2xl font-bold">23</p>
                <ul className="mt-3 space-y-1.5 text-xs">
                    <li className="flex items-center justify-between rounded-md bg-primary/5 px-2 py-1.5">
                        <span className="truncate">Nguyễn An · Học phí</span>
                        <span className="text-primary">AI</span>
                    </li>
                    <li className="flex items-center justify-between rounded-md bg-primary/5 px-2 py-1.5">
                        <span className="truncate">Trần Bình · Điểm GK</span>
                        <span className="text-primary">AI</span>
                    </li>
                </ul>
            </div>
            <div className="rounded-xl border border-border/60 bg-background/60 p-4">
                <p className="text-xs font-medium text-muted-foreground">
                    Tỷ lệ giữ chân
                </p>
                <p className="mt-1 font-serif text-2xl font-bold">94.2%</p>
                <div className="mt-3 flex h-16 items-end gap-1">
                    {[40, 55, 48, 70, 62, 80, 74].map((h, i) => (
                        <span
                            key={i}
                            className="flex-1 rounded-sm bg-primary/70"
                            style={{ height: `${h}%` }}
                        />
                    ))}
                </div>
            </div>
        </div>
    );
}
