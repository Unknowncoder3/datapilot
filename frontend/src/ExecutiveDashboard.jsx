import { useEffect, useMemo, useState } from "react";
import {
  getBusinessKpis,
  getSalesTrends,
  getSalesByCountry,
  getBusinessInsights,
  getApiErrorMessage,
} from "./api.js";

const unwrap = (response) => response?.data?.data ?? response?.data ?? {};
const asArray = (value) => Array.isArray(value) ? value : Array.isArray(value?.items) ? value.items : Array.isArray(value?.results) ? value.results : [];
const pretty = (value) => {
  if (value == null || value === "") return "—";
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return String(value);
  const absValue = Math.abs(numericValue);
  const sign = numericValue < 0 ? "-" : "";
  if (absValue >= 1_000_000) return `${sign}${(absValue / 1_000_000).toFixed(2)}M`;
  if (absValue >= 10_000) return `${sign}${(absValue / 1_000).toFixed(1)}K`;
  return numericValue.toLocaleString("en-IN", { maximumFractionDigits: 2 });
};
const currency = (value) => {
  if (value == null || value === "") return "—";
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return String(value);
  const absValue = Math.abs(numericValue);
  const sign = numericValue < 0 ? "-£" : "£";
  if (absValue >= 1_000_000) return `${sign}${(absValue / 1_000_000).toFixed(2)}M`;
  if (absValue >= 1_000) return `${sign}${(absValue / 1_000).toFixed(1)}K`;
  return numericValue.toLocaleString("en-GB", { style: "currency", currency: "GBP", maximumFractionDigits: 2 });
};
const labelOf = (item, fallback) => item?.label ?? item?.name ?? item?.metric ?? item?.period ?? item?.month ?? item?.country ?? item?.title ?? fallback;
const valueOf = (item) => {
  if (typeof item === "number") return item;
  if (!item || typeof item !== "object") return null;
  for (const key of ["value", "total", "revenue", "sales", "count", "amount", "net_revenue", "customers"]) {
    if (typeof item[key] === "number") return item[key];
  }
  return null;
};

export default function ExecutiveDashboard({ dataset }) {
  const [payload, setPayload] = useState({ kpis: null, trends: null, countries: null, insights: null });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [frequency, setFrequency] = useState("month");

  const loadDashboard = () => {
    if (!dataset?.id) return;
    setLoading(true);
    setError("");
    Promise.all([
      getBusinessKpis(dataset.id),
      getSalesTrends(dataset.id, frequency),
      getSalesByCountry(dataset.id, 8),
      getBusinessInsights(dataset.id, 5),
    ]).then(([k, t, c, i]) => {
      setPayload({ kpis: unwrap(k), trends: unwrap(t), countries: unwrap(c), insights: unwrap(i) });
    }).catch((err) => setError(getApiErrorMessage(err, "Could not load executive BI data for this dataset.")))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (!dataset?.id) { setPayload({ kpis: null, trends: null, countries: null, insights: null }); return; }
    let active = true;
    setLoading(true);
    setError("");
    Promise.all([
      getBusinessKpis(dataset.id),
      getSalesTrends(dataset.id, frequency),
      getSalesByCountry(dataset.id, 8),
      getBusinessInsights(dataset.id, 5),
    ]).then(([k, t, c, i]) => {
      if (active) setPayload({ kpis: unwrap(k), trends: unwrap(t), countries: unwrap(c), insights: unwrap(i) });
    }).catch((err) => { if (active) setError(getApiErrorMessage(err, "Could not load executive BI data for this dataset.")); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [dataset?.id, frequency]);

  const kpiItems = useMemo(() => {
    const source = payload.kpis?.kpis ?? payload.kpis?.metrics ?? payload.kpis;
    if (Array.isArray(source)) return source.map((item, index) => ({
      label: labelOf(item, `Metric ${index + 1}`),
      value: valueOf(item) ?? item?.formatted_value ?? item?.formatted ?? item?.value ?? "—",
      note: item?.description ?? item?.unit ?? "",
    }));
    if (source && typeof source === "object") return Object.entries(source)
      .filter(([, value]) => typeof value === "number" || typeof value === "string")
      .slice(0, 8).map(([key, value]) => ({ label: key.replaceAll("_", " "), value: pretty(value), note: "" }));
    return [];
  }, [payload.kpis]);

  const trendItems = useMemo(() => asArray(payload.trends?.trends ?? payload.trends?.data ?? payload.trends?.series ?? payload.trends)
    .map((item, index) => ({ label: labelOf(item, `Period ${index + 1}`), value: valueOf(item) }))
    .filter((item) => item.value != null), [payload.trends]);
  const countryItems = useMemo(() => asArray(payload.countries?.countries ?? payload.countries?.data ?? payload.countries).slice(0, 8), [payload.countries]);
  const insightItems = useMemo(() => asArray(payload.insights?.insights ?? payload.insights?.items ?? payload.insights).slice(0, 6), [payload.insights]);
  const maxTrend = Math.max(1, ...trendItems.map((item) => Math.abs(item.value)));
  const maxCountry = Math.max(1, ...countryItems.map((item) => Math.abs(valueOf(item) ?? 0)));

  if (!dataset?.id) return <div className="empty-state"><div className="empty-icon">✦</div><h3>Select a dataset first</h3><p>Choose a dataset from Analytics to load executive business metrics.</p></div>;

  return <section className="executive-bi executive-bi-pro">
    <div className="bi-hero">
      <div>
        <div className="bi-kicker"><span className="bi-live-dot" /> EXECUTIVE INTELLIGENCE <span className="bi-kicker-divider">/</span> OVERVIEW</div>
        <h1>Business performance</h1>
        <p>Explore the signals shaping <strong>{dataset.name || dataset.original_filename}</strong>.</p>
      </div>
      <div className="bi-toolbar">
        <div className="bi-dataset-chip"><span className="bi-dataset-glyph">▤</span><span><small>ACTIVE DATASET</small><strong>{dataset.name || dataset.original_filename}</strong></span></div>
        <label className="bi-period-control" htmlFor="bi-frequency"><span>Period</span><select id="bi-frequency" value={frequency} onChange={(e) => setFrequency(e.target.value)}><option value="month">Monthly</option><option value="day">Daily</option></select></label>
        <button className="bi-refresh" type="button" onClick={loadDashboard} title="Refresh dashboard" disabled={loading}>↻</button>
      </div>
    </div>

    {loading && <div className="bi-loading-line"><span />Refreshing analytical workspace…</div>}
    {error && <div className="alert alert-warning">{error}<button className="text-button ms-2" onClick={loadDashboard}>Retry</button></div>}

    <div className="bi-section-caption"><span>PERFORMANCE SNAPSHOT</span><span className="bi-caption-note">Dataset-derived metrics</span></div>
    <div className="metric-grid bi-kpi-grid">
      {kpiItems.slice(0, 8).map((metric, index) => <article className={`metric-card bi-kpi-card bi-kpi-${index % 4}`} key={metric.label}>
        <div className="bi-kpi-head"><span>{metric.label}</span><span className="bi-kpi-icon">{["↗", "◈", "▦", "∑"][index % 4]}</span></div>
        <div className="bi-kpi-value">{pretty(metric.value)}</div>
        <div className="bi-kpi-foot"><span className="bi-kpi-foot-dot" />{metric.note || "Calculated from selected dataset"}</div>
        <div className="bi-kpi-accent" />
      </article>)}
      {!loading && !kpiItems.length && <div className="panel-card"><p className="metric-note">KPI metrics were not returned for this dataset.</p></div>}
    </div>

    <div className="bi-section-caption bi-analysis-caption"><span>REVENUE & MARKET ANALYSIS</span><span className="bi-caption-note">Interactive period selection</span></div>
    <div className="bi-analysis-grid">
      <article className="panel-card bi-trend-panel">
        <div className="bi-panel-heading"><div><span className="bi-panel-overline">REVENUE MOVEMENT</span><h3>Sales trend</h3><p>{frequency === "month" ? "Month-over-month" : "Day-by-day"} performance across the selected period</p></div><span className="bi-panel-icon">⌁</span></div>
        {trendItems.length ? <div className="bi-chart-pro" role="img" aria-label="Sales trend bar visualization">
          <div className="bi-chart-gridlines"><span>{currency(maxTrend)}</span><span>{currency(maxTrend * .75)}</span><span>{currency(maxTrend * .5)}</span><span>{currency(maxTrend * .25)}</span><span>£0</span></div>
          <div className="bi-chart-columns">{trendItems.slice(-16).map((item, index) => <div className="bi-chart-column" key={item.label + index} title={`${item.label}: ${currency(item.value)}`}>
            <span className="bi-chart-tooltip-value">{currency(item.value)}</span><div className="bi-chart-bar-wrap"><div className="bi-chart-bar" style={{ height: `${Math.max(2, Math.abs(item.value) / maxTrend * 100)}%` }} /></div><small>{item.label}</small>
          </div>)}</div>
        </div> : <div className="empty-inline">{loading ? "Loading trend…" : "Trend data is unavailable or has no numeric points."}</div>}
        <div className="bi-chart-footer"><span><i className="bi-legend-dot" /> Revenue</span><span>{trendItems.length} {frequency === "month" ? "periods" : "days"} represented</span></div>
      </article>

      <article className="panel-card bi-market-panel">
        <div className="bi-panel-heading"><div><span className="bi-panel-overline">GEOGRAPHIC MIX</span><h3>Sales by country</h3><p>Top markets ranked by sales</p></div><span className="bi-panel-icon">◎</span></div>
        {countryItems.length ? <div className="bi-market-list">{countryItems.map((item, index) => {
          const amount = valueOf(item) ?? 0;
          return <div className="bi-market-row" key={labelOf(item, index)}>
            <div className="bi-market-meta"><span className="bi-market-rank">{String(index + 1).padStart(2, "0")}</span><span className="bi-market-name">{labelOf(item, `Country ${index + 1}`)}</span><strong>{currency(amount || item?.formatted_value || "—")}</strong></div>
            <div className="bi-market-track"><span style={{ width: `${Math.max(2, Math.abs(amount) / maxCountry * 100)}%` }} /></div>
          </div>;
        })}</div> : <div className="empty-inline">{loading ? "Loading markets…" : "Country breakdown is unavailable."}</div>}
        <div className="bi-market-footer">Showing {countryItems.length} leading markets</div>
      </article>
    </div>

    <article className="panel-card bi-insights-panel">
      <div className="bi-panel-heading"><div><span className="bi-panel-overline">AUTOMATED ANALYSIS</span><h3>Business insights</h3><p>Rule-based observations generated from the selected dataset</p></div><span className="bi-panel-icon">✧</span></div>
      {insightItems.length ? <div className="bi-insights-pro">{insightItems.map((item, index) => <div className="bi-insight-pro" key={item.id ?? index}>
        <div className="bi-insight-number">{String(index + 1).padStart(2, "0")}</div><div className="bi-insight-body"><div className="bi-insight-title">{item.title ?? item.name ?? item.headline ?? `Insight ${index + 1}`}</div><p>{item.description ?? item.message ?? item.insight ?? item.summary ?? (typeof item === "string" ? item : "Insight details were not provided.")}</p>{item.severity && <span className={`bi-severity bi-severity-${String(item.severity).toLowerCase()}`}>{String(item.severity).toUpperCase()}</span>}</div><span className="bi-insight-arrow">↗</span>
      </div>)}</div> : <div className="empty-inline">{loading ? "Generating insights…" : "No insights were returned for this dataset."}</div>}
    </article>
    <p className="bi-disclaimer">All metrics and observations are calculated from the selected dataset. Automated insights are analytical signals, not causal conclusions.</p>
  </section>;
}
