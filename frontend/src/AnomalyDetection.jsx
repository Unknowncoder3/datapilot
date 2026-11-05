import { useEffect, useState } from "react";
import { getBusinessAnomalies, getApiErrorMessage } from "./api.js";

const number = (value) => Number(value ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 3 });
const money = (value) => Number(value ?? 0).toLocaleString("en-GB", { style: "currency", currency: "GBP", maximumFractionDigits: 2 });

export default function AnomalyDetection({ dataset }) {
  const [sensitivity, setSensitivity] = useState("3.5");
  const [minPeriods, setMinPeriods] = useState("14");
  const [limit, setLimit] = useState("100");
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [reviewStatuses, setReviewStatuses] = useState({});
  const [reviewFilter, setReviewFilter] = useState("all");

  useEffect(() => {
    if (!dataset?.id) { setReviewStatuses({}); return; }
    try { setReviewStatuses(JSON.parse(localStorage.getItem(`datapilot-anomaly-review-${dataset.id}`) || "{}")); }
    catch { setReviewStatuses({}); }
  }, [dataset?.id]);

  const setReviewStatus = (anomalyId, status) => {
    setReviewStatuses((previous) => {
      const next = { ...previous, [anomalyId]: status };
      try { localStorage.setItem(`datapilot-anomaly-review-${dataset.id}`, JSON.stringify(next)); } catch {}
      return next;
    });
  };

  const load = async () => {
    if (!dataset?.id) { setPayload(null); return; }
    setLoading(true); setError("");
    try {
      const response = await getBusinessAnomalies(dataset.id, {
        sensitivity: Number(sensitivity), minPeriods: Number(minPeriods), limit: Number(limit),
      });
      setPayload(response.data);
    } catch (err) {
      setError(getApiErrorMessage(err, "Could not detect anomalies for this dataset."));
      setPayload(null);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [dataset?.id, sensitivity, minPeriods, limit]);

  const anomalies = payload?.anomalies || [];
  const high = anomalies.filter((item) => item.severity === "high").length;
  const medium = anomalies.filter((item) => item.severity === "medium").length;
  const reviewCounts = { open: anomalies.filter((item) => (reviewStatuses[item.id] || "open") === "open").length, investigating: anomalies.filter((item) => reviewStatuses[item.id] === "investigating").length, resolved: anomalies.filter((item) => reviewStatuses[item.id] === "resolved").length, dismissed: anomalies.filter((item) => reviewStatuses[item.id] === "dismissed").length };
  const visibleAnomalies = anomalies.filter((item) => reviewFilter === "all" || (reviewStatuses[item.id] || "open") === reviewFilter);

  if (!dataset) return <div className="empty-state"><div className="empty-icon">⌁</div><h3>Select a dataset first</h3><p>Upload or select a dataset to run anomaly detection.</p></div>;

  return <section className="anomaly-page">
    <div className="page-heading"><div><div className="eyebrow">PHASE 9 · ANOMALY DETECTION</div><h1>Detect unusual patterns</h1><p>Identify statistical outliers in revenue and transaction fields for review.</p></div>
      <div className="anomaly-dataset-chip"><small>ACTIVE DATASET</small><strong>{dataset.name || dataset.original_filename}</strong><span>{number(dataset.row_count)} rows · {number(dataset.column_count)} columns</span></div>
    </div>

    <div className="anomaly-controls panel-card">
      <label><span>Sensitivity threshold</span><select value={sensitivity} onChange={(e) => setSensitivity(e.target.value)}><option value="2.5">2.5 · More sensitive</option><option value="3.5">3.5 · Balanced</option><option value="4.5">4.5 · Strict</option></select></label>
      <label><span>Minimum observations</span><select value={minPeriods} onChange={(e) => setMinPeriods(e.target.value)}><option value="5">5 observations</option><option value="14">14 observations</option><option value="30">30 observations</option></select></label>
      <label><span>Maximum findings</span><select value={limit} onChange={(e) => setLimit(e.target.value)}><option value="25">25 findings</option><option value="50">50 findings</option><option value="100">100 findings</option><option value="250">250 findings</option></select></label>
      <button className="primary-button" onClick={load} disabled={loading}>{loading ? "Analyzing…" : "↻ Run detection"}</button>
    </div>

    {error && <div className="alert alert-danger">{error}</div>}
    <div className="metric-grid anomaly-metrics">
      <div className="metric-card"><div className="metric-top"><span>Detected findings</span><span className="metric-icon">⌁</span></div><div className="metric-value">{loading ? "…" : number(payload?.anomaly_count)}</div><div className="metric-note">Statistical outliers returned</div></div>
      <div className="metric-card"><div className="metric-top"><span>High severity</span><span className="metric-icon">!</span></div><div className="metric-value anomaly-high">{loading ? "…" : number(high)}</div><div className="metric-note">Prioritize for review</div></div>
      <div className="metric-card"><div className="metric-top"><span>Medium severity</span><span className="metric-icon">◈</span></div><div className="metric-value anomaly-medium">{loading ? "…" : number(medium)}</div><div className="metric-note">Worth inspecting</div></div>
      <div className="metric-card"><div className="metric-top"><span>Method</span><span className="metric-icon">∑</span></div><div className="metric-value anomaly-method">Robust MAD</div><div className="metric-note">Median absolute deviation</div></div>
    </div>

    <div className="panel-card anomaly-results">
      <div className="section-heading inner-heading"><div><h3>Anomaly findings</h3><p>Ranked by robust outlier score · evidence shown for each result</p></div><div className="anomaly-review-toolbar"><select aria-label="Filter review status" value={reviewFilter} onChange={(e) => setReviewFilter(e.target.value)}><option value="all">All findings ({number(anomalies.length)})</option><option value="open">Open ({number(reviewCounts.open)})</option><option value="investigating">Investigating ({number(reviewCounts.investigating)})</option><option value="resolved">Resolved ({number(reviewCounts.resolved)})</option><option value="dismissed">Dismissed ({number(reviewCounts.dismissed)})</option></select><span className="subtle-count">{number(visibleAnomalies.length)} shown</span></div></div>
      {loading ? <div className="empty-inline">Analyzing dataset records…</div> : visibleAnomalies.length ? <div className="anomaly-list">
        {visibleAnomalies.map((item) => {
          const evidence = item.evidence || {};
          const amount = evidence.revenue ?? evidence.value;
          return <article className="anomaly-item" key={item.id}>
            <div className="anomaly-item-top"><span className={`anomaly-severity severity-${item.severity || "medium"}`}>{String(item.severity || "medium").toUpperCase()}</span><span className="anomaly-category">{item.category || "finding"} · score {number(item.score)}</span></div>
            <div className="anomaly-review-title"><h4>{item.title || "Unusual data point"}</h4><span className={`anomaly-review-status status-${reviewStatuses[item.id] || "open"}`}>{(reviewStatuses[item.id] || "open").replace("investigating", "In progress")}</span></div><p>{item.description}</p>
            <div className="anomaly-evidence">
              {evidence.period && <span><small>Period</small><b>{evidence.period}</b></span>}
              {evidence.row_index != null && <span><small>Row index</small><b>{number(evidence.row_index)}</b></span>}
              {evidence.column && <span><small>Field</small><b>{evidence.column}</b></span>}
              {amount != null && <span><small>Observed value</small><b>{evidence.revenue != null ? money(amount) : number(amount)}</b></span>}
              {evidence.baseline_median != null && <span><small>Median baseline</small><b>{evidence.revenue != null ? money(evidence.baseline_median) : number(evidence.baseline_median)}</b></span>}
              {evidence.direction && <span><small>Direction</small><b>{evidence.direction} baseline</b></span>}
              {evidence.robust_z_score != null && <span><small>Robust z-score</small><b>{number(evidence.robust_z_score)}</b></span>}
            </div>
            <div className="anomaly-review-actions">{(reviewStatuses[item.id] || "open") === "open" && <button onClick={() => setReviewStatus(item.id, "investigating")}>Start review</button>}{(reviewStatuses[item.id] || "open") === "investigating" && <button onClick={() => setReviewStatus(item.id, "resolved")}>Mark resolved</button>}{(reviewStatuses[item.id] || "open") !== "dismissed" && <button className="muted-action" onClick={() => setReviewStatus(item.id, "dismissed")}>Dismiss</button>}{["resolved", "dismissed"].includes(reviewStatuses[item.id]) && <button className="muted-action" onClick={() => setReviewStatus(item.id, "open")}>Reopen</button>}</div>\n            {!!item.limitations?.length && <details><summary>Limitations & review notes</summary><ul>{item.limitations.map((note, index) => <li key={index}>{note}</li>)}</ul></details>}
          </article>;
        })}
      </div> : <div className="anomaly-empty"><div>✓</div><h3>{anomalies.length ? "No findings match this review filter" : "No outliers detected at this threshold"}</h3><p>{anomalies.length ? "Change the review status filter to see other findings." : "Try a more sensitive threshold or inspect the unavailable checks below."}</p></div>}
    </div>

    {!!payload?.unavailable_checks?.length && <div className="panel-card anomaly-notes"><h3>Checks unavailable</h3>{payload.unavailable_checks.map((item, index) => <p key={index}><strong>{item.category}:</strong> {item.reason}</p>)}</div>}
    {!!payload?.notes?.length && <div className="panel-card anomaly-notes"><h3>Method notes</h3><ul>{payload.notes.map((note, index) => <li key={index}>{note}</li>)}</ul></div>}
    <p className="anomaly-disclaimer">Anomalies are statistical review signals—not proof of fraud, error, or causation. Verify each finding against the source records before acting.</p>
  </section>;
}
