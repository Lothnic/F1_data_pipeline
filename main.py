"""Plot the fastest race lap for selected drivers in one season."""

import argparse
from pathlib import Path

import fastf1
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--round", type=int, help="Process only this championship round")
    parser.add_argument("--drivers", nargs="+", default=["VER", "PIA", "NOR"])
    parser.add_argument("--output", help="Save the plot to a file instead of opening a window")
    args = parser.parse_args()
    Path("f1_cache").mkdir(exist_ok=True)
    fastf1.Cache.enable_cache("f1_cache")
    if args.round is not None:
        rounds = [args.round]
    else:
        schedule = fastf1.get_event_schedule(args.year)
        rounds = schedule.loc[schedule["RoundNumber"] > 0, "RoundNumber"]
    data = {driver: [] for driver in args.drivers}
    for round_number in rounds:
        try:
            session = fastf1.get_session(args.year, int(round_number), "R")
            session.load(laps=True, telemetry=False, weather=False, messages=False)
            for driver in args.drivers:
                laps = session.laps.pick_drivers(driver)
                if not laps.empty:
                    lap = laps.pick_fastest()
                    if lap is not None and not lap.empty:
                        data[driver].append((lap["LapNumber"], lap["LapTime"].total_seconds()))
        except Exception as exc:
            print(f"Skipping round {round_number}: {exc}")
    if not any(data.values()):
        raise SystemExit("No lap data found; no plot was produced.")
    for driver, points in data.items():
        if points:
            x, y = zip(*points)
            plt.scatter(x, y, label=driver)
    plt.title(f"Fastest race laps by lap number ({args.year})")
    plt.xlabel("Lap number")
    plt.ylabel("Lap time (seconds)")
    plt.legend()
    plt.tight_layout()
    if args.output:
        plt.savefig(args.output)
        print(f"Saved plot to {args.output}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
