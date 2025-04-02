from fastapi import FastAPI, File, UploadFile
import pymongo
import requests
import fitz  # PyMuPDF for extracting text
from sentence_transformers import SentenceTransformer, util
import numpy as np
from io import BytesIO
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from contextlib import asynccontextmanager
from fastapi.encoders import jsonable_encoder

# Load environment variables
load_dotenv()

# FastAPI app with lifespan event
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\U0001F680 Backend started: Extracting and storing text from PDFs...")
    store_extracted_text()
    print("\u2705 Text extraction completed and stored in DB. Ready for PDF uploads.")
    yield

app = FastAPI(lifespan=lifespan)

# Allow frontend to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to MongoDB
MONGO_URI = os.getenv("MONGO_URI")
client = pymongo.MongoClient(MONGO_URI)
db = client["AI-Document_Originality_Verification"]
collection = db["Project_Reports"]  # Original PDFs collection
extracted_db = client["Extracted_Texts"]
extracted_collection = extracted_db["Processed_Documents"]  # Extracted text collection

# Load Sentence Transformer model
model = SentenceTransformer("all-MiniLM-L6-v2")

def extract_text_from_pdf(pdf_bytes, max_pages=10):
    """Extract text from the first max_pages of a given PDF file bytes."""
    text = ""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page_num, page in enumerate(doc):
            if page_num >= max_pages:
                break
            text += page.get_text("text") + "\n"
    except Exception as e:
        print(f"Error extracting text: {e}")
    return text.strip()

def store_extracted_text():
    """Extract text from the first 10 pages of PDFs in Project_Reports and store in Extracted_Texts DB."""
    stored_docs = list(collection.find({}, {"file_url": 1, "name": 1}))

    for doc in stored_docs:
        if extracted_collection.find_one({"name": doc["name"]}):
            continue  # Skip if already processed
        try:
            response = requests.get(doc["file_url"])
            if response.status_code == 200:
                text = extract_text_from_pdf(BytesIO(response.content), max_pages=10)
                if text:
                    extracted_collection.insert_one({"name": doc["name"], "text": text})
                    print(f"\u2705 Stored extracted text for {doc['name']}")
        except Exception as e:
            print(f"\u274C Error downloading {doc['file_url']}: {e}")

def check_similarity(uploaded_text):
    """Compare uploaded text with stored documents and return originality score."""
    stored_docs = list(extracted_collection.find({}, {"name": 1, "text": 1}))

    if not stored_docs:
        return {"originality": 100.0, "most_similar_doc": "No documents in database"}

    stored_texts = [doc["text"] for doc in stored_docs]
    names = [doc["name"] for doc in stored_docs]

    uploaded_embedding = model.encode(uploaded_text, convert_to_tensor=True)
    stored_embeddings = model.encode(stored_texts, convert_to_tensor=True)

    similarity_scores = util.pytorch_cos_sim(uploaded_embedding, stored_embeddings)[0].cpu().numpy()

    max_similarity = np.max(similarity_scores)
    most_similar_doc = names[np.argmax(similarity_scores)]
    originality_score = (1 - max_similarity) * 100  # Adjust score to 0-100 scale

    return jsonable_encoder(
        {"originality": round(originality_score, 2), "most_similar_doc": most_similar_doc},
        custom_encoder={np.float32: float}
    )

@app.post("/check-similarity/")
async def check_similarity_endpoint(file: UploadFile = File(...)):
    """Endpoint to receive a PDF file, extract first 10 pages, and check originality."""
    pdf_bytes = await file.read()
    extracted_text = extract_text_from_pdf(BytesIO(pdf_bytes), max_pages=10)

    if not extracted_text:
        return {"error": "Failed to extract text from PDF"}

    result = check_similarity(extracted_text)
    return result
