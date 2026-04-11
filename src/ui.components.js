import { RISK_CLS } from "./ui.constants.js";

const e = React.createElement;

export function TabBtn({ label, active, onClick }) {
  return e(
    "button",
    { className: "tab-btn" + (active ? " active" : ""), onClick },
    label,
  );
}

export function SubtabBtn({ label, active, onClick }) {
  return e(
    "button",
    { className: "subtab-btn" + (active ? " active" : ""), onClick },
    label,
  );
}

export function DataTable({ table }) {
  if (!table) return null;
  return e(
    "div",
    { className: "table-wrap" },
    e(
      "table",
      null,
      e(
        "thead",
        null,
        e("tr", null, ...table.columns.map((c, i) => e("th", { key: i }, c))),
      ),
      e(
        "tbody",
        null,
        ...table.rows.map((row, ri) =>
          e(
            "tr",
            { key: ri },
            ...table.columns.map((col, ci) => {
              const val = row[col] ?? "—";
              const cls = col === "Rủi ro" ? RISK_CLS[val] || "" : "";
              return e("td", { key: ci, className: cls }, val);
            }),
          ),
        ),
      ),
    ),
  );
}

export function DashContent({
  data,
  activeTab,
  setActiveTab,
  tIdx,
  setTIdx,
  cIdx,
  setCIdx,
  chartRef,
}) {
  if (!data) {
    return e(
      "div",
      { className: "empty-dash" },
      e("div", { className: "empty-icon" }, "📊"),
      e("span", null, "Gửi câu hỏi để tải dashboard"),
    );
  }

  return e(
    React.Fragment,
    null,
    e(
      "div",
      { className: "tab-bar" },
      e("span", { className: "tab-section-title" }, "Dashboard"),
      e(
        "div",
        { className: "tabs" },
        e(TabBtn, {
          label: "Table",
          active: activeTab === "table",
          onClick: () => setActiveTab("table"),
        }),
        e(TabBtn, {
          label: "Chart",
          active: activeTab === "chart",
          onClick: () => setActiveTab("chart"),
        }),
      ),
    ),
    e("div", { className: "insight-card" }, data.text),
    e(
      "div",
      { className: "subtab-bar" },
      ...(activeTab === "table" ? data.tables : data.charts).map((item, i) =>
        e(SubtabBtn, {
          key: i,
          label: item.name,
          active: (activeTab === "table" ? tIdx : cIdx) === i,
          onClick: () => (activeTab === "table" ? setTIdx(i) : setCIdx(i)),
        }),
      ),
    ),
    activeTab === "table"
      ? e(DataTable, { table: data.tables[tIdx] })
      : e(
          "div",
          { className: "chart-wrap" },
          e("div", { className: "chart-canvas-wrap", ref: chartRef }),
        ),
  );
}

export function Arrow(dir) {
  return e(
    "svg",
    {
      width: 14,
      height: 14,
      viewBox: "0 0 24 24",
      fill: "none",
      stroke: "currentColor",
      strokeWidth: 2.3,
      strokeLinecap: "round",
      strokeLinejoin: "round",
    },
    dir === "right"
      ? e("polyline", { points: "9 18 15 12 9 6" })
      : e("polyline", { points: "15 18 9 12 15 6" }),
  );
}

export function Markdown({ content }) {
  if (!content) return null;
  const html = marked.parse(content, { breaks: true, gfm: true });
  return e("div", {
    className: "markdown-body",
    dangerouslySetInnerHTML: { __html: html },
  });
}
