const API_BASE = "http://localhost:8000";

async function apiGet(path) {
  const res = await fetch(API_BASE + path);
  if (!res.ok) throw new Error("GET " + path + " failed: " + res.status);
  return res.json();
}
async function apiPost(path, body) {
  const opts = { method: "POST" };
  if (body instanceof FormData) {
    opts.body = body;
  } else if (body !== undefined) {
    opts.headers = { "Content-Type": "application/json" };
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(API_BASE + path, opts);
  if (!res.ok) throw new Error("POST " + path + " failed: " + res.status);
  return res.json();
}

const CURRENT_CASE = { id: "NX-2026-041" };
