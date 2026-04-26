const STATUS_CONFIG = {
  started:             { label: "Starting",            color: "bg-slate-100 text-slate-600" },
  searched:            { label: "Searching News",       color: "bg-blue-100 text-blue-700" },
  deduplicated:        { label: "Deduplicating",        color: "bg-indigo-100 text-indigo-700" },
  filtered:            { label: "Filtering",            color: "bg-amber-100 text-amber-700" },
  credibility_checked: { label: "Credibility Check",   color: "bg-orange-100 text-orange-700" },
  enriched:            { label: "Enriching",            color: "bg-purple-100 text-purple-700" },
  generated:           { label: "Complete",             color: "bg-emerald-100 text-emerald-700" },
  running:             { label: "Running",              color: "bg-blue-100 text-blue-700" },
};

export default function StatusBadge({ status }) {
  const config = STATUS_CONFIG[status] || { label: status, color: "bg-slate-100 text-slate-600" };
  const isRunning = status !== "generated" && !status?.startsWith("error");

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${config.color}`}>
      {isRunning && status && status !== "started" && (
        <span className="w-1.5 h-1.5 rounded-full bg-current opacity-75 animate-pulse" />
      )}
      {config.label}
    </span>
  );
}
