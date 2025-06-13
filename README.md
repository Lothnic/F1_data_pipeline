# F1 Data Pipeline

This ongoing project analyzes Formula 1 race data, focusing on driver performance metrics such as lap times and race positions.

## Features

- Analyzes fastest lap times for multiple drivers across races
- Visualizes performance data using scatter plots
- Supports multiple drivers (currently tracking VER, PIA, and NOR)
- Uses FastF1 library for data retrieval and analysis
- Implements caching for efficient data handling

## Setup

This project uses [uv](https://github.com/astral-sh/uv) for package management and virtual environment management, providing faster and more reliable dependency management than traditional pip.

### Prerequisites
- Python 3.10 or higher
- `uv` package manager

### Installation

1. Install `uv` (if not already installed):
   ```bash
   curl -sSf https://astral.sh/uv/install.sh | sh
   ```
   For macOS/Linux:
   ```bash
   brew install astral-sh/uv/uv
   ```

2. Sync dependencies from pyproject.toml and uv.lock:

   ```bash
   uv venv  # Creates a virtual environment (optional, but recommended)

   .venv\Scripts\activate # on Windows

   source .venv/bin/activate  # on macOS/Linux

   uv pip sync  # Installs exactly what’s in uv.lock

   ```

3. To add more packages:
   ```bash
   uv add <package_name>
   ```

## Usage

### Create a folder 'f1_cache' for caching the data.

### Run the main script:
```bash
uv run main.py
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