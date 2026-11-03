import { useEffect, useMemo, useRef, useState } from "react";
import { deleteDataset, getDatasets, getHealth, getPreview, getProfile, uploadDataset } from "./api.js";
import ExecutiveDashboard from "./ExecutiveDashboard.jsx";

const number = (value) => Number(value || 0).toLocaleString("en-IN");
const prettyDate = (value) => value ? new Date(value).toLocaleDateString("en-IN", { day:"2-digit", month:"short", year:"numeric" }) : "—";
const unwrap = (data) => data?.data ?? data;

function Icon({ children }) { return <span className="icon" aria-hidden="true">{children}</span>; }


function DownloadExport({ dataset, profile, preview, dashboardExportData }) {
  const [format, setFormat] = useState(null);
  const [chosen, setChosen] = useState("executive");
  const safeName = (dataset?.name || dataset?.original_filename || "datapilot-dashboard").replace(/[^a-z0-9-_]/gi, "-");
  const rows = preview?.rows || preview?.data || [];
  const headers = preview?.columns || (rows[0] ? Object.keys(rows[0]) : []);
  const d = dashboardExportData || {};
  const designs = [
    {id:"executive",name:"Executive Dark",desc:"Dark navy, KPI-first hierarchy, trend + donut charts.",bg:"#080b15",panel:"#111a2d",text:"#f2f5ff",muted:"#8d9bb5",accent:"#7889ff",accent2:"#46c6b6",layout:"wide"},
    {id:"clean",name:"Clean Professional",desc:"Light canvas, crisp typography, report-ready structure.",bg:"#f4f6fb",panel:"#ffffff",text:"#17223b",muted:"#75819a",accent:"#596be8",accent2:"#159c87",layout:"wide"},
    {id:"aurora",name:"Aurora Analytics",desc:"Violet gradients, compact KPI strip, chart-rich layout.",bg:"#100d24",panel:"#1c1734",text:"#f5f0ff",muted:"#b2a6d0",accent:"#b99aff",accent2:"#d47eb4",layout:"stack"},
    {id:"teal",name:"Corporate Teal",desc:"Calm teal palette with structured business breakdowns.",bg:"#071a1b",panel:"#102526",text:"#eafffb",muted:"#8db5b1",accent:"#46c6b6",accent2:"#e4c65a",layout:"wide"},
    {id:"insights",name:"Analytics Focus",desc:"Charts take center stage; segments and quarter views emphasized.",bg:"#101827",panel:"#19263a",text:"#eef5ff",muted:"#9bb0c9",accent:"#5ba8ff",accent2:"#fa7e91",layout:"stack"}
  ];
  const design = designs.find(x=>x.id===chosen) || designs[0];
  const kpis=(d.kpis||[]).slice(0,5), trend=(d.monthly_revenue||[]).slice(0,12);
  const countries=(d.country_revenue||[]).slice(0,8), products=(d.product_revenue||[]).slice(0,8);
  const segments=(d.customer_segments||[]).slice(0,6), quarters=(d.quarterly_revenue||[]).slice(0,4);
  const money=(v)=>{const n=Number(v||0),a=Math.abs(n);return a>=1e6?"£"+(n/1e6).toFixed(2)+"M":a>=1e3?"£"+(n/1e3).toFixed(1)+"K":n.toLocaleString("en-GB",{style:"currency",currency:"GBP",maximumFractionDigits:2});};
  const value=(item)=>item?.format==="currency"?money(item.value):Number(item?.value||0).toLocaleString("en-IN");
  const chartBars=(items,key)=>items.map((item,i)=><div className="gallery-bar" key={i}><span>{item[key]||item.quarter||item.segment||"—"}</span><b>{money(item.revenue??item.value)}</b><i><em style={{width:(Math.max(0,Number(item.revenue??item.value??0))/Math.max(1,...items.map(x=>Math.max(0,Number(x.revenue??x.value??0))))*100)+"%",background:design.accent2}}/></i></div>);
  const downloadCsv=()=>{
    if(!headers.length){window.alert("No preview rows are available to export yet.");return;}
    const quote=(v)=>"\""+String(v??"").replaceAll("\"","\"\"")+"\"";
    const csv=[headers.map(quote).join(","),...rows.map(row=>headers.map(key=>quote(row[key])).join(","))].join("\r\n");
    const blob=new Blob(["\ufeff",csv],{type:"text/csv;charset=utf-8;"}),url=URL.createObjectURL(blob),link=document.createElement("a");
    link.href=url;link.download=safeName+"-data-export.csv";link.click();URL.revokeObjectURL(url);
  };
  const exportPng=(designOverride)=>{
    const activeDesign=designOverride || design;
    const canvas=document.createElement("canvas");canvas.width=1800;canvas.height=2100;const ctx=canvas.getContext("2d");
    ctx.fillStyle=activeDesign.bg;ctx.fillRect(0,0,canvas.width,canvas.height);
    const txt=(s,x,y,font="20px Arial",color=activeDesign.text)=>{ctx.font=font;ctx.fillStyle=color;ctx.fillText(String(s??""),x,y);};
    const card=(x,y,w,h)=>{ctx.fillStyle=activeDesign.panel;ctx.strokeStyle=activeDesign.accent+"66";ctx.lineWidth=2;ctx.fillRect(x,y,w,h);ctx.strokeRect(x,y,w,h);};
    txt("DATAPILOT AI",85,100,"bold 52px Arial",activeDesign.accent);txt("EXECUTIVE DASHBOARD  /  "+(dataset?.name||"Selected dataset"),85,150,"26px Arial",activeDesign.muted);
    const kw=310;kpis.forEach((item,i)=>{let x=85+i*(kw+18);card(x,210,kw,145);txt(String(item.label||"METRIC").toUpperCase(),x+20,250,"bold 18px Arial",activeDesign.accent2);txt(value(item),x+20,310,"bold 34px Arial");});
    card(85,390,1050,430);txt("REVENUE TREND",115,440,"bold 26px Arial",activeDesign.accent);const vals=trend.map(x=>Number(x.revenue||0)),max=Math.max(1,...vals),min=Math.min(0,...vals);
    ctx.strokeStyle=activeDesign.accent2;ctx.lineWidth=6;ctx.beginPath();vals.forEach((v,i)=>{const x=140+i*900/Math.max(1,vals.length-1),y=750-(v-min)/Math.max(1,max-min)*250;i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.stroke();
    vals.forEach((v,i)=>{const x=140+i*900/Math.max(1,vals.length-1),y=750-(v-min)/Math.max(1,max-min)*250;ctx.fillStyle=activeDesign.accent;ctx.beginPath();ctx.arc(x,y,7,0,Math.PI*2);ctx.fill();txt(trend[i]?.period||"",x-24,790,"13px Arial",activeDesign.muted);});
    card(1165,390,550,430);txt("COUNTRY MIX",1195,440,"bold 26px Arial",activeDesign.accent);
    const valsC=countries.map(x=>Math.max(0,Number(x.revenue||0))),total=valsC.reduce((a,b)=>a+b,0);let angle=-Math.PI/2;const colors=[activeDesign.accent,activeDesign.accent2,"#ffad55","#fa7e91","#b99aff","#5ba8ff","#e4c65a","#d47eb4"];
    countries.forEach((item,i)=>{const next=angle+(total?valsC[i]/total*Math.PI*2:0);ctx.beginPath();ctx.moveTo(1440,620);ctx.arc(1440,620,150,angle,next);ctx.closePath();ctx.fillStyle=colors[i%colors.length];ctx.fill();angle=next;});ctx.beginPath();ctx.arc(1440,620,85,0,Math.PI*2);ctx.fillStyle=activeDesign.panel;ctx.fill();
    const drawList=(title,items,key,y,h,color)=>{card(85,y,1630,h);txt(title,115,y+45,"bold 26px Arial",activeDesign.accent);const maxV=Math.max(1,...items.map(x=>Number(x.revenue??x.value??0)));items.forEach((it,i)=>{const yy=y+85+i*((h-105)/Math.max(1,items.length));txt(String(it[key]||it.quarter||it.segment||"").slice(0,44),115,yy+15,"16px Arial");txt(money(it.revenue??it.value),500,yy+15,"bold 16px Arial");ctx.fillStyle=activeDesign.panel;ctx.fillRect(700,yy,950,14);ctx.fillStyle=color;ctx.fillRect(700,yy,Math.max(3,950*Number(it.revenue??it.value??0)/maxV),14);});};
    drawList("TOP PRODUCTS BY REVENUE",products,"product",860,300,activeDesign.accent2);drawList("CUSTOMER SEGMENTS",segments,"segment",1180,270,activeDesign.accent);drawList("QUARTERLY REVENUE",quarters,"quarter",1470,220,activeDesign.accent2);
    txt("Generated by DataPilot AI · "+new Date().toLocaleDateString(),85,2025,"16px Arial",activeDesign.muted);
    const link=document.createElement("a");link.download=safeName+"-"+activeDesign.id+"-dashboard.png";link.href=canvas.toDataURL("image/png");link.click();
  };
  const exportPdf=(designOverride)=>{
    const activeDesign=designOverride || design;
    const kpiHtml=kpis.map(item=>"<div class='kpi'><small>"+String(item.label||"Metric")+"</small><strong>"+value(item)+"</strong></div>").join("");
    const rowsHtml=(items,key,color=activeDesign.accent2)=>{const maxV=Math.max(1,...items.map(item=>Math.max(0,Number(item.revenue??item.value??0))));return items.map(item=>{const label=String(item[key]||item.quarter||item.segment||"");const val=Math.max(0,Number(item.revenue??item.value??0));return "<div class='barrow'><div class='barlabel'><span>"+label+"</span><b>"+money(val)+"</b></div><div class='track'><i style='width:"+Math.max(1,val/maxV*100)+"%;background:"+color+"'></i></div></div>";}).join("");};
    const trendValues=trend.map(item=>Number(item.revenue||0)),trendMax=Math.max(1,...trendValues),trendMin=Math.min(0,...trendValues),trendRange=Math.max(1,trendMax-trendMin);
    const trendPoints=trendValues.map((v,i)=>({x:36+i*628/Math.max(1,trendValues.length-1),y:190-(v-trendMin)/trendRange*145}));
    const trendSvg=activeDesign.id==="clean"?"<svg class='trend-svg' viewBox='0 0 700 235'>"+trendValues.map((v,i)=>{const h=(v-trendMin)/trendRange*145,x=30+i*630/Math.max(1,trendValues.length);return "<rect x='"+x+"' y='"+(190-h)+"' width='26' height='"+h+"' fill='"+activeDesign.accent2+"'/>";}).join("")+"</svg>":activeDesign.id==="aurora"?"<svg class='trend-svg' viewBox='0 0 700 235'>"+trendValues.map((v,i)=>{const x=350+145*Math.cos(i/Math.max(1,trendValues.length)*Math.PI*2),y=115+75*Math.sin(i/Math.max(1,trendValues.length)*Math.PI*2),r=8+(v-trendMin)/trendRange*18;return "<circle cx='"+x+"' cy='"+y+"' r='"+r+"' fill='"+activeDesign.accent2+"'/>";}).join("")+"</svg>":activeDesign.id==="teal"?"<svg class='trend-svg' viewBox='0 0 700 235'><polygon points='25,190 "+trendPoints.map(p=>p.x+","+p.y).join(" ")+" 675,190' fill='"+activeDesign.accent2+"' opacity='.22'/><polyline fill='none' stroke='"+activeDesign.accent2+"' stroke-width='4' points='"+trendPoints.map(p=>p.x+","+p.y).join(" ")+"'/></svg>":"<svg class='trend-svg' viewBox='0 0 700 235'><g stroke='"+activeDesign.accent+"33'>"+[45,80,115,150,190].map(y=>"<line x1='25' x2='675' y1='"+y+"' y2='"+y+"'/>").join("")+"</g><polyline fill='none' stroke='"+activeDesign.accent2+"' stroke-width='4' points='"+trendPoints.map(p=>p.x+","+p.y).join(" ")+"'/>"+trendPoints.map((p,i)=>"<circle cx='"+p.x+"' cy='"+p.y+"' r='4' fill='"+activeDesign.accent+"'><title>"+String(trend[i]?.period||"")+" · "+money(trendValues[i])+"</title></circle>").join("")+"</svg><div class='trend-labels'>"+trend.map(item=>"<span>"+String(item.period||"")+"</span>").join("")+"</div>";
    const countryVals=countries.map(item=>Math.max(0,Number(item.revenue||0))),countryTotal=countryVals.reduce((a,b)=>a+b,0),countryColors=[activeDesign.accent,activeDesign.accent2,"#ffad55","#fa7e91","#b99aff","#5ba8ff","#e4c65a","#d47eb4"];
    let countryAngle=-Math.PI/2;const countrySlices=countries.map((item,i)=>{const portion=countryTotal?countryVals[i]/countryTotal:0,next=countryAngle+portion*Math.PI*2;const x1=100+80*Math.cos(countryAngle),y1=100+80*Math.sin(countryAngle),x2=100+80*Math.cos(next),y2=100+80*Math.sin(next),large=portion>.5?1:0;const path=portion>=.9999?"M100 20 A80 80 0 1 1 99.99 20":"M100 100 L"+x1+" "+y1+" A80 80 0 "+large+" 1 "+x2+" "+y2+" Z";countryAngle=next;return "<path d='"+path+"' fill='"+countryColors[i%countryColors.length]+"'><title>"+String(item.country||"")+" · "+money(countryVals[i])+"</title></path>";}).join("");
    const countrySvg="<svg class='donut-svg' viewBox='0 0 200 200'>"+countrySlices+(activeDesign.id==="clean"||activeDesign.id==="insights"?"":"<circle cx='100' cy='100' r='48' fill='"+activeDesign.panel+"'/>")+"</svg>";
    const html="<!doctype html><html><head><title>"+safeName+" dashboard</title><style>@page{size:landscape;margin:8mm}*{box-sizing:border-box}html,body{margin:0;background:"+activeDesign.bg+"!important;color:"+activeDesign.text+"!important;font:13px Arial;-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important;color-adjust:exact}.bodywrap{padding:16px;background:"+activeDesign.bg+"}.head{border-left:7px solid "+activeDesign.accent+";padding:8px 16px;margin-bottom:14px}.head h1{margin:0;font-size:28px}.head p{color:"+activeDesign.muted+"}.kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:8px}.kpi,.panel{background:"+activeDesign.panel+"!important;border:1px solid "+activeDesign.accent+"66;padding:12px;margin-bottom:10px;break-inside:avoid}.kpi small{display:block;color:"+activeDesign.accent2+";font-weight:bold}.kpi strong{display:block;font-size:23px;margin-top:8px}.charts{display:grid;grid-template-columns:2fr 1fr;gap:10px}.panel h2{font-size:16px;color:"+activeDesign.accent+";margin:0 0 10px}.trend-svg{width:100%;height:190px;display:block}.trend-labels{display:flex;justify-content:space-between;color:"+activeDesign.muted+";font-size:9px}.donut-svg{width:175px;height:175px;display:block;margin:4px auto}.barrow{padding:5px 0}.barlabel{display:flex;justify-content:space-between;gap:12px;margin-bottom:4px}.barlabel span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.barlabel b{white-space:nowrap}.track{height:8px;background:"+activeDesign.accent+"22;border-radius:4px;overflow:hidden}.track i{display:block;height:100%;border-radius:4px}.footer{color:"+activeDesign.muted+";font-size:10px;margin-top:12px}@media print{html,body,.bodywrap{background:"+activeDesign.bg+"!important}.kpi,.panel{-webkit-print-color-adjust:exact;print-color-adjust:exact}} </style></head><body><main class='bodywrap'><div class='head'><h1>DataPilot AI · "+(dataset?.name||"Executive BI")+"</h1><p>"+activeDesign.name+" dashboard · Dataset analysis snapshot</p></div><div class='kpis'>"+kpiHtml+"</div><div class='charts'><section class='panel'><h2>Monthly Revenue Trend</h2>"+trendSvg+"</section><section class='panel'><h2>Revenue Mix by Country</h2>"+countrySvg+rowsHtml(countries,"country",activeDesign.accent2)+"</section></div><section class='panel'><h2>Top Products by Revenue</h2>"+rowsHtml(products,"product",activeDesign.accent2)+"</section><section class='panel'><h2>Customer Segments</h2>"+rowsHtml(segments,"segment",activeDesign.accent)+"</section><section class='panel'><h2>Quarterly Revenue</h2>"+rowsHtml(quarters,"quarter",activeDesign.accent2)+"</section><div class='footer'>Generated by DataPilot AI · "+new Date().toLocaleDateString()+"</div></main><script>window.onload=()=>setTimeout(()=>window.print(),700)</script></body></html>";
    const win=window.open("","_blank");if(!win){window.alert("Allow pop-ups for DataPilot to save the dashboard as PDF.");return;}win.document.open();win.document.write(html);win.document.close();
  };
  if(!dataset)return <div className="empty-state"><h3>Select a dataset first</h3><p>Upload or select a dataset to create exports.</p></div>;
  if(format==="PDF"||format==="PNG")return <section className="export-studio"><div className="gallery-heading"><button className="gallery-back" onClick={()=>setFormat(null)}>← Back to formats</button><div><div className="export-eyebrow"><span/> DASHBOARD DESIGN GALLERY</div><h1>Choose your {format} dashboard</h1><p>Select a visual design. Each template changes the presentation and chart composition.</p></div></div><div className="gallery-grid">{designs.map(item=><article key={item.id} className={"gallery-card "+(chosen===item.id?"selected":"")} style={{background:item.bg,color:item.text,borderColor:chosen===item.id?item.accent: item.accent+"44"}}><div className="gallery-preview-head" style={{borderColor:item.accent}}><strong style={{color:item.accent}}>DataPilot AI</strong><span>{item.name}</span></div><div className="gallery-preview-kpis">{kpis.slice(0,3).map((k,i)=><div key={i} style={{background:item.panel,borderColor:item.accent+"44"}}><small style={{color:item.accent2}}>{k.label}</small><b>{value(k)}</b></div>)}</div><div className={"gallery-preview-charts "+item.layout}>
{item.id==="executive" && <><div className="gallery-preview-line" style={{background:item.panel,borderColor:item.accent+"44"}}><span style={{color:item.accent}}>Revenue trend · Line</span><svg viewBox="0 0 220 70"><polyline points={trend.map((v,i)=>((10+i*200/Math.max(1,trend.length-1))+","+(60-Number(v.revenue||0)/Math.max(1,...trend.map(x=>Number(x.revenue||0)))*48))).join(" ")} fill="none" stroke={item.accent2} strokeWidth="3"/></svg></div><div className="gallery-preview-breakdown" style={{background:item.panel,borderColor:item.accent+"44"}}><span style={{color:item.accent}}>Country share · Donut</span><svg viewBox="0 0 100 100" style={{width:"100%",height:72}}><circle cx="50" cy="50" r="34" fill="none" stroke={item.accent2} strokeWidth="18" strokeDasharray="150 64"/><circle cx="50" cy="50" r="34" fill="none" stroke={item.accent} strokeWidth="18" strokeDasharray="42 172" transform="rotate(220 50 50)"/></svg></div></>}
{item.id==="clean" && <><div className="gallery-preview-line" style={{background:item.panel,borderColor:item.accent+"44"}}><span style={{color:item.accent}}>Monthly revenue · Columns</span><svg viewBox="0 0 220 70">{trend.slice(0,10).map((v,i)=><rect key={i} x={8+i*21} y={60-Number(v.revenue||0)/Math.max(1,...trend.map(x=>Number(x.revenue||0)))*48} width="13" height={Number(v.revenue||0)/Math.max(1,...trend.map(x=>Number(x.revenue||0)))*48} fill={item.accent2}/>)}</svg></div><div className="gallery-preview-breakdown" style={{background:item.panel,borderColor:item.accent+"44"}}><span style={{color:item.accent}}>Category share · Pie</span><svg viewBox="0 0 100 100" style={{width:"100%",height:72}}><circle cx="50" cy="50" r="38" fill={item.accent2}/><path d="M50 50 L50 12 A38 38 0 0 1 86 62 Z" fill={item.accent}/><path d="M50 50 L86 62 A38 38 0 0 1 30 83 Z" fill="#fa7e91"/></svg></div></>}
{item.id==="aurora" && <><div className="gallery-preview-line" style={{background:item.panel,borderColor:item.accent+"44"}}><span style={{color:item.accent}}>Revenue distribution · Bubble</span><svg viewBox="0 0 220 70">{trend.slice(0,8).map((v,i)=><circle key={i} cx={12+i*27} cy="35" r={4+Number(v.revenue||0)/Math.max(1,...trend.map(x=>Number(x.revenue||0)))*9} fill={item.accent2}/>)}</svg></div><div className="gallery-preview-breakdown" style={{background:item.panel,borderColor:item.accent+"44"}}><span style={{color:item.accent}}>Product ranking · Bars</span>{chartBars(products.slice(0,3),"product")}</div></>}
{item.id==="teal" && <><div className="gallery-preview-line" style={{background:item.panel,borderColor:item.accent+"44"}}><span style={{color:item.accent}}>Revenue · Area chart</span><svg viewBox="0 0 220 70"><polygon points={"0,65 "+trend.map((v,i)=>((10+i*200/Math.max(1,trend.length-1))+","+(60-Number(v.revenue||0)/Math.max(1,...trend.map(x=>Number(x.revenue||0)))*48))).join(" ")+" 220,65"} fill={item.accent2} opacity=".35"/><polyline points={trend.map((v,i)=>((10+i*200/Math.max(1,trend.length-1))+","+(60-Number(v.revenue||0)/Math.max(1,...trend.map(x=>Number(x.revenue||0)))*48))).join(" ")} fill="none" stroke={item.accent2} strokeWidth="3"/></svg></div><div className="gallery-preview-breakdown" style={{background:item.panel,borderColor:item.accent+"44"}}><span style={{color:item.accent}}>Country mix · Donut</span><svg viewBox="0 0 100 100" style={{width:"100%",height:72}}><circle cx="50" cy="50" r="34" fill="none" stroke={item.accent2} strokeWidth="18" strokeDasharray="170 44"/><circle cx="50" cy="50" r="34" fill="none" stroke={item.accent} strokeWidth="18" strokeDasharray="35 179" transform="rotate(245 50 50)"/></svg></div></>}
{item.id==="insights" && <><div className="gallery-preview-line" style={{background:item.panel,borderColor:item.accent+"44"}}><span style={{color:item.accent}}>Quarterly revenue · Bars</span><svg viewBox="0 0 220 70">{quarters.map((v,i)=><rect key={i} x={12+i*50} y={60-Number(v.revenue||v.value||0)/Math.max(1,...quarters.map(x=>Number(x.revenue||x.value||0)))*48} width="30" height={Number(v.revenue||v.value||0)/Math.max(1,...quarters.map(x=>Number(x.revenue||x.value||0)))*48} fill={item.accent2}/>)}</svg></div><div className="gallery-preview-breakdown" style={{background:item.panel,borderColor:item.accent+"44"}}><span style={{color:item.accent}}>Customer segments · Line</span><svg viewBox="0 0 220 70"><polyline points={segments.map((v,i)=>((10+i*200/Math.max(1,segments.length-1))+","+(60-Number(v.revenue||v.value||0)/Math.max(1,...segments.map(x=>Number(x.revenue||x.value||0)))*48))).join(" ")} fill="none" stroke={item.accent2} strokeWidth="3"/></svg></div></>}
</div><div className="gallery-card-foot"><div><h3>{item.name}</h3><p>{item.desc}</p></div><button style={{background:chosen===item.id?item.accent:"transparent",borderColor:item.accent,color:chosen===item.id?"#fff":item.text}} onClick={()=>setChosen(item.id)}>{chosen===item.id?"✓ Selected":"Select design"}</button></div><div className="gallery-downloads"><button onClick={()=>{setChosen(item.id);exportPdf(item);}}>↓ Download PDF</button><button onClick={()=>{setChosen(item.id);exportPng(item);}}>↓ Download PNG</button></div></article>)}</div></section>;
  return <section className="export-studio"><div className="export-hero"><div><div className="export-eyebrow"><span/> DATAPILOT AI · REPORT STUDIO</div><h1>Download & Export</h1><p>Choose a format, preview dashboard design options, and export the selected dashboard.</p></div><div className="export-dataset-pill"><span>ACTIVE DATASET</span><strong>{dataset.name||dataset.original_filename}</strong><small>{Number(dataset.row_count||0).toLocaleString("en-IN")} rows · {Number(dataset.column_count||0).toLocaleString("en-IN")} columns</small></div></div><div className="export-format-grid"><article className="export-format-card export-pdf"><div className="export-format-icon">PDF</div><h2>Dashboard PDF</h2><p>Choose from five designs and save a colored, presentation-ready dashboard.</p><button className="export-action" onClick={()=>setFormat("PDF")}>Browse PDF designs →</button></article><article className="export-format-card export-png"><div className="export-format-icon">PNG</div><h2>Dashboard PNG</h2><p>Choose a layout and download a high-resolution dashboard image.</p><button className="export-action" onClick={()=>setFormat("PNG")}>Browse PNG designs →</button></article><article className="export-format-card export-xls"><div className="export-format-icon">CSV</div><h2>Data Export</h2><p>Export the selected dataset preview for spreadsheet analysis.</p><button className="export-action" onClick={downloadCsv} disabled={!headers.length}>Export CSV →</button></article></div><div className="export-note"><span>✦</span><div><strong>Dashboard export gallery</strong><p>PDF uses browser print/save with background graphics enabled in the print dialog. PNG exports a high-resolution image with KPI cards and analytical chart sections. CSV remains the preview-data export.</p></div></div></section>;
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
    const frame = window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
      window.print();
      setPrintDashboard(false);
    }));
    return () => window.cancelAnimationFrame(frame);
  }, [printDashboard, section, dashboardExportData]);

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

          {section === "Download & Export" && <DownloadExport dataset={selected} profile={profile} preview={preview} dashboardExportData={dashboardExportData} />}
          {section === "Download & Export" && !dashboardExportData && selected && <div style={{display:"none"}}><ExecutiveDashboard dataset={selected} onDashboardData={setDashboardExportData}/></div>}

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
