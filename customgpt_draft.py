import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from azure.storage.blob import ContainerClient
import openai
from PyPDF2 import PdfReader
from io import BytesIO
from docx import Document

app = Flask(__name__)
CORS(app, resources={r"/ask": {"origins": "*"}})  # Allow CORS for /ask

CONFIG = {
    "MAX_TEXT_LENGTH": 1500,
    "MAX_BLOBS": 10,
    "SIMILARITY_THRESHOLD": 0.15
}

# Initialize Azure Client with error handling
try:
    container_client = ContainerClient.from_connection_string(
        conn_str=os.getenv("AZURE_CONN_STR"),
        container_name="documents"
    )
    # Verify container exists
    if not container_client.exists():
        raise RuntimeError("Azure container 'documents' not found")
except Exception as e:
    logging.error(f"Azure init failed: {str(e)}")
    raise

def process_file(blob_data, extension):
    try:
        if extension.lower() == 'pdf':
            reader = PdfReader(BytesIO(blob_data))
            return [page.extract_text()[:CONFIG['MAX_TEXT_LENGTH']] 
                   for page in reader.pages if page.extract_text()]
        elif extension.lower() == 'docx':
            doc = Document(BytesIO(blob_data))
            return [para.text[:CONFIG['MAX_TEXT_LENGTH']] 
                   for para in doc.paragraphs if para.text.strip()]
    except Exception as e:
        logging.error(f"Error processing {extension} file: {str(e)}")
    return []

@app.route('/ask', methods=['POST'])
def handle_query():
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        if not query:
            return jsonify({"error": "Empty query"}), 400

        results = []
        blobs = list(container_client.list_blobs())[:CONFIG['MAX_BLOBS']]
        
        for blob in blobs:
            try:
                blob_client = container_client.get_blob_client(blob.name)
                data = blob_client.download_blob().readall()
                extension = blob.name.split('.')[-1].lower()
                content = process_file(data, extension)
                
                if any(query.lower() in text.lower() for text in content):
                    results.append({
                        "filename": blob.name,
                        "excerpts": [t for t in content if query.lower() in t.lower()][:3]
                    })
            except Exception as e:
                logging.error(f"Error processing {blob.name}: {str(e)}")
                continue

        if results:
            return jsonify({"results": results})
            
        # OpenAI fallback
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
    app.run(host='0.0.0.0', port=8000)


