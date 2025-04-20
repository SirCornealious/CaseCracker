# utils.py 
# Created by SuperGrok and Sir_Cornealious on X

import os
import re
import logging
import base64
import shutil
import tempfile

# Constants
API_URL = "https://api.x.ai/v1/chat/completions"
TIMEOUT = 30
# Path to API key file, used in gui.py for saving/loading API keys
API_KEY_FILE = os.path.expanduser("~/.grok_sleuth_api_key")
POPPLER_PATH = "/opt/homebrew/Cellar/poppler/25.04.0/bin"

def setup_logging(timestamp_dir):
    log_file = os.path.join(timestamp_dir, "grok_sleuth.log")
    # Create a new logger instance specific to this timestamped directory
    logger = logging.getLogger(f"grok_sleuth_{timestamp_dir}")
    logger.setLevel(logging.DEBUG)
    
    # Remove any existing handlers to avoid conflicts
    logger.handlers.clear()
    
    # Add file handler
    file_handler = logging.FileHandler(log_file, mode='w')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    # Add stream handler
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(stream_handler)
    
    logger.debug("Logging initialized")
    return logger

def encode_image(image_path):
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    except (OSError, IOError) as e:
        logging.getLogger(__name__).error(f"Error encoding image {image_path}: {str(e)}")
        raise

def group_split_files(pdf_files):
    grouped_files = {}
    for pdf in pdf_files:
        base_name = re.sub(r"-part_\d+_of_\d+\.pdf$", "", pdf, flags=re.IGNORECASE)
        grouped_files.setdefault(base_name, []).append(pdf)
    
    for base_name in grouped_files:
        grouped_files[base_name].sort(
            key=lambda x: int(re.search(r"part_(\d+)_of_\d+", x).group(1)) if "part_" in x.lower() else 0
        )
    
    return grouped_files

def get_processed_files(ocr_dir):
    processed_files = set()
    ocr_file = os.path.join(ocr_dir, "combined_ocr.txt")
    if os.path.exists(ocr_file):
        with open(ocr_file, "r", encoding='utf-8') as f:
            content = f.read()
            matches = re.findall(r"File: (.*?)\n", content)
            processed_files = set(matches)
    return processed_files

def get_followup_files(followups_dir):
    followup_files = [f for f in os.listdir(followups_dir) if f.startswith("followup_") and f.endswith(".txt")]
    followup_files.sort()
    return followup_files