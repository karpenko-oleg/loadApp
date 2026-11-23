export type ConnectionState = "connecting" | "online" | "stale" | "offline";
export type LoadKind = "cpu" | "memory" | "disk" | "http";

export interface MetricsSnapshot {
  timestamp: string;
  cpu_percent: number;
  load_1m: number;
  memory_percent: number;
  memory_available_mb: number;
  disk_usage_percent: number;
  disk_read_mb: number;
  disk_write_mb: number;
  network_rx_mb: number;
  network_tx_mb: number;
  process_count: number;
  api_latency_ms: number;
  api_requests: number;
  api_errors: number;
}

export interface MetricsResponse {
  latest: MetricsSnapshot;
  history: MetricsSnapshot[];
}

export interface LoadProfile {
  kind: LoadKind;
  duration_seconds: number;
  intensity?: number;
  workers?: number;
  memory_mb?: number;
  disk_mb?: number;
  concurrency?: number;
}

export interface LoadJob {
  id: string;
  profile: LoadProfile;
  status: "queued" | "running" | "completed" | "stopped" | "failed";
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  error?: string | null;
}

export interface FaultState {
  api_delay_ms: number;
  error_rate: number;
  readiness_degraded: boolean;
}

export interface LabEvent {
  id: string;
  timestamp: string;
  message: string;
  tone: "info" | "warning" | "error" | "success";
}

