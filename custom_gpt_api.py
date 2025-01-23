from flask import Flask, request, jsonify
import os
from pathlib import Path
from PyPDF2 import PdfReader
from pytesseract import image_to_string
from pdf2image import convert_from_path
from PIL import Image
from difflib import SequenceMatcher
import openai

app = Flask(__name__)

# Define constants using `pathlib`
BASE_DIR = Path(__file__).parent  # Dynamically get the base directory
PDF_ROOT = BASE_DIR / "Uploaded_PDFs"
CUSTOMGPT_FILES = BASE_DIR / "CustomGPT_files"
POPLER_PATH = "/opt/homebrew/bin"

# Ensure directories exist
for path in [PDF_ROOT, CUSTOMGPT_FILES]:
    if not path.exists():
        path.mkdir(parents=True)
        print(f"Created missing directory: {path}")

# Set OpenAI API Key
openai.api_key = os.getenv("CUSTOM_API_KEY")

# Helper: Get all PDFs
def get_all_pdfs():
    """Recursively find all PDF files in the Uploaded_PDFs folder."""
    pdf_files = [f for f in PDF_ROOT.glob("**/*.pdf")]
    print(f"Found PDF files: {pdf_files}")  # Debug log
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
                        "file": pdf_path.relative_to(PDF_ROOT).as_posix(),
                        "page": page_num,
                        "snippet": snippet
                    })
        except Exception as e:
            print(f"Error reading {pdf_path}: {e}")
    print(f"Search results: {results}")  # Debug log
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

    # Step 1: Search in PDFs
    pdf_results = search_query_in_pdfs(query)
    if pdf_results:
        # Format the first result from the PDF search
        top_result = pdf_results[0]
        return (
            f"I found this in '{top_result['file']}' (page {top_result['page']}): "
            f"{top_result['snippet']}"
        )

    # Step 2: Search in cached text files
    for filename in CUSTOMGPT_FILES.glob("*.pdf.txt"):
        with filename.open("r") as f:
            content = f.read()
            if is_query_match(query, content):
                start_index = content.lower().find(query.lower())
                snippet = content[start_index:start_index + 200]
                return f"Found in {filename.stem}: {snippet}..."

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

@app.route('/list', methods=['GET'])
def list_pdfs():
    """List all PDFs available in the Uploaded_PDFs directory."""
    pdf_files = [path.relative_to(PDF_ROOT).as_posix() for path in get_all_pdfs()]
    return jsonify({"pdf_files": pdf_files})

@app.route('/routes', methods=['GET'])
def list_routes():
    """List all registered routes in the app."""
    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods)
        output.append(f"{rule.endpoint}: {rule.rule} [{methods}]")
    return jsonify(output)

# Main execution
if __name__ == "__main__":
    print(f"Starting server with PDF_ROOT set to: {PDF_ROOT}")
    app.run(debug=True, port=8000)


