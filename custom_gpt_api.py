from flask import Flask, request, jsonify
import os
from PyPDF2 import PdfReader
from pytesseract import image_to_string
from pdf2image import convert_from_path
from PIL import Image
import psutil  # For memory usage debugging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import openai

app = Flask(__name__)

# Ensure the "CustomGPT_files" directory exists
if not os.path.exists("CustomGPT_files"):
    os.makedirs("CustomGPT_files")
    print("Created missing 'CustomGPT_files' directory.")

# Define your custom API key
CUSTOM_API_KEY = os.getenv("CUSTOM_API_KEY")  # Use environment variable for API key

# Use CUSTOM_API_KEY for OpenAI
openai.api_key = os.getenv("CUSTOM_API_KEY")

# Function to perform OCR on a single image
def ocr_page(image):
    image = image.resize((image.width // 2, image.height // 2))  # Downscale image for memory optimization
    return image_to_string(image, config="--oem 3 --psm 6")

# Function to process user queries
def custom_gpt(query):
    folder_path = "CustomGPT_files"
    response = "No relevant content found."

    print(f"Processing query: {query}")  # Debug: Log the query
    files = [f for f in os.listdir(folder_path) if f.endswith(".pdf")]
    print(f"Files in {folder_path}: {files}")  # Debug: List files in the directory

    found_in_pdfs = False  # Track if the query is answered from PDFs

    for filename in files:
        file_path = os.path.join(folder_path, filename)
        print(f"Processing file: {file_path}")  # Debug: Log file being processed

        try:
            # Convert PDF to images
            images = convert_from_path(file_path, poppler_path="/usr/bin")
            print(f"Generated {len(images)} images from {file_path}")  # Debug: Log number of images generated

            content = ""
            for i, image in enumerate(images):
                print(f"Processing page {i + 1} of {filename}")  # Debug: Log page number
                content += image_to_string(image, config="--oem 3 --psm 6")

            print(f"Extracted content (first 500 chars): {content[:500]}")  # Debug: Log extracted text

            # Search for the query in the content
            if query.lower() in content.lower():
                start_index = content.lower().find(query.lower())
                snippet = content[start_index:start_index + 200]
                response = f"Found in {filename}: {snippet}..."
                found_in_pdfs = True
                break
        except Exception as e:
            print(f"Error processing {filename}: {e}")  # Debug: Log exceptions

    if not found_in_pdfs:
        print("Query not found in PDFs. Falling back to OpenAI GPT.")
        # Fallback to OpenAI GPT
        try:
            ai_response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=query,
                max_tokens=150
            )
            response = ai_response.choices[0].text.strip()
        except Exception as e:
            print(f"Error querying OpenAI: {e}")
            response = "Sorry, I couldn't process your request."

    print(f"Final response: {response}")  # Debug: Log the final response
    return response

# Function to initialize the PDF directory on server startup
def initialize_pdfs():
    folder_path = "CustomGPT_files"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print("Created missing 'CustomGPT_files' directory.")

    files = [f for f in os.listdir(folder_path) if f.endswith(".pdf")]
    print(f"Found {len(files)} PDFs in {folder_path}: {files}")
    if not files:
        print("No PDFs found. Please add files to the CustomGPT_files directory.")
    else:
        print("All PDFs will be processed dynamically during queries.")

# Function to monitor the directory for new PDFs
class PDFHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith(".pdf"):
            print(f"New PDF detected: {event.src_path}")

# Start watching the directory
def start_watcher():
    folder_path = "CustomGPT_files"
    event_handler = PDFHandler()
    observer = Observer()
    observer.schedule(event_handler, folder_path, recursive=False)
    observer.start()
    print("Watching for new PDFs...")

# Define the API route
@app.route('/chat', methods=['POST'])
def chat():
    api_key = request.headers.get('Authorization')
    if api_key != CUSTOM_API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    user_message = data.get('message', '')
    return jsonify({"reply": custom_gpt(user_message)})

@app.route('/upload', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Save the file to the "CustomGPT_files" directory
    file.save(os.path.join("CustomGPT_files", file.filename))
    return jsonify({"message": f"Uploaded {file.filename} successfully"}), 200

@app.route('/bulk-upload', methods=['POST'])
def bulk_upload():
    source_directory = request.json.get('source_directory')
    if not source_directory or not os.path.isdir(source_directory):
        return jsonify({"error": "Invalid source directory"}), 400

    destination_directory = "CustomGPT_files"
    for filename in os.listdir(source_directory):
        if filename.endswith(".pdf"):
            src = os.path.join(source_directory, filename)
            dst = os.path.join(destination_directory, filename)
            os.rename(src, dst)  # Or use shutil.copy(src, dst) to keep originals

    return jsonify({"message": "Bulk upload completed successfully!"}), 200

@app.route('/list', methods=['GET'])
def list_files():
    files = os.listdir("CustomGPT_files")
    return jsonify({"files": files})

if __name__ == '__main__':
    initialize_pdfs()  # Auto-load existing PDFs
    start_watcher()    # Watch for new PDFs dynamically
    app.run(debug=True, host='0.0.0.0', port=8000)
