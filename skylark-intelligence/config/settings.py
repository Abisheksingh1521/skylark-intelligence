import os
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env located at project root
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

def get_current_date() -> pd.Timestamp:
    """Returns the current system date normalized to midnight (YYYY-MM-DD 00:00:00)."""
    return pd.Timestamp.now().normalize()

class Settings:
    # Environment Variables
    MONDAY_API_TOKEN: str = os.getenv("MONDAY_API_TOKEN", "")
    MONDAY_DEALS_BOARD_ID: str = os.getenv("MONDAY_DEALS_BOARD_ID", "")
    MONDAY_WORK_ORDERS_BOARD_ID: str = os.getenv("MONDAY_WORK_ORDERS_BOARD_ID", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Cache & Timeout Settings
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))
    REQUEST_TIMEOUT_SECONDS: int = 15
    MAX_RETRIES: int = 3
    
    # Closure Probability Mappings (Correction 1: Missing = None, NOT 0.0)
    PROBABILITY_MAPPING = {
        "High": 0.75,
        "Medium": 0.50,
        "Low": 0.25,
        # Missing or unknown labels map to None
    }
    
    # Canonical Sector Mapping (normalizes case & variations)
    SECTOR_MAPPING = {
        "mining": "Mining",
        "renewables": "Renewables",
        "powerline": "Powerline",
        "railways": "Railways",
        "construction": "Construction",
        "highways": "Highways",
        "dsp": "DSP",
        "tender": "Tender",
        "manufacturing": "Manufacturing",
        "aviation": "Aviation",
        "security and surveillance": "Security and Surveillance",
        "others": "Others",
        "other": "Others"
    }
    
    @classmethod
    def validate_monday_config(cls) -> bool:
        """Check if all required Monday.com env vars are configured."""
        return bool(
            cls.MONDAY_API_TOKEN and 
            cls.MONDAY_DEALS_BOARD_ID and 
            cls.MONDAY_WORK_ORDERS_BOARD_ID
        )

settings = Settings()
