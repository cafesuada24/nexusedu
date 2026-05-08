"use client"

import { motion } from "framer-motion"
import { Sparkles } from "lucide-react"
import { CASE_STUDIES, CaseStudyCard } from "@/components/dashboard/success-case-studies"

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
}

const item = {
  hidden: { y: 20, opacity: 0 },
  show: { y: 0, opacity: 1 },
}

export default function StoriesPage() {
  return (
    <div className="flex w-full flex-1 flex-col gap-6">
      <div className="flex items-center gap-3">
        <div className="grid size-10 place-items-center rounded-xl bg-success/10 text-success ring-1 ring-success/20 shadow-sm shadow-success/10">
          <Sparkles className="size-5" />
        </div>
        <div className="flex flex-col">
          <h1 className="font-serif text-2xl font-bold tracking-tight md:text-3xl">
            Câu chuyện thành công
          </h1>
          <p className="text-sm text-muted-foreground">
            Những bước tiến vượt bậc của sinh viên đồng hành cùng{" "}
            <span className="mx-1 font-semibold text-primary">NexusEdu</span>
          </p>
        </div>
      </div>

      <div
        aria-hidden
        className="h-px w-full bg-gradient-to-r from-success/40 via-success/10 to-transparent"
      />

      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="flex flex-col gap-4"
      >
        {CASE_STUDIES.map((c) => (
          <motion.div key={c.id} variants={item}>
            <CaseStudyCard data={c} />
          </motion.div>
        ))}
      </motion.div>
    </div>
  )
}
