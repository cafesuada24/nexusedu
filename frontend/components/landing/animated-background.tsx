"use client";

import { motion } from "framer-motion";

export function AnimatedBackground() {
  return (
    <div className="fixed inset-0 -z-10 overflow-hidden bg-slate-50">
      <motion.div
        animate={{
          x: [0, 100, 0],
          y: [0, -50, 0],
        }}
        transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
        className="absolute -top-[10%] -left-[10%] size-[500px] rounded-full bg-blue-300 blur-[120px] opacity-20 will-change-transform"
      />
      <motion.div
        animate={{
          x: [0, -100, 0],
          y: [0, 100, 0],
        }}
        transition={{ duration: 25, repeat: Infinity, ease: "easeInOut" }}
        className="absolute top-[20%] right-[10%] size-[400px] rounded-full bg-purple-300 blur-[120px] opacity-20 will-change-transform"
      />
      <motion.div
        animate={{
          x: [50, -50, 50],
          y: [50, 50, 50],
        }}
        transition={{ duration: 30, repeat: Infinity, ease: "easeInOut" }}
        className="absolute bottom-0 left-[20%] size-[450px] rounded-full bg-orange-200 blur-[120px] opacity-20 will-change-transform"
      />
    </div>
  );
}
