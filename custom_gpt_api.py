from flask import Flask, request, jsonify
import os
from PyPDF2 import PdfReader
from pytesseract import image_to_string
from pdf2image import convert_from_path
from PIL import Image
from multiprocessing import Pool
from difflib import SequenceMatcher

app = Flask(__name__)

# Ensure the "CustomGPT_files" directory exists
if not os.path.exists("CustomGPT_files"):
    os.makedirs("CustomGPT_files")
    print("Created missing 'CustomGPT_files' directory.")

# Define your custom API key
CUSTOM_API_KEY = os.getenv("CUSTOM_API_KEY")  # Use environment variable for API key

# Function to perform OCR on a single image
def ocr_page(image):
    # Downscale image for faster processing
    image = image.resize((image.width // 2, image.height // 2))
    return image_to_string(image, config="--oem 3 --psm 6")

# Function to check partial query match
def is_query_match(query, content):
    similarity = SequenceMatcher(None, query.lower(), content.lower()).ratio()
    print(f"Similarity score for query '{query}': {similarity}")  # Debug: Log similarity score
    return similarity > 0.3  # Lower threshold for partial match

# Function to process user queries with CustomGPT logic
def custom_gpt(query):
    folder_path = "CustomGPT_files"  # Folder containing your PDFs
    response = "No relevant content found."

    # Debug: List all files in the folder
    files = [f for f in os.listdir(folder_path) if f.endswith(".pdf")]
    print(f"Files in {folder_path}: {files}")  # Debug: Log all PDFs in the folder

    for filename in files:
        print(f"Processing file: {filename}")  # Debug: File being processed
        file_path = os.path.join(folder_path, filename)

        try:
            # Process only the first 3 pages for optimization
            images = convert_from_path(file_path, first_page=1, last_page=3, poppler_path="/usr/bin")
            ocr_output_path = f"{file_path}.txt"

            # Check if OCR results are cached
            if os.path.exists(ocr_output_path):
                with open(ocr_output_path, "r") as f:
                    content = f.read()
            else:
                # Perform OCR in parallel for better performance
                with Pool(processes=4) as pool:  # Adjust number of processes based on your CPU cores
                    text_list = pool.map(ocr_page, images)
                content = ''.join(text_list)

                # Cache the OCR results
                with open(ocr_output_path, "w") as f:
                    f.write(content)

            # Debug: Print full extracted content
            print(f"Processing file: {filename}")
            print(f"Full OCR content extracted (first 500 chars):\n{content[:500]}\n")

            # Use partial matching for query
            if is_query_match(query, content):
                print(f"Query '{query}' found in {filename}")
                response = f"Found in {filename}: Matching content found!"
                break
            else:
                # Debug: Check each word in the query
                for word in query.lower().split():
                    print(f"Checking for word '{word}' in the content...")
                    if word in content.lower():
                        print(f"Word '{word}' found in the content!")
                        start_index = content.lower().find(word)
                        snippet = content[start_index:start_index + 200]
                        response = f"Found in {filename}: Partial match for word '{word}': {snippet}..."
                        break
                    else:
                        print(f"Word '{word}' NOT found in the content.")

        except Exception as e:
            print(f"Error processing {filename}: {e}")

    print(f"Final response: {response}")
    return response

# Root route
@app.route('/')
def home():
    print("Root route accessed")
    return "Welcome to the Custom GPT API! Use /upload to upload files and /chat to query."

# Define the API route with API key validation
@app.route('/chat', methods=['POST'])
def chat():
    api_key = request.headers.get('Authorization')
    print(f"Received API Key: {api_key}")  # Debug log
    print(f"Expected API Key: {CUSTOM_API_KEY}")  # Debug log

    if api_key != CUSTOM_API_KEY:
        print("API Key mismatch! Unauthorized access.")  # Debug log
        return jsonify({"error": "Unauthorized"}), 401

    # Process the query
    data = request.json
    user_message = data.get('message', '')
    gpt_response = custom_gpt(user_message)
    return jsonify({"reply": gpt_response})

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

@app.route('/list', methods=['GET'])
def list_files():
    files = os.listdir("CustomGPT_files")
    return jsonify({"files": files})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv("PORT", 5000)))
