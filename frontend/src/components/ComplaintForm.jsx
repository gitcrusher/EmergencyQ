/**
 * ComplaintForm.jsx
 * Text area + submit button for entering an emergency complaint.
 */

import { useState } from "react";

const PLACEHOLDER =
  "Describe the emergency in detail — include location, number of people affected, and any visible hazards…";

export default function ComplaintForm({ onSubmit, loading }) {
  const [text, setText] = useState("");

  const handleSubmit = () => {
    if (text.trim().length < 10) return;
    onSubmit(text.trim());
  };

  const charCount = text.length;
  const tooShort  = charCount > 0 && charCount < 10;
  const tooLong   = charCount > 2000;

  return (
    <div className="bg-white rounded-2xl shadow-md p-6 space-y-4">
      <h2 className="text-lg font-semibold text-gray-800">Submit Emergency Complaint</h2>

      <textarea
        className={`w-full h-36 resize-none rounded-lg border p-3 text-sm text-gray-700
          focus:outline-none focus:ring-2 transition
          ${tooLong
            ? "border-red-400 focus:ring-red-300"
            : "border-gray-300 focus:ring-blue-400"}`}
        placeholder={PLACEHOLDER}
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={loading}
        maxLength={2100}
      />

      <div className="flex items-center justify-between">
        <span className={`text-xs ${tooLong ? "text-red-500" : "text-gray-400"}`}>
          {charCount} / 2000 characters
          {tooShort && " — minimum 10 characters"}
        </span>

        <button
          onClick={handleSubmit}
          disabled={loading || tooShort || tooLong || charCount === 0}
          className="px-5 py-2 rounded-lg bg-red-600 hover:bg-red-700 active:bg-red-800
            text-white font-semibold text-sm transition disabled:opacity-50
            disabled:cursor-not-allowed flex items-center gap-2"
        >
          {loading ? (
            <>
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"
                  className="opacity-25" />
                <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="4"
                  className="opacity-75" strokeLinecap="round" />
              </svg>
              Analyzing…
            </>
          ) : (
            "🚨 Analyze"
          )}
        </button>
      </div>
    </div>
  );
}