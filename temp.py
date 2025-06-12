import fastf1
from fastf1 import plotting
from rich import print
import matplotlib.pyplot as plt

plotting.setup_mpl()
fastf1.Cache.enable_cache('f1_cache')

def get_race_fastest_laps(year, race_num, drivers):
    """
    Loads a race session once and extracts fastest lap data for multiple drivers.
    Returns a dictionary with driver as key and (fastest_lap_time_seconds, lap_number) as value.
    """
    try:
        session = fastf1.get_session(year, race_num, 'R')
        print(f"[bold green]Loading session for {year} Round {race_num}: {session.event['EventName']}[/bold green]")
        session.load(laps=True) # Only load laps data if that's all you need initially

        driver_fastest_laps = {}
        for driver_code in drivers:
            try:
                # Pick drivers from the already loaded session.laps
                driver_laps = session.laps.pick_drivers(driver_code)
                if not driver_laps.empty:
                    fastest_lap = driver_laps.pick_fastest()
                    if not fastest_lap.empty:
                        lap_time_seconds = int(fastest_lap['LapTime'].total_seconds())
                        lap_number = int(fastest_lap['LapNumber'])
                        driver_fastest_laps[driver_code] = (lap_time_seconds, lap_number)
                    else:
                        print(f"[yellow]No fastest lap found for {driver_code} in {year} Round {race_num}[/yellow]")
                else:
                    print(f"[yellow]Driver {driver_code} not found in laps data for {year} Round {race_num}[/yellow]")
            except Exception as e:
                print(f"[red]Error processing driver {driver_code} for {year} Round {race_num}: {e}[/red]")
        return driver_fastest_laps

    except Exception as e:
        print(f"[red]Error loading session for {year} Round {race_num}: {e}[/red]")
        return {} # Return empty dict on session load error

# --- Main script starts here ---
years_to_process = [2024] # Example: process multiple recent years
drivers_to_track = ['VER', 'PIA', 'NOR']

all_driver_data = {driver: [] for driver in drivers_to_track}

# Loop through years and then races
for year in years_to_process:
    # Use fastf1.get_event_schedule(year) to get total rounds for the year
    # This avoids hardcoding 9 races and handles varying race counts
    try:
        schedule = fastf1.get_event_schedule(year)
        # Filter for actual races, not test sessions or non-race events if needed
        race_rounds = schedule[schedule['EventFormat'] == 'conventional']['RoundNumber'].tolist()
        if not race_rounds:
            print(f"[yellow]No 'conventional' races found in schedule for {year}. Processing all rounds.[/yellow]")
            race_rounds = schedule['RoundNumber'].tolist() # Fallback to all rounds

    except Exception as e:
        print(f"[red]Error getting event schedule for {year}: {e}. Skipping year.[/red]")
        continue # Skip to next year if schedule cannot be fetched

    for race_num in race_rounds:
        race_data = get_race_fastest_laps(year, race_num, drivers_to_track)
        for driver_code, data in race_data.items():
            all_driver_data[driver_code].append(data)

# Prepare data for plotting
ver_times = [t[0] for t in all_driver_data['VER']]
ver_numbers = [t[1] for t in all_driver_data['VER']]
pia_times = [t[0] for t in all_driver_data['PIA']]
pia_numbers = [t[1] for t in all_driver_data['PIA']]
nor_times = [t[0] for t in all_driver_data['NOR']]
nor_numbers = [t[1] for t in all_driver_data['NOR']]

# Create scatter plot (rest of your plotting code remains similar)
plt.figure(figsize=(10, 6))
plt.scatter(ver_numbers, ver_times, color='blue', marker='o', label='VER')
plt.scatter(pia_numbers, pia_times, color='red', marker='o', label='PIA')
plt.scatter(nor_numbers, nor_times, color='green', marker='o', label='NOR')
# Add labels and title
plt.title('Fastest Lap Times by Lap Number')
plt.xlabel('Lap Number')
plt.ylabel('Lap Time (seconds)')
plt.legend()
plt.tight_layout()
plt.show()