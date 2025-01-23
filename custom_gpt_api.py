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
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created missing directory: {path}")

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

# Helper: Check for partial query matches
def is_query_match(query, content):
    """Check if the query partially matches the content."""
    similarity = SequenceMatcher(None, query.lower(), content.lower()).ratio()
    return similarity > 0.5  # Adjust threshold as needed

# Function: Process user queries
def custom_gpt(query):
    """Process a query using PDFs first, then cached files, and finally OpenAI GPT."""
    print(f"Processing query: {query}")

    # Step 1: Search in PDFs using the same logic as /query
    pdf_results = search_query_in_pdfs(query)
    if pdf_results:
        # Format the first result from the PDF search
        top_result = pdf_results[0]
        return (
            f"I found this in '{top_result['file']}' (page {top_result['page']}): "
            f"{top_result['snippet']}"
        )

    # Step 2: Search in cached text files
    for filename in os.listdir(CUSTOMGPT_FILES):
        if filename.endswith(".pdf.txt"):
            with open(os.path.join(CUSTOMGPT_FILES, filename), "r") as f:
                content = f.read()
                if is_query_match(query, content):
                    start_index = content.lower().find(query.lower())
                    snippet = content[start_index:start_index + 200]
                    return f"Found in {filename.replace('.txt', '')}: {snippet}..."

    # Step 3: Fallback to OpenAI GPT
    print("Query not found in PDFs or cached files. Falling back to OpenAI GPT.")
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
        return "An error occurred while processing your query."

# Flask Endpoints
@app.route('/chat', methods=['POST'])
def chat():
    """Chat endpoint to process queries using CustomGPT."""
    api_key = request.headers.get('Authorization')
    if api_key != os.getenv("CUSTOM_API_KEY"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    user_message = data.get('message', '')
    return jsonify({"reply": custom_gpt(user_message)})

if __name__ == "__main__":
    app.run(debug=True, port=8000)