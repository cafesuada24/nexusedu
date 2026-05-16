import { AdvisorScheduleRead, WorkingHoursCreate, DayOffCreate } from "./api";
import { Schedule, WeekSchedule, Override, DayKey, DAYS, DEFAULT_SCHEDULE } from "./schedule";

export function parseDateToDDMMYYYY(dateString: string): string {
  if (!dateString) return "";
  const parts = dateString.split("-");
  if (parts.length !== 3) return dateString;
  return `${parts[2]}/${parts[1]}/${parts[0]}`;
}

export function parseDDMMYYYYToDate(ddmmyyyy: string): string {
  const parts = ddmmyyyy.split("/");
  if (parts.length !== 3) return ddmmyyyy;
  return `${parts[2]}-${parts[1]}-${parts[0]}`;
}

export function backendToFrontend(be: AdvisorScheduleRead): Schedule {
  const week: WeekSchedule = {
    mon: { enabled: false, slots: [] },
    tue: { enabled: false, slots: [] },
    wed: { enabled: false, slots: [] },
    thu: { enabled: false, slots: [] },
    fri: { enabled: false, slots: [] },
    sat: { enabled: false, slots: [] },
    sun: { enabled: false, slots: [] },
  };

  const groupedByDay: Record<number, any[]> = {};
  for (const wh of be.working_hours) {
    if (!groupedByDay[wh.day_of_week]) {
      groupedByDay[wh.day_of_week] = [];
    }
    groupedByDay[wh.day_of_week].push(wh);
  }

  for (const d of DAYS) {
    const whs = groupedByDay[d.apiDay] || [];
    if (whs.length > 0) {
      week[d.key].enabled = true;
      whs.sort((a, b) => a.start_time.localeCompare(b.start_time));
      week[d.key].slots = whs.map((wh) => ({
        id: wh.id,
        from: wh.start_time.substring(0, 5),
        to: wh.end_time.substring(0, 5),
      }));
    }
  }

  const overrides: Override[] = be.days_off.map((doff) => {
    let type: "off" | "custom" = "off";
    let note = doff.reason || "";
    if (note.startsWith("[CUSTOM] ")) {
      type = "custom";
      note = note.replace("[CUSTOM] ", "");
    }
    return {
      id: doff.id,
      date: parseDateToDDMMYYYY(doff.date),
      type,
      note,
    };
  });

  return {
    ...DEFAULT_SCHEDULE,
    week,
    overrides,
  };
}

export function generateDiffCommands(
  prevBe: AdvisorScheduleRead,
  nextFe: Schedule,
) {
  const commands = {
    addWorkingHours: [] as WorkingHoursCreate[],
    deleteWorkingHours: [] as string[],
    addDayOff: [] as DayOffCreate[],
    deleteDayOff: [] as string[],
  };

  // Build target working hours
  const targetWhs: Array<{
    day_of_week: number;
    start_time: string;
    end_time: string;
    timezone: string;
  }> = [];

  for (const d of DAYS) {
    const dayConfig = nextFe.week[d.key];
    if (dayConfig.enabled) {
      for (const slot of dayConfig.slots) {
        targetWhs.push({
          day_of_week: d.apiDay,
          start_time: `${slot.from}:00`,
          end_time: `${slot.to}:00`,
          timezone: nextFe.timezone,
        });
      }
    }
  }

  // Find deletions and matching existing ones
  for (const beWh of prevBe.working_hours) {
    const match = targetWhs.find(
      (t) =>
        t.day_of_week === beWh.day_of_week &&
        t.start_time === beWh.start_time &&
        t.end_time === beWh.end_time
    );

    if (!match) {
      commands.deleteWorkingHours.push(beWh.id);
    }
  }

  // Find additions
  for (const t of targetWhs) {
    const isExisting = prevBe.working_hours.some(
      (beWh) =>
        beWh.day_of_week === t.day_of_week &&
        beWh.start_time === t.start_time &&
        beWh.end_time === t.end_time
    );
    if (!isExisting) {
      commands.addWorkingHours.push({
        day_of_week: t.day_of_week,
        start_time: t.start_time,
        end_time: t.end_time,
        timezone: t.timezone,
      });
    }
  }

  // Build target days off
  const targetDaysOff: Array<{
    date: string;
    reason: string;
    id: string;
  }> = [];

  for (const ov of nextFe.overrides) {
    targetDaysOff.push({
      date: parseDDMMYYYYToDate(ov.date),
      reason: ov.type === "custom" ? `[CUSTOM] ${ov.note}` : ov.note,
      id: ov.id,
    });
  }

  // Find deletions for days off
  for (const beDo of prevBe.days_off) {
    const match = targetDaysOff.find(
      (t) =>
        t.id === beDo.id ||
        (t.date === beDo.date && t.reason === (beDo.reason || ""))
    );
    if (!match) {
      commands.deleteDayOff.push(beDo.id);
    }
  }

  // Find additions for days off
  for (const t of targetDaysOff) {
    const isExisting = prevBe.days_off.some(
      (beDo) =>
        beDo.id === t.id ||
        (beDo.date === t.date && (beDo.reason || "") === t.reason)
    );
    if (!isExisting) {
      commands.addDayOff.push({
        date: t.date,
        reason: t.reason,
      });
    }
  }

  return commands;
}
