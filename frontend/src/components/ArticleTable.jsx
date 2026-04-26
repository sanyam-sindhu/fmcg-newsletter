export default function ArticleTable({ articles }) {
  if (!articles?.length) return null;

  const badge = (score) => {
    const pct = Math.round(score * 100);
    const color = pct >= 80 ? "bg-green-100 text-green-800" : pct >= 60 ? "bg-yellow-100 text-yellow-800" : "bg-red-100 text-red-800";
    return <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${color}`}>{pct}%</span>;
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left border-collapse">
        <thead>
          <tr className="border-b border-gray-200 text-xs text-gray-500 uppercase">
            <th className="py-2 pr-4">Title</th>
            <th className="py-2 pr-4">Source</th>
            <th className="py-2 pr-4">Deal Type</th>
            <th className="py-2 pr-4">Companies</th>
            <th className="py-2 pr-4">Value</th>
            <th className="py-2 pr-4">Relevance</th>
            <th className="py-2">Credibility</th>
          </tr>
        </thead>
        <tbody>
          {articles.map((a) => (
            <tr key={a.id} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="py-2 pr-4 max-w-xs">
                <a href={a.url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline line-clamp-2">
                  {a.title}
                </a>
              </td>
              <td className="py-2 pr-4 text-gray-500 whitespace-nowrap">{a.source}</td>
              <td className="py-2 pr-4">
                <span className="bg-purple-100 text-purple-700 text-xs px-2 py-0.5 rounded-full">{a.deal_type || "—"}</span>
              </td>
              <td className="py-2 pr-4 text-gray-700">{(a.companies || []).join(", ") || "—"}</td>
              <td className="py-2 pr-4 text-gray-700 whitespace-nowrap">{a.deal_value || "Undisclosed"}</td>
              <td className="py-2 pr-4">{badge(a.relevance_score)}</td>
              <td className="py-2">{badge(a.credibility_score)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
