import axios from "axios";

export const analyzeComplaint = async (text) => {
  const res = await axios.post("http://localhost:8000/api/analyze", {
    complaint: text,
  });
  return res.data;
};