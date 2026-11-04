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
    const topCountry=countries[0]||{},topProduct=products[0]||{},topSegment=segments[0]||{};
    const trendBars=trendValues.map((v,i)=>{const x=34+i*632/Math.max(1,trendValues.length-1),y=190-(v-trendMin)/trendRange*145;return "<circle cx='"+x+"' cy='"+y+"' r='5' fill='"+activeDesign.accent2+"' stroke='"+activeDesign.bg+"' stroke-width='2'><title>"+String(trend[i]?.period||"")+" · "+money(v)+"</title></circle>";}).join("");
    const trendArea="M"+trendPoints.map(p=>p.x+","+p.y).join(" L")+" L675,205 L36,205 Z";
    const quarterlySvg="<svg class='quarter-svg' viewBox='0 0 520 220'><g class='grid'>"+[35,75,115,155,195].map(y=>"<line x1='35' x2='500' y1='"+y+"' y2='"+y+"'/>").join("")+"</g>"+quarters.map((q,i)=>{const v=Number(q.revenue??q.value??0),max=Math.max(1,...quarters.map(x=>Number(x.revenue??x.value??0))),h=v/max*150,x=58+i*110;return "<rect x='"+x+"' y='"+(195-h)+"' width='62' height='"+h+"' rx='7' fill='"+activeDesign.accent2+"'/><text x='"+(x+31)+"' y='"+(187-h)+"' text-anchor='middle' class='chart-value'>"+money(v)+"</text><text x='"+(x+31)+"' y='214' text-anchor='middle' class='axis-label'>"+String(q.quarter||("Q"+(i+1)))+"</text>";}).join("")+"</svg>";
    const insightsHtml=[{label:"Leading country",value:String(topCountry.country||"—"),detail:money(topCountry.revenue??0)},{label:"Top revenue product",value:String(topProduct.product||"—"),detail:money(topProduct.revenue??0)},{label:"Largest customer segment",value:String(topSegment.segment||"—"),detail:money(topSegment.revenue??topSegment.value??0)}].map((x,i)=>"<div class='insight-row'><span class='insight-index'>0"+(i+1)+"</span><div><small>"+x.label+"</small><strong>"+x.value+"</strong><b>"+x.detail+"</b></div></div>").join("");
    const html=`<!doctype html><html><head><title>${safeName} · DataPilot AI report</title><style>
    @page{size:A4 landscape;margin:7mm}*{box-sizing:border-box}html,body{margin:0;background:${activeDesign.bg}!important;color:${activeDesign.text}!important;font:10px Inter,Arial,sans-serif;-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important}
    :root{--accent:${activeDesign.accent};--accent2:${activeDesign.accent2};--panel:${activeDesign.panel};--muted:${activeDesign.muted};--line:${activeDesign.accent}55}
    .page{height:190mm;overflow:hidden;padding:5mm 6mm;position:relative;background:radial-gradient(ellipse at 90% 0%,var(--accent)20,transparent 38%),${activeDesign.bg};page-break-after:always;break-after:page}
    .page:last-child{page-break-after:auto;break-after:auto}.masthead{display:flex;align-items:center;justify-content:space-between;padding:0 0 3mm;border-bottom:1px solid var(--line);margin-bottom:4mm}
    .brand{display:flex;align-items:center;gap:8px;font-size:15px;font-weight:900;letter-spacing:-.4px}.brand-mark{display:grid;place-items:center;width:27px;height:27px;border-radius:8px;background:var(--accent);color:white;font-size:17px}.report-type{font-size:8px;letter-spacing:1.6px;color:var(--muted);font-weight:800}
    .hero{display:flex;justify-content:space-between;align-items:end;margin-bottom:4mm}.eyebrow{font-size:8px;font-weight:900;letter-spacing:2px;color:var(--accent2);margin-bottom:5px}.hero h1{font-size:25px;line-height:1.05;letter-spacing:-1px;margin:0;font-weight:900}.hero p{margin:5px 0 0;color:var(--muted);font-size:9px}.date-chip{border:1px solid var(--line);background:var(--panel);padding:8px 11px;border-radius:10px;color:var(--muted);font-weight:700}
    .kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:7px;margin-bottom:3.5mm}.kpi{position:relative;border:1px solid var(--line);background:linear-gradient(145deg,var(--accent)14,transparent 70%),var(--panel);border-radius:11px;padding:10px 11px;min-height:22mm;box-shadow:0 3px 12px #0002}.kpi small{font-size:7px;letter-spacing:1px;text-transform:uppercase;color:var(--accent2);font-weight:900}.kpi strong{display:block;font-size:19px;letter-spacing:-.5px;margin:6px 0 3px}.kpi:after{content:"";position:absolute;right:10px;top:10px;width:5px;height:5px;border-radius:50%;background:var(--accent2);box-shadow:0 0 8px var(--accent2)}
    .layout-main{display:grid;grid-template-columns:1.48fr 1fr;gap:3mm;margin-bottom:3mm}.layout-secondary{display:grid;grid-template-columns:1fr 1fr;gap:3mm;margin-bottom:3mm}.panel{background:linear-gradient(145deg,var(--accent)0a,transparent 50%),var(--panel);border:1px solid var(--line);border-radius:12px;padding:11px 12px;min-width:0;box-shadow:0 4px 14px #0002;break-inside:avoid}.panel h2{margin:0 0 8px;font-size:13px;letter-spacing:-.3px}.kicker{font-size:7px;letter-spacing:1.5px;font-weight:900;color:var(--accent2);margin-bottom:4px}.chart-svg{width:100%;height:43mm;display:block}.grid line{stroke:var(--line);stroke-dasharray:3 4}.axis-label{fill:var(--muted);font-size:10px}.chart-value{fill:var(--text);font-size:10px;font-weight:bold}.trend-labels{display:flex;justify-content:space-between;color:var(--muted);font-size:7px;margin-top:1px}
    .mix-layout{display:grid;grid-template-columns:45% 55%;align-items:center;gap:4px}.donut-svg{width:100%;max-height:43mm}.mix-legend{display:grid;gap:6px}.legend-item{display:flex;align-items:center;gap:6px;font-size:8px}.legend-dot{width:7px;height:7px;border-radius:50%;flex:none}.legend-item b{margin-left:auto;font-size:8px}.barrow{padding:5px 0;border-bottom:1px solid var(--line)}.barrow:last-child{border:0}.barlabel{display:flex;justify-content:space-between;gap:8px;font-size:8px;margin-bottom:4px}.barlabel span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.barlabel b{white-space:nowrap}.track{height:6px;background:var(--accent)22;border-radius:5px;overflow:hidden}.track i{display:block;height:100%;border-radius:5px}
    .insights{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.insight-row{display:flex;gap:8px;align-items:center;border:1px solid var(--line);background:var(--accent)0c;border-radius:9px;padding:8px}.insight-index{display:grid;place-items:center;width:23px;height:23px;background:var(--accent)25;color:var(--accent2);border-radius:7px;font-weight:900}.insight-row small,.insight-row strong,.insight-row b{display:block}.insight-row small{font-size:7px;color:var(--muted);margin-bottom:2px}.insight-row strong{font-size:9px;max-width:170px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.insight-row b{font-size:9px;color:var(--accent2);margin-top:3px}
    .quarter-svg{width:100%;height:47mm;display:block}.summary-grid{display:grid;grid-template-columns:1.5fr 1fr;gap:3mm}.summary-table{width:100%;border-collapse:collapse;font-size:8px}.summary-table th{text-align:left;color:var(--muted);font-size:7px;letter-spacing:.7px;padding:6px;border-bottom:1px solid var(--line)}.summary-table td{padding:7px 6px;border-bottom:1px solid var(--line)}.summary-table td:last-child{text-align:right;color:var(--accent2);font-weight:900}.takeaway{border:1px solid var(--accent);border-radius:12px;background:linear-gradient(135deg,var(--accent)30,transparent),var(--panel);padding:13px}.takeaway h2{font-size:14px;margin:0 0 8px}.takeaway p{font-size:10px;line-height:1.6;color:var(--muted);margin:0}.footer{position:absolute;bottom:4mm;left:6mm;right:6mm;display:flex;justify-content:space-between;padding-top:2mm;border-top:1px solid var(--line);color:var(--muted);font-size:7px}
    ${activeDesign.id==="clean"?".kpi,.panel{box-shadow:0 2px 8px #1b2d4b12}.page{background:${activeDesign.bg}}":""}
    </style></head><body>
    <section class="page"><header class="masthead"><div class="brand"><span class="brand-mark">D</span>DataPilot AI</div><div class="report-type">DATA INTELLIGENCE REPORT&nbsp; | &nbsp;EXECUTIVE BRIEF</div></header>
    <div class="hero"><div><div class="eyebrow">BUSINESS PERFORMANCE · SNAPSHOT</div><h1>${dataset?.name||"Online Retail"}<br/>Performance Dashboard</h1><p>${activeDesign.name} · Dataset analysis snapshot · ${Number(dataset?.row_count||0).toLocaleString("en-IN")} records</p></div><div class="date-chip">GENERATED · ${new Date().toLocaleDateString("en-GB")}</div></div>
    <div class="kpis">${kpiHtml}</div>
    <div class="layout-main"><section class="panel"><div class="kicker">PERFORMANCE · TIME SERIES</div><h2>Monthly Revenue Trend</h2><svg class="chart-svg" viewBox="0 0 700 235"><g class="grid">${[45,80,115,150,190].map(y=>"<line x1='25' x2='675' y1='"+y+"' y2='"+y+"'/>").join("")}</g><path d="${trendArea}" fill="var(--accent)" opacity=".18"/><polyline fill="none" stroke="var(--accent2)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" points="${trendPoints.map(p=>p.x+","+p.y).join(" ")}"/>${trendBars}</svg><div class="trend-labels">${trend.map(item=>"<span>"+String(item.period||"").slice(-5)+"</span>").join("")}</div></section>
    <section class="panel"><div class="kicker">GEOGRAPHIC CONTRIBUTION</div><h2>Revenue Mix by Country</h2><div class="mix-layout"><div>${countrySvg}</div><div class="mix-legend">${countries.slice(0,6).map((item,i)=>"<div class='legend-item'><i class='legend-dot' style='background:"+countryColors[i%countryColors.length]+"'></i><span>"+String(item.country||"—")+"</span><b>"+money(item.revenue)+"</b></div>").join("")}</div></div><div class="chart-insight"><b>Top market</b><span>${String(topCountry.country||"—")} · ${money(topCountry.revenue??0)}</span></div></section></div>
    <div class="layout-secondary"><section class="panel"><div class="kicker">PRODUCT PERFORMANCE</div><h2>Top Products by Revenue</h2>${rowsHtml(products.slice(0,5),"product",activeDesign.accent2)}</section><section class="panel"><div class="kicker">ANALYST NOTES · KEY DRIVERS</div><h2>Business Highlights</h2><div class="insights">${insightsHtml}</div><p style="font-size:8px;color:var(--muted);line-height:1.5;margin:8px 0 0">Highlights identify the strongest contributors from the selected dataset. Values reflect the available aggregated analysis.</p></section></div>
    <section class="panel"><div class="kicker">REVENUE & VOLUME · OVERVIEW</div><h2>Monthly Revenue Pulse</h2><div style="display:flex;align-items:center;gap:12px"><span style="color:var(--accent2);font-weight:900;font-size:9px">● Revenue</span><span style="color:var(--muted);font-size:8px">Monthly series from current dataset</span></div><svg class="chart-svg" style="height:34mm" viewBox="0 0 700 235"><g class="grid">${[45,80,115,150,190].map(y=>"<line x1='25' x2='675' y1='"+y+"' y2='"+y+"'/>").join("")}</g><path d="${trendArea}" fill="var(--accent2)" opacity=".13"/><polyline fill="none" stroke="var(--accent2)" stroke-width="4" points="${trendPoints.map(p=>p.x+","+p.y).join(" ")}"/>${trendBars}</svg></section>
    <div class="footer"><span>DataPilot AI · Autonomous BI Workspace</span><span>${activeDesign.name} · Page 1 / 2</span><span>CONFIDENTIAL · DATASET REPORT</span></div></section>
    <section class="page"><header class="masthead"><div class="brand"><span class="brand-mark">D</span>DataPilot AI</div><div class="report-type">ONLINE RETAIL ANALYTICS&nbsp; | &nbsp;DETAILED ANALYSIS</div></header>
    <div class="hero"><div><div class="eyebrow">PERFORMANCE DEEP DIVE</div><h1>Revenue Composition<br/> & Customer Intelligence</h1><p>Category, segment and period-level contribution views</p></div><div class="date-chip">REPORT DETAIL · 02</div></div>
    <div class="layout-main"><section class="panel"><div class="kicker">PERIOD COMPARISON</div><h2>Quarterly Revenue Performance</h2>${quarterlySvg}<div class="chart-insight"><b>Period view</b><span>Quarter aggregates supplied by the analytics engine</span></div></section><section class="panel"><div class="kicker">CUSTOMER VALUE DISTRIBUTION</div><h2>Customer Segments</h2>${rowsHtml(segments.slice(0,6),"segment",activeDesign.accent)}<div class="mini-note">Segment contribution helps locate the highest-value audience groups.</div></section></div>
    <div class="layout-secondary"><section class="panel"><div class="kicker">PRODUCT PORTFOLIO</div><h2>Revenue Leaders · Product Ranking</h2>${rowsHtml(products.slice(0,8),"product",activeDesign.accent2)}</section><section class="panel"><div class="kicker">MARKET COMPOSITION</div><h2>Country Contribution</h2>${rowsHtml(countries.slice(0,8),"country",activeDesign.accent)}</section></div>
    <div class="summary-grid"><section class="panel"><div class="kicker">EXECUTIVE SCORECARD</div><h2>Performance Summary</h2><table class="summary-table"><thead><tr><th>METRIC</th><th>VALUE</th><th>DATA VIEW</th></tr></thead><tbody>${kpis.map(k=>"<tr><td>"+String(k.label||"Metric")+"</td><td>"+value(k)+"</td><td>Current snapshot</td></tr>").join("")}</tbody></table></section><aside class="takeaway"><h2>✦ Key Takeaway</h2><p>The report highlights revenue trend, geographic contribution, product concentration, and customer-segment distribution. Use these views together to understand where the dataset’s business value is concentrated.</p><p style="margin-top:10px;font-size:8px">All figures are rendered from the selected dataset’s analytical response; no period-over-period change is fabricated.</p></aside></div>
    <div class="footer"><span>DataPilot AI · ${dataset?.name||"Dataset"} Report</span><span>${activeDesign.name} · Page 2 / 2</span><span>GENERATED ${new Date().toLocaleDateString("en-GB")}</span></div></section>
    <script>window.onload=()=>setTimeout(()=>window.print(),900)</script></body></html>`;
    const win=window.open("","_blank");if(!win){window.alert("Allow pop-ups for DataPilot to save the dashboard as PDF.");return;}win.document.open();win.document.write(html);win.document.close();
  };
  if(!dataset)return <div className="empty-state"><h3>Select a dataset first</h3><p>Upload or select a dataset to create exports.</p></div>;
  if(format==="PDF"||format==="PNG")return <section className="export-studio"><div className="gallery-heading"><button className="gallery-back" onClick={()=>setFormat(null)}>← Back to formats</button><div><div className="export-eyebrow"><span/> DASHBOARD DESIGN GALLERY</div><h1>Choose your {format} dashboard</h1><p>Select a visual design. Each template changes the presentation and chart composition.</p></div></div><div className="gallery-grid">{designs.map(item=><article key={item.id} className={"gallery-card "+(chosen===item.id?"selected":"")} style={{background:item.bg,color:item.text,borderColor:chosen===item.id?item.accent: item.accent+"44"}}><div className="gallery-dashboard-preview" style={{background:item.panel,borderColor:item.accent+"44"}}>
  <div className="gallery-dashboard-toolbar"><div><span className="gallery-live-dot"/> DATA PILOT / ANALYTICAL WORKSPACE</div><b>{item.name.toUpperCase()}</b></div>
  <div className="gallery-dashboard-title"><div><h4>Online Sales Dashboard</h4><p>Revenue drivers · Customer behavior · Performance snapshot</p></div><span className="gallery-filter-chip">ALL COUNTRIES⌄</span></div>
  <div className="gallery-dashboard-kpis">{kpis.slice(0,5).map((k,index)=><div key={index} style={{borderColor:item.accent+"33",background:item.bg}}><small style={{color:item.accent2}}>{String(k.label||"Metric").toUpperCase()}</small><strong>{value(k)}</strong><em style={{color:item.accent2}}>● Dataset calculated</em></div>)}</div>
  <div className="gallery-dashboard-main">
    <section className="gallery-dashboard-panel gallery-revenue-panel"><div className="gallery-panel-label" style={{color:item.accent}}>REVENUE PERFORMANCE</div><h5>Monthly revenue trend</h5><p>Net revenue by month</p><svg viewBox="0 0 420 145" preserveAspectRatio="none"><g stroke={item.accent+"22"} strokeDasharray="3 4"><path d="M8 30H412 M8 62H412 M8 94H412 M8 126H412"/></g><path d={"M8,126 "+trend.map((v,index)=>((8+index*404/Math.max(1,trend.length-1))+","+(120-Number(v.revenue||0)/Math.max(1,...trend.map(x=>Number(x.revenue||0)))*95))).join(" ")+" 412,126 Z"} fill={item.accent2} opacity=".12"/><polyline points={trend.map((v,index)=>((8+index*404/Math.max(1,trend.length-1))+","+(120-Number(v.revenue||0)/Math.max(1,...trend.map(x=>Number(x.revenue||0)))*95))).join(" ")} fill="none" stroke={item.accent2} strokeWidth="3.4" strokeLinejoin="round" strokeLinecap="round"/>{trend.map((v,index)=><circle key={index} cx={8+index*404/Math.max(1,trend.length-1)} cy={120-Number(v.revenue||0)/Math.max(1,...trend.map(x=>Number(x.revenue||0)))*95} r="3" fill={item.accent2} stroke={item.panel} strokeWidth="2"/>)}</svg><div className="gallery-axis-labels">{trend.slice(0,6).map((v,index)=><span key={index}>{String(v.period||"").slice(-5)}</span>)}</div></section>
    <section className="gallery-dashboard-panel gallery-country-panel"><div className="gallery-panel-label" style={{color:item.accent}}>MARKET DISTRIBUTION</div><h5>Revenue mix by country</h5><p>Top contributing markets</p><div className="gallery-country-visual"><svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="35" fill="none" stroke={item.accent+"22"} strokeWidth="17"/><circle cx="50" cy="50" r="35" fill="none" stroke={item.accent2} strokeWidth="17" strokeDasharray="145 75" transform="rotate(-90 50 50)"/><circle cx="50" cy="50" r="35" fill="none" stroke={item.accent} strokeWidth="17" strokeDasharray="48 172" transform="rotate(165 50 50)"/><circle cx="50" cy="50" r="35" fill="none" stroke="#ffad55" strokeWidth="17" strokeDasharray="23 197" transform="rotate(245 50 50)"/></svg><div>{countries.slice(0,4).map((c,index)=><div key={index}><i style={{background:[item.accent2,item.accent,"#ffad55","#fa7e91"][index]}}/><span>{c.country||"Market"}</span><b>{money(c.revenue||c.value)}</b></div>)}</div></div></section>
  </div>
  <div className="gallery-dashboard-bottom">
    <section className="gallery-dashboard-panel"><div className="gallery-panel-label" style={{color:item.accent}}>PRODUCT PERFORMANCE</div><h5>Top products by revenue</h5>{products.slice(0,4).map((p,index)=><div className="gallery-mini-bar" key={index}><div><span>{String(p.product||p.name||"Product").slice(0,23)}</span><b>{money(p.revenue||p.value)}</b></div><i><em style={{width:(Math.max(0,Number(p.revenue||p.value||0))/Math.max(1,...products.slice(0,4).map(x=>Number(x.revenue||x.value||0)))*100)+"%",background:item.accent2}}/></i></div>)}</section>
    <section className="gallery-dashboard-panel"><div className="gallery-panel-label" style={{color:item.accent}}>CUSTOMER INTELLIGENCE</div><h5>Customer segment mix</h5><div className="gallery-segment-visual"><svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="35" fill="none" stroke={item.accent2} strokeWidth="18" strokeDasharray="145 75"/><circle cx="50" cy="50" r="35" fill="none" stroke={item.accent} strokeWidth="18" strokeDasharray="58 162" transform="rotate(145 50 50)"/><circle cx="50" cy="50" r="35" fill="none" stroke="#fa7e91" strokeWidth="18" strokeDasharray="30 190" transform="rotate(220 50 50)"/></svg><div>{segments.slice(0,3).map((s,index)=><div key={index}><span>{s.segment||"Segment"}</span><b>{money(s.revenue||s.value)}</b></div>)}</div></div></section>
    <section className="gallery-dashboard-panel"><div className="gallery-panel-label" style={{color:item.accent}}>TIME ANALYSIS</div><h5>Quarterly revenue</h5><svg className="gallery-quarter-bars" viewBox="0 0 180 100">{quarters.slice(0,4).map((q,index)=>{const v=Number(q.revenue||q.value||0),max=Math.max(1,...quarters.map(x=>Number(x.revenue||x.value||0))),height=v/max*70;return <g key={index}><rect x={12+index*42} y={78-height} width="25" height={height} rx="3" fill={item.accent}/><text x={24+index*42} y="94" textAnchor="middle" fill={item.muted} fontSize="8">{q.quarter||"Q"+(index+1)}</text></g>})}</svg></section>
  </div>
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
