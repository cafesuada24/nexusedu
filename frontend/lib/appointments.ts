export type AppointmentMode = "video" | "inperson"

export type Appointment = {
  id: string
  advisorToken: string
  caseId: string
  date: string
  slot: string
  mode: AppointmentMode
  createdAt: number
}

export type CreateAppointmentInput = Omit<Appointment, "id" | "createdAt">

export class SlotTakenError extends Error {
  code = "SLOT_TAKEN" as const
  constructor(message = "slot_taken") {
    super(message)
    this.name = "SlotTakenError"
  }
}
