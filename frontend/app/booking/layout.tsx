"use client";

import * as React from "react";
import { Providers } from "@/components/providers";
import { Analytics } from "@vercel/analytics/next";

export default function BookingLayout({ children }: { children: React.ReactNode }) {
  return (
    <Providers>
      {children}
      {process.env.NODE_ENV === "production" && <Analytics />}
    </Providers>
  );
}
