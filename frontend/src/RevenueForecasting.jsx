import { useEffect, useMemo, useState } from "react";
import { getRevenueForecast } from "./api.js";

const money = (value) => Number(value || 0).toLocaleString("en-GB", {
  style: "currency", currency: "GBP", maximumFractionDigits: 0,
});
const unwrap = (response) => response?.data?.data ?? response?.data ?? {};

function ForecastChart({ data }) {
  const historical = data?.historical || [];
  const forecast = data?.forecast || [];
  const all = [
    ...historical.map((item) => ({ period: item.period, value: item.actual })),
    ...forecast.map((item) => ({ period: item.period, value: item.prediction })),
  ];
  if (!all.length) return null;
  const bounds = [
    ...historical.map((item) => item.actual),
    ...forecast.flatMap((item) => [item.lower_bound, item.upper_bound, item.prediction]),
  ];
  const min = Math.min(...bounds);
  const max = Math.max(...bounds);
  const range = max - min || 1;
  const width = 900, height = 320, left = 58, right = 20, top = 18, bottom = 42;
  const x = (index) => left + (index / Math.max(all.length - 1, 1)) * (width - left - right);
  const y = (value) => top + ((max - value) / range) * (height - top - bottom);
  const historicalPath = historical.map((item, index) => `${index ? "L" : "M"} ${x(index)} ${y(item.actual)}`).join(" ");
  const forecastPath = forecast.map((item, index) => {
    const globalIndex = historical.length + index;
    return `${index ? "L" : "M"} ${x(globalIndex)} ${y(item.prediction)}`;
  }).join(" ");
  const bandTop = forecast.map((item, index) => `${index ? "L" : "M"} ${x(historical.length + index)} ${y(item.upper_bound)}`).join(" ");
  const bandBottom = forecast.slice().reverse().map((item, reverseIndex) => {
    const index = forecast.length - 1 - reverseIndex;
    return `L ${x(historical.length + index)} ${y(item.lower_bound)}`;
  }).join(" ");
  const labels = [all[0], all[Math.floor((all.length - 1) / 2)], all[all.length - 1]];
  return <div className="forecast-chart-wrap">
    <svg className="forecast-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Historical revenue and forecast with uncertainty band">
      {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
        const value = max - ratio * range;
        const yy = top + ratio * (height - top - bottom);
        return <g key={ratio}><line x1={left} x2={width - right} y1={yy} y2={yy} className="forecast-gridline"/><text x={left - 8} y={yy + 4} textAnchor="end" className="forecast-axis-label">{money(value)}</text></g>;
      })}
      {forecast.length > 0 && <path d={`${bandTop} ${bandBottom} Z`} className="forecast-band"/>}
      <path d={historicalPath} className="forecast-actual-line"/>
      <path d={forecastPath} className="forecast-prediction-line"/>
      <line x1={x(historical.length - 1)} x2={x(historical.length - 1)} y1={top} y2={height - bottom} className="forecast-divider"/>
      {labels.map((item, index) => <text key={item.period} x={x(all.findIndex((entry) => entry.period === item.period))} y={height - 12} textAnchor={index === 0 ? "start" : index === 2 ? "end" : "middle"} className="forecast-axis-label">{item.period}</text>)}
    </svg>
    <div className="forecast-legend"><span><i className="forecast-legend-actual"/>Historical actual</span><span><i className="forecast-legend-prediction"/>Forecast</span><span><i className="forecast-legend-band"/>Approx. uncertainty band</span></div>
  </div>;
}

export default function RevenueForecasting({ dataset }) {
  const [frequency, setFrequency] = useState("month");
  const [horizon, setHorizon] = useState(6);
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!dataset?.id) { setForecast(null); return; }
    let active = true;
    setLoading(true);
    setError("");
    getRevenueForecast(dataset.id, { horizon: Number(horizon), frequency })
      .then((response) => { if (active) setForecast(unwrap(response)); })
      .catch((err) => { if (active) setError(err.response?.data?.detail || "Unable to generate a revenue forecast for this dataset."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [dataset?.id, frequency, horizon]);

  const stats = useMemo(() => {
    const predictions = forecast?.forecast || [];
    const total = predictions.reduce((sum, item) => sum + Number(item.prediction || 0), 0);
    const avg = predictions.length ? total / predictions.length : 0;
    const first = predictions[0]?.prediction;
    const last = predictions[predictions.length - 1]?.prediction;
    const change = first && last ? ((last - first) / Math.abs(first)) * 100 : null;
    return { total, avg, change, last };
  }, [forecast]);

  return <section className="forecast-page">
    <div className="page-heading forecast-heading"><div><div className="eyebrow">PHASE 8 · PREDICTIVE ANALYTICS</div><h1>Revenue Forecasting</h1><p>Explore historical performance and a transparent revenue forecast for your selected dataset.</p></div><div className="forecast-controls">
      <label>Period<select value={frequency} onChange={(event) => setFrequency(event.target.value)}><option value="month">Monthly</option><option value="day">Daily</option></select></label>
      <label>Forecast horizon<select value={horizon} onChange={(event) => setHorizon(Number(event.target.value))}>{[3, 6, 9, 12, 18, 24].map((value) => <option key={value} value={value}>{value} periods</option>)}</select></label>
    </div></div>
    {!dataset && <div className="panel-card">Select or upload a dataset to begin forecasting.</div>}
    {loading && <div className="panel-card forecast-message">Generating forecast…</div>}
    {error && <div className="panel-card forecast-error">{error}</div>}
    {!loading && forecast && <>
      <div className="forecast-kpis">
        <div className="panel-card"><span className="eyebrow">FORECAST TOTAL</span><strong>{money(stats.total)}</strong><small>Across {forecast.forecast_horizon} future periods</small></div>
        <div className="panel-card"><span className="eyebrow">AVERAGE PER PERIOD</span><strong>{money(stats.avg)}</strong><small>Mean predicted revenue</small></div>
        <div className="panel-card"><span className="eyebrow">LAST PERIOD ESTIMATE</span><strong>{money(stats.last)}</strong><small>{forecast.forecast?.at(-1)?.period || "—"}</small></div>
        <div className="panel-card"><span className="eyebrow">MODEL</span><strong className="forecast-model-label">{forecast.model === "linear_trend_with_additive_seasonality" ? "Trend + seasonality" : "Linear trend baseline"}</strong><small>{forecast.historical_periods} historical periods analyzed</small></div>
      </div>
      <div className="panel-card forecast-visual-card"><div className="forecast-card-heading"><div><span className="eyebrow">ACTUAL VS PREDICTED</span><h2>Revenue trend & outlook</h2></div><span className="forecast-pill">{forecast.frequency === "month" ? "Monthly" : "Daily"} · {forecast.forecast_horizon} periods</span></div><ForecastChart data={forecast}/></div>
      <div className="panel-card forecast-table-card"><div className="forecast-card-heading"><div><span className="eyebrow">FORECAST DETAILS</span><h2>Predicted revenue by period</h2></div></div><div className="table-responsive"><table className="table forecast-table"><thead><tr><th>Period</th><th>Prediction</th><th>Lower bound</th><th>Upper bound</th></tr></thead><tbody>{forecast.forecast.map((item) => <tr key={item.period}><td>{item.period}</td><td>{money(item.prediction)}</td><td>{money(item.lower_bound)}</td><td>{money(item.upper_bound)}</td></tr>)}</tbody></table></div></div>
      <div className="panel-card forecast-notes"><h3>Model notes</h3><ul>{(forecast.notes || []).map((note, index) => <li key={index}>{note}</li>)}</ul></div>
    </>}
  </section>;
}
