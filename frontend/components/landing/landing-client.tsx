"use client";

import dynamic from "next/dynamic";

const SiteHeader = dynamic(
    () =>
        import("@/components/landing/site-header").then(
            (mod) => mod.SiteHeader,
        ),
    { ssr: false },
);
const Hero = dynamic(
    () => import("@/components/landing/hero").then((mod) => mod.Hero),
    { ssr: false },
);
const Features = dynamic(
    () => import("@/components/landing/features").then((mod) => mod.Features),
    { ssr: false },
);
const HowItWorks = dynamic(
    () =>
        import("@/components/landing/how-it-works").then(
            (mod) => mod.HowItWorks,
        ),
    { ssr: false },
);
const Metrics = dynamic(
    () => import("@/components/landing/metrics").then((mod) => mod.Metrics),
    { ssr: false },
);
const Cta = dynamic(
    () => import("@/components/landing/cta").then((mod) => mod.Cta),
    { ssr: false },
);

export default function LandingClient() {
    const bentoCard =
        "p-[2px] rounded-3xl bg-gradient-to-br from-blue-500 to-cyan-400";
    const bentoContent =
        "h-full rounded-[22px] bg-white/50 backdrop-blur-sm p-8 shadow-sm";

    return (
        <>
            <SiteHeader />
            <main className="flex-1 space-y-6 p-6">
                <div className={bentoCard}>
                    <div className={bentoContent}>
                        <Hero />
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className={bentoCard}>
                        <div className={bentoContent}>
                            <Features />
                        </div>
                    </div>
                    <div className={bentoCard}>
                        <div className={bentoContent}>
                            <HowItWorks />
                        </div>
                    </div>
                </div>

                <div className={bentoCard}>
                    <div className={bentoContent}>
                        <Metrics />
                    </div>
                </div>

                <div className={bentoCard}>
                    <div className={bentoContent}>
                        <Cta />
                    </div>
                </div>
            </main>
        </>
    );
}
