import { useState } from "react";
import { analyzeComplaint } from "../services/api";

export default function ComplaintForm() {
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);

  const handleSubmit = async () => {
    const res = await analyzeComplaint(text);
    setResult(res);
  };

  return (
    <div>
      <textarea
        placeholder="Enter emergency..."
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <button onClick={handleSubmit}>Analyze</button>

      {result && (
        <div>
          <h3>{result.category}</h3>
          <p>{result.severity}</p>
        </div>
      )}
    </div>
  );
}