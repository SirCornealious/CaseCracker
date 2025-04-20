# Case Cracker
Crack your case with xAI. Converts PDF to JPEG, OCR with grok-2-vision-latest, analysis with grok-3-fast-latest. Solve the mysteries of the universe, and more.

## Setup
1. Install Python 3.
2. Clone the repository: `git clone https://github.com/SirCornealious/CaseCracker.git`
3. Navigate to the directory: `cd CaseCracker`
4. Create a virtual environment: `python3 -m venv venv`
5. Activate the virtual environment: `source venv/bin/activate` (macOS/Linux) or `venv\Scripts\activate` (Windows)
6. Install dependencies: `pip install requests pdf2image Pillow`
7. For PDFs, install Poppler and update POPPLER_PATH in utils.py.
8. Run the application: `python3 CaseCracker.py`
