import type { FaultState, LoadJob, LoadProfile, MetricsResponse } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status = 0) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch (error) {
    throw new ApiError(error instanceof Error ? error.message : "Сетевая ошибка запроса");
  }

  const body = await response.json().catch(() => undefined);
  if (!response.ok) {
    const detail = Array.isArray(body?.detail)
      ? body.detail.map((item: { msg?: string }) => item.msg ?? "Некорректный запрос").join("; ")
      : body?.detail;
    throw new ApiError(detail ?? `Запрос завершился с HTTP ${response.status}`, response.status);
  }
  return body as T;
}

export function validateLoadProfile(profile: Partial<LoadProfile>): string[] {
  const errors: string[] = [];
  if (!profile.kind) errors.push("Выберите тип нагрузки");
  if (!profile.duration_seconds || profile.duration_seconds < 1 || profile.duration_seconds > 300) {
    errors.push("Длительность должна быть от 1 до 300 секунд");
  }
  if (profile.intensity !== undefined && (!Number.isFinite(profile.intensity) || profile.intensity < 0 || profile.intensity > 1)) {
    errors.push("Интенсивность должна быть от 0 до 1");
  }
  if (profile.memory_mb !== undefined && (!Number.isInteger(profile.memory_mb) || profile.memory_mb < 1 || profile.memory_mb > 512)) {
    errors.push("Память должна быть от 1 до 512 МиБ");
  }
  if (profile.disk_mb !== undefined && (!Number.isInteger(profile.disk_mb) || profile.disk_mb < 1 || profile.disk_mb > 256)) {
    errors.push("Размер диска должен быть от 1 до 256 МиБ");
  }
  if (profile.concurrency !== undefined && (!Number.isInteger(profile.concurrency) || profile.concurrency < 1 || profile.concurrency > 50)) {
    errors.push("Параллельность должна быть от 1 до 50");
  }
  if (profile.workers !== undefined && (!Number.isInteger(profile.workers) || profile.workers < 1 || profile.workers > 8)) {
    errors.push("Количество процессов должно быть от 1 до 8");
  }
  return errors;
}

export const api = {
  getMetrics: (signal?: AbortSignal) => request<MetricsResponse>("/api/metrics", { signal }),
  getJobs: (signal?: AbortSignal) => request<LoadJob[]>("/api/load/jobs", { signal }),
  startJob: async (profile: LoadProfile) => {
    const errors = validateLoadProfile(profile);
    if (errors.length) throw new ApiError(errors.join("; "));
    return request<LoadJob>("/api/load/jobs", { method: "POST", body: JSON.stringify(profile) });
  },
  stopJob: (id: string) => request<LoadJob>(`/api/load/jobs/${id}`, { method: "DELETE" }),
  getFaults: (signal?: AbortSignal) => request<FaultState>("/api/faults", { signal }),
  updateFaults: (patch: Partial<FaultState>) =>
    request<FaultState>("/api/faults", { method: "PATCH", body: JSON.stringify(patch) }),
};

