import { PALETTE } from "./ui.constants.js";

export function renderChart({ chartRef, chartInst, chart }) {
  if (!chartRef.current) return;

  const labels = Array.isArray(chart.labels) ? chart.labels : [];
  const data = Array.isArray(chart.data) ? chart.data : [];
  const name = chart.name || "Chart";

  const colors = data.map((_, i) => PALETTE[i % PALETTE.length]);
  const borderColors = colors.map((c) => c.replace(".78", "1"));

  const trace = {
    x: labels,
    y: data,
    type: "bar",
    marker: {
      color: colors,
      line: { color: borderColors, width: 1 },
    },
    hovertemplate: "%{x}: %{y}<extra></extra>",
  };

  const layout = {
    title: { text: name, font: { size: 13, color: "#c8d8ff" } },
    margin: { t: 36, r: 14, b: 48, l: 44 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: "#8da0c8", size: 11 },
    xaxis: {
      tickangle: -20,
      automargin: true,
      gridcolor: "rgba(99,140,255,.08)",
      zeroline: false,
      linecolor: "rgba(99,140,255,.2)",
    },
    yaxis: {
      gridcolor: "rgba(99,140,255,.08)",
      zeroline: false,
      linecolor: "rgba(99,140,255,.2)",
      tickformat: "~s",
    },
    bargap: 0.35,
  };

  const config = { displayModeBar: false, responsive: true };

  Plotly.react(chartRef.current, [trace], layout, config);
  chartInst.current = true;
}
