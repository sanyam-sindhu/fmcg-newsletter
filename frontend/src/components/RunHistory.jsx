const STATUS_COLOR = {
  generated:           "bg-emerald-100 text-emerald-700",
  enriched:            "bg-purple-100 text-purple-700",
  credibility_checked: "bg-orange-100 text-orange-700",
  filtered:            "bg-amber-100 text-amber-700",
  running:             "bg-blue-100 text-blue-700",
  done:                "bg-emerald-100 text-emerald-700",
};

const MARKET_FLAG = {
  global: "🌐", india: "🇮🇳", usa: "🇺🇸",
  uk: "🇬🇧", europe: "🇪🇺", asia_pacific: "🌏",
};

export default function RunHistory({ runs, currentRunId, onSelect }) {
  if (!runs?.length) return null;

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
      <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">Previous Runs</h2>
      <div className="space-y-1.5">
        {runs.map((r) => (
          <div
            key={r.run_id}
            onClick={() => r.status === "generated" && onSelect(r.run_id)}
            className={`flex items-center justify-between px-3 py-2.5 rounded-lg border text-sm transition-colors
              ${r.run_id === currentRunId ? "border-blue-400 bg-blue-50" : "border-slate-100 hover:bg-slate-50"}
              ${r.status === "generated" ? "cursor-pointer" : "opacity-50 cursor-not-allowed"}`}
          >
            <div className="flex items-center gap-2.5">
              <span className="text-base">{MARKET_FLAG[r.market] || "🌐"}</span>
              <span className="font-mono text-xs text-slate-400">{r.run_id.slice(0, 8)}</span>
              {r.article_count > 0 && (
                <span className="text-xs text-slate-500">{r.article_count} articles</span>
              )}
              <span className="text-xs text-slate-400 capitalize">{(r.market || "global").replace("_", "-")}</span>
            </div>
            <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${STATUS_COLOR[r.status] || "bg-slate-100 text-slate-500"}`}>
              {r.status === "generated" ? "complete" : r.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
