import { useEffect, useMemo, useRef, useState } from "react";
import { deleteDataset, getDatasets, getHealth, getPreview, getProfile, uploadDataset } from "./api.js";
import ExecutiveDashboard from "./ExecutiveDashboard.jsx";

const number = (value) => Number(value || 0).toLocaleString("en-IN");
const prettyDate = (value) => value ? new Date(value).toLocaleDateString("en-IN", { day:"2-digit", month:"short", year:"numeric" }) : "—";
const unwrap = (data) => data?.data ?? data;

function Icon({ children }) { return <span className="icon" aria-hidden="true">{children}</span>; }


function DownloadExport({ dataset, profile, preview, dashboardExportData, onPdfExport }) {
  const safeName = (dataset?.name || dataset?.original_filename || "datapilot-report").replace(/[^a-z0-9-_]/gi, "-");
  const rows = preview?.rows || preview?.data || [];
  const headers = preview?.columns || (rows[0] ? Object.keys(rows[0]) : []);
  const downloadPdf = () => { onPdfExport?.(); };
  const downloadCsv = () => {
    if (!headers.length) { window.alert("No preview rows are available to export yet."); return; }
    const quote = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
    const csv = [headers.map(quote).join(","), ...rows.map((row) => headers.map((key) => quote(row[key])).join(","))].join("\r\n");
    const blob = new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob); const link = document.createElement("a");
    link.href = url; link.download = `${safeName}-data-export.csv`; link.click(); URL.revokeObjectURL(url);
  };
  const downloadPng = () => {
    const data = dashboardExportData;
    if (!data) { window.alert("Open Executive BI once so the dashboard charts can load before exporting."); return; }
    const canvas = document.createElement("canvas"); canvas.width = 1600; canvas.height = 900;
    const ctx = canvas.getContext("2d");
    const bg = ctx.createLinearGradient(0,0,1600,900); bg.addColorStop(0,"#080b15"); bg.addColorStop(1,"#111a2d");
    ctx.fillStyle=bg;ctx.fillRect(0,0,1600,900);
    ctx.fillStyle="#7889ff";ctx.fillRect(90,90,8,80);
    ctx.fillStyle="#f2f5ff";ctx.font="bold 52px Arial";ctx.fillText("DataPilot AI",120,130);
    ctx.fillStyle="#8d9bb5";ctx.font="24px Arial";ctx.fillText("DATASET SNAPSHOT  /  "+(dataset?.name || dataset?.original_filename || "Selected dataset"),120,180);
    ctx.strokeStyle="#263650";ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(90,230);ctx.lineTo(1510,230);ctx.stroke();
    const metrics=(data.kpis||[]).slice(0,4).map((item)=>[String(item.label||"METRIC").toUpperCase(),item.format==="currency" ? "£"+Number(item.value||0).toLocaleString("en-GB",{maximumFractionDigits:2}) : Number(item.value||0).toLocaleString("en-IN")]);
    metrics.forEach((m,i)=>{const x=90+i*360;ctx.fillStyle="#111a2d";ctx.strokeStyle="#263650";ctx.fillRect(x,290,330,190);ctx.strokeRect(x,290,330,190);ctx.fillStyle="#e8c46e";ctx.font="bold 19px Arial";ctx.fillText(m[0],x+25,335);ctx.fillStyle="#f2f5ff";ctx.font="bold 42px Arial";ctx.fillText(m[1],x+25,405);ctx.fillStyle="#46c6b6";ctx.fillRect(x+25,445,75,5);});
    ctx.fillStyle="#e8c46e";ctx.font="bold 24px Arial";ctx.fillText("MONTHLY REVENUE TREND",90,545);
    const trend=(data.monthly_revenue||[]).slice(0,12), vals=trend.map((item)=>Number(item.revenue||0)), maxTrend=Math.max(1,...vals);
    ctx.strokeStyle="#263650";ctx.lineWidth=1;for(let y=580;y<=700;y+=30){ctx.beginPath();ctx.moveTo(90,y);ctx.lineTo(1510,y);ctx.stroke();}
    ctx.strokeStyle="#d47eb4";ctx.lineWidth=5;ctx.beginPath();vals.forEach((value,i)=>{const x=100+i*(1380/Math.max(1,vals.length-1)),y=700-(value/maxTrend)*110;i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.stroke();
    vals.forEach((value,i)=>{const x=100+i*(1380/Math.max(1,vals.length-1)),y=700-(value/maxTrend)*110;ctx.fillStyle="#7889ff";ctx.beginPath();ctx.arc(x,y,5,0,Math.PI*2);ctx.fill();ctx.fillStyle="#8d9bb5";ctx.font="13px Arial";ctx.fillText(trend[i]?.period||"",x-24,730);});
    ctx.fillStyle="#e8c46e";ctx.font="bold 24px Arial";ctx.fillText("TOP PRODUCTS BY REVENUE",90,780);
    const products=(data.product_revenue||[]).slice(0,3),maxProduct=Math.max(1,...products.map((p)=>Number(p.revenue||0)));
    products.forEach((item,i)=>{const y=815+i*25;ctx.fillStyle="#8d9bb5";ctx.font="14px Arial";ctx.fillText(String(item.product||"").slice(0,48),90,y);ctx.fillStyle="#46c6b6";ctx.fillRect(600,y-12,Math.max(5,800*Number(item.revenue||0)/maxProduct),8);});
    ctx.fillStyle="#8d9bb5";ctx.font="16px Arial";ctx.fillText("Generated in DataPilot AI · "+new Date().toLocaleDateString(),90,890);
    const link=document.createElement("a");link.download=`${safeName}-snapshot.png`;link.href=canvas.toDataURL("image/png");link.click();
  };
  if (!dataset) return <div className="empty-state"><div className="empty-icon">⇩</div><h3>Select a dataset first</h3><p>Upload or select a dataset to create exports.</p></div>;
  return <section className="export-studio">
    <div className="export-hero"><div><div className="export-eyebrow"><span/> DATAPILOT AI · REPORT STUDIO</div><h1>Download & Export</h1><p>Choose a format to take your analysis with you. Export options are designed to match your workflow.</p></div><div className="export-dataset-pill"><span>ACTIVE DATASET</span><strong>{dataset.name || dataset.original_filename}</strong><small>{Number(dataset.row_count||0).toLocaleString("en-IN")} rows · {Number(dataset.column_count||0).toLocaleString("en-IN")} columns</small></div></div>
    <div className="export-format-grid">
      <article className="export-format-card export-pdf"><div className="export-card-top"><div className="export-format-icon">PDF</div><span className="export-format-badge">PRESENTATION READY</span></div><h2>PDF Report</h2><p>Print or save a polished report with the DataPilot dark theme. Use your browser's Save as PDF option.</p><ul><li>Branded report studio cover</li><li>Dataset snapshot and metadata</li><li>Optimized for landscape pages</li></ul><button onClick={downloadPdf} className="export-action">⇩ Export Executive BI PDF <span>→</span></button></article>
      <article className="export-format-card export-png"><div className="export-card-top"><div className="export-format-icon">PNG</div><span className="export-format-badge">HIGH RESOLUTION</span></div><h2>Dashboard Image</h2><p>Download a crisp branded snapshot to share in presentations, reports, or messages.</p><ul><li>1600 × 900 image</li><li>Dark navy with gradient accents</li><li>KPI summary tiles</li></ul><button onClick={downloadPng} className="export-action">⇩ Download PNG <span>→</span></button></article>
      <article className="export-format-card export-xls"><div className="export-card-top"><div className="export-format-icon">XLS</div><span className="export-format-badge">EXCEL COMPATIBLE</span></div><h2>Excel Data Export</h2><p>Export the available dataset preview as a CSV file that opens directly in Microsoft Excel.</p><ul><li>Column headers preserved</li><li>UTF-8 encoding</li><li>Easy to sort and analyze</li></ul><button onClick={downloadCsv} className="export-action" disabled={!headers.length}>⇩ Export CSV for Excel <span>→</span></button></article>
    </div>
    <div className="export-note"><span>✦</span><div><strong>Exporting the selected dataset</strong><p>CSV export includes the preview rows currently provided by DataPilot. The PDF action opens print/save dialog. PNG is a branded dataset snapshot.</p></div></div>
  </section>;
}

function App() {
  const [datasets, setDatasets] = useState([]);
  const [selected, setSelected] = useState(null);
  const [profile, setProfile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [health, setHealth] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [section, setSection] = useState("Overview");
  const [theme, setTheme] = useState("dark");
  const [dashboardExportData, setDashboardExportData] = useState(null);
  const [printDashboard, setPrintDashboard] = useState(false);
  const fileRef = useRef(null);

  const refresh = async () => {
    setLoading(true);
    try {
      const [healthResult, listResult] = await Promise.all([getHealth(), getDatasets()]);
      setHealth(healthResult.data?.status === "ok");
      const items = Array.isArray(listResult.data) ? listResult.data : listResult.data?.items ?? listResult.data?.datasets ?? [];
      setDatasets(items);
      if (items.length && !selected) setSelected(items[0]);
    } catch (err) {
      setError(err.response?.data?.detail || "Couldn't connect to the DataPilot API. Start the backend and check the database.");
    } finally { setLoading(false); }
  };

  useEffect(() => { refresh(); }, []);

  useEffect(() => {
    if (!printDashboard || section !== "Executive BI" || !dashboardExportData) return;
    const frame = window.requestAnimationFrame(() => window.requestAnimationFrame(() => { window.print(); setPrintDashboard(false); }));
    return () => window.cancelAnimationFrame(frame);
  }, [printDashboard, section]);

  useEffect(() => {
    if (!selected?.id) { setProfile(null); setPreview(null); return; }
    let active = true;
    Promise.all([getProfile(selected.id), getPreview(selected.id)])
      .then(([p, v]) => {
        if (active) {
          const payload = unwrap(p.data);
          setProfile(payload?.profile ? { ...payload.profile, dataset: payload.dataset } : payload);
          setPreview(unwrap(v.data));
        }
      })
      .catch(() => { if (active) { setProfile(null); setPreview(null); } });
    return () => { active = false; };
  }, [selected?.id]);

  const filtered = useMemo(() => datasets.filter((d) =>
    (d.name || d.original_filename || "").toLowerCase().includes(query.toLowerCase())
  ), [datasets, query]);

  const totalRows = datasets.reduce((sum, d) => sum + Number(d.row_count || 0), 0);
  const totalColumns = datasets.reduce((sum, d) => sum + Number(d.column_count || 0), 0);
  const quality = profile?.quality_score ?? profile?.data_quality_score;

  const handleUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setError(""); setNotice(""); setBusy(true); setProgress(0);
    try {
      const response = await uploadDataset(file, (event) => setProgress(Math.round((event.loaded * 100) / (event.total || 1))));
      const uploaded = response.data;
      await refresh();
      setSelected(uploaded);
      setNotice(`${file.name} uploaded and profiled successfully.`);
      setSection("Datasets");
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed. Check the file and backend logs.");
    } finally { setBusy(false); setProgress(0); event.target.value = ""; }
  };

  const chooseDataset = (dataset) => { setSelected(dataset); setSection("Analytics"); };
  const handleDelete = async (dataset) => {
    if (!window.confirm(`Delete "${dataset.name || dataset.original_filename}"? This cannot be undone.`)) return;
    try {
      await deleteDataset(dataset.id);
      const remaining = datasets.filter((d) => d.id !== dataset.id);
      setDatasets(remaining); setSelected(remaining[0] || null);
      setNotice("Dataset deleted.");
    } catch (err) { setError(err.response?.data?.detail || "Could not delete this dataset."); }
  };

  const columns = profile?.columns || [];
  const rows = preview?.rows || preview?.data || [];
  const headers = preview?.columns || (rows[0] ? Object.keys(rows[0]) : []);
  const numericColumns = columns.filter((c) => ["numeric", "number", "integer", "float"].includes(String(c.semantic_type || c.dtype || "").toLowerCase()));
  const stats = profile?.statistics || profile?.summary || {};

  return (
    <div className={`app-shell theme-${theme}`}>
      <aside className="sidebar">
        <a className="brand" href="#" onClick={() => setSection("Overview")}><span className="brand-mark">D</span><span>DataPilot<span className="brand-ai"> AI</span><small>INTELLIGENCE WORKSPACE</small></span></a>
        <div className="workspace-label">WORKSPACE</div>
        <nav className="nav flex-column">
          {[["Overview","◫"],["Datasets","▤"],["Analytics","▥"],["Executive BI","✦"],["Download & Export","⇩"]].map(([label, icon]) =>
            <button key={label} className={`nav-link ${section === label ? "active" : ""}`} onClick={() => setSection(label)}><span>{icon}</span>{label}</button>
          )}
        </nav>
        <div className="sidebar-bottom">
          <div className="api-status"><span className={health ? "status-dot online" : "status-dot"} />API {health ? "Connected" : "Disconnected"}</div>
          <button className="nav-link theme-toggle" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}><span>{theme === "dark" ? "☼" : "☾"}</span>Switch to {theme === "dark" ? "light" : "dark"} mode</button>
          <div className="user-chip"><div className="avatar">SD</div><div><strong>Data Analyst</strong><small>Personal workspace</small></div></div>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div><span className="breadcrumb-muted">Workspace</span><span className="breadcrumb-sep">/</span><strong>{section}</strong></div>
          <div className="topbar-actions"><span className="live-indicator"><i /> {health ? "System operational" : "API offline"}</span><button className="icon-button" onClick={refresh} title="Refresh">↻</button><button className="upload-button" onClick={() => fileRef.current?.click()} disabled={busy}>＋ Upload data</button><input ref={fileRef} type="file" accept=".csv,.xlsx,.xls" hidden onChange={handleUpload}/></div>
        </header>

        <div className="content-area">
          {error && <div className="alert alert-danger alert-dismissible"><strong>Something went wrong:</strong> {error}<button className="btn-close" onClick={() => setError("")}/></div>}
          {notice && <div className="alert alert-success alert-dismissible">{notice}<button className="btn-close" onClick={() => setNotice("")}/></div>}
          {busy && <div className="upload-progress"><div className="d-flex justify-content-between"><span>Uploading and profiling dataset…</span><strong>{progress}%</strong></div><div className="progress mt-2"><div className="progress-bar" style={{width:`${progress}%`}}/></div></div>}

          {section === "Overview" && <>
            <div className="page-heading"><div><div className="eyebrow">YOUR DATA, IN FOCUS</div><h1>Good to see you again.</h1><p>Your business intelligence workspace at a glance.</p></div><button className="primary-button" onClick={() => fileRef.current?.click()}>＋ Add a dataset</button></div>
            <div className="metric-grid">
              <Metric icon="▤" label="Total datasets" value={number(datasets.length)} note="Files in your workspace"/>
              <Metric icon="↗" label="Rows analyzed" value={number(totalRows)} note="Across all datasets"/>
              <Metric icon="▦" label="Columns discovered" value={number(totalColumns)} note="Available data fields"/>
              <Metric icon="◈" label="Data quality" value={quality == null ? "—" : `${quality}%`} note={selected ? selected.name || "Selected dataset" : "Upload data to begin"}/>
            </div>
            <div className="section-heading"><div><h2>Recent datasets</h2><p>Your latest uploaded files</p></div><button className="text-button" onClick={() => setSection("Datasets")}>View all →</button></div>
            <DatasetTable datasets={datasets.slice(0,5)} onSelect={chooseDataset} onDelete={handleDelete} loading={loading}/>
            <div className="bottom-grid">
              <div className="panel-card"><div className="panel-title"><div><h3>Quick start</h3><p>Get insights from your data in seconds</p></div><span className="panel-symbol">✦</span></div><div className="quick-steps"><div><b>01</b><span><strong>Upload your file</strong><small>CSV, XLSX or XLS formats</small></span></div><div><b>02</b><span><strong>Explore the profile</strong><small>Understand columns and data quality</small></span></div><div><b>03</b><span><strong>Discover insights</strong><small>Review statistics and data patterns</small></span></div></div></div>
              <div className="panel-card insight-card"><div className="eyebrow">SELECTED DATASET</div><h3>{selected?.name || "No dataset selected"}</h3><p>{selected ? `${number(selected.row_count)} rows · ${number(selected.column_count)} columns` : "Upload a dataset to start exploring."}</p>{selected && <button className="text-button" onClick={() => setSection("Analytics")}>Explore analytics →</button>}<div className="insight-orb">✧</div></div>
            </div>
          </>}

          {section === "Executive BI" && <ExecutiveDashboard dataset={selected} onDashboardData={setDashboardExportData} />}

          {section === "Download & Export" && <DownloadExport dataset={selected} profile={profile} preview={preview} dashboardExportData={dashboardExportData} onPdfExport={() => { setDashboardExportData(null); setPrintDashboard(true); setSection("Executive BI"); }} />}

          {section === "Datasets" && <>
            <div className="page-heading"><div><div className="eyebrow">DATA MANAGEMENT</div><h1>Your datasets</h1><p>Upload, organize and inspect your data sources.</p></div><button className="primary-button" onClick={() => fileRef.current?.click()}>＋ Upload dataset</button></div>
            <div className="search-row"><input className="form-control search-input" placeholder="Search datasets…" value={query} onChange={(e) => setQuery(e.target.value)}/><span>{filtered.length} dataset{filtered.length === 1 ? "" : "s"}</span></div>
            <DatasetTable datasets={filtered} onSelect={chooseDataset} onDelete={handleDelete} loading={loading}/>
          </>}

          {section === "Analytics" && <>
            <div className="page-heading"><div><div className="eyebrow">DATA EXPLORER</div><h1>Analytics overview</h1><p>Profile, inspect and understand your selected dataset.</p></div><select className="form-select dataset-select" value={selected?.id || ""} onChange={(e) => setSelected(datasets.find((d) => String(d.id) === e.target.value) || null)}><option value="">Select a dataset</option>{datasets.map((d) => <option key={d.id} value={d.id}>{d.name || d.original_filename}</option>)}</select></div>
            {!selected ? <EmptyState onUpload={() => fileRef.current?.click()}/> : <>
              <div className="selected-banner"><div><span className="file-pill">{(selected.file_type || "FILE").toUpperCase()}</span><strong>{selected.name || selected.original_filename}</strong><small>Uploaded {prettyDate(selected.created_at)}</small></div><div className="selected-stats"><span><b>{number(profile?.row_count ?? selected.row_count)}</b> rows</span><span><b>{number(profile?.column_count ?? selected.column_count)}</b> columns</span></div></div>
              <div className="metric-grid analytics-metrics"><Metric label="Quality score" value={quality == null ? "—" : `${quality}%`} icon="◈" note="Overall data quality"/><Metric label="Missing cells" value={number(profile?.missing_cells ?? selected.missing_cells)} icon="◌" note="Null or empty values"/><Metric label="Duplicate rows" value={number(profile?.duplicate_rows ?? selected.duplicate_rows)} icon="⧉" note="Repeated records"/><Metric label="Numeric fields" value={number(numericColumns.length)} icon="∑" note="Detected numeric columns"/></div>
              <div className="panel-card table-panel"><div className="section-heading inner-heading"><div><h3>Column profile</h3><p>Detected types and field-level statistics</p></div><span className="subtle-count">{columns.length} fields</span></div><div className="table-responsive"><table className="table data-table"><thead><tr><th>FIELD NAME</th><th>DATA TYPE</th><th>SEMANTIC TYPE</th><th>MISSING</th></tr></thead><tbody>{columns.map((c, i) => <tr key={c.name || i}><td className="field-name">{c.name}</td><td>{c.dtype || c.data_type || "—"}</td><td><span className="type-pill">{c.semantic_type || "unknown"}</span></td><td>{number(c.missing_count ?? c.missing ?? 0)}</td></tr>)}</tbody></table>{!columns.length && <div className="empty-inline">Column profile is not available for this dataset.</div>}</div></div>
              <div className="panel-card table-panel"><div className="section-heading inner-heading"><div><h3>Data preview</h3><p>First records from your uploaded file</p></div><span className="subtle-count">Preview</span></div><div className="table-responsive"><table className="table data-table"><thead><tr>{headers.map((h) => <th key={h}>{h}</th>)}</tr></thead><tbody>{rows.slice(0,8).map((row, i) => <tr key={i}>{headers.map((h) => <td key={h}>{String(row[h] ?? "—")}</td>)}</tr>)}</tbody></table>{!rows.length && <div className="empty-inline">Preview data is not available.</div>}</div></div>
            </>}
          </>}
          <footer className="footer-note">DataPilot AI <span>·</span> Your autonomous BI workspace <span>·</span> Phase 5.2</footer>
        </div>
      </main>
    </div>
  );
}

function Metric({ icon, label, value, note }) {
  return <div className="metric-card"><div className="metric-top"><span>{label}</span><span className="metric-icon">{icon}</span></div><div className="metric-value">{value}</div><div className="metric-note">{note}</div></div>;
}

function DatasetTable({ datasets, onSelect, onDelete, loading }) {
  return <div className="panel-card table-panel"><div className="table-responsive"><table className="table data-table align-middle"><thead><tr><th>DATASET</th><th>FORMAT</th><th>ROWS</th><th>COLUMNS</th><th>UPLOADED</th><th>STATUS</th><th/></tr></thead><tbody>
    {datasets.map((d) => <tr key={d.id}><td><button className="dataset-name" onClick={() => onSelect(d)}><span className="dataset-file-icon">▤</span><span><strong>{d.name || d.original_filename}</strong><small>{d.original_filename || "Uploaded file"}</small></span></button></td><td><span className="type-pill">{(d.file_type || "file").toUpperCase()}</span></td><td>{number(d.row_count)}</td><td>{number(d.column_count)}</td><td>{prettyDate(d.created_at)}</td><td><span className="status-pill"><i/>Ready</span></td><td><button className="delete-button" title="Delete dataset" onClick={() => onDelete(d)}>×</button></td></tr>)}
    {!datasets.length && <tr><td colSpan="7"><div className="empty-inline">{loading ? "Loading datasets…" : "No datasets yet. Upload a CSV or Excel file to get started."}</div></td></tr>}
  </tbody></table></div></div>;
}

function EmptyState({ onUpload }) {
  return <div className="empty-state"><div className="empty-icon">↥</div><h3>No dataset selected</h3><p>Upload a CSV or Excel file to generate your first data profile.</p><button className="primary-button" onClick={onUpload}>Upload a dataset</button></div>;
}

export default App;
