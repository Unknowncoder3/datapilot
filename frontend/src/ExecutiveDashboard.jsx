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
  if (value == null) return "—";
  if (typeof value === "number") return value.toLocaleString("en-IN", { maximumFractionDigits: 2 });
  return String(value);
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

  useEffect(() => {
    if (!dataset?.id) { setPayload({ kpis: null, trends: null, countries: null, insights: null }); return; }
    let active = true;
    setLoading(true); setError("");
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
    if (Array.isArray(source)) return source.map((item, index) => ({ label: labelOf(item, `Metric ${index + 1}`), value: valueOf(item) ?? item?.formatted_value ?? item?.formatted ?? item?.value ?? "—", note: item?.description ?? item?.unit ?? "" }));
    if (source && typeof source === "object") return Object.entries(source).filter(([, value]) => typeof value === "number" || typeof value === "string").slice(0, 8).map(([key, value]) => ({ label: key.replaceAll("_", " "), value: pretty(value), note: "" }));
    return [];
  }, [payload.kpis]);

  const trendItems = useMemo(() => asArray(payload.trends?.trends ?? payload.trends?.data ?? payload.trends?.series ?? payload.trends).map((item, index) => ({ label: labelOf(item, `Period ${index + 1}`), value: valueOf(item) })).filter((item) => item.value != null), [payload.trends]);
  const countryItems = useMemo(() => asArray(payload.countries?.countries ?? payload.countries?.data ?? payload.countries).slice(0, 8), [payload.countries]);
  const insightItems = useMemo(() => asArray(payload.insights?.insights ?? payload.insights?.items ?? payload.insights).slice(0, 5), [payload.insights]);
  const maxTrend = Math.max(1, ...trendItems.map((item) => Math.abs(item.value)));

  if (!dataset?.id) return <div className="empty-state"><div className="empty-icon">✦</div><h3>Select a dataset first</h3><p>Choose a dataset from Analytics to load executive business metrics.</p></div>;

  return <section className="executive-bi">
    <div className="page-heading"><div><div className="eyebrow">PHASE 5.2 · EXECUTIVE VIEW</div><h1>Executive dashboard</h1><p>Business performance snapshot for <strong>{dataset.name || dataset.original_filename}</strong>.</p></div><div className="d-flex align-items-center gap-2"><label className="small text-secondary" htmlFor="bi-frequency">Trend</label><select id="bi-frequency" className="form-select dataset-select" value={frequency} onChange={(e) => setFrequency(e.target.value)}><option value="month">Monthly</option><option value="day">Daily</option></select></div></div>
    {loading && <div className="upload-progress">Loading business intelligence metrics…</div>}
    {error && <div className="alert alert-warning">{error}<button className="text-button ms-2" onClick={() => setFrequency((current) => current)}>Retry</button></div>}
    <div className="metric-grid">
      {kpiItems.slice(0, 8).map((metric, index) => <div className="metric-card" key={metric.label}><div className="metric-top"><span>{metric.label}</span><span className="metric-icon">{["↗","◈","▦","∑"][index % 4]}</span></div><div className="metric-value">{pretty(metric.value)}</div><div className="metric-note">{metric.note || "Business KPI"}</div></div>)}
      {!loading && !kpiItems.length && <div className="panel-card"><p className="metric-note">KPI metrics were not returned for this dataset.</p></div>}
    </div>
    <div className="bottom-grid">
      <div className="panel-card"><div className="panel-title"><div><h3>Sales trend</h3><p>{frequency === "month" ? "Monthly" : "Daily"} business performance</p></div><span className="panel-symbol">↗</span></div>
        {trendItems.length ? <div className="bi-chart" role="img" aria-label="Sales trend bar visualization">{trendItems.slice(-16).map((item, index) => <div className="bi-bar-column" key={item.label + index}><div className="bi-bar-value">{pretty(item.value)}</div><div className="bi-bar-track"><div className="bi-bar" style={{ height: `${Math.max(4, Math.abs(item.value) / maxTrend * 100)}%` }} /></div><small>{item.label}</small></div>)}</div> : <div className="empty-inline">{loading ? "Loading trend…" : "Trend data is unavailable or has no numeric points."}</div>}
      </div>
      <div className="panel-card"><div className="panel-title"><div><h3>Sales by country</h3><p>Leading markets in this dataset</p></div><span className="panel-symbol">◎</span></div>
        {countryItems.length ? <div className="bi-list">{countryItems.map((item, index) => <div className="bi-list-row" key={labelOf(item, index)}><span><b>{index + 1}</b>{labelOf(item, `Country ${index + 1}`)}</span><strong>{pretty(valueOf(item) ?? item?.formatted_value ?? "—")}</strong></div>)}</div> : <div className="empty-inline">{loading ? "Loading markets…" : "Country breakdown is unavailable."}</div>}
      </div>
    </div>
    <div className="panel-card mt-3"><div className="panel-title"><div><h3>Automated business insights</h3><p>Rule-based observations generated from the selected dataset</p></div><span className="panel-symbol">✧</span></div>
      {insightItems.length ? <div className="bi-insights">{insightItems.map((item, index) => <div className="bi-insight" key={item.id ?? index}><span className="bi-insight-mark">✦</span><div><strong>{item.title ?? item.name ?? item.headline ?? `Insight ${index + 1}`}</strong><p>{item.description ?? item.message ?? item.insight ?? item.summary ?? (typeof item === "string" ? item : "Insight details were not provided.")}</p>{item.severity && <small>{String(item.severity).toUpperCase()}</small>}</div></div>)}</div> : <div className="empty-inline">{loading ? "Generating insights…" : "No insights were returned for this dataset."}</div>}
    </div>
    <p className="metric-note mt-3">Metrics and observations are generated from the selected dataset. Treat automated insights as analytical signals, not causal conclusions.</p>
  </section>;
}
