# F1 Data Pipeline

This project analyzes Formula 1 race data, focusing on driver performance metrics such as lap times and race positions.

## Features

- Analyzes fastest lap times for multiple drivers across races
- Visualizes performance data using scatter plots
- Supports multiple drivers (currently tracking VER, PIA, and NOR)
- Uses FastF1 library for data retrieval and analysis
- Implements caching for efficient data handling

## Setup

1. Install Python 3.8 or higher
2. Install required packages:
   ```bash
   pip install fastf1 matplotlib rich
   ```

## Usage

Run the main script:
```bash
python main.py
```

The script will:
1. Load race data for the specified drivers
2. Calculate fastest lap times for each race
3. Generate a scatter plot comparing driver performances

## Project Structure

- `main.py`: Main script containing analysis logic
- `f1_cache/`: Directory for storing cached race data
- `.gitignore`: Configuration to ignore cache files

## Dependencies

- fastf1: For F1 data retrieval and analysis
- matplotlib: For data visualization
- rich: For enhanced console output
- pymongo: For cache management

## Data Sources

The project uses official F1 data through the FastF1 API, which provides:
- Race lap times
- Driver positions
- Session information
- Weather data

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- FastF1 project for the amazing F1 data API
- Formula 1 for providing the data