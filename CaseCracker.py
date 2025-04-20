# CaseCracker.py 
# Created by SuperGrok and Sir_Cornealious on X

import argparse
import logging
import os
import shutil
import tempfile
import tkinter as tk
from tkinter import messagebox
import requests
from gui import CaseCrackerGUI
from processing import process_pdfs, analyze_combined_ocr, interactive_query
from utils import setup_logging

def main():
    # Set up temporary logging before GUI starts
    temp_dir = tempfile.mkdtemp()
    temp_log = os.path.join(temp_dir, "casecracker_temp.log")
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(temp_log, mode='w'),
            logging.StreamHandler()
        ],
        force=True
    )
    logger = logging.getLogger(__name__)
    logger.debug("Initializing main with temporary logger")

    gui = CaseCrackerGUI()

    try:
        logger.debug("Starting GUI mode")
        api_key, input_dir, files_to_process, timestamp_dir, query, processing_mode = gui.run_gui()
        logger.debug(f"GUI returned: api_key={len(api_key)} chars, input_dir={input_dir}, files_to_process={files_to_process}, timestamp_dir={timestamp_dir}, processing_mode={processing_mode}")

        # Switch to timestamped logger after GUI completes
        logger = setup_logging(timestamp_dir)
        logger.info("Starting main processing")

        jpeg_dir = os.path.join(timestamp_dir, "JPEG")
        ocr_dir = os.path.join(timestamp_dir, "OCR")
        analysis_dir = os.path.join(timestamp_dir, "ANALYSIS")
        followups_dir = os.path.join(timestamp_dir, "QUARRY")

        if processing_mode in ["ocr_only", "ocr_and_analysis"]:
            logger.info("Processing files...")
            combined_ocr_file = process_pdfs(api_key, input_dir, files_to_process, jpeg_dir, ocr_dir)
            logger.info("File processing complete")
        else:  # analyze_only
            logger.info("Skipping OCR, using provided text file for analysis")
            combined_ocr_file = os.path.join(input_dir, files_to_process[0])  # Use the selected text file directly

        if processing_mode == "ocr_only":
            logger.info(f"OCR processing complete. Results saved to: {timestamp_dir}")
            tk.Tk().withdraw()
            messagebox.showinfo("Success", f"OCR processing complete. Results saved to: {timestamp_dir}")
            return

        logger.info("Performing combined analysis...")
        analysis_result = analyze_combined_ocr(api_key, combined_ocr_file, analysis_dir, query)
        logger.info("Analysis complete")

        logger.info(f"Results saved to {timestamp_dir}")
        tk.Tk().withdraw()
        messagebox.showinfo("Success", f"Processing complete. Results saved to: {timestamp_dir}")
        logger.info("Starting interactive query")
        interactive_query(api_key, combined_ocr_file, followups_dir)

    except requests.RequestException as e:
        logger.exception(f"API request error: {str(e)}")
        tk.Tk().withdraw()
        messagebox.showerror("Error", f"API request failed: {str(e)}")
    except (OSError, IOError) as e:
        logger.exception(f"File operation error: {str(e)}")
        tk.Tk().withdraw()
        messagebox.showerror("Error", f"File operation failed: {str(e)}")
    except ValueError as e:
        logger.exception(f"Configuration error: {str(e)}")
        tk.Tk().withdraw()
        messagebox.showerror("Error", f"Invalid configuration: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        tk.Tk().withdraw()
        messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")
    finally:
        logger.debug("Cleaning up")
        gui.cleanup_temp_dir()
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    main()