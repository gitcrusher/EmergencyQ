/**
 * SeverityBadge.jsx
 * Colored pill badge for severity and urgency labels.
 */

const SEVERITY_STYLES = {
  Critical: "bg-red-100 text-red-800 border-red-300",
  High:     "bg-orange-100 text-orange-800 border-orange-300",
  Moderate: "bg-yellow-100 text-yellow-800 border-yellow-300",
  Low:      "bg-green-100 text-green-800 border-green-300",
};

const URGENCY_STYLES = {
  Immediate: "bg-red-600 text-white",
  Urgent:    "bg-orange-500 text-white",
  Medium:    "bg-yellow-500 text-white",
  Normal:    "bg-gray-400 text-white",
};

export function SeverityBadge({ severity }) {
  const cls = SEVERITY_STYLES[severity] || "bg-gray-100 text-gray-700 border-gray-200";
  return (
    <span className={`inline-block px-3 py-0.5 rounded-full border text-xs font-semibold ${cls}`}>
      {severity}
    </span>
  );
}

export function UrgencyBadge({ urgency }) {
  const cls = URGENCY_STYLES[urgency] || "bg-gray-400 text-white";
  return (
    <span className={`inline-block px-3 py-0.5 rounded-full text-xs font-bold uppercase tracking-wide ${cls}`}>
      {urgency}
    </span>
  );
}