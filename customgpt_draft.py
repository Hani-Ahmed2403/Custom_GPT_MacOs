import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from azure.storage.blob import ContainerClient
import openai
from PyPDF2 import PdfReader
from io import BytesIO
from docx import Document
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add validation check
if not os.getenv("AZURE_CONN_STR"):
    raise ValueError("AZURE_CONN_STR environment variable is missing!")

app = Flask(__name__)
CORS(app)

# Simplified Configuration
CONFIG = {
    "MAX_TEXT_LENGTH": 1500,
    "MAX_BLOBS": 10,  # Reduced for WordPress compatibility
    "SIMILARITY_THRESHOLD": 0.15  # Lower threshold for broader matches
}

# Initialize Azure Client
container_client = ContainerClient.from_connection_string(
    conn_str=os.getenv("AZURE_CONN_STR"),
    container_name="customgpt"
)

# Simplified Processing Functions
def process_file(blob_data, extension):
    try:
        if extension == 'pdf':
            reader = PdfReader(BytesIO(blob_data))
            return [page.extract_text()[:CONFIG['MAX_TEXT_LENGTH']] for page in reader.pages]
        elif extension == 'docx':
            doc = Document(BytesIO(blob_data))
            return [para.text[:CONFIG['MAX_TEXT_LENGTH']] for para in doc.paragraphs if para.text.strip()]
    except Exception as e:
        logging.error(f"Processing error: {str(e)}")
    return []

# Unified Search Endpoint
@app.route('/ask', methods=['POST'])
def handle_query():
    query = request.json.get('query', '').strip()
    if not query:
        return jsonify({"error": "Empty query"}), 400

    try:
        # 1. Search Documents
        results = []
        blobs = list(container_client.list_blobs())[:CONFIG['MAX_BLOBS']]
        
        for blob in blobs:
            blob_client = container_client.get_blob_client(blob.name)
            data = blob_client.download_blob().readall()
            content = process_file(data, blob.name.split('.')[-1])
            
            if any(query.lower() in text.lower() for text in content):
                results.append({
                    "filename": blob.name,
                    "excerpts": [t for t in content if query.lower() in t.lower()][:3]
                })

        # 2. Return matches or fallback to OpenAI
        if results:
            return jsonify({"results": results})
            
        # 3. OpenAI Fallback
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": query}]
        )
        return jsonify({
            "reply": response.choices[0].message.content
        })

    except Exception as e:
        logging.error(f"System error: {str(e)}")
        return jsonify({"error": "Service unavailable"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)


