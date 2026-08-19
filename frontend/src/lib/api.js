const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  // Targets
  listTargets: () => request("/targets"),
  createTarget: (payload) =>
    request("/targets", { method: "POST", body: JSON.stringify(payload) }),
  deleteTarget: (id) => request(`/targets/${id}`, { method: "DELETE" }),

  // Scans
  startScan: (targetId) =>
    request("/scans", {
      method: "POST",
      body: JSON.stringify({ target_id: targetId }),
    }),
  getScan: (id) => request(`/scans/${id}`),
  getAttackLogs: (scanId) => request(`/scans/${scanId}/attack-logs`),

  // Vulnerabilities
  listVulnerabilities: (scanId) =>
    request(`/vulnerabilities${scanId ? `?scan_id=${scanId}` : ""}`),

  // Patches
  generatePatch: (vulnerabilityId) =>
    request(`/patches/generate/${vulnerabilityId}`, { method: "POST" }),
  listPatches: (vulnerabilityId) => request(`/patches/${vulnerabilityId}`),
};

export function scanStreamUrl(scanId) {
  return `${BASE}/scans/${scanId}/stream`;
}
