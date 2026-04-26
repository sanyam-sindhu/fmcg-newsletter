export default function PipelineStats({ stats }) {
  const steps = [
    { label: "Raw Articles", key: "raw", color: "bg-gray-100 border-gray-200" },
    { label: "After Dedup", key: "after_dedup", color: "bg-blue-50 border-blue-200" },
    { label: "After Filter", key: "after_filter", color: "bg-yellow-50 border-yellow-200" },
    { label: "Final (Credible)", key: "after_credibility", color: "bg-green-50 border-green-200" },
  ];

  return (
    <div className="flex items-center gap-0">
      {steps.map((step, i) => (
        <div key={step.key} className="flex items-center flex-1">
          <div className={`flex-1 rounded-lg border p-4 ${step.color}`}>
            <div className="text-2xl font-bold text-gray-800">{stats[step.key] ?? 0}</div>
            <div className="text-xs text-gray-500 mt-1">{step.label}</div>
          </div>
          {i < steps.length - 1 && (
            <div className="px-2 text-gray-300 text-lg font-light">→</div>
          )}
        </div>
      ))}
    </div>
  );
}
