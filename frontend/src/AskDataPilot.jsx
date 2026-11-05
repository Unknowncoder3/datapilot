import { useEffect, useRef, useState } from "react";
import { askBusinessQuestion, getApiErrorMessage } from "./api.js";
import "./AskDataPilot.css";

const suggestions = [
  "What is the total revenue?",
  "Show me the top 5 products by revenue",
  "Which country has the highest sales?",
  "How many unique customers are there?",
];

const number = (value, format) => {
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value ?? "—");
  return format === "currency"
    ? n.toLocaleString("en-GB", { style: "currency", currency: "GBP", maximumFractionDigits: 2 })
    : n.toLocaleString("en-IN", { maximumFractionDigits: 2 });
};

export default function AskDataPilot({ dataset }) {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    setMessages([]);
    setQuestion("");
    setError("");
  }, [dataset?.id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  const ask = async (value) => {
    const prompt = String(value || question).trim();
    if (!prompt || busy || !dataset?.id) return;
    setError("");
    setQuestion("");
    setBusy(true);
    const history = messages.map((item) => ({ role: item.role, content: item.content }));
    setMessages((prev) => [...prev, { role: "user", content: prompt }]);
    try {
      const response = await askBusinessQuestion(dataset.id, prompt, history);
      const result = response.data || {};
      setMessages((prev) => [...prev, {
        role: "assistant",
        content: result.answer || "The analyst returned no explanation.",
        result,
      }]);
    } catch (err) {
      setError(getApiErrorMessage(err, "Could not answer this question."));
    } finally {
      setBusy(false);
    }
  };

  const reset = () => { setMessages([]); setError(""); setQuestion(""); };

  const exportConversation = () => {
    if (!messages.length) return;
    const transcript = messages.map((item) => `${item.role === "user" ? "You" : "DataPilot AI"}: ${item.content}`).join("\\n\\n");
    const markdown = `# DataPilot analysis transcript\\n\\nDataset: ${dataset.name || dataset.original_filename}\\n\\n${transcript}\\n`;
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `datapilot-analysis-${dataset.id}.md`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const lastAssistant = [...messages].reverse().find((item) => item.role === "assistant");

  if (!dataset?.id) return <section className="dp-ask-page"><div className="dp-ask-empty"><span>✦</span><h2>Select a dataset to begin</h2><p>Choose or upload a dataset in the workspace, then ask DataPilot questions about its contents.</p></div></section>;

  return (
    <section className="dp-ask-page">
      <header className="dp-ask-hero">
        <div><div className="dp-ask-kicker">PHASE 7 · NATURAL LANGUAGE ANALYST</div><h1>Ask DataPilot</h1><p>Ask business questions and get answers grounded in the selected dataset.</p></div>
        <div className="dp-ask-dataset"><span>ACTIVE DATASET</span><strong>{dataset.name || dataset.original_filename}</strong><small>{Number(dataset.row_count || 0).toLocaleString("en-IN")} rows · {Number(dataset.column_count || 0).toLocaleString("en-IN")} columns</small></div>
      </header>
      <div className="dp-ask-workspace">
        <div className="dp-ask-chat-head"><div><span className="dp-ask-status-dot"/><strong>DataPilot Analyst</strong><small>Answers use dataset evidence</small></div><div className="dp-ask-head-actions"><button onClick={exportConversation} disabled={!messages.length || busy}>Export chat ↓</button><button onClick={reset} disabled={!messages.length || busy}>Clear chat</button></div></div>
        {!messages.length ? <div className="dp-ask-welcome"><div className="dp-ask-orb">✦</div><h2>What would you like to understand?</h2><p>Start with a question or choose a prompt below.</p><div className="dp-ask-suggestions">{suggestions.map((item) => <button key={item} onClick={() => ask(item)} disabled={busy}>{item}<span>↗</span></button>)}</div></div> :
          <div className="dp-ask-messages">{messages.map((item, index) => <article key={index} className={`dp-ask-message dp-ask-${item.role}`}>
            <div className="dp-ask-message-label">{item.role === "user" ? "YOU" : "DATAPILOT AI"}</div><p>{item.content}</p>
            {item.result?.metric && <div className="dp-ask-metric"><span>{item.result.metric.label}</span><strong>{number(item.result.metric.value, item.result.metric.format)}</strong></div>}
            {item.result?.chart?.data?.length > 0 && <div className="dp-ask-chart"><h3>{item.result.chart.title}</h3>{item.result.chart.data.slice(0,12).map((row, i, arr) => { const max = Math.max(1, ...arr.map((r) => Math.abs(Number(r.value || 0)))); return <div className="dp-ask-bar-row" key={i}><span title={row.label}>{row.label}</span><i><b style={{width: `${Math.min(100, Math.abs(Number(row.value || 0)) / max * 100)}%`}}/></i><strong>{number(row.value, item.result.chart.metric === "revenue" ? "currency" : "number")}</strong></div>; })}</div>}
            {item.result?.clarification_required && item.result?.suggested_metrics && <div className="dp-ask-clarify">{item.result.suggested_metrics.map((metric) => <button key={metric} onClick={() => ask(`Rank the best product by ${metric}`)} disabled={busy}>{metric.replaceAll("_", " ")}</button>)}</div>}
            {item.result?.rows_analyzed != null && <small className="dp-ask-source">Dataset source · {Number(item.result.rows_analyzed).toLocaleString("en-IN")} rows analyzed</small>}
          </article>)}</div>}
        {lastAssistant?.result?.chart?.data?.length > 0 && !busy && <div className="dp-ask-followups"><span>EXPLORE FURTHER</span><button onClick={() => ask("Explain this result")}>Explain this result ↗</button><button onClick={() => ask("Show me more results")}>Show more results ↗</button></div>}{error && <div className="dp-ask-error" role="alert">{error}</div>}
        {busy && <div className="dp-ask-thinking"><span/><span/><span/>Analyzing dataset…</div>}
        <form className="dp-ask-composer" onSubmit={(event) => { event.preventDefault(); ask(); }}><textarea value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask a question about your data…" maxLength={500} rows={2} disabled={busy}/><div><small>{question.length}/500 · Enter to send, Shift+Enter for a new line</small><button type="submit" disabled={busy || !question.trim()}>{busy ? "Analyzing…" : "Ask ↗"}</button></div></form>
      </div>
      <div ref={bottomRef}/>
      <p className="dp-ask-disclaimer">Answers are generated from supported dataset analyses. They describe observed patterns and do not establish causation.</p>
    </section>
  );
}
