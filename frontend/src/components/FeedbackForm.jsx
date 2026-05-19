/**
 * FeedbackForm.jsx  —  Novelty ④
 * Allows a responder to submit actual observed severity,
 * triggering adaptive weight updates in the backend.
 */

import { useState } from "react";
import { submitFeedback } from "../services/api";

const SEVERITIES = ["Critical", "High", "Moderate", "Low"];

export default function FeedbackForm({ result }) {
  const [actualSeverity, setActualSeverity] = useState("");
  const [notes, setNotes]                   = useState("");
  const [status, setStatus]                 = useState(null);   // null | "success" | "error"
  const [message, setMessage]               = useState("");
  const [loading, setLoading]               = useState(false);

  if (!result) return null;

  const handleSubmit = async () => {
    if (!actualSeverity) return;
    setLoading(true);
    setStatus(null);
    try {
      const res = await submitFeedback({
        complaint_id:       result.complaint_id,
        predicted_severity: result.severity,
        actual_severity:    actualSeverity,
        responder_notes:    notes || null,
      });
      setStatus("success");
      setMessage(res.message);
    } catch (err) {
      setStatus("error");
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-md p-6 space-y-4">
      <div className="flex items-center gap-2">
        <span className="text-lg">📋</span>
        <h3 className="font-semibold text-gray-800 text-sm">
          Responder Feedback{" "}
          <span className="text-gray-400 font-normal">(Adaptive Severity ④)</span>
        </h3>
      </div>

      <p className="text-xs text-gray-500">
        Model predicted:{" "}
        <strong className="text-gray-700">{result.severity}</strong>.
        If the actual severity on scene was different, select it below.
      </p>

      {/* Severity selector */}
      <div className="flex gap-2 flex-wrap">
        {SEVERITIES.map((s) => (
          <button
            key={s}
            onClick={() => setActualSeverity(s)}
            className={`px-3 py-1.5 rounded-lg border text-sm font-medium transition
              ${actualSeverity === s
                ? "bg-red-600 text-white border-red-600"
                : "bg-white text-gray-700 border-gray-300 hover:border-red-400"}`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Notes */}
      <textarea
        className="w-full h-20 resize-none rounded-lg border border-gray-300 p-3 text-sm
          text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
        placeholder="Optional: describe what you found on arrival…"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        maxLength={1000}
        disabled={loading}
      />

      {/* Submit */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <button
          onClick={handleSubmit}
          disabled={!actualSeverity || loading || status === "success"}
          className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white
            text-sm font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Submitting…" : "Submit Feedback"}
        </button>

        {status === "success" && (
          <p className="text-sm text-green-600 font-medium">✓ {message}</p>
        )}
        {status === "error" && (
          <p className="text-sm text-red-600 font-medium">✗ {message}</p>
        )}
      </div>
    </div>
  );
}