"""
Google Cloud Platform credentials loader.
Loads credentials from environment variables or a JSON file.
"""
import os
import json
from pathlib import Path


def load_gcp_credentials():
    """
    Load Google Cloud Platform service account credentials.
    
    Priority:
    1. Environment variable GOOGLE_APPLICATION_CREDENTIALS_JSON (JSON string)
    2. Environment variable GOOGLE_APPLICATION_CREDENTIALS (path to JSON file)
    3. credentials.json file in the project root
    
    Returns:
        dict: Service account credentials dictionary
        
    Raises:
        FileNotFoundError: If credentials file is not found
        ValueError: If credentials cannot be loaded
    """
    # Try loading from environment variable as JSON string
    creds_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if creds_json:
        try:
            return json.loads(creds_json)
        except json.JSONDecodeError:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS_JSON is not valid JSON")
    
    # Try loading from file path in environment variable
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if creds_path and Path(creds_path).exists():
        with open(creds_path, 'r') as f:
            return json.load(f)
    
    # Try loading from default location
    default_path = Path(__file__).parent / 'credentials.json'
    if default_path.exists():
        with open(default_path, 'r') as f:
            return json.load(f)
    
    raise FileNotFoundError(
        "Google Cloud credentials not found. "
        "Please set GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable, "
        "or set GOOGLE_APPLICATION_CREDENTIALS to point to a credentials file, "
        "or place credentials.json in the project root."
    )

