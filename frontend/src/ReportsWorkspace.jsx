import { useCallback, useEffect, useMemo, useState } from "react";
import { createReport, deleteReport, getDatasetReports, getReport, getApiErrorMessage } from "./api.js";

const fmtDate = (value) => value ? new Date(value).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "—";
const fmtNum = (value) => typeof value === "number" ? value.toLocaleString("en-IN", { maximumFractionDigits: 4 }) : String(value ?? "—");
const titleCase = (value) => String(value || "").replaceAll("_", " ").replace(/\b\w/g, (s) => s.toUpperCase());

function ReportValue({ value }) {
  if (value == null || typeof value !== "object") return <span>{fmtNum(value)}</span>;
  if (Array.isArray(value)) {
    if (!value.length) return <span className="report-muted">No values</span>;
    if (value.every((item) => item == null || typeof item !== "object")) return <p>{value.map(fmtNum).join(", ")}</p>;
    if (value.every((item) => item && typeof item === "object" && !Array.isArray(item))) {
      const columns = Object.keys(value[0] || {});
      return <div className="report-sample-table-wrap"><table className="report-sample-table"><thead><tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{value.slice(0, 20).map((row, index) => <tr key={index}>{columns.map((column) => <td key={column}>{row[column] == null ? "—" : String(row[column])}</td>)}</tr>)}</tbody></table>{value.length > 20 && <p className="report-muted">Showing first 20 records.</p>}</div>;
    }
    return <div className="report-narrative-list">{value.slice(0, 30).map((item, i) => <div className="report-narrative-item" key={i}><ReportValue value={item}/></div>)}</div>;
  }
  const entries = Object.entries(value);
  if (!entries.length) return <span className="report-muted">Empty</span>;
  if (value.matrix && Array.isArray(value.columns)) {
    const pairs = [];
    for (let i = 0; i < value.columns.length; i += 1) for (let j = i + 1; j < value.columns.length; j += 1) {
      const left = value.columns[i], right = value.columns[j], coefficient = value.matrix[left]?.[right] ?? value.matrix[right]?.[left];
      if (typeof coefficient === "number" && Number.isFinite(coefficient)) {
        const abs = Math.abs(coefficient), strength = abs >= .7 ? "strong" : abs >= .4 ? "moderate" : abs >= .2 ? "weak" : "very weak", direction = coefficient > 0 ? "positive" : coefficient < 0 ? "negative" : "zero";
        pairs.push(<p key={left+"-"+right}>{left} and {right} have a {strength} {direction} correlation (coefficient {fmtNum(coefficient)}). Correlation indicates association, not causation.</p>);
      }
    }
    return <div className="report-narrative-copy"><p>Correlation was calculated using the {titleCase(value.method || "pearson")} method.</p>{pairs.length ? pairs : <p>There are not enough numeric columns to calculate pairwise correlations.</p>}</div>;
  }
  if (entries.some(([key]) => ["data_type","count","missing","unique","type"].includes(key))) {
    const type = value.type || value.data_type || "unspecified";
    const intro = `This field is classified as ${String(type).replaceAll("_"," ")} data. It has ${fmtNum(value.count)} populated values, ${fmtNum(value.missing)} missing values, and ${fmtNum(value.unique)} distinct values.`;
    const details = type === "numeric" ? [value.mean != null && "mean "+fmtNum(value.mean),value.median != null && "median "+fmtNum(value.median),value.min != null && value.max != null && "range "+fmtNum(value.min)+" to "+fmtNum(value.max),value.std != null && "standard deviation "+fmtNum(value.std),value.q1 != null && value.q3 != null && "middle 50% from "+fmtNum(value.q1)+" to "+fmtNum(value.q3)].filter(Boolean).join("; ")
      : type === "categorical" && value.top_value != null ? "Most frequent value: “"+value.top_value+"” ("+fmtNum(value.top_frequency)+" occurrences)."
      : type === "datetime" && (value.minimum || value.maximum) ? "Observed date range: "+(value.minimum || "—")+" to "+(value.maximum || "—")+"."
      : type === "boolean" && value.true_count != null ? fmtNum(value.true_count)+" true and "+fmtNum(value.false_count)+" false values." : "";
    return <div className="report-narrative-copy"><p>{intro}</p>{details && <p>{type === "numeric" ? "Distribution details: "+details+"." : details}</p>}</div>;
  }
  return <div className="report-narrative-list">{entries.map(([key,item]) => <p className="report-narrative-paragraph" key={key}><strong>{titleCase(key)}:</strong> <ReportValue value={item}/></p>)}</div>;
}

function ReportCard({ report, onOpen, onDelete }) {
  return <article className="report-history-card">
    <div className="report-history-icon">▤</div>
    <div className="report-history-main"><strong>{report.title || "Untitled report"}</strong><div className="report-history-meta"><span className={`report-type-tag report-type-${report.report_type || "summary"}`}>{titleCase(report.report_type || "summary")}</span><span>{fmtDate(report.created_at || report.content?.generated_at)}</span></div></div>
    <div className="report-history-actions"><button className="report-action-button" onClick={() => onOpen(report)} title="View report">View ↗</button><button className="report-delete-button" onClick={() => onDelete(report)} title="Delete report">×</button></div>
  </article>;
}


function ExecutiveReportView({ analysis }) {
  const fmtMetric = (value) => {
    if (value == null || !Number.isFinite(Number(value))) return "—";
    const n = Number(value);
    return Math.abs(n) >= 1e6 ? n.toLocaleString("en-IN",{maximumFractionDigits:2}) : n.toLocaleString("en-IN",{maximumFractionDigits:2});
  };
  const change = analysis.trend?.period_change;
  const likeForLike = change?.like_for_like;
  const series = analysis.trend?.series || [];
  const vals = series.map((p) => Number(p.value || 0));
  const min = Math.min(0,...vals), max = Math.max(1,...vals), span = Math.max(1,max-min);
  const points = vals.map((v,i)=>({x:35+i*730/Math.max(1,vals.length-1),y:205-(v-min)/span*160}));
  const line = points.map(p=>p.x+","+p.y).join(" ");
  return <div className="executive-report">
    <section className="executive-report-summary">
      <div><span className="executive-report-kicker">MANAGEMENT OVERVIEW</span><h3>{analysis.report_title || "Executive Business Performance Report"}</h3><p>{analysis.executive_summary || "Performance overview calculated from the uploaded dataset."}</p><small>Primary measure: {analysis.metric_name || "Observed metric"}{analysis.metric_formula ? " · Formula: "+analysis.metric_formula : ""}</small></div>
    </section>
    <section className="executive-report-kpis">
      {(analysis.kpis || []).map((kpi,i)=><article key={i}><span>{kpi.label}</span><strong>{fmtMetric(kpi.value)}</strong>{kpi.metric && <small>{kpi.metric}</small>}</article>)}
    </section>
    <section className="executive-report-panel">
      <div className="executive-report-section-head"><div><span className="executive-report-kicker">PERFORMANCE OVER TIME</span><h3>Monthly trend</h3><p>Aggregated {analysis.trend?.metric || "metric"} by month using {analysis.trend?.date_field || "the detected date field"}.</p></div>
      {change && <div className={"executive-change executive-change-"+change.direction}><b>{change.direction==="up"?"↗":change.direction==="down"?"↘":"→"} {change.percentage_change == null ? "N/A" : fmtMetric(change.percentage_change)+"%"}</b><small>{change.previous_period} → {change.period}</small><span>Period-over-period</span></div>}</div>
      {series.length > 1 ? <div className="executive-trend-wrap"><svg className="executive-trend-svg" viewBox="0 0 800 250" role="img" aria-label="Monthly metric trend line">
        {[45,85,125,165,205].map(y=><line key={y} x1="25" x2="775" y1={y} y2={y} className="executive-chart-grid"/>)}<polygon points={"35,205 "+line+" 765,205"} className="executive-trend-area"/><polyline points={line} className="executive-trend-line"/>
        {points.map((p,i)=><g key={i}><circle cx={p.x} cy={p.y} r="4" className="executive-trend-dot"/><title>{series[i].period}: {fmtMetric(series[i].value)}</title></g>)}
      </svg><div className="executive-trend-labels">{series.map((p,i)=><span key={i}>{p.period}</span>)}</div></div> : <div className="executive-report-empty">A reliable date field and at least two periods are needed to display a trend.</div>}
      <div className="executive-period-comparison">{change && <><div><small>Previous period</small><b>{fmtMetric(change.previous_value)}</b><span>{change.previous_period}</span></div><div><small>Latest period</small><b>{fmtMetric(change.current_value)}</b><span>{change.period}</span></div><div><small>Absolute change</small><b>{fmtMetric(change.absolute_change)}</b><span>{change.direction==="up"?"Increase":change.direction==="down"?"Decrease":"No change"}</span></div></>}</div>
      {likeForLike && <div className="executive-period-comparison executive-like-for-like"><div><small>Like-for-like previous</small><b>{fmtMetric(likeForLike.previous_value)}</b><span>{likeForLike.previous_period} · days 1–{likeForLike.cutoff_day}</span></div><div><small>Like-for-like latest</small><b>{fmtMetric(likeForLike.current_value)}</b><span>{likeForLike.period} · days 1–{likeForLike.cutoff_day}</span></div><div><small>Comparable change</small><b>{likeForLike.percentage_change == null ? "N/A" : fmtMetric(likeForLike.percentage_change)+"%"}</b><span>{likeForLike.direction==="up"?"Increase":likeForLike.direction==="down"?"Decrease":"No change"}</span></div></div>}
      {likeForLike?.partial_period && <div className="report-alert report-alert-error executive-period-warning"><strong>Partial-period caution:</strong> {likeForLike.warning} The raw monthly decline should not be interpreted as a like-for-like business drop.</div>}
      <div className="executive-extremes">{analysis.trend?.peak_period && <div><span>▲ Peak period</span><b>{analysis.trend.peak_period.period}</b><strong>{fmtMetric(analysis.trend.peak_period.value)}</strong></div>}{analysis.trend?.lowest_period && <div><span>▼ Lowest period</span><b>{analysis.trend.lowest_period.period}</b><strong>{fmtMetric(analysis.trend.lowest_period.value)}</strong></div>}</div>
    </section>
    {(analysis.performance_breakdowns || []).length > 0 && <section className="executive-report-panel"><div className="executive-report-section-head"><div><span className="executive-report-kicker">BUSINESS DRIVERS</span><h3>Performance by segment</h3><p>Leading dimensions ranked by aggregated metric.</p></div></div><div className="executive-breakdowns">{analysis.performance_breakdowns.map((item,i)=>{const leaders=item.leaders||[],maxValue=Math.max(1,...leaders.map(x=>Math.max(0,Number(x.value||0))));return <article key={i}><h4>{item.dimension}</h4>{leaders.map((leader,j)=><div className="executive-breakdown-row" key={j}><div><span>{leader.name}</span><b>{fmtMetric(leader.value)}{leader.contribution_pct != null && <small className="executive-contribution-share"> · {fmtMetric(leader.contribution_pct)}% of total</small>}</b></div><i><em style={{width:Math.max(0,Number(leader.value||0))/maxValue*100+"%"}}/></i></div>)}</article>})}</div></section>}
    <section className="executive-report-panel"><div className="executive-report-section-head"><div><span className="executive-report-kicker">WHAT MANAGEMENT SHOULD KNOW</span><h3>Key findings</h3></div></div><div className="executive-findings">{(analysis.key_findings||[]).map((finding,i)=><article key={i}><span>{String(i+1).padStart(2,"0")}</span><div><h4>{finding.title}</h4><p>{finding.detail}</p></div></article>)}</div></section>
    <section className="executive-report-panel executive-recommendations"><div className="executive-report-section-head"><div><span className="executive-report-kicker">ACTION PLAN</span><h3>Management recommendations</h3><p>Suggested follow-ups based on descriptive analysis.</p></div></div><ol>{(analysis.management_recommendations||[]).map((item,i)=><li key={i}><span>{i+1}</span><p>{item}</p></li>)}</ol></section>
    {analysis.analysis_notes?.length>0 && <details className="executive-methodology"><summary>Methodology & limitations</summary><ul>{analysis.analysis_notes.map((note,i)=><li key={i}>{note}</li>)}</ul></details>}
  </div>;
}

export default function ReportsWorkspace({ dataset }) {
  const [reports, setReports] = useState([]);
  const [title, setTitle] = useState("");
  const [reportType, setReportType] = useState("executive");
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
          <label className={reportType === "executive" ? "selected" : ""}><input type="radio" name="reportType" value="executive" checked={reportType === "executive"} onChange={() => setReportType("executive")}/><span className="report-type-option-icon">↗</span><span><strong>Executive business report</strong><small>Management summary, trends, ups and downs, business drivers, findings and recommended actions</small></span></label><label className={reportType === "summary" ? "selected" : ""}><input type="radio" name="reportType" value="summary" checked={reportType === "summary"} onChange={() => setReportType("summary")}/><span className="report-type-option-icon">✧</span><span><strong>Technical summary</strong><small>Overview, data quality, descriptive stats</small></span></label>
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
      {reportContent.executive_analysis && <div className="report-content-section"><div className="report-content-title"><span>↗</span><div><h3>Executive business analysis</h3><p>Management-facing performance trends, findings, and recommendations.</p></div></div><ExecutiveReportView analysis={reportContent.executive_analysis}/></div>}
      {!reportContent.executive_analysis && <>
      <div className="report-overview-kpis">
        {[["Rows",overview.row_count],["Columns",overview.column_count],["Numeric fields",overview.numeric_column_count],["Missing cells",overview.missing_cells],["Duplicate rows",overview.duplicate_rows]].map(([label,value]) => <div key={label}><small>{label}</small><strong>{fmtNum(value)}</strong></div>)}
      </div>
      {overview.numeric_columns?.length > 0 && <div className="report-data-tags"><span>Numeric columns</span>{numericCols.map((col) => <b key={col}>{col}</b>)}</div>}
      {qualityItems.length > 0 && <div className="report-content-section"><div className="report-content-title"><span>◈</span><div><h3>Data quality profile</h3><p>Quality metrics computed from the dataset.</p></div></div><ReportValue value={Object.fromEntries(qualityItems)}/></div>}
      {Object.keys(stats).length > 0 && <div className="report-content-section"><div className="report-content-title"><span>∑</span><div><h3>Descriptive statistics</h3><p>Statistical summary of dataset fields.</p></div></div><ReportValue value={stats}/></div>}
      {(reportContent.correlation || reportContent.correlations) && <div className="report-content-section"><div className="report-content-title"><span>⌁</span><div><h3>Correlation analysis</h3><p>Relationships between numeric columns.</p></div></div><ReportValue value={reportContent.correlation || reportContent.correlations}/></div>}
      {(reportContent.sample_rows || reportContent.preview || reportContent.row_preview) && <div className="report-content-section"><div className="report-content-title"><span>▤</span><div><h3>Sample rows</h3><p>{fmtNum(reportContent.sample_row_count)} source records shown (maximum 20).</p></div></div><ReportValue value={reportContent.sample_rows || reportContent.preview || reportContent.row_preview}/></div>}
      {!Object.keys(overview).length && !Object.keys(stats).length && <div className="report-empty-state">Report content is unavailable or uses a different schema.</div>}
      </>}
    </section>}
  </section>;
}
