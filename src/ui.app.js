import { normalizePayload, hasDashContent } from "./ui.payload.js";
import { DashContent, Arrow } from "./ui.components.js";
import { renderChart } from "./ui.charts.js";
import { registerModelPayloadHandler, askModel } from "./ui.api.js";

const e = React.createElement;

export function App() {
  const [messages, setMessages] = React.useState([
    {
      role: "assistant",
      text: "Chào bạn! Hãy hỏi mình bất kỳ thông tin học tập nào.",
    },
  ]);
  const [input, setInput] = React.useState("");
  const [showDash, setShowDash] = React.useState(false);
  const [dashData, setDashData] = React.useState(null);
  const [activeTab, setActiveTab] = React.useState("table");
  const [tIdx, setTIdx] = React.useState(0);
  const [cIdx, setCIdx] = React.useState(0);

  const chartRef = React.useRef(null);
  const chartInst = React.useRef(null);
  const msgEnd = React.useRef(null);

  const appendMessages = (items) => {
    if (!items || !items.length) return;
    setMessages((prev) => [...prev, ...items]);
  };

  const openDashboard = (dashboard) => {
    setDashData(dashboard);
    setShowDash(true);
    setActiveTab("table");
    setTIdx(0);
    setCIdx(0);
  };

  const canOpenDash = hasDashContent(dashData);

  React.useEffect(() => {
    if (!canOpenDash) setShowDash(false);
  }, [canOpenDash]);

  const applyPayload = (payload) => {
    const normalized = normalizePayload(payload);
    if (!normalized) return;
    appendMessages(normalized.messages);
    if (normalized.dashboard) openDashboard(normalized.dashboard);
  };

  React.useEffect(() => {
    const cleanup = registerModelPayloadHandler(applyPayload);
    return () => cleanup();
  }, []);

  React.useEffect(() => {
    msgEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  React.useEffect(() => {
    if (!dashData || !showDash || activeTab !== "chart") {
      if (chartRef.current) {
        Plotly.purge(chartRef.current);
      }
      chartInst.current = null;
      return;
    }
    const charts = dashData.charts || [];

    if (!charts.length) {
      if (chartRef.current) {
        Plotly.purge(chartRef.current);
      }
      chartInst.current = null;
      return;
    }
    const cur = charts[Math.min(cIdx, charts.length - 1)];
    renderChart({ chartRef, chartInst, chart: cur });
  }, [dashData, showDash, activeTab, cIdx]);

  const handleSend = () => {
    const q = input.trim();
    if (!q) return;
    appendMessages([{ role: "user", text: q }]);
    setInput("");
    askModel(q, "session_123").then(applyPayload).catch(console.error);
  };

  return e(
    "div",
    { style: { display: "flex", flexDirection: "column", height: "100%" } },
    e(
      "header",
      { className: "header" },
      e("div", { className: "h-logo" }, "Σ"),
      e("span", { className: "h-title" }, "EduAI Analytics"),
      e("span", { className: "h-badge" }, "Beta"),
    ),
    e(
      "div",
      {
        className: "body-wrap" + (showDash && canOpenDash ? " dash-open" : ""),
      },
      e(
        "div",
        { className: "chat-col" },
        e(
          "div",
          { className: "chat-card" },
          e(
            "div",
            { className: "chat-messages" },
            ...messages.map((m, i) =>
              m.role === "assistant"
                ? e(
                    "div",
                    { key: i, className: "bubble bubble-ai" },
                    e("span", { className: "ai-label" }, "AI"),
                    m.text,
                  )
                : e("div", { key: i, className: "bubble bubble-user" }, m.text),
            ),
            e("div", { ref: msgEnd }),
          ),
          e(
            "div",
            { className: "input-wrap" },
            e("input", {
              className: "chat-input",
              placeholder: "Nhập câu hỏi của bạn…",
              value: input,
              onChange: (ev) => setInput(ev.target.value),
              onKeyDown: (ev) => ev.key === "Enter" && handleSend(),
            }),
            e(
              "button",
              { className: "send-btn", onClick: handleSend },
              e(
                "svg",
                {
                  width: 13,
                  height: 13,
                  viewBox: "0 0 24 24",
                  fill: "none",
                  stroke: "currentColor",
                  strokeWidth: 2.2,
                },
                e("line", { x1: 22, y1: 2, x2: 11, y2: 13 }),
                e("polygon", { points: "22 2 15 22 11 13 2 9 22 2" }),
              ),
              "Gửi",
            ),
          ),
        ),
        canOpenDash
          ? e(
              "button",
              {
                className: "toggle-pill",
                onClick: () => setShowDash((v) => !v),
              },
              Arrow(showDash ? "left" : "right"),
              showDash ? "Ẩn Dashboard" : "Mở Dashboard",
            )
          : null,
      ),
      e("div", { className: "divider" }),
      e(
        "div",
        { className: "dash-panel" },
        e(
          "div",
          { className: "dash-inner" },
          e(DashContent, {
            data: dashData,
            activeTab,
            setActiveTab,
            tIdx,
            setTIdx,
            cIdx,
            setCIdx,
            chartRef,
          }),
        ),
      ),
    ),
  );
}
