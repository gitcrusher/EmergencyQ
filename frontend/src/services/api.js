/**
 * src/services/api.js
 * Central Axios instance + typed API calls.
 */

import axios from "axios";

// Use relative URL "" so Vite's dev proxy forwards /api/* to the backend.
// For production, set VITE_API_URL to the deployed backend URL.
const BASE_URL = import.meta.env.VITE_API_URL || "";

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 120_000,
  headers: { "Content-Type": "application/json" },
});

// ── Intercept errors globally ────────────────────────────────────────────────
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const message =
      err.response?.data?.detail ||
      err.message ||
      "Unknown network error";
    return Promise.reject(new Error(message));
  }
);

// ── API calls ────────────────────────────────────────────────────────────────

/**
 * POST /api/analyze
 * @param {string} complaint  Free-text complaint text.
 * @returns {Promise<AnalyzeResponse>}
 */
export const analyzeComplaint = (complaint) =>
  api.post("/api/analyze", { complaint }).then((r) => r.data);

/**
 * POST /api/feedback
 * @param {object} payload  { complaint_id, predicted_severity, actual_severity, responder_notes }
 * @returns {Promise<FeedbackResponse>}
 */
export const submitFeedback = (payload) =>
  api.post("/api/feedback", payload).then((r) => r.data);

/**
 * GET /api/health
 */
export const healthCheck = () =>
  api.get("/api/health").then((r) => r.data);