from flask import Flask, request, jsonify
import os
from PyPDF2 import PdfReader
from pytesseract import image_to_string
from pdf2image import convert_from_path
from PIL import Image
import psutil  # For memory usage debugging

app = Flask(__name__)

# Ensure the "CustomGPT_files" directory exists
if not os.path.exists("CustomGPT_files"):
    os.makedirs("CustomGPT_files")
    print("Created missing 'CustomGPT_files' directory.")

# Define your custom API key
CUSTOM_API_KEY = os.getenv("CUSTOM_API_KEY")  # Use environment variable for API key

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
                break
        except Exception as e:
            print(f"Error processing {filename}: {e}")  # Debug: Log exceptions

    print(f"Final response: {response}")  # Debug: Log the final response
    return response

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv("PORT", 5000)))
