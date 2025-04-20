# processing.py 
# Created by SuperGrok and Sir_Cornealious on X

import requests
import os
import json
from pdf2image import convert_from_path
import base64
import re
import logging
from utils import API_URL, TIMEOUT, POPPLER_PATH, get_followup_files
from token_utils import estimate_tokens, truncate_text

logger = logging.getLogger(__name__)

def convert_pdf_to_jpeg(pdf_path, jpeg_dir):
    try:
        if not os.access(jpeg_dir, os.W_OK):
            raise PermissionError(f"No write permission for {jpeg_dir}")
        images = convert_from_path(pdf_path, dpi=200, thread_count=2, poppler_path=POPPLER_PATH)
        jpeg_paths = []
        failed_paths = []
        base_name = os.path.basename(pdf_path).replace(".pdf", "")
        for i, image in enumerate(images):
            jpeg_path = os.path.join(jpeg_dir, f"{base_name}-page-{i+1}.jpg")
            try:
                image.save(jpeg_path, "JPEG", quality=85)
                jpeg_paths.append(jpeg_path)
                logger.debug(f"Saved JPEG: {jpeg_path}")
            except (OSError, IOError) as e:
                logger.error(f"Failed to save JPEG for page {i+1} of {pdf_path}: {str(e)}")
                failed_paths.append(jpeg_path)
        return jpeg_paths, failed_paths
    except (OSError, IOError, ValueError) as e:
        logger.error(f"Error converting PDF {pdf_path}: {str(e)}")
        return [], [pdf_path]

def extract_ocr(pdf_path, jpeg_paths, api_key, logs_dir):
    try:
        ocr_texts = []
        headers = {"Authorization": f"Bearer {api_key}"}
        base_name = os.path.basename(pdf_path).replace(".pdf", "").replace(".jpeg", "").replace(".jpg", "").replace(".png", "")
        for i, jpeg_path in enumerate(jpeg_paths):
            logger.debug(f"Sending OCR API call for {jpeg_path}")
            base64_image = base64.b64encode(open(jpeg_path, "rb").read()).decode("utf-8")
            payload = {
                "model": "grok-2-vision-latest",
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "high"
                            }
                        },
                        {"type": "text", "text": "Perform OCR on this image and extract the raw text."}
                    ]
                }],
                "temperature": 0.01
            }
            response = requests.post(API_URL, headers=headers, json=payload, timeout=TIMEOUT)
            response.raise_for_status()
            response_json = response.json()
            ocr_text = response_json['choices'][0]['message']['content']
            json_file = os.path.join(logs_dir, f"ocr_response_{base_name}_page-{i+1}.json")
            with open(json_file, "w", encoding='utf-8') as f:
                json.dump(response_json, f, indent=2)
                f.flush()
            logger.debug(f"Saved JSON response: {json_file}")
            ocr_texts.append(ocr_text)
            logger.debug(f"Received OCR response for {jpeg_path}")
            # Keep JPEGs for debugging
            logger.debug(f"Retained JPEG: {jpeg_path}")
        return pdf_path, "\n\n--- Page Break ---\n\n".join(ocr_texts)
    except requests.RequestException as e:
        logger.error(f"OCR API error for {pdf_path}: {str(e)}")
        return pdf_path, f"Error: {str(e)}"
    except (OSError, IOError) as e:
        logger.error(f"File operation error for {pdf_path}: {str(e)}")
        return pdf_path, f"Error: {str(e)}"

def group_split_files(pdf_files):
    grouped_files = {}
    for pdf in pdf_files:
        base_name = re.sub(r"-part_\d+_of_\d+\.(pdf|jpeg|jpg|png)$", "", pdf, flags=re.IGNORECASE)
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

def process_pdfs(api_key, pdf_dir, files_to_process, jpeg_dir, ocr_dir):
    logger = logging.getLogger(__name__)
    try:
        if not os.access(ocr_dir, os.W_OK):
            raise PermissionError(f"No write permission for {ocr_dir}")
        logs_dir = os.path.join(os.path.dirname(ocr_dir), "logs")
        grouped_files = group_split_files(files_to_process)
        processed_files = get_processed_files(ocr_dir)
        pdf_groups_to_process = {
            base_name: files for base_name, files in grouped_files.items()
            if base_name not in processed_files
        }
        logger.info(f"Processing {len(pdf_groups_to_process)} new groups.")

        combined_ocr_file = os.path.join(ocr_dir, "combined_ocr.txt")
        combined_ocr_content = ""

        # Process groups, retrying failed parts as individuals
        for base_name, group in pdf_groups_to_process.items():
            try:
                for file_path in group:
                    full_path = os.path.join(pdf_dir, file_path)
                    logger.debug(f"Starting processing for {full_path}")
                    # Check file extension to determine processing path
                    if file_path.lower().endswith('.pdf'):
                        jpeg_paths, failed_paths = convert_pdf_to_jpeg(full_path, jpeg_dir)
                        if failed_paths:
                            logger.warning(f"Failed to convert some pages for {full_path}: {failed_paths}")
                    else:  # JPEG, JPG, PNG
                        jpeg_paths = [full_path]  # Use the image file directly
                        failed_paths = []
                        logger.debug(f"Using image file directly: {full_path}")
                    if not jpeg_paths:
                        logger.warning(f"Skipping {full_path}: No JPEGs converted")
                        continue
                    _, ocr_text = extract_ocr(full_path, jpeg_paths, api_key, logs_dir)
                    output = f"File: {base_name}\n### OCR ###\n{ocr_text}\n{'-'*50}\n"
                    logger.debug(f"Writing OCR output for {base_name}")
                    ocr_file = os.path.join(ocr_dir, f"{base_name}.txt")
                    with open(ocr_file, "w", encoding='utf-8') as f:
                        f.write(output)
                        f.flush()
                    logger.debug(f"Saved OCR file: {ocr_file}")
                    combined_ocr_content += output
            except (requests.RequestException, OSError, IOError) as e:
                logger.error(f"Error processing group {base_name}: {str(e)}")
                # Retry each part as an individual file
                for file_path in group:
                    single_group = {f"{base_name}-{os.path.basename(file_path)}": [file_path]}
                    pdf_groups_to_process.update(single_group)
                    logger.info(f"Retrying {file_path} as individual due to group failure")
                continue

        # Write combined OCR file once after all processing
        logger.debug(f"Writing combined OCR file: {combined_ocr_file}")
        with open(combined_ocr_file, "w", encoding='utf-8') as f:
            f.write(combined_ocr_content)
            f.flush()
        logger.debug(f"Saved combined OCR file: {combined_ocr_file}")

        return combined_ocr_file
    except (OSError, IOError) as e:
        logger.error(f"File operation error in process_pdfs: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in process_pdfs: {str(e)}")
        raise

def analyze_combined_ocr(api_key, combined_ocr_file, analysis_dir, query):
    logger = logging.getLogger(__name__)
    try:
        if not os.access(analysis_dir, os.W_OK):
            raise PermissionError(f"No write permission for {analysis_dir}")
        logs_dir = os.path.join(os.path.dirname(analysis_dir), "logs")
        headers = {"Authorization": f"Bearer {api_key}"}
        ocr_content = ""
        if os.path.exists(combined_ocr_file):
            with open(combined_ocr_file, "r", encoding='utf-8') as f:
                ocr_content = f.read()
        else:
            raise FileNotFoundError(f"{combined_ocr_file} not found")

        logger.debug("Sending analysis API call")
        full_query = f"Here is the OCR-extracted text for your investigation:\n\n{ocr_content}\n\n{query}"
        query_tokens = estimate_tokens(full_query)
        if query_tokens > 120000:
            logger.warning(f"Analysis query exceeds token limit ({query_tokens} tokens). Truncating...")
            full_query = truncate_text(full_query, 120000)

        payload = {
            "model": "grok-3-fast-latest",
            "messages": [{"role": "user", "content": full_query}],
            "temperature": 0.01
        }
        response = requests.post(API_URL, headers=headers, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        response_json = response.json()
        response_content = response_json['choices'][0]['message']['content']
        json_file = os.path.join(logs_dir, "analysis_response.json")
        with open(json_file, "w", encoding='utf-8') as f:
            json.dump(response_json, f, indent=2)
            f.flush()
        logger.debug(f"Saved JSON response: {json_file}")
        logger.debug("Received analysis response")

        analysis_file = os.path.join(analysis_dir, "combined_analysis.txt")
        with open(analysis_file, "w", encoding='utf-8') as f:
            f.write(response_content)
            f.flush()
        logger.debug(f"Saved analysis file: {analysis_file}")
        return response_content
    except requests.RequestException as e:
        logger.error(f"Analysis API error: {str(e)}")
        return f"Analysis error: {str(e)}"
    except (OSError, IOError) as e:
        logger.error(f"File operation error: {str(e)}")
        return f"Analysis error: {str(e)}"

def interactive_query(api_key, combined_ocr_file, followups_dir):
    logger = logging.getLogger(__name__)
    try:
        if not os.access(followups_dir, os.W_OK):
            raise PermissionError(f"No write permission for {followups_dir}")
        logs_dir = os.path.join(os.path.dirname(followups_dir), "logs")
        followup_counter = len(get_followup_files(followups_dir)) + 1
        headers = {"Authorization": f"Bearer {api_key}"}

        while True:
            ocr_content = ""
            if os.path.exists(combined_ocr_file):
                with open(combined_ocr_file, "r", encoding='utf-8') as f:
                    ocr_content = f.read()

            followup_files = get_followup_files(followups_dir)
            selected_content = ""
            if followup_files:
                print("\nPrevious Follow-up Questions:")
                for idx, followup_file in enumerate(followup_files, 1):
                    with open(os.path.join(followups_dir, followup_file), "r", encoding='utf-8') as f:
                        content = f.read()
                        question_match = re.search(r"Follow-up Query:\n(.*?)\nResponse:", content, re.DOTALL)
                        if question_match:
                            print(f"{idx}. {question_match.group(1).strip()}")
                print("0. None (only include OCR data)")
                selection = input("Select questions to include (e.g., 1, 3 for followups 1 and 3, or 0 for none): ").strip()
                if selection != "0":
                    # Deduplicate selected indices
                    selected_indices = list(set(int(idx.strip()) for idx in selection.split(",") if idx.strip().isdigit()))
                    for idx in selected_indices:
                        if 1 <= idx <= len(followup_files):
                            with open(os.path.join(followups_dir, followup_files[idx-1]), "r", encoding='utf-8') as f:
                                selected_content += f"\nPrevious Follow-up:\n{f.read().strip()}\n"

            query = input("\nEnter follow-up query (or 'exit' to quit): ")
            if query.lower() == "exit":
                break

            logger.debug("Sending follow-up query API call")
            full_query = f"Here is the OCR-extracted text for your investigation:\n\n{ocr_content}\n\n{selected_content}\n\nFollow-up question:\n{query}"
            query_tokens = estimate_tokens(full_query)
            if query_tokens > 120000:
                logger.warning(f"Query exceeds token limit ({query_tokens} tokens). Truncating...")
                full_query = truncate_text(full_query, 120000)

            payload = {
                "model": "grok-3-fast-latest",
                "messages": [{"role": "user", "content": full_query}],
                "temperature": 0.01
            }
            response = requests.post(API_URL, headers=headers, json=payload, timeout=TIMEOUT)
            response.raise_for_status()
            response_json = response.json()
            response_content = response_json['choices'][0]['message']['content']
            json_file = os.path.join(logs_dir, f"followup_response_{followup_counter:03d}.json")
            with open(json_file, "w", encoding='utf-8') as f:
                json.dump(response_json, f, indent=2)
                f.flush()
            logger.debug(f"Saved JSON response: {json_file}")
            logger.debug("Received follow-up query response")
            print(response_content)

            followup_filename = f"followup_{followup_counter:03d}.txt"
            followup_file = os.path.join(followups_dir, followup_filename)
            with open(followup_file, "w", encoding='utf-8') as f:
                f.write(f"Follow-up Query:\n{query}\nResponse:\n{response_content}\n{'-'*50}\n")
                f.flush()
            logger.debug(f"Saved follow-up file: {followup_file}")
            followup_counter += 1
    except requests.RequestException as e:
        logger.error(f"Interactive query API error: {str(e)}")
        raise
    except (OSError, IOError) as e:
        logger.error(f"File operation error in interactive query: {str(e)}")
        raise