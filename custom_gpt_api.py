from flask import Flask, request, jsonify
import os
from PyPDF2 import PdfReader
from pytesseract import image_to_string
from pdf2image import convert_from_path
from PIL import Image
from difflib import SequenceMatcher
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import subprocess
import openai

app = Flask(__name__)

# Define constants
PDF_ROOT = "/Users/haniahmed/Documents/Uploaded_PDFs"
PDF_FOLDER = "/Users/haniahmed/Documents/Uploaded_PDFs/Basic_Pdfs"
CUSTOMGPT_FILES = "CustomGPT_files"
POPLER_PATH = "/opt/homebrew/bin"

# Ensure directories exist
for path in [PDF_ROOT, PDF_FOLDER, CUSTOMGPT_FILES]:
    try:
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"Created missing directory: {path}")
    except Exception as e:
        print(f"Error creating directory {path}: {e}")

# Set OpenAI API Key
openai.api_key = os.getenv("CUSTOM_API_KEY")

# Helper: Get all PDFs
def get_all_pdfs():
    """Recursively find all PDF files in the root directory."""
    pdf_files = []
    for root, dirs, files in os.walk(PDF_ROOT):
        for file in files:
            if file.endswith(".pdf"):
                pdf_files.append(os.path.join(root, file))
    return pdf_files

# Helper: Search query in PDFs
def search_query_in_pdfs(query):
    """Search for a query in all PDFs and return matching results."""
    results = []
    for pdf_path in get_all_pdfs():
        try:
            reader = PdfReader(pdf_path)
            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text()
                if query.lower() in text.lower():
                    snippet_start = text.lower().find(query.lower())
                    snippet = text[max(0, snippet_start - 50):snippet_start + 150]
                    results.append({
                        "file": os.path.relpath(pdf_path, PDF_ROOT),
                        "page": page_num,
                        "snippet": snippet
                    })
        except Exception as e:
            print(f"Error reading {pdf_path}: {e}")
    return results

# Helper: Preprocess PDFs into cached text files
def preprocess_pdfs():
    """Convert PDFs to text files using OCR and cache results."""
    for filename in os.listdir(CUSTOMGPT_FILES):
        if filename.endswith(".pdf"):
            file_path = os.path.join(CUSTOMGPT_FILES, filename)
            text_output_path = f"{file_path}.txt"
            if not os.path.exists(text_output_path):
                try:
                    images = convert_from_path(file_path, poppler_path=POPLER_PATH)
                    content = ''.join([image_to_string(img, config="--oem 3 --psm 6") for img in images])
                    with open(text_output_path, "w") as f:
                        f.write(content)
                    print(f"Processed and cached: {filename}")
                except Exception as e:
                    print(f"Error processing {filename}: {e}")

# Helper: Check for partial query matches
def is_query_match(query, content):
    """Check if the query partially matches the content."""
    similarity = SequenceMatcher(None, query.lower(), content.lower()).ratio()
    return similarity > 0.5  # Adjust threshold as needed

# Function: Process user queries
def custom_gpt(query):
    """Process a query using cached PDFs or fallback to OpenAI GPT."""
    response = "No relevant content found."
    print(f"Processing query: {query}")

    for filename in os.listdir(CUSTOMGPT_FILES):
        if filename.endswith(".pdf.txt"):
            with open(os.path.join(CUSTOMGPT_FILES, filename), "r") as f:
                content = f.read()
                if is_query_match(query, content):
                    start_index = content.lower().find(query.lower())
                    snippet = content[start_index:start_index + 200]
                    return f"Found in {filename.replace('.txt', '')}: {snippet}..."

    # Fallback to OpenAI GPT
    print("Query not found in PDFs. Falling back to OpenAI GPT.")
    try:
        ai_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": query}],
            max_tokens=200,
            temperature=0.7
        )
        return ai_response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error querying OpenAI: {e}")
        return "Sorry, I couldn't process your request."

# Flask Endpoints
@app.route('/list', methods=['GET'])
def list_pdfs():
    """List all PDFs available in the root directory."""
    pdf_files = [os.path.relpath(path, PDF_ROOT) for path in get_all_pdfs()]
    return jsonify({"pdf_files": pdf_files})

@app.route('/query', methods=['POST'])
def query_pdfs():
    """Query a term in all PDFs."""
    data = request.json
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "No query provided"}), 400

    results = search_query_in_pdfs(query)
    if not results:
        return jsonify({"results": "No matches found."})
    return jsonify({"results": results})

@app.route('/chat', methods=['POST'])
def chat():
    """Chat endpoint to process queries using CustomGPT."""
    api_key = request.headers.get('Authorization')
    if api_key != os.getenv("CUSTOM_API_KEY"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    user_message = data.get('message', '')
    return jsonify({"reply": custom_gpt(user_message)})

# Watchdog: Monitor PDF Folder
class PDFHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith(".pdf"):
            print(f"New PDF detected: {event.src_path}")
            subprocess.run(["python3", "extract_text.py", event.src_path])

    def on_deleted(self, event):
        if event.src_path.endswith(".pdf"):
            print(f"PDF removed: {event.src_path}")

def start_watchdog():
    event_handler = PDFHandler()
    observer = Observer()
    observer.schedule(event_handler, PDF_FOLDER, recursive=False)
    observer.start()
    print("Monitoring PDFs...")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

# Main Function
if __name__ == "__main__":
    preprocess_pdfs()  # Preprocess PDFs on startup

    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=lambda: app.run(debug=True, port=8000, use_reloader=False))
    flask_thread.start()

    # Start watchdog for monitoring
    start_watchdog()
