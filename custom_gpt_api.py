import os
from flask import Flask, request, jsonify
from PyPDF2 import PdfReader
from pytesseract import image_to_string
from pdf2image import convert_from_path
from PIL import Image
import psutil  # Add the psutil import to monitor memory usage

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
    print(f"Memory usage before processing query: {psutil.virtual_memory().percent}%")  # Log memory usage

    for filename in os.listdir(folder_path):
        if filename.endswith(".pdf"):
            file_path = os.path.join(folder_path, filename)
            print(f"Processing file: {filename}")
            try:
                images = convert_from_path(file_path, first_page=1, last_page=3, poppler_path="/usr/bin")
                content = ''.join([ocr_page(img) for img in images])
                print(f"Memory usage after OCR: {psutil.virtual_memory().percent}%")  # Log memory usage

                if query.lower() in content.lower():
                    response = f"Found in {filename}: Matching content found!"
                    break
            except Exception as e:
                print(f"Error processing {filename}: {e}")

    print(f"Final response: {response}")
    print(f"Memory usage after processing: {psutil.virtual_memory().percent}%")  # Log memory usage
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv("PORT", 5000)))
