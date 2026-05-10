export type AppointmentMeetingMethod = "online" | "in_person"

export type Appointment = {
  date: string
  slot: string
  meeting_method: AppointmentMeetingMethod
}

export class SlotTakenError extends Error {
  code = "SLOT_TAKEN" as const
  constructor(message = "slot_taken") {
    super(message)
    this.name = "SlotTakenError"
  }
}
