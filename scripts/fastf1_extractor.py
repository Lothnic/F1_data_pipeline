import fastf1
import pandas as pd
import io
import os
from google.cloud import storage
from rich import print
from dotenv import load_dotenv

# --- fastf1 setup ---
fastf1.Cache.enable_cache('f1_cache')

load_dotenv()

GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID')
GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME')
RAW_PREFIX = 'raw/fastf1/'


if not GCP_PROJECT_ID or not GCS_BUCKET_NAME:
    print("[bold red]Error: GCP_PROJECT_ID or GCS_BUCKET_NAME environment variables are not set.[/bold red]")
    print("[bold red]Please ensure you have a .env file configured at the project root.[/bold red]")
    exit(1)

try:
    storage_client = storage.Client(project=GCP_PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    print(f"[bold green]Successfully connected to GCS bucket: gs://{GCS_BUCKET_NAME}[/bold green]")
except Exception as e:
    print(f"[bold red]Failed to initialize GCS client or connect to bucket: {e}[/bold red]")
    print("[bold red]Ensure your GCP Project ID and Bucket Name are correct and 'gcloud auth application-default login' is done.[/bold red]")
    exit(1)
