import fastf1
from fastf1 import plotting
from rich import print
import matplotlib.pyplot as plt
import pandas as pd # Ensure pandas is imported

plotting.setup_mpl()
fastf1.Cache.enable_cache('f1_cache')

def get_race_fastest_laps_optimized(year, race_num, drivers):
    """
    Loads a race session once and efficiently extracts fastest lap data for multiple drivers.
    Returns a dictionary with driver as key and (fastest_lap_time_seconds, lap_number) as value.
    """
    try:
        session = fastf1.get_session(year, race_num, 'R')
        print(f"[bold green]Loading session for {year} Round {race_num}: {session.event['EventName']}[/bold green]")
        session.load(laps=True)

        if session.laps.empty:
            print(f"[yellow]No lap data available for {year} Round {race_num}.[/yellow]")
            return {}

        # 1. Filter for drivers we care about once (if drivers list is provided)
        # fastf1.pick_drivers() is good, but we can do it after all processing
        # if not just picking for the session object, but using the raw df.
        # For fastest lap, it's often better to let pick_fastest() do its thing on relevant data.

        # 2. Add total_seconds column for easier comparison and storage
        # This converts Timedelta objects to a numeric type, which is good for storage too.
        session.laps['LapTimeSeconds'] = session.laps['LapTime'].dt.total_seconds()

        driver_fastest_laps_data = {}
        for driver_code in drivers:
            try:
                # Filter for the specific driver first
                driver_laps = session.laps.loc[session.laps['Driver'] == driver_code]

                if not driver_laps.empty:
                    # Find the minimum LapTimeSeconds for this driver
                    fastest_lap_time_seconds = driver_laps['LapTimeSeconds'].min()

                    # Find the row(s) corresponding to the fastest lap.
                    # Using .loc to get the actual row, and .iloc[0] to pick the first one
                    # if there are ties for fastest lap.
                    fastest_lap_row = driver_laps.loc[
                        driver_laps['LapTimeSeconds'] == fastest_lap_time_seconds
                    ].iloc[0]

                    lap_number = int(fastest_lap_row['LapNumber'])
                    driver_fastest_laps_data[driver_code] = (int(fastest_lap_time_seconds), lap_number)
                else:
                    print(f"[yellow]Driver {driver_code} not found in laps data for {year} Round {race_num}[/yellow]")
            except Exception as e:
                print(f"[red]Error processing driver {driver_code} for {year} Round {race_num}: {e}[/red]")
        return driver_fastest_laps_data

    except Exception as e:
        print(f"[red]Error loading session for {year} Round {race_num}: {e}[/red]")
        return {}

# --- Main script remains largely the same, but calls the optimized function ---
years_to_process = [2024]
drivers_to_track = ['VER', 'PIA', 'NOR']

all_driver_data = {driver: [] for driver in drivers_to_track}

for year in years_to_process:
    try:
        schedule = fastf1.get_event_schedule(year)
        # Ensure to pick 'conventional' and 'sprint' races as schedule.json often includes testing/non-race events
        race_rounds = schedule[schedule['EventFormat'].isin(['conventional', 'sprint'])]['RoundNumber'].tolist()
        if not race_rounds:
            print(f"[yellow]No 'conventional' or 'sprint' races found in schedule for {year}. Processing all rounds as fallback.[/yellow]")
            race_rounds = schedule['RoundNumber'].tolist()

    except Exception as e:
        print(f"[red]Error getting event schedule for {year}: {e}. Skipping year.[/red]")
        continue

    for race_num in race_rounds:
        # Call the optimized function
        race_data = get_race_fastest_laps_optimized(year, race_num, drivers_to_track)
        for driver_code, data in race_data.items():
            all_driver_data[driver_code].append(data)

# Preparing data for plotting (this part is fine as it is)
ver_times = [t[0] for t in all_driver_data['VER']]
ver_numbers = [t[1] for t in all_driver_data['VER']]
pia_times = [t[0] for t in all_driver_data['PIA']]
pia_numbers = [t[1] for t in all_driver_data['PIA']]
nor_times = [t[0] for t in all_driver_data['NOR']]
nor_numbers = [t[1] for t in all_driver_data['NOR']]

# Creating Scatter Plot (this part is fine as it is)
plt.figure(figsize=(10, 6))
plt.scatter(ver_numbers, ver_times, color='blue', marker='o', label='VER')
plt.scatter(pia_numbers, pia_times, color='red', marker='o', label='PIA')
plt.scatter(nor_numbers, nor_times, color='green', marker='o', label='NOR')

# Adding labels and title
plt.title('Fastest Lap Times by Lap Number')
plt.xlabel('Race Round Number') # Changed label as it represents round number not lap number
plt.ylabel('Fastest Lap Time (seconds)')
plt.legend() # plt.legend({"VER":"blue", "PIA":"red", "NOR":"green"}) is not how legend works directly, better to set label in scatter and call legend()
plt.tight_layout()
plt.show()