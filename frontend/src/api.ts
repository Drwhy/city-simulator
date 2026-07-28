import type {
  BuildingDetail,
  CitizenDetail,
  IncidentDetail,
  SocialGraphData,
  VehicleDetail,
} from "./types/city";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? `Erreur HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function getCitizen(id: number): Promise<CitizenDetail> {
  return request<CitizenDetail>(`/api/citizens/${id}`);
}
export function getVehicle(id: number): Promise<VehicleDetail> {
  return request<VehicleDetail>(`/api/vehicles/${id}`);
}
export function getIncident(id: number): Promise<IncidentDetail> {
  return request<IncidentDetail>(`/api/incidents/${id}`);
}
export function getBuilding(id: number): Promise<BuildingDetail> {
  return request<BuildingDetail>(`/api/buildings/${id}`);
}
export function getSocialGraph(): Promise<SocialGraphData> {
  return request<SocialGraphData>("/api/social/graph");
}

export function pauseSimulation(): Promise<{ paused: boolean }> {
  return request("/api/simulation/pause", { method: "POST" });
}

export function resumeSimulation(): Promise<{ paused: boolean }> {
  return request("/api/simulation/resume", { method: "POST" });
}

export function setSimulationSpeed(speed: number): Promise<{ speed: number }> {
  return request("/api/simulation/speed", {
    method: "POST",
    body: JSON.stringify({ speed }),
  });
}

export function stepSimulation(minutes: number): Promise<unknown> {
  return request("/api/simulation/step", {
    method: "POST",
    body: JSON.stringify({ minutes }),
  });
}

export function resetCity(seed = 12345): Promise<unknown> {
  return request("/api/city/reset", {
    method: "POST",
    body: JSON.stringify({ seed }),
  });
}

export function saveCity(): Promise<{ saved: boolean; path: string }> {
  return request("/api/city/save", { method: "POST" });
}

export function loadCity(): Promise<unknown> {
  return request("/api/city/load", { method: "POST" });
}
