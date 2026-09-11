const BASE = import.meta.env.VITE_API_URL || "";

async function request(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, options);
  let data = null;
  const text = await response.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }
  if (!response.ok) {
    const detail = data?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg || JSON.stringify(item)).join(" ")
      : detail || `Request failed (${response.status})`;
    throw new Error(message);
  }
  return data;
}

export const api = {
  health: () => request("/api/health"),
  documents: () => request("/api/documents"),
  upload: (file) => {
    const body = new FormData();
    body.append("file", file);
    return request("/api/documents/upload", { method: "POST", body });
  },
  remove: (id) => request(`/api/documents/${id}`, { method: "DELETE" }),
  ask: (question, top_k = 5) =>
    request("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k }),
    }),
  search: (query, top_k = 8) =>
    request("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k }),
    }),
};
