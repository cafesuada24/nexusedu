import { SiteHeader } from "@/components/landing/site-header";
import { AnimatedBackground } from "@/components/landing/animated-background";
import { Hero } from "@/components/landing/hero";
import { SiteFooter } from "@/components/landing/site-footer";
import { Features } from "@/components/landing/features";
import { HowItWorks } from "@/components/landing/how-it-works";
import { Metrics } from "@/components/landing/metrics";
import { Cta } from "@/components/landing/cta";

export default function LandingPage() {
    const bentoCard =
        "p-[2px] rounded-3xl bg-gradient-to-br from-blue-500 to-cyan-400";
    const bentoContent = "h-full rounded-[22px] bg-white/50 p-8 shadow-sm";

    return (
        <div className="flex min-h-screen flex-col bg-transparent">
            <AnimatedBackground />
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
            <SiteFooter />
        </div>
    );
}
