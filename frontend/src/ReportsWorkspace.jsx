import { useCallback, useEffect, useMemo, useState } from "react";
import { createReport, deleteReport, getDatasetReports, getReport, getApiErrorMessage } from "./api.js";

const fmtDate = (value) => value ? new Date(value).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "—";
const fmtNum = (value) => typeof value === "number" ? value.toLocaleString("en-IN", { maximumFractionDigits: 4 }) : String(value ?? "—");
const titleCase = (value) => String(value || "").replaceAll("_", " ").replace(/\b\w/g, (s) => s.toUpperCase());

function ReportValue({ value }) {
  if (value == null || typeof value !== "object") return <span>{fmtNum(value)}</span>;
  if (Array.isArray(value)) {
    if (!value.length) return <span className="report-muted">No values</span>;
    if (value.every((item) => item == null || typeof item !== "object")) return <div className="report-chips">{value.map((item, i) => <span key={i}>{fmtNum(item)}</span>)}</div>;
    return <div className="report-nested-list">{value.slice(0, 30).map((item, i) => <div className="report-nested-item" key={i}><ReportValue value={item}/></div>)}{value.length > 30 && <small>Showing first 30 entries</small>}</div>;
  }
  const entries = Object.entries(value);
  if (!entries.length) return <span className="report-muted">Empty</span>;
  return <div className="report-object">{entries.map(([key, item]) => <div className="report-object-row" key={key}><span className="report-object-key">{titleCase(key)}</span><div className="report-object-value"><ReportValue value={item}/></div></div>)}</div>;
}

function ReportCard({ report, onOpen, onDelete }) {
  return <article className="report-history-card">
    <div className="report-history-icon">▤</div>
    <div className="report-history-main"><strong>{report.title || "Untitled report"}</strong><div className="report-history-meta"><span className={`report-type-tag report-type-${report.report_type || "summary"}`}>{titleCase(report.report_type || "summary")}</span><span>{fmtDate(report.created_at || report.content?.generated_at)}</span></div></div>
    <div className="report-history-actions"><button className="report-action-button" onClick={() => onOpen(report)} title="View report">View ↗</button><button className="report-delete-button" onClick={() => onDelete(report)} title="Delete report">×</button></div>
  </article>;
}

export default function ReportsWorkspace({ dataset }) {
  const [reports, setReports] = useState([]);
  const [title, setTitle] = useState("");
  const [reportType, setReportType] = useState("summary");
  const [activeReport, setActiveReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadReports = useCallback(async () => {
    if (!dataset?.id) { setReports([]); return; }
    setLoading(true); setError("");
    try {
      const response = await getDatasetReports(dataset.id);
      const data = response.data?.data ?? response.data;
      setReports(Array.isArray(data) ? data : data?.reports || []);
    } catch (err) { setError(getApiErrorMessage(err, "Unable to load report history.")); }
    finally { setLoading(false); }
  }, [dataset?.id]);

  useEffect(() => { setActiveReport(null); setTitle(""); loadReports(); }, [loadReports]);

  const handleGenerate = async (event) => {
    event.preventDefault();
    if (!dataset?.id || generating) return;
    setGenerating(true); setError(""); setNotice("");
    try {
      const response = await createReport(dataset.id, { title: title.trim() || `${dataset.name || dataset.original_filename || "Dataset"} · ${titleCase(reportType)} report`, report_type: reportType });
      const created = response.data?.data ?? response.data;
      setNotice("Report generated and saved successfully.");
      setActiveReport(created);
      setTitle("");
      await loadReports();
    } catch (err) { setError(getApiErrorMessage(err, "Report generation failed.")); }
    finally { setGenerating(false); }
  };

  const handleOpen = async (report) => {
    setError("");
    try {
      const response = await getReport(report.id);
      setActiveReport(response.data?.data ?? response.data);
    } catch (err) { setError(getApiErrorMessage(err, "Unable to open this report.")); }
  };

  const handleDelete = async (report) => {
    if (!window.confirm(`Delete report “${report.title || "Untitled report"}”? This cannot be undone.`)) return;
    setError(""); setNotice("");
    try {
      await deleteReport(report.id);
      if (String(activeReport?.id) === String(report.id)) setActiveReport(null);
      setNotice("Report deleted.");
      await loadReports();
    } catch (err) { setError(getApiErrorMessage(err, "Unable to delete this report.")); }
  };

  const reportContent = activeReport?.content ?? activeReport?.report_content ?? {};
  const overview = reportContent?.overview || {};
  const qualityItems = useMemo(() => Object.entries(reportContent?.data_quality || reportContent?.quality_profile || {}).slice(0, 12), [reportContent]);
  const stats = reportContent?.descriptive_statistics || reportContent?.statistics || {};
  const numericCols = overview.numeric_columns || [];
  const datasetLabel = dataset?.name || dataset?.original_filename || "Selected dataset";

  if (!dataset) return <div className="reports-page"><div className="empty-state"><div className="empty-icon">▤</div><h3>Select a dataset first</h3><p>Choose or upload a dataset in the Datasets section to generate reports.</p></div></div>;

  return <section className="reports-page">
    <div className="page-heading reports-heading"><div><div className="eyebrow">DOCUMENT INTELLIGENCE</div><h1>Automated reports</h1><p>Generate, revisit, and manage structured analysis reports.</p></div><div className="report-dataset-chip"><small>ACTIVE DATASET</small><strong>{datasetLabel}</strong><span>{fmtNum(dataset.row_count)} rows · {fmtNum(dataset.column_count)} columns</span></div></div>

    {error && <div className="report-alert report-alert-error"><span>{error}</span><button onClick={() => setError("")}>×</button></div>}
    {notice && <div className="report-alert report-alert-success"><span>{notice}</span><button onClick={() => setNotice("")}>×</button></div>}

    <div className="reports-top-grid">
      <form className="panel-card report-generator" onSubmit={handleGenerate}>
        <div className="report-section-kicker">CREATE NEW</div><h2>Build a report</h2><p>Choose the depth of analysis, then save it to your report library.</p>
        <label className="report-form-label">Report title <span>Optional</span><input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={120} placeholder={`${datasetLabel} analysis report`}/></label>
        <div className="report-type-options">
          <label className={reportType === "summary" ? "selected" : ""}><input type="radio" name="reportType" value="summary" checked={reportType === "summary"} onChange={() => setReportType("summary")}/><span className="report-type-option-icon">✧</span><span><strong>Summary</strong><small>Overview, data quality, descriptive stats</small></span></label>
          <label className={reportType === "full" ? "selected" : ""}><input type="radio" name="reportType" value="full" checked={reportType === "full"} onChange={() => setReportType("full")}/><span className="report-type-option-icon">▤</span><span><strong>Full report</strong><small>Summary plus correlations and row preview</small></span></label>
        </div>
        <button className="primary-button report-generate-button" type="submit" disabled={generating}>{generating ? <><span className="report-button-spinner"/>Generating report…</> : "✦ Generate report"}</button>
      </form>
      <div className="panel-card report-library"><div className="report-library-heading"><div><div className="report-section-kicker">SAVED OUTPUTS</div><h2>Report history</h2><p>Reports created for this dataset.</p></div><span className="report-count">{reports.length}</span></div>
        {loading ? <div className="report-empty-state"><span className="report-button-spinner"/>Loading reports…</div> : reports.length ? <div className="report-history-list">{reports.map((report) => <ReportCard key={report.id} report={report} onOpen={handleOpen} onDelete={handleDelete}/>)}</div> : <div className="report-empty-state"><div>▤</div><strong>No reports yet</strong><span>Generate your first report to see it here.</span></div>}
        <button className="report-refresh-button" onClick={loadReports} disabled={loading}>↻ Refresh history</button>
      </div>
    </div>

    {activeReport && <section className="report-viewer panel-card">
      <div className="report-viewer-heading"><div><div className="report-section-kicker">REPORT PREVIEW</div><h2>{activeReport.title || "Untitled report"}</h2><p>{titleCase(activeReport.report_type || reportContent.report_type || "summary")} · Generated {fmtDate(activeReport.created_at || reportContent.generated_at)}</p></div><button className="report-close-button" onClick={() => setActiveReport(null)}>Close ×</button></div>
      <div className="report-overview-kpis">
        {[["Rows",overview.row_count],["Columns",overview.column_count],["Numeric fields",overview.numeric_column_count],["Missing cells",overview.missing_cells],["Duplicate rows",overview.duplicate_rows]].map(([label,value]) => <div key={label}><small>{label}</small><strong>{fmtNum(value)}</strong></div>)}
      </div>
      {overview.numeric_columns?.length > 0 && <div className="report-data-tags"><span>Numeric columns</span>{numericCols.map((col) => <b key={col}>{col}</b>)}</div>}
      {qualityItems.length > 0 && <div className="report-content-section"><div className="report-content-title"><span>◈</span><div><h3>Data quality profile</h3><p>Quality metrics computed from the dataset.</p></div></div><ReportValue value={Object.fromEntries(qualityItems)}/></div>}
      {Object.keys(stats).length > 0 && <div className="report-content-section"><div className="report-content-title"><span>∑</span><div><h3>Descriptive statistics</h3><p>Statistical summary of dataset fields.</p></div></div><ReportValue value={stats}/></div>}
      {reportContent.correlations && <div className="report-content-section"><div className="report-content-title"><span>⌁</span><div><h3>Correlation analysis</h3><p>Relationships between numeric columns.</p></div></div><ReportValue value={reportContent.correlations}/></div>}
      {(reportContent.preview || reportContent.row_preview) && <div className="report-content-section"><div className="report-content-title"><span>▤</span><div><h3>Sample rows</h3><p>Small preview of the source records.</p></div></div><ReportValue value={reportContent.preview || reportContent.row_preview}/></div>}
      {!Object.keys(overview).length && !Object.keys(stats).length && <div className="report-empty-state">Report content is unavailable or uses a different schema.</div>}
    </section>}
  </section>;
}
