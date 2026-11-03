import { useEffect, useState } from "react";
import { getAdvancedDashboard, getApiErrorMessage } from "./api.js";

const money = (value) => {
  if (value == null || !Number.isFinite(Number(value))) return "—";
  const n = Number(value), abs = Math.abs(n), sign = n < 0 ? "-£" : "£";
  if (abs >= 1e6) return `${sign}${(abs / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${sign}${(abs / 1e3).toFixed(1)}K`;
  return n.toLocaleString("en-GB", { style: "currency", currency: "GBP", maximumFractionDigits: 2 });
};
const number = (value) => value == null ? "—" : Number(value).toLocaleString("en-IN", { maximumFractionDigits: 0 });
const titleCase = (text) => String(text || "").replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());

function BarList({ items = [], nameKey, maxRows = 10, format = money, accent = "blue" }) {
  const list = items.slice(0, maxRows);
  const max = Math.max(1, ...list.map((item) => Math.abs(Number(item.revenue ?? item.value ?? 0))));
  return <div className={`adv-bar-list adv-${accent}`}>{list.map((item, index) => {
    const value = Number(item.revenue ?? item.value ?? 0);
    return <div className="adv-bar-item" key={item[nameKey] ?? index}>
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
function QuarterChart({ items = [] }) {
  if (!items.length) return <div className="adv-empty">No quarter/date data available.</div>;
  const max = Math.max(1, ...items.map((item) => Math.abs(Number(item.revenue ?? item.value ?? 0))));
  return <div className="adv-quarter-chart">{items.map((item, index) => { const value = Number(item.revenue ?? item.value ?? 0); return <div className="adv-quarter-column" key={item.quarter ?? index}><span>{money(value)}</span><i style={{height:`${Math.max(3, Math.abs(value)/max*100)}%`}}/><b>{item.quarter}</b></div>; })}</div>;
}

export default function ExecutiveDashboard({ dataset }) {
  const [dashboard, setDashboard] = useState(null);
  const [country, setCountry] = useState("All");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!dataset?.id) { setDashboard(null); return; }
    let active = true;
    setLoading(true); setError("");
    const params = {};
    if (country && country !== "All") params.country = country;
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    getAdvancedDashboard(dataset.id, params)
      .then((response) => { if (active) setDashboard(response?.data?.data ?? response?.data ?? null); })
      .catch((err) => { if (active) setError(getApiErrorMessage(err, "Unable to load advanced dashboard data.")); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [dataset?.id, country, startDate, endDate]);

  if (!dataset?.id) return <div className="empty-state"><div className="empty-icon">✦</div><h3>Select a dataset first</h3><p>Choose a dataset to build an advanced BI dashboard.</p></div>;

  const kpis = dashboard?.kpis || [];
  const periodLabel = startDate || endDate ? `${startDate || "Dataset start"} — ${endDate || "Dataset end"}` : "All available dates";
  return <section className="executive-bi advanced-bi">
    <header className="adv-header">
      <div><div className="adv-eyebrow"><span /> DATA PILOT / ANALYTICAL WORKSPACE</div><h1>Online Sales Dashboard</h1><p>Explore performance, revenue drivers, and customer behavior across your data.</p></div>
      <div className="adv-filter-panel">
        <label><span>Country</span><select value={country} onChange={(e) => setCountry(e.target.value)}><option value="All">All countries</option>{(dashboard?.countries || []).map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
        <label><span>Invoice date · from</span><input type="date" value={startDate} min={dashboard?.date_min || undefined} max={endDate || dashboard?.date_max || undefined} onChange={(e) => setStartDate(e.target.value)} /></label>
        <label><span>Invoice date · to</span><input type="date" value={endDate} min={startDate || dashboard?.date_min || undefined} max={dashboard?.date_max || undefined} onChange={(e) => setEndDate(e.target.value)} /></label>
        <button type="button" onClick={() => { setCountry("All"); setStartDate(""); setEndDate(""); }} className="adv-reset">Reset filters</button>
      </div>
    </header>
    <div className="adv-dashboard-status"><span className={loading ? "adv-status-loading" : "adv-status-dot"} />{loading ? "Updating visuals…" : `Dataset loaded · ${number(dashboard?.dataset_rows)} filtered rows`}<span className="adv-status-period">{periodLabel}</span></div>
    {error && <div className="alert alert-warning">{error}<button className="text-button ms-2" onClick={() => { setCountry(country); }}>Retry by changing a filter</button></div>}
    <div className="adv-kpi-grid">{kpis.map((item, i) => <article className={`adv-kpi-card adv-kpi-${i}`} key={item.label}><div className="adv-kpi-label">{item.label}</div><div className="adv-kpi-value">{item.format === "currency" ? money(item.value) : number(item.value)}</div><div className="adv-kpi-bottom"><span />Dataset calculated metric</div></article>)}</div>
    <div className="adv-chart-grid">
      <article className="adv-panel adv-panel-wide"><div className="adv-panel-head"><div><span>REVENUE PERFORMANCE</span><h2>Monthly revenue trend</h2><p>Net revenue by month</p></div><strong className="adv-panel-tag">TREND</strong></div><TrendChart items={dashboard?.monthly_revenue || []} /></article>
      <article className="adv-panel"><div className="adv-panel-head"><div><span>MARKET DISTRIBUTION</span><h2>Revenue mix by country</h2><p>Click a slice or legend item to cross-filter the dashboard</p></div><strong className="adv-panel-tag">DONUT · INTERACTIVE</strong></div><DonutChart items={dashboard?.country_revenue || []} nameKey="country" selected={country !== "All" ? country : null} onSelect={(value) => setCountry(country === value ? "All" : value)} label="Revenue by country" /></article>
      <article className="adv-panel"><div className="adv-panel-head"><div><span>PRODUCT PERFORMANCE</span><h2>Top 10 products by revenue</h2><p>Best performing product descriptions</p></div><strong className="adv-panel-tag">PRODUCTS</strong></div><BarList items={dashboard?.product_revenue || []} nameKey="product" accent="teal" /></article>
      <article className="adv-panel"><div className="adv-panel-head"><div><span>CUSTOMER INTELLIGENCE</span><h2>Customer segment mix</h2><p>Revenue contribution by inferred segment</p></div><strong className="adv-panel-tag">DONUT</strong></div><DonutChart items={dashboard?.customer_segments || []} nameKey="segment" label="Revenue by customer segment" /></article>
      <article className="adv-panel"><div className="adv-panel-head"><div><span>TIME ANALYSIS</span><h2>Quarterly revenue</h2><p>Compare seasonal performance</p></div><strong className="adv-panel-tag">COLUMNS</strong></div><QuarterChart items={dashboard?.quarterly_revenue || []} /></article>
      <article className="adv-panel adv-panel-wide"><div className="adv-panel-head"><div><span>WEEKLY PATTERN</span><h2>Revenue by day of week</h2><p>Identify strongest transaction days</p></div><strong className="adv-panel-tag">WEEKDAYS</strong></div><BarList items={dashboard?.weekday_revenue || []} nameKey="day" accent="orange" /></article>
    </div>
    <footer className="adv-footer">DataPilot Advanced BI · Metrics recalculate when filters change. Customer segments are inferred from relative recency, order frequency, and revenue; they are not source dataset labels.</footer>
  </section>;
}
