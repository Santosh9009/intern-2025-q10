import os 
from typing import Union, Optional
from dotenv import load_dotenv

load_dotenv()

def env(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(name, default)


