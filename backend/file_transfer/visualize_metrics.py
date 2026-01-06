import csv
import matplotlib.pyplot as plt
from pathlib import Path
from collections import defaultdict

def load_data(csv_path: Path):
    data = defaultdict(lambda: {"ts": [], "cwnd": [], "ssthresh": []})
    try:
        if not csv_path.exists():
            print(f"File {csv_path} not found.")
            return {}
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    algo = row["algo"].lower()
                    data[algo]["ts"].append(float(row["ts"]))
                    data[algo]["cwnd"].append(float(row["cwnd"]))
                    if "ssthresh" in row and row["ssthresh"]:
                        data[algo]["ssthresh"].append(float(row["ssthresh"]))
                    else:
                        data[algo]["ssthresh"].append(0.0)
                except (ValueError, KeyError, TypeError):
                    continue
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return {}
    return data

def visualize(metrics_data, output_path: Path):
    if not metrics_data:
        print("No data to visualize.")
        return

    plt.figure(figsize=(14, 8))
    
    # We want a clean side-by-side comparison, so we align each algo run to its own T=0
    for algo in sorted(metrics_data.keys()):
        vals = metrics_data[algo]
        if not vals["ts"]:
            continue
        
        # We might have multiple runs in the same CSV, let's just take the LATEST run for each algo
        # A "run" starts when timestamps have a large gap (e.g. > 2 seconds)
        # But for simplicity in this project, we'll just take all points and align them
        # to the very first point of that algo.
        start_ts = min(vals["ts"])
        rel_ts = [t - start_ts for t in vals["ts"]]
        
        # Use different colors and markers to distinguish
        color = 'tab:blue' if 'reno' in algo else 'tab:orange'
        
        plt.step(rel_ts, vals["cwnd"], label=f"{algo.upper()} CWND", where='post', linewidth=2.5, color=color)
        
        # Plot ssthresh as a dashed line
        if any(v > 0 for v in vals["ssthresh"]):
            plt.step(rel_ts, vals["ssthresh"], '--', label=f"{algo.upper()} ssthresh", where='post', alpha=0.6, color=color)

    plt.title("SyncroX: UDP Congestion Control Side-by-Side Comparison", fontsize=18, fontweight='bold')
    plt.xlabel("Time Since Transfer Start (seconds)", fontsize=14)
    plt.ylabel("Congestion Window Size (packets)", fontsize=14)
    plt.legend(loc='upper right', fontsize=12)
    plt.grid(True, which='both', linestyle='--', alpha=0.5)
    
    # Set axis limits to make it readable
    plt.ylim(0, 35) # rwnd is 32, so this is a good scale
    
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    print(f"Improved visualization saved to {output_path}")

if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parents[2]
    CSV_FILE = BASE_DIR / "data" / "metrics" / "room_1111_file_metrics.csv"
    OUTPUT_FILE = BASE_DIR / "data" / "metrics" / "reno_vs_tahoe_comparison.png"
    
    data = load_data(CSV_FILE)
    visualize(data, OUTPUT_FILE)
