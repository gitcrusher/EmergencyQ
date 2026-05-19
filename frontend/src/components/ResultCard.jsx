/**
 * ResultCard.jsx
 * Displays the full analysis result from /api/analyze.
 */

import { SeverityBadge, UrgencyBadge } from "./SeverityBadge";
import UncertaintyBanner from "./UncertaintyBanner";
import SimilarIncidents from "./SimilarIncidents";

const CATEGORY_ICONS = {
  Fire:     "🔥",
  Flood:    "🌊",
  Medical:  "🏥",
  Accident: "🚗",
  Other:    "⚡",
};

function AtomicFacts({ facts }) {
  const entries = Object.entries(facts).filter(([, v]) => v);
  if (entries.length === 0) return null;
  return (
    <div className="rounded-lg bg-blue-50 border border-blue-100 p-4">
      <p className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-2">
        Atomic Facts Extracted  <span className="font-normal normal-case text-blue-500">(Novelty ①)</span>
      </p>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-1">
        {entries.map(([key, val]) => (
          <div key={key} className="flex gap-1">
            <dt className="text-xs text-blue-600 capitalize font-medium w-24 shrink-0">
              {key.replace("_", " ")}:
            </dt>
            <dd className="text-xs text-blue-900 font-semibold">{val}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export default function ResultCard({ result }) {
  if (!result) return null;

  const icon = CATEGORY_ICONS[result.category] || "🚨";

  return (
    <div className="bg-white rounded-2xl shadow-md p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <span className="text-4xl">{icon}</span>
          <div>
            <p className="text-xl font-bold text-gray-900">{result.category}</p>
            <p className="text-xs text-gray-400 font-mono">ID: {result.complaint_id}</p>
          </div>
        </div>
        <div className="flex gap-2 items-center flex-wrap">
          <SeverityBadge severity={result.severity} />
          <UrgencyBadge urgency={result.urgency} />
          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
            {(result.confidence * 100).toFixed(1)}% confidence
          </span>
        </div>
      </div>

      {/* Uncertainty banner */}
      <UncertaintyBanner predictionSet={result.prediction_set} />

      {/* Atomic facts */}
      <AtomicFacts facts={result.atomic_facts} />

      {/* Similar incidents */}
      <SimilarIncidents incidents={result.similar_incidents} />
    </div>
  );
}