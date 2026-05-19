/**
 * UncertaintyBanner.jsx  —  Novelty ②
 * Displays a prominent warning when the conformal prediction set
 * contains more than one label, signalling model uncertainty.
 */

export default function UncertaintyBanner({ predictionSet }) {
  if (!predictionSet || predictionSet.length <= 1) return null;

  const labels = predictionSet.join(", ");

  return (
    <div className="flex items-start gap-3 bg-amber-50 border-l-4 border-amber-500
      rounded-md p-4 shadow-sm">
      <span className="text-amber-500 text-xl select-none">⚠</span>
      <div>
        <p className="font-semibold text-amber-800 text-sm">
          Model Uncertainty Detected
        </p>
        <p className="text-amber-700 text-sm mt-0.5">
          This complaint could belong to:{" "}
          <strong>{labels}</strong>.{" "}
          Treat as <strong>{predictionSet[0]}</strong> (highest risk) until
          a responder confirms the category on scene.
        </p>
        <p className="text-amber-600 text-xs mt-1">
          Conformal prediction set — guaranteed to contain the true label
          with ≥ 95 % probability.
        </p>
      </div>
    </div>
  );
}