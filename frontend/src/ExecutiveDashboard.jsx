import { useEffect, useState } from "react";
import { getAdvancedDashboard, getApiErrorMessage, askBusinessQuestion } from "./api.js";

const money = (value) => {
  if (value == null || !Number.isFinite(Number(value))) return "—";
  const n = Number(value), abs = Math.abs(n), sign = n < 0 ? "-£" : "£";
  if (abs >= 1e6) return `${sign}${(abs / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${sign}${(abs / 1e3).toFixed(1)}K`;
  return n.toLocaleString("en-GB", { style: "currency", currency: "GBP", maximumFractionDigits: 2 });
};
const number = (value) => value == null ? "—" : Number(value).toLocaleString("en-IN", { maximumFractionDigits: 0 });
const titleCase = (text) => String(text || "").replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());

function BarList({ items = [], nameKey, maxRows = 10, format = money, accent = "blue", onSelect, selected = null }) {
  const list = items.slice(0, maxRows);
  const max = Math.max(1, ...list.map((item) => Math.abs(Number(item.revenue ?? item.value ?? 0))));
  return <div className={`adv-bar-list adv-${accent}`}>{list.map((item, index) => {
    const value = Number(item.revenue ?? item.value ?? 0);
    return <div className={`adv-bar-item ${selected === item[nameKey] ? "adv-selected" : ""} ${onSelect ? "adv-clickable" : ""}`} key={item[nameKey] ?? index} role={onSelect ? "button" : undefined} tabIndex={onSelect ? 0 : undefined} onClick={onSelect ? () => onSelect(item[nameKey]) : undefined} onKeyDown={onSelect ? (e) => { if (e.key === "Enter" || e.key === " ") onSelect(item[nameKey]); } : undefined}>
      <div className="adv-bar-label"><span title={item[nameKey]}>{item[nameKey]}</span><b>{format(value)}</b></div>
      <div className="adv-bar-track"><i style={{ width: `${Math.max(1.5, Math.abs(value) / max * 100)}%` }} /></div>
    </div>;
  })}{!list.length && <div className="adv-empty">No data available for this breakdown.</div>}</div>;
}

function TrendChart({ items = [] }) {
  if (!items.length) return <div className="adv-empty">No date field was detected for this dataset.</div>;
  const values = items.map((item) => Number(item.revenue || 0));
  const max = Math.max(1, ...values), min = Math.min(0, ...values), range = Math.max(1, max - min);
  const points = values.map((v, i) => `${22 + i * (656 / Math.max(1, values.length - 1))},${210 - ((v - min) / range) * 175}`);
  return <div className="adv-line-chart">
    <svg viewBox="0 0 700 245" role="img" aria-label="Monthly revenue line chart" preserveAspectRatio="none">
      {[35, 78, 122, 166, 210].map((y) => <line key={y} x1="20" x2="680" y1={y} y2={y} className="adv-gridline" />)}
      <polyline points={points.join(" ")} className="adv-line-area" />
      <polyline points={points.join(" ")} className="adv-line-path" />
      {points.map((p, i) => { const [x,y] = p.split(","); return <circle key={i} cx={x} cy={y} r="3.2" className="adv-line-point"><title>{items[i].period}: {money(values[i])}</title></circle>; })}
    </svg>
    <div className="adv-line-labels">{items.map((item, i) => <span key={i}>{item.period}</span>)}</div>
  </div>;
}


const DONUT_COLORS = ["#7889ff", "#46c6b6", "#ffad55", "#fa7e91", "#b99aff", "#5ba8ff", "#e4c65a", "#d47eb4", "#7ed08b", "#ff8d62"];
function DonutChart({ items = [], nameKey, onSelect, selected = null, label = "Revenue mix" }) {
  const values = items.slice(0, 8).map((item) => Math.max(0, Number(item.revenue ?? item.value ?? 0)));
  const total = values.reduce((sum, value) => sum + value, 0);
  if (!items.length || total <= 0) return <div className="adv-empty">No category data available.</div>;
  let cursor = 0;
  const arcs = items.slice(0, 8).map((item, index) => {
    const value = values[index], start = cursor / total * Math.PI * 2;
    cursor += value;
    const end = cursor / total * Math.PI * 2;
    const point = (angle, radius) => [100 + Math.sin(angle) * radius, 100 - Math.cos(angle) * radius];
    const [sx, sy] = point(start, 72), [ex, ey] = point(end, 72);
    const large = end - start > Math.PI ? 1 : 0;
    const path = value >= total ? "M100 28 A72 72 0 1 1 99.99 28" : `M ${sx} ${sy} A72 72 0 ${large} 1 ${ex} ${ey}`;
    return { item, value, path, color: DONUT_COLORS[index % DONUT_COLORS.length], index };
  });
  return <div className="adv-donut-layout"><div className="adv-donut-wrap"><svg viewBox="0 0 200 200" role="img" aria-label={label}>{arcs.map((arc) => <path key={arc.index} d={arc.path} fill="none" stroke={arc.color} strokeWidth="25" strokeLinecap="butt" opacity={selected && selected !== arc.item[nameKey] ? .28 : 1} className={onSelect ? "adv-donut-slice" : ""} onClick={onSelect ? () => onSelect(arc.item[nameKey]) : undefined} tabIndex={onSelect ? 0 : undefined} role={onSelect ? "button" : undefined}><title>{arc.item[nameKey]}: {money(arc.value)} · click to filter</title></path>)}</svg><div className="adv-donut-center"><b>{items.length}</b><span>categories</span></div></div><div className="adv-donut-legend">{arcs.map((arc) => <button type="button" key={arc.index} onClick={onSelect ? () => onSelect(arc.item[nameKey]) : undefined} className={selected && selected !== arc.item[nameKey] ? "is-muted" : ""} disabled={!onSelect}><i style={{background:arc.color}}/><span>{arc.item[nameKey]}</span><b>{money(arc.value)}</b></button>)}</div></div>;
}
function QuarterChart({ items = [], onSelect, selected = null }) {
  if (!items.length) return <div className="adv-empty">No quarter/date data available.</div>;
  const max = Math.max(1, ...items.map((item) => Math.abs(Number(item.revenue ?? item.value ?? 0))));
  return <div className="adv-quarter-chart">{items.map((item, index) => { const value = Number(item.revenue ?? item.value ?? 0); return <div className={`adv-quarter-column ${selected === item.quarter ? "adv-selected" : ""} ${onSelect ? "adv-clickable" : ""}`} key={item.quarter ?? index} role={onSelect ? "button" : undefined} tabIndex={onSelect ? 0 : undefined} onClick={onSelect ? () => onSelect(item.quarter) : undefined} onKeyDown={onSelect ? (e) => { if (e.key === "Enter" || e.key === " ") onSelect(item.quarter); } : undefined}><span>{money(value)}</span><i style={{height:`${Math.max(3, Math.abs(value)/max*100)}%`}}/><b>{item.quarter}</b></div>; })}</div>;
}

export default function ExecutiveDashboard({ dataset, onDashboardData }) {
  const [dashboard, setDashboard] = useState(null);
  const [country, setCountry] = useState("All");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [product, setProduct] = useState("");
  const [quarter, setQuarter] = useState("");
  const [weekday, setWeekday] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [askText, setAskText] = useState("");
  const [askLoading, setAskLoading] = useState(false);
  const [askError, setAskError] = useState("");
  const [askResult, setAskResult] = useState(null);
  const [layoutEditing, setLayoutEditing] = useState(false);
  const [draggingPanel, setDraggingPanel] = useState("");
  const [layoutReady, setLayoutReady] = useState(false);
  const defaultPanelOrder = ["monthly", "country", "products", "segments", "quarterly", "weekday"];
  const [panelOrder, setPanelOrder] = useState(defaultPanelOrder);

  useEffect(() => {
    setLayoutReady(false);
    try {
      const saved = window.localStorage.getItem(`datapilot-bi-layout-${dataset?.id}`);
      const parsed = saved ? JSON.parse(saved) : null;
      setPanelOrder(Array.isArray(parsed) && parsed.length === defaultPanelOrder.length &&
        defaultPanelOrder.every((id) => parsed.includes(id)) ? parsed : defaultPanelOrder);
    } catch {
      setPanelOrder(defaultPanelOrder);
    } finally {
      setLayoutReady(true);
    }
  }, [dataset?.id]);

  useEffect(() => {
    if (!dataset?.id || !layoutReady) return;
    window.localStorage.setItem(`datapilot-bi-layout-${dataset.id}`, JSON.stringify(panelOrder));
  }, [dataset?.id, layoutReady, panelOrder]);

  const movePanel = (panelId, direction) => {
    setPanelOrder((current) => {
      const index = current.indexOf(panelId), target = index + direction;
      if (index < 0 || target < 0 || target >= current.length) return current;
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  };
  const resetPanelLayout = () => setPanelOrder(defaultPanelOrder);

  useEffect(() => {
    if (!dataset?.id) { setDashboard(null); return; }
    let active = true;
    setLoading(true); setError("");
    const params = {};
    if (country && country !== "All") params.country = country;
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    if (product) params.product = product;
    if (quarter) params.quarter = quarter;
    if (weekday) params.weekday = weekday;
    getAdvancedDashboard(dataset.id, params)
      .then((response) => { if (active) setDashboard(response?.data?.data ?? response?.data ?? null); })
      .catch((err) => { if (active) setError(getApiErrorMessage(err, "Unable to load advanced dashboard data.")); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [dataset?.id, country, startDate, endDate, product, quarter, weekday]);

  useEffect(() => { onDashboardData?.(dashboard); }, [dashboard, onDashboardData]);

  if (!dataset?.id) return <div className="empty-state"><div className="empty-icon">✦</div><h3>Select a dataset first</h3><p>Choose a dataset to build an advanced BI dashboard.</p></div>;

  const kpis = dashboard?.kpis || [];
  const periodLabel = startDate || endDate ? `${startDate || "Dataset start"} — ${endDate || "Dataset end"}` : "All available dates";
  const clearFilters = () => { setCountry("All"); setStartDate(""); setEndDate(""); setProduct(""); setQuarter(""); setWeekday(""); };
  const exportCsv = () => {
    const rows = [
      ...kpis.map((item) => ({ section: "KPI", category: item.label, value: item.value })),
      ...(dashboard?.country_revenue || []).map((item) => ({ section: "Country revenue", category: item.country, value: item.revenue })),
      ...(dashboard?.product_revenue || []).map((item) => ({ section: "Product revenue", category: item.product, value: item.revenue })),
      ...(dashboard?.monthly_revenue || []).map((item) => ({ section: "Monthly revenue", category: item.period, value: item.revenue })),
      ...(dashboard?.quarterly_revenue || []).map((item) => ({ section: "Quarterly revenue", category: item.quarter, value: item.revenue })),
      ...(dashboard?.weekday_revenue || []).map((item) => ({ section: "Weekday revenue", category: item.day, value: item.revenue })),
      ...(dashboard?.customer_segments || []).map((item) => ({ section: "Customer segment", category: item.segment, value: item.revenue })),
    ];
    const quote = (value) => `"${String(value ?? "").replaceAll("\"", "\"\"")}"`;
    const csv = ["Section,Category,Value", ...rows.map((row) => [row.section, row.category, row.value].map(quote).join(","))].join("\r\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob); const link = document.createElement("a");
    link.href = url; link.download = `${(dataset.name || "datapilot-dashboard").replace(/[^a-z0-9-_]/gi, "-")}-filtered.csv`;
    link.click(); URL.revokeObjectURL(url);
  };
  return <section className="executive-bi advanced-bi">
    <header className="adv-header">
      <div><div className="adv-eyebrow"><span /> DATA PILOT / ANALYTICAL WORKSPACE</div><h1>Online Sales Dashboard</h1><p>Explore performance, revenue drivers, and customer behavior across your data.</p></div>
      <div className="adv-filter-panel">
        <label><span>Country</span><select value={country} onChange={(e) => setCountry(e.target.value)}><option value="All">All countries</option>{(dashboard?.countries || []).map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
        <label><span>Invoice date · from</span><input type="date" value={startDate} min={dashboard?.date_min || undefined} max={endDate || dashboard?.date_max || undefined} onChange={(e) => setStartDate(e.target.value)} /></label>
        <label><span>Invoice date · to</span><input type="date" value={endDate} min={startDate || dashboard?.date_min || undefined} max={dashboard?.date_max || undefined} onChange={(e) => setEndDate(e.target.value)} /></label>
        <button type="button" onClick={clearFilters} className="adv-reset">Reset filters</button>
      </div>
      <div className="adv-export-actions"><button type="button" onClick={exportCsv} className="adv-export-button">↓ Export CSV</button></div>
    </header>
    <div className="adv-dashboard-status"><span className={loading ? "adv-status-loading" : "adv-status-dot"} />{loading ? "Updating visuals…" : `Dataset loaded · ${number(dashboard?.dataset_rows)} filtered rows`}<span className="adv-status-period">{periodLabel}</span></div>
    <section className="adv-ai-ask" aria-label="Ask DataPilot">
      <div className="adv-ai-ask-head"><div><span className="adv-ai-kicker">✦ AI DATA ASSISTANT</span><h2>Ask your data a question</h2><p>Get a dataset-grounded answer with a quick breakdown.</p></div><span className="adv-ai-chip">NATURAL LANGUAGE</span></div>
      <form className="adv-ai-ask-form" onSubmit={async (event) => { event.preventDefault(); if (!askText.trim() || askLoading) return; setAskLoading(true); setAskError(""); setAskResult(null); try { const response = await askBusinessQuestion(dataset.id, askText.trim()); setAskResult(response.data); } catch (err) { setAskError(getApiErrorMessage(err)); } finally { setAskLoading(false); } }}>
        <input value={askText} onChange={(event) => setAskText(event.target.value)} placeholder="e.g. Which country generated the highest revenue?" aria-label="Ask a question about the dataset" maxLength={500}/>
        <button type="submit" disabled={askLoading || !askText.trim()}>{askLoading ? "Analyzing…" : "✦ Ask DataPilot"}</button>
      </form>
      <div className="adv-ai-suggestions">{["Which country generated the highest revenue?","Show the top products by sales","How many unique customers are there?","What is the total revenue?"].map((sample) => <button type="button" key={sample} onClick={() => setAskText(sample)}>{sample}</button>)}</div>
      {askError && <div className="adv-ai-error" role="alert">{askError}</div>}
      {askResult && <div className="adv-ai-answer"><div className="adv-ai-answer-label"><span>✦ ANSWER</span><small>{number(askResult.rows_analyzed)} rows analyzed · Dataset source</small></div><p>{askResult.answer}</p>{askResult.metric && <div className="adv-ai-metric"><span>{askResult.metric.label}</span><strong>{askResult.metric.format === "currency" ? money(askResult.metric.value) : number(askResult.metric.value)}</strong></div>}{askResult.chart?.data?.length > 0 && <div className="adv-ai-chart-list"><h3>{askResult.chart.title}</h3>{askResult.chart.data.map((item,index) => { const max=Math.max(1,...askResult.chart.data.map(row=>Math.abs(Number(row.value)||0))); return <div className="adv-ai-chart-row" key={item.label}><span title={item.label}>{item.label}</span><i><b style={{width:`${Math.max(2,Math.abs(Number(item.value)||0)/max*100)}%`}}/></i><strong>{askResult.chart.metric === "revenue" ? money(item.value) : number(item.value)}</strong></div>; })}</div>}</div>}
    </section>
    {error && <div className="alert alert-warning">{error}<button className="text-button ms-2" onClick={() => { setCountry(country); }}>Retry by changing a filter</button></div>}
    <div className="adv-kpi-grid">{kpis.map((item, i) => <article className={`adv-kpi-card adv-kpi-${i}`} key={item.label}><div className="adv-kpi-label">{item.label}</div><div className="adv-kpi-value">{item.format === "currency" ? money(item.value) : number(item.value)}</div><div className="adv-kpi-bottom"><span />Dataset calculated metric</div></article>)}</div>
    <div className="adv-layout-toolbar">
      <div><span className="adv-layout-spark">✦</span><div><strong>Dashboard layout</strong><small>{layoutEditing ? "Rearrange panels with drag-and-drop or arrow controls." : "Customize the chart order to match your workflow."}</small></div></div>
      <div className="adv-layout-actions">
        {layoutEditing && <button type="button" onClick={resetPanelLayout} className="adv-layout-reset">Reset layout</button>}
        <button type="button" onClick={() => { setLayoutEditing((value) => !value); setDraggingPanel(""); }} className={`adv-layout-toggle ${layoutEditing ? "is-active" : ""}`}>{layoutEditing ? "✓ Done editing" : "↕ Customize layout"}</button>
      </div>
    </div>
    <div className={`adv-chart-grid ${layoutEditing ? "adv-layout-editing" : ""}`}>
      {panelOrder.map((panelId, index) => {
        const panelProps = {
          draggable: layoutEditing,
          onDragStart: (event) => { setDraggingPanel(panelId); event.dataTransfer.effectAllowed = "move"; event.dataTransfer.setData("text/plain", panelId); },
          onDragOver: (event) => { if (layoutEditing) event.preventDefault(); },
          onDrop: (event) => {
            event.preventDefault();
            const source = event.dataTransfer.getData("text/plain") || draggingPanel;
            if (!source || source === panelId) return;
            setPanelOrder((current) => {
              const next = [...current], from = next.indexOf(source), to = next.indexOf(panelId);
              if (from < 0 || to < 0) return current;
              next.splice(from, 1); next.splice(to, 0, source); return next;
            });
            setDraggingPanel("");
          },
          onDragEnd: () => setDraggingPanel(""),
          className: `adv-panel ${["monthly", "weekday"].includes(panelId) ? "adv-panel-wide" : ""} ${layoutEditing ? "adv-layout-panel" : ""} ${draggingPanel === panelId ? "adv-panel-dragging" : ""}`,
          key: panelId
        };
        const controls = layoutEditing && <div className="adv-panel-layout-controls" aria-label={`Reorder ${panelId} panel`}>
          <span>⠿ Move</span><button type="button" disabled={index === 0} onClick={() => movePanel(panelId, -1)} aria-label="Move panel up">↑</button><button type="button" disabled={index === panelOrder.length - 1} onClick={() => movePanel(panelId, 1)} aria-label="Move panel down">↓</button>
        </div>;
        const panelContent = {
          monthly: <><div className="adv-panel-head"><div><span>REVENUE PERFORMANCE</span><h2>Monthly revenue trend</h2><p>Net revenue by month</p></div><strong className="adv-panel-tag">TREND</strong></div><TrendChart items={dashboard?.monthly_revenue || []} /></>,
          country: <><div className="adv-panel-head"><div><span>MARKET DISTRIBUTION</span><h2>Revenue mix by country</h2><p>Click a slice or legend item to cross-filter the dashboard</p></div><strong className="adv-panel-tag">DONUT · INTERACTIVE</strong></div><DonutChart items={dashboard?.country_revenue || []} nameKey="country" selected={country !== "All" ? country : null} onSelect={(value) => setCountry(country === value ? "All" : value)} label="Revenue by country" /></>,
          products: <><div className="adv-panel-head"><div><span>PRODUCT PERFORMANCE</span><h2>Top 10 products by revenue</h2><p>Best performing product descriptions</p></div><strong className="adv-panel-tag">PRODUCTS</strong></div><BarList items={dashboard?.product_revenue || []} nameKey="product" accent="teal" selected={product || null} onSelect={(value) => setProduct(product === value ? "" : value)} /></>,
          segments: <><div className="adv-panel-head"><div><span>CUSTOMER INTELLIGENCE</span><h2>Customer segment mix</h2><p>Revenue contribution by inferred segment</p></div><strong className="adv-panel-tag">DONUT</strong></div><DonutChart items={dashboard?.customer_segments || []} nameKey="segment" label="Revenue by customer segment" /></>,
          quarterly: <><div className="adv-panel-head"><div><span>TIME ANALYSIS</span><h2>Quarterly revenue</h2><p>Compare seasonal performance</p></div><strong className="adv-panel-tag">COLUMNS</strong></div><QuarterChart items={dashboard?.quarterly_revenue || []} selected={quarter || null} onSelect={(value) => setQuarter(quarter === value ? "" : value)} /></>,
          weekday: <><div className="adv-panel-head"><div><span>WEEKLY PATTERN</span><h2>Revenue by day of week</h2><p>Identify strongest transaction days</p></div><strong className="adv-panel-tag">WEEKDAYS</strong></div><BarList items={dashboard?.weekday_revenue || []} nameKey="day" accent="orange" selected={weekday || null} onSelect={(value) => setWeekday(weekday === value ? "" : value)} /></>
        };
        return <article {...panelProps}>{controls}{panelContent[panelId]}</article>;
      })}
    </div>
    <footer className="adv-footer">DataPilot Advanced BI · Metrics recalculate when filters change. Customer segments are inferred from relative recency, order frequency, and revenue; they are not source dataset labels.</footer>
  </section>;
}
