export const normalizeMessages = (messages) => {
  if (!Array.isArray(messages)) return [];
  return messages
    .filter((m) => m && m.role && m.text)
    .map((m) => ({ role: m.role, text: String(m.text) }));
};

export const normalizeDashboard = (dashboard) => {
  if (!dashboard) return null;
  const text = typeof dashboard.text === "string" ? dashboard.text : "";
  const tables = Array.isArray(dashboard.tables) ? dashboard.tables : [];
  const charts = Array.isArray(dashboard.charts) ? dashboard.charts : [];
  if (!text && tables.length === 0 && charts.length === 0) return null;
  return { text, tables, charts };
};

const normalizeModelOutput = (payload) => {
  const messages = [];
  if (payload?.query) {
    messages.push({ role: "user", text: String(payload.query) });
  }
  if (payload?.answer) {
    messages.push({ role: "assistant", text: String(payload.answer) });
  }

  const tables = Array.isArray(payload?.tables)
    ? payload.tables.map((rows, idx) => {
        const safeRows = Array.isArray(rows) ? rows : [];
        const columns =
          safeRows.length > 0 ? Object.keys(safeRows[0]) : ["value"];
        return {
          name: `Table ${idx + 1}`,
          columns,
          rows: safeRows,
        };
      })
    : [];

  let charts = [];
  const vis = Array.isArray(payload?.visualizations)
    ? payload.visualizations
    : [];
  if (vis.length > 0 && Array.isArray(vis[0]?.data) && vis[0].data.length > 0) {
    const trace = vis[0].data[0] || {};
    const labels = Array.isArray(trace.x) ? trace.x : [];
    const data = Array.isArray(trace.y) ? trace.y : [];
    const name =
      vis[0]?.layout?.title?.text || vis[0]?.layout?.title || "Chart 1";
    if (labels.length && data.length) {
      charts = [{ name, labels, data }];
    }
  }

  if (charts.length === 0 && tables.length > 0) {
    const rows = tables[0].rows || [];
    const hasGrade =
      rows.length > 0 && "grade" in rows[0] && "student_id" in rows[0];
    if (hasGrade) {
      charts = [
        {
          name: "Grades",
          labels: rows.map((r) => r.student_id),
          data: rows.map((r) => r.grade),
        },
      ];
    }
  }

  const dashboard = normalizeDashboard({
    text: payload?.answer || "",
    tables,
    charts,
  });

  return { messages, dashboard };
};

export const normalizePayload = (payload) => {
  if (!payload) return { messages: [], dashboard: null };
  const isModelOutput =
    "answer" in payload || "tables" in payload || "visualizations" in payload;
  if (isModelOutput) return normalizeModelOutput(payload);
  return {
    messages: normalizeMessages(payload?.messages),
    dashboard: normalizeDashboard(payload?.dashboard),
  };
};

export const hasDashContent = (dashboard) =>
  dashboard &&
  Array.isArray(dashboard.tables) &&
  dashboard.tables.length > 0 &&
  Array.isArray(dashboard.charts) &&
  dashboard.charts.length > 0;
