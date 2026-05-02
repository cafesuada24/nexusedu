"use client";

import React from "react";

type Props = {
    icon: React.ElementType;
    title: string;
    desc: string;
    colorClass?: string;
};

function FeatureCard({
    icon: Icon,
    title,
    desc,
    colorClass = "bg-blue-200/40",
}: Props) {
    return (
        <article
            className="group relative h-full p-px rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-400 dark:from-blue-700 dark:to-cyan-600 transition-transform duration-300 hover:-translate-y-2 hover:scale-[1.02] hover:shadow-[0_8px_20px_rgba(56,189,248,0.06)]"
            style={{ willChange: "transform" }}
        >
            <div className="h-full flex flex-col items-center text-center p-6 rounded-[14px] bg-white dark:bg-slate-900 border border-white/10 dark:border-white/10">
                {/* Subtle background glow implemented with low-opacity color overlay (cheap) */}
                <div
                    className={`absolute -inset-0.5 rounded-2xl ${colorClass} opacity-[0.04] group-hover:opacity-[0.12] transition-opacity duration-500`}
                />

                <div className="relative z-10 flex flex-col items-center">
                    <div
                        className="relative flex size-12 items-center justify-center rounded-2xl bg-slate-50 dark:bg-slate-800 shadow-sm mb-4 transition-transform duration-300"
                        style={{ willChange: "transform" }}
                    >
                        <Icon className="size-6 text-foreground dark:text-white transition-colors duration-300" />
                    </div>

                    <h3 className="text-lg font-bold text-foreground dark:text-white">
                        {title}
                    </h3>

                    <p className="mt-2 text-sm leading-relaxed text-muted-foreground dark:text-slate-300">
                        {desc}
                    </p>
                </div>
            </div>
        </article>
    );
}

export default React.memo(FeatureCard);
