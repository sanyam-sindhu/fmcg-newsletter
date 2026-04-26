import { useState, useEffect, useRef } from "react";
import { RefreshCw, Play, Newspaper, History, ChevronDown, Calendar } from "lucide-react";
import PipelineStats from "./components/PipelineStats";
import ArticleTable from "./components/ArticleTable";
import NewsletterView from "./components/NewsletterView";
import StatusBadge from "./components/StatusBadge";
import RunHistory from "./components/RunHistory";
import MarketSelector from "./components/MarketSelector";

const API = import.meta.env.VITE_API_URL || "";
const POLL_INTERVAL = 3000;
const TABS = ["Newsletter", "Raw Data"];
const LS_KEY = "fmcg_run_id";
const LS_MARKET = "fmcg_market";
const LS_DATE = "fmcg_date";

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

const MARKET_FLAG = {
  global: "🌐", india: "🇮🇳", usa: "🇺🇸",
  uk: "🇬🇧", europe: "🇪🇺", asia_pacific: "🌏",
};

const EXPORT_OPTIONS = [
  { key: "csv",  label: "CSV",   color: "text-gray-700" },
  { key: "excel",label: "Excel", color: "text-emerald-700" },
  { key: "word", label: "Word",  color: "text-blue-700" },
  { key: "pptx", label: "PPT",   color: "text-orange-600" },
];

function useDropdown() {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);
  return { open, setOpen, ref };
}

function ExportDropdown({ onDownload }) {
  const { open, setOpen, ref } = useDropdown();
  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-slate-800 text-white rounded-lg hover:bg-slate-700 transition-colors">
        Export
        <ChevronDown size={11} className={`transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="absolute right-0 mt-1 w-36 bg-white border border-slate-200 rounded-xl shadow-lg z-50 py-1 overflow-hidden">
          {EXPORT_OPTIONS.map(({ key, label, color }) => (
            <button
              key={key}
              onClick={() => { onDownload(key); setOpen(false); }}
              className={`w-full text-left px-4 py-2 text-xs font-medium hover:bg-slate-50 transition-colors ${color}`}>
              {label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function GenerateButton({ loading, market, markets, onChangeMarket, onGenerate }) {
  const { open, setOpen, ref } = useDropdown();
  const flag = MARKET_FLAG[market] || "🌐";
  const label = markets.find((m) => m.key === market)?.label || "Global";

  return (
    <div className="flex items-center" ref={ref}>
      <button
        onClick={onGenerate}
        disabled={loading}
        className="flex items-center gap-2 pl-4 pr-3 py-1.5 bg-blue-700 text-white text-xs font-semibold rounded-l-lg hover:bg-blue-800 disabled:opacity-50 transition-colors shadow-sm border-r border-blue-600">
        {loading ? <RefreshCw size={12} className="animate-spin" /> : <Play size={12} />}
        {loading ? "Running…" : "Generate"}
      </button>
      <button
        onClick={() => !loading && setOpen((v) => !v)}
        disabled={loading}
        className="flex items-center gap-1 pl-2 pr-2.5 py-1.5 bg-blue-700 text-white text-xs font-medium rounded-r-lg hover:bg-blue-800 disabled:opacity-50 transition-colors shadow-sm">
        <span>{flag}</span>
        <span className="hidden sm:inline">{label}</span>
        <ChevronDown size={10} className={`transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="absolute right-0 mt-1 w-44 bg-white border border-slate-200 rounded-xl shadow-lg z-50 py-1 overflow-hidden" style={{ top: "100%" }}>
          <div className="px-3 py-1.5 text-xs text-slate-400 font-semibold uppercase tracking-wide border-b border-slate-100">Select Market</div>
          {markets.map((m) => (
            <button
              key={m.key}
              onClick={() => { onChangeMarket(m.key); setOpen(false); }}
              className={`w-full text-left px-4 py-2 text-xs flex items-center gap-2 hover:bg-slate-50 transition-colors
                ${m.key === market ? "font-semibold text-blue-700" : "text-slate-700"}`}>
              <span>{MARKET_FLAG[m.key] || "🌐"}</span>
              <span>{m.label}</span>
              {m.key === market && <span className="ml-auto text-blue-500">✓</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [runId, setRunId] = useState(() => {
    const v = localStorage.getItem(LS_KEY);
    return v && v !== "undefined" ? v : null;
  });
  const [market, setMarket] = useState(() => localStorage.getItem(LS_MARKET) || "global");
  const [asOfDate, setAsOfDate] = useState(() => localStorage.getItem(LS_DATE) || todayStr());
  const [markets, setMarkets] = useState([]);
  const [status, setStatus] = useState(null);
  const [pipelineStats, setPipelineStats] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("Newsletter");
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const pollRef = useRef(null);

  const clearPoll = () => { if (pollRef.current) clearInterval(pollRef.current); };

  const fetchHistory = async () => {
    try {
      const data = await fetch(`${API}/api/history`).then((r) => r.json());
      setHistory(data.runs || []);
    } catch {}
  };

  const fetchStatus = async (id) => {
    const data = await fetch(`${API}/api/status/${id}`).then((r) => r.json());
    setStatus(data.status);
    if (data.article_counts) setPipelineStats(data.article_counts);
    return data.status;
  };

  const fetchResult = async (id) => {
    const res = await fetch(`${API}/api/result/${id}`);
    if (!res.ok) return;
    const data = await res.json();
    setResult(data);
    if (data.market) setMarket(data.market);
    if (data.pipeline_stats) setPipelineStats(data.pipeline_stats);
  };

  useEffect(() => {
    fetch(`${API}/api/markets`).then((r) => r.json()).then((d) => setMarkets(d.markets || []));
    fetchHistory();
    if (!runId) return;
    fetchStatus(runId).then((s) => { if (s === "generated") fetchResult(runId); });
  }, []);

  const startRun = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setPipelineStats(null);
    setStatus("started");
    clearPoll();

    try {
      const data = await fetch(`${API}/api/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ market, as_of_date: asOfDate }),
      }).then((r) => r.json());

      setRunId(data.run_id);
      if (data.run_id) localStorage.setItem(LS_KEY, data.run_id);
      localStorage.setItem(LS_MARKET, market);
      localStorage.setItem(LS_DATE, asOfDate);

      pollRef.current = setInterval(async () => {
        const s = await fetchStatus(data.run_id);
        if (s === "generated") {
          clearPoll();
          await fetchResult(data.run_id);
          await fetchHistory();
          setLoading(false);
        } else if (s?.startsWith("error")) {
          clearPoll();
          setError(s.replace("error:", ""));
          setLoading(false);
        }
      }, POLL_INTERVAL);
    } catch (e) {
      setError(e.message);
      setLoading(false);
    }
  };

  const loadRun = async (id) => {
    setRunId(id);
    localStorage.setItem(LS_KEY, id);
    setError(null);
    setResult(null);
    const s = await fetchStatus(id);
    if (s === "generated") await fetchResult(id);
    setShowHistory(false);
  };

  const changeMarket = (m) => {
    setMarket(m);
    localStorage.setItem(LS_MARKET, m);
  };

  const changeDate = (d) => {
    setAsOfDate(d);
    localStorage.setItem(LS_DATE, d);
  };

  const download = (type) => {
    if (!runId) return;
    window.open(`${API}/api/result/${runId}/${type}`, "_blank");
  };

  useEffect(() => () => clearPoll(), []);

  const marketLabel = markets.find((m) => m.key === market)?.label || "Global";
  const formattedDate = asOfDate
    ? new Date(asOfDate + "T00:00:00").toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })
    : "";

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200 px-6 py-4 shadow-sm">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="bg-blue-700 p-2 rounded-xl">
                <Newspaper className="text-white" size={18} />
              </div>
              <div>
                <h1 className="text-base font-bold text-slate-900 leading-tight tracking-tight">FMCG Intelligence</h1>
                <p className="text-xs text-slate-400">M&A Newsletter Generator</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {status && <StatusBadge status={status} />}

              {result && <ExportDropdown onDownload={download} />}

              <button
                onClick={() => { fetchHistory(); setShowHistory((v) => !v); }}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border rounded-lg transition-colors
                  ${showHistory
                    ? "border-blue-500 bg-blue-50 text-blue-700"
                    : "border-slate-200 text-slate-600 hover:bg-slate-50"}`}>
                <History size={12} />
                History
                {history.length > 0 && (
                  <span className="bg-slate-200 text-slate-600 text-xs rounded-full px-1.5 py-0.5 leading-none">
                    {history.length}
                  </span>
                )}
              </button>

              <div className="relative">
                <GenerateButton
                  loading={loading}
                  market={market}
                  markets={markets}
                  onChangeMarket={changeMarket}
                  onGenerate={startRun}
                />
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4 flex-wrap">
            <MarketSelector
              markets={markets}
              selected={market}
              onChange={changeMarket}
              disabled={loading}
            />
            <div className="h-4 w-px bg-slate-200" />
            <div className="flex items-center gap-1.5">
              <Calendar size={12} className="text-slate-400" />
              <span className="text-xs text-slate-400 font-medium">As of</span>
              <input
                type="date"
                value={asOfDate}
                max={todayStr()}
                onChange={(e) => changeDate(e.target.value)}
                disabled={loading}
                className="text-xs border border-slate-200 rounded-lg px-2 py-1 text-slate-600 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 cursor-pointer"
              />
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 space-y-5">
        {showHistory && (
          <RunHistory runs={history} currentRunId={runId} onSelect={loadRun} />
        )}

        {!runId && !loading && !showHistory && (
          <div className="text-center py-24">
            <div className="text-6xl mb-5">{MARKET_FLAG[market] || "🌐"}</div>
            <h2 className="text-xl font-semibold text-slate-600 mb-2">Ready to generate</h2>
            <p className="text-slate-400 max-w-sm mx-auto text-sm leading-relaxed">
              Choose a market and date, then click <strong className="text-slate-600">Generate</strong> to run the full pipeline — search, dedup, filter, credibility score, enrich, and compile.
            </p>
          </div>
        )}

        {result && (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-lg">{MARKET_FLAG[result.market] || "🌐"}</span>
            <span className="font-semibold text-slate-700">
              {markets.find((m) => m.key === result.market)?.label || "Global"}
            </span>
            <span className="text-slate-300">·</span>
            <span className="text-slate-500">{result.article_count} articles · {result.pipeline_stats?.raw} fetched</span>
            <span className="text-slate-300">·</span>
            <span className="font-mono text-xs text-slate-400">run:{result.run_id?.slice(0, 8)}</span>
          </div>
        )}

        {(loading || result) && pipelineStats && (
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">Pipeline</h2>
            <PipelineStats stats={pipelineStats} />
          </div>
        )}

        {loading && !result && (
          <div className="bg-white rounded-xl border border-slate-200 p-10 text-center shadow-sm">
            <div className="text-5xl mb-4">{MARKET_FLAG[market]}</div>
            <RefreshCw size={26} className="animate-spin mx-auto text-blue-600 mb-4" />
            <p className="text-slate-600 font-semibold">Searching {marketLabel} FMCG news…</p>
            <p className="text-slate-400 text-sm mt-1.5 font-mono tracking-tight">
              search → dedup → filter → credibility → enrich → generate
            </p>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">{error}</div>
        )}

        {result && (
          <>
            <div className="flex gap-0 border-b border-slate-200">
              {TABS.map((tab) => (
                <button key={tab} onClick={() => setActiveTab(tab)}
                  className={`px-5 py-2.5 text-sm font-medium transition-all
                    ${activeTab === tab
                      ? "border-b-2 border-blue-700 text-blue-700"
                      : "text-slate-400 hover:text-slate-600"}`}>
                  {tab}
                </button>
              ))}
            </div>

            {activeTab === "Newsletter" && (
              <NewsletterView
                draft={result.newsletter_draft}
                market={result.market}
                markets={markets}
                asOfDate={formattedDate}
              />
            )}

            {activeTab === "Raw Data" && (
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
                <h2 className="text-sm font-semibold text-slate-700 mb-4">
                  Source Articles <span className="text-slate-400 font-normal">({result.article_count})</span>
                </h2>
                <ArticleTable articles={result.articles} />
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
