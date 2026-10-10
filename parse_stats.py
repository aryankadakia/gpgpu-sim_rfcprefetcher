import re
from pathlib import Path


# --------------------------------------------------
# Configuration
# --------------------------------------------------

BASE_DIR = Path("sim_run_11.2")
OUTPUT_FILE = Path("test_stats_10_1_26.txt")

INTEGER = r"\d+"
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"


# --------------------------------------------------
# Metrics (also determines output column order)
# --------------------------------------------------

patterns = {
    # MRF statistics
    "mrf_reads": INTEGER,
    "mrf_writes": INTEGER,
    "mrf_bank_conflicts": INTEGER,
    "mrf_port_occupancy": INTEGER,
    "mrf_port_capacity": INTEGER,
    "mrf_global_port_utilization": NUMBER,
    "mrf_busy_cycle_occupancy": INTEGER,
    "mrf_busy_cycle_capacity": INTEGER,
    "mrf_busy_cycle_utilization": NUMBER,
    "mrf_active_cycles": INTEGER,
    "sm_active_cycles": INTEGER,
    "mrf_active_cycles_percentage": NUMBER,

    # RFC statistics
    "rfc_read_hits": INTEGER,
    "rfc_read_misses": INTEGER,
    "rfc_evictions": INTEGER,
    "warp_demotions": INTEGER,
    "rfc_flush_entries": INTEGER,
}

column_names = {
    "mrf_reads": "MRF Reads",
    "mrf_writes": "MRF Writes",
    "mrf_bank_conflicts": "Bank Conf",
    "mrf_port_occupancy": "MRF Occ",
    "mrf_port_capacity": "MRF Cap",
    "mrf_global_port_utilization": "MRF Util",
    "mrf_busy_cycle_occupancy": "Busy Occ",
    "mrf_busy_cycle_capacity": "Busy Cap",
    "mrf_busy_cycle_utilization": "Busy Util",
    "mrf_active_cycles": "MRF Active",
    "sm_active_cycles": "SM Active",
    "mrf_active_cycles_percentage": "Active %",
    "rfc_read_hits": "RFC Hits",
    "rfc_read_misses": "RFC Misses",
    "rfc_evictions": "RFC Evict",
    "warp_demotions": "Warp Dem",
    "rfc_flush_entries": "RFC Flush",
    "kernel_count": "Kernels",
    "total_ipc": "Total IPC",
    "total_occupancy": "GPU Occupancy",
}

PERCENT_METRICS = {
    "mrf_global_port_utilization",
    "mrf_busy_cycle_utilization",
    "mrf_active_cycles_percentage",
}

compiled_patterns = {
    key: re.compile(rf"\b{key}\s*=\s*({number})")
    for key, number in patterns.items()
}

ipc_pattern = re.compile(rf"\bgpu_tot_ipc\s*=\s*({NUMBER})")
occupancy_pattern = re.compile(rf"\bgpu_tot_occupancy\s*=\s*({NUMBER})\s*%")
kernel_id_pattern = re.compile(r"-kernel\s+id\s*=\s*(\d+)")


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def average(kernel_stats, key):
    """Average a counter across all kernel blocks."""
    if not all(key in k for k in kernel_stats):
        return None
    return sum(k[key] for k in kernel_stats) / len(kernel_stats)


def ratio_of_sums(kernel_stats, numerator, denominator):
    """Compute utilization from accumulated counts."""
    if not all(numerator in k and denominator in k for k in kernel_stats):
        return None
    total_num = sum(k[numerator] for k in kernel_stats)
    total_den = sum(k[denominator] for k in kernel_stats)
    return total_num / total_den if total_den > 0 else None


def format_value(key, value):
    """Format counters, utilization, occupancy, and IPC."""
    if value is None:
        return "N/A"
    if key == "kernel_count":
        return f"{value:,d}"
    if key == "total_occupancy":
        return f"{value:,.4f}%"  # Already a percentage in the log
    if key in PERCENT_METRICS:
        return f"{value * 100:,.4f}%"
    if key == "total_ipc":
        return f"{value:,.4f}"
    return f"{value:,.3f}"


# --------------------------------------------------
# Parse GPGPU-Sim output
# --------------------------------------------------

def parse_sim_out(file_path):
    with open(file_path, "r", errors="ignore") as f:
        content = f.read()

    ipc_matches = ipc_pattern.findall(content)
    final_ipc = float(ipc_matches[-1]) if ipc_matches else None

    occupancy_matches = occupancy_pattern.findall(content)
    final_occupancy = float(occupancy_matches[-1]) if occupancy_matches else None

    kernel_id_matches = kernel_id_pattern.findall(content)
    kernel_count = int(kernel_id_matches[-1]) if kernel_id_matches else None

    blocks = re.split(r"\bkernel_name\s*=", content)
    kernel_stats = []

    for block in blocks[1:]:
        current_k = {}
        for key, pattern in compiled_patterns.items():
            match = pattern.search(block)
            if match:
                raw_value = match.group(1)
                current_k[key] = (
                    float(raw_value) if key in PERCENT_METRICS
                    else int(raw_value)
                )
        if current_k:
            kernel_stats.append(current_k)

    if not kernel_stats and final_ipc is None and final_occupancy is None and kernel_count is None:
        return None

    results = {
        key: average(kernel_stats, key) if kernel_stats else None
        for key in patterns
    }

    results["mrf_global_port_utilization"] = ratio_of_sums(
        kernel_stats, "mrf_port_occupancy", "mrf_port_capacity"
    ) if kernel_stats else None
    results["mrf_busy_cycle_utilization"] = ratio_of_sums(
        kernel_stats, "mrf_busy_cycle_occupancy", "mrf_busy_cycle_capacity"
    ) if kernel_stats else None
    results["mrf_active_cycles_percentage"] = ratio_of_sums(
        kernel_stats, "mrf_active_cycles", "sm_active_cycles"
    ) if kernel_stats else None

    results["kernel_count"] = kernel_count
    results["total_ipc"] = final_ipc
    results["total_occupancy"] = final_occupancy
    return results


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():
    if not BASE_DIR.is_dir():
        print(f"Directory not found: {BASE_DIR}")
        return

    metric_keys = list(patterns) + ["kernel_count", "total_ipc", "total_occupancy"]
    widths = {
        key: max(len(column_names[key]), 14)
        for key in metric_keys
    }
    bench_width = 24

    header = (
        f"{'Benchmark':<{bench_width}} | "
        + " | ".join(
            f"{column_names[key]:>{widths[key]}}"
            for key in metric_keys
        )
    )
    separator = "-" * len(header)

    with open(OUTPUT_FILE, "w") as out:
        out.write(header + "\n")
        out.write(separator + "\n")

        for bench_dir in sorted(BASE_DIR.iterdir()):
            if not bench_dir.is_dir() or "rodinia" not in bench_dir.name:
                continue

            output_files = sorted(
                p for p in bench_dir.rglob("*")
                if p.is_file() and ".o" in p.name
            )

            for sim_file in output_files:
                data = parse_sim_out(sim_file)
                if data is None:
                    continue

                values = " | ".join(
                    f"{format_value(key, data[key]):>{widths[key]}}"
                    for key in metric_keys
                )
                out.write(f"{bench_dir.name:<{bench_width}} | {values}\n")
                break

    print(f"Stats saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
