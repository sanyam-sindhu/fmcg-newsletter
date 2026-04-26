function renderInline(text) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

function renderLine(line, i) {
  const trimmed = line.trim();

  if (/^#{1,3}\s/.test(trimmed)) {
    const text = trimmed.replace(/^#{1,3}\s*/, "");
    return (
      <h2 key={i} className="text-sm font-bold text-slate-800 mt-6 mb-2 uppercase tracking-widest border-b border-slate-100 pb-1.5">
        {renderInline(text)}
      </h2>
    );
  }

  if (/^\*\*[^*]+\*\*$/.test(trimmed)) {
    return (
      <h3 key={i} className="text-sm font-semibold text-blue-800 mt-4 mb-1">
        {trimmed.slice(2, -2)}
      </h3>
    );
  }

  if (/^(\d+)\.\s/.test(trimmed)) {
    const text = trimmed.replace(/^\d+\.\s*/, "");
    return (
      <div key={i} className="mt-3 mb-1 font-semibold text-slate-800 text-sm">
        {renderInline(text)}
      </div>
    );
  }

  if (/^[-•]\s/.test(trimmed)) {
    const text = trimmed.replace(/^[-•]\s*/, "");
    return (
      <div key={i} className="flex gap-2 ml-3 mb-0.5">
        <span className="text-blue-500 shrink-0 mt-0.5 text-xs">◆</span>
        <p className="text-sm text-slate-600 leading-relaxed">{renderInline(text)}</p>
      </div>
    );
  }

  if (trimmed === "") return <div key={i} className="h-1.5" />;

  return (
    <p key={i} className="text-sm text-slate-600 leading-relaxed mb-1">
      {renderInline(trimmed)}
    </p>
  );
}

export default function NewsletterView({ draft, asOfDate }) {
  const lines = (draft || "").split("\n");
  const dateLabel = asOfDate || new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });

  return (
    <div className="max-w-none">
      <div className="bg-gradient-to-br from-slate-900 via-blue-950 to-blue-900 text-white rounded-t-xl px-8 py-6">
        <div className="text-xs uppercase tracking-widest text-blue-300 mb-2 font-semibold">FMCG Intelligence · M&A Briefing</div>
        <h1 className="text-2xl font-bold tracking-tight">FMCG M&A Newsletter</h1>
        <div className="flex items-center gap-3 mt-2">
          <span className="text-blue-300 text-sm">{dateLabel}</span>
          <span className="w-1 h-1 rounded-full bg-blue-500"></span>
          <span className="text-blue-400 text-xs font-mono">Powered by LangGraph + Claude</span>
        </div>
      </div>
      <div className="border border-t-0 border-slate-200 rounded-b-xl px-8 py-7 bg-white shadow-sm">
        {lines.map((line, i) => renderLine(line, i))}
      </div>
    </div>
  );
}
