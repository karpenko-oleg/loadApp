from .metrics import MetricsStore


def render_prometheus(store: MetricsStore) -> str:
    snapshot = store.latest()
    values = {
        "vps_lab_cpu_percent": snapshot.cpu_percent,
        "vps_lab_load_1m": snapshot.load_1m,
        "vps_lab_memory_percent": snapshot.memory_percent,
        "vps_lab_memory_available_mb": snapshot.memory_available_mb,
        "vps_lab_disk_usage_percent": snapshot.disk_usage_percent,
        "vps_lab_disk_read_mb": snapshot.disk_read_mb,
        "vps_lab_disk_write_mb": snapshot.disk_write_mb,
        "vps_lab_network_rx_mb": snapshot.network_rx_mb,
        "vps_lab_network_tx_mb": snapshot.network_tx_mb,
        "vps_lab_process_count": snapshot.process_count,
        "vps_lab_api_latency_ms": snapshot.api_latency_ms,
        "vps_lab_api_requests_total": snapshot.api_requests,
        "vps_lab_api_errors_total": snapshot.api_errors,
    }
    return "".join(f"{name} {value}\n" for name, value in values.items())

