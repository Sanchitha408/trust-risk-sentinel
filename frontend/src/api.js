import axios from "axios";

const API_BASE = "http://127.0.0.1:8000";

export const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

export async function screenTransaction(payload) {
  const res = await api.post("/screen", payload);
  return res.data;
}

export async function getAuditLog(limit = 50) {
  const res = await api.get(`/audit-log?limit=${limit}`);
  return res.data;
}
