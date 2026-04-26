const FLAG = {
  global:       "🌐",
  india:        "🇮🇳",
  usa:          "🇺🇸",
  uk:           "🇬🇧",
  europe:       "🇪🇺",
  asia_pacific: "🌏",
};

export default function MarketSelector({ markets, selected, onChange, disabled }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-slate-400 font-medium shrink-0">Market</span>
      <div className="flex gap-1 flex-wrap">
        {markets.map((m) => (
          <button
            key={m.key}
            onClick={() => !disabled && onChange(m.key)}
            disabled={disabled}
            className={`flex items-center gap-1 px-3 py-1 text-xs rounded-full border font-medium transition-all
              ${selected === m.key
                ? "bg-blue-700 text-white border-blue-700 shadow-sm"
                : "bg-white text-slate-500 border-slate-200 hover:border-blue-300 hover:text-blue-700"
              } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
          >
            <span>{FLAG[m.key] || "🌐"}</span>
            <span>{m.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
