import os
from flask import Flask, request, jsonify
from PyPDF2 import PdfReader
from pytesseract import image_to_string
from pdf2image import convert_from_path
from PIL import Image
from docx import Document
from fuzzywuzzy import fuzz
from difflib import SequenceMatcher
import openai

# Flask app initialization
app = Flask(__name__)

@app.route("/")
def home():
    return "Hello, Azure!"

# Define constants
FOLDER_PATH = "/Users/haniahmed/Documents/Uploaded_PDFs/Basic_Pdfs"

# Ensure directory exists
if not os.path.exists(FOLDER_PATH):
    os.makedirs(FOLDER_PATH)
    print(f"Created missing directory: {FOLDER_PATH}")

# Set OpenAI API Key
openai.api_key = os.getenv("CUSTOM_API_KEY")

# Function to normalize queries
def normalize_query(query):
    question_phrases = [
        "what is", "define", "explain", "tell me about",
        "describe", "how to", "why is", "list", "give me"
    ]
    normalized_query = query.lower()
    for phrase in question_phrases:
        if normalized_query.startswith(phrase):
            normalized_query = normalized_query.replace(phrase, "").strip()
            break
    return " ".join(normalized_query.split())  # Remove extra spaces

# Extract text from a PDF
def extract_text_from_pdf(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        return "".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return ""

# Extract text from images in a PDF
def extract_text_from_images(pdf_path):
    try:
        images = convert_from_path(pdf_path)
        return "".join(image_to_string(image) for image in images)
    except Exception as e:
        print(f"Error processing images in {pdf_path}: {e}")
        return ""

# Extract text from DOCX files
def extract_text_from_docx(docx_path):
    try:
        doc = Document(docx_path)
        return "\n".join(p.text for p in doc.paragraphs if p.text)
    except Exception as e:
        print(f"Error processing {docx_path}: {e}")
        return ""

# Preprocess and cache text for supported files
def preprocess_file(file_path):
    txt_file_path = f"{file_path}.txt"

    if os.path.exists(txt_file_path):
        print(f"Skipping already cached file: {file_path}")
        return

    ext = os.path.splitext(file_path)[1].lower()
    content = ""

    if ext == ".pdf":
        content = extract_text_from_pdf(file_path) or extract_text_from_images(file_path)
    elif ext == ".docx":
        content = extract_text_from_docx(file_path)
    else:
        print(f"Unsupported file type: {file_path}")
        return

    if content:
        with open(txt_file_path, "w") as f:
            f.write(content)
        print(f"Processed and cached: {txt_file_path}")
    else:
        print(f"No content extracted from: {file_path}")

# Preprocess all files in the folder
def preprocess_all_files():
    print("Starting preprocessing of all files...")
    for root, _, files in os.walk(FOLDER_PATH):
        for file in files:
            file_path = os.path.join(root, file)
            preprocess_file(file_path)
    print("Preprocessing complete.")

# Endpoint to preprocess all files
@app.route('/preprocess', methods=['GET'])
def preprocess_endpoint():
    try:
        preprocess_all_files()
        return jsonify({"message": "All files successfully preprocessed."})
    except Exception as e:
        return jsonify({"message": f"Error during preprocessing: {e}"}), 500

# Fuzzy match query in text
def fuzzy_match(query, content, snippet_length=500):
    paragraphs = content.split("\n\n")
    best_match = None
    highest_score = 0

    for paragraph in paragraphs:
        # Use partial_ratio and SequenceMatcher for more accurate matching
        partial_score = fuzz.partial_ratio(query.lower(), paragraph.lower())
        sequence_score = SequenceMatcher(None, query.lower(), paragraph.lower()).ratio() * 100

        combined_score = (partial_score + sequence_score) / 2

        if combined_score > highest_score and combined_score > 75:  # Adjustable threshold
            highest_score = combined_score
            best_match = paragraph

    if best_match:
        # Return a longer snippet with surrounding text
        start_index = content.find(best_match)
        return content[max(0, start_index - snippet_length):start_index + len(best_match) + snippet_length]
    return None

# Query endpoint
@app.route('/query', methods=['POST'])
def query_files():
    data = request.json
    query = data.get('query', '').strip()
    matches = []

    if not query:
        return jsonify({"message": "Query cannot be empty."}), 400

    preprocess_all_files()

    normalized_query = normalize_query(query)

    for root, _, files in os.walk(FOLDER_PATH):
        for file in files:
            if file.endswith(".txt"):
                txt_file_path = os.path.join(root, file)
                with open(txt_file_path, "r") as f:
                    content = f.read()
                    if normalized_query in content.lower():
                        start_index = content.lower().find(normalized_query)
                        snippet = content[max(0, start_index - 500):start_index + 500]
                        matches.append({"file": file.replace(".txt", ""), "snippet": snippet})
                    else:
                        match = fuzzy_match(normalized_query, content, snippet_length=500)
                        if match:
                            matches.append({"file": file.replace(".txt", ""), "snippet": match})

    if matches:
        return jsonify({"matches": matches})

    # Fallback to OpenAI GPT
    print("No matches found. Falling back to OpenAI GPT.")
    try:
        ai_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": query}],
            max_tokens=500,
            temperature=0.7
        )
        return jsonify({"reply": ai_response['choices'][0]['message']['content'].strip()})
    except Exception as e:
        print(f"Error querying OpenAI: {e}")
        return jsonify({"message": "Error querying OpenAI GPT."}), 500

if __name__ == "__main__":
    print("Starting Flask server...")
    app.run(debug=True, host='0.0.0.0', port=8000)



