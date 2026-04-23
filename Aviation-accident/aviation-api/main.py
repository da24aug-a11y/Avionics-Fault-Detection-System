from fastapi import FastAPI
from pydantic import BaseModel
import pickle
import numpy as np
import spacy
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from fastapi.middleware.cors import CORSMiddleware
from database import get_connection

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str


model = pickle.load(open("model.pkl", "rb"))
tfidf = pickle.load(open("tfidf.pkl", "rb"))
mlb = pickle.load(open("mlb.pkl", "rb"))
embeddings = pickle.load(open("embeddings.pkl", "rb"))
df = pickle.load(open("df.pkl", "rb"))

nlp = spacy.load("en_core_web_sm")
sbert_model = SentenceTransformer("all-MiniLM-L6-v2")


# ================= SAFE DB LOG =================
def log_prediction(text, label, severity, risk_score, is_correct):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO incidents 
            (input_text, prediction_label, severity, risk_score, is_correct)
            VALUES (%s, %s, %s, %s, %s)
        """, (text, label, severity, risk_score, is_correct))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        print("DB Logging Failed:", e)


def preprocess_text(text):
    doc = nlp(text.lower())
    return " ".join([t.lemma_ for t in doc if not t.is_stop and not t.is_punct])


def retrieve_similar_cases(query):
    query_embedding = sbert_model.encode([query])
    similarities = cosine_similarity(query_embedding, embeddings)[0]
    top_indices = np.argsort(similarities)[-3:][::-1]

    return [
        {
            "summary": df.iloc[i]["Summary"],
            "faults": df.iloc[i]["faults"],
            "similarity": float(round(similarities[i], 3))
        }
        for i in top_indices
    ]


def suggest_actions(labels):
    actions = []

    if "Engine Failure" in labels:
        actions.append("Reduce thrust and attempt emergency landing")
    if "Weather" in labels:
        actions.append("Adjust route or altitude")
    if "Human Error" in labels:
        actions.append("Follow SOP and verify inputs")
    if "Mechanical Failure" in labels:
        actions.append("Inspect systems immediately")

    if not actions:
        actions.append("General diagnostics")

    return actions


def predict_logic(query):
    clean = preprocess_text(query)
    vec = tfidf.transform([clean])
    probs = model.predict_proba(vec)[0]

    labels = mlb.classes_
    threshold = 0.3

    predicted = []
    confidences = {}

    for i, p in enumerate(probs):
        if p >= threshold:
            predicted.append(labels[i])
            confidences[labels[i]] = float(round(p * 100, 2))

    if not predicted:
        idx = np.argmax(probs)
        predicted.append(labels[idx])
        confidences[labels[idx]] = float(round(probs[idx] * 100, 2))

    return {
        "labels": predicted,
        "confidences": confidences,
        "actions": suggest_actions(predicted),
        "evidence": retrieve_similar_cases(query)
    }


# ================= PREDICT API =================
@app.post("/predict")
def predict_api(req: QueryRequest):

    try:
        result = predict_logic(req.query)

        labels = result["labels"]
        confidences = result["confidences"]

        severity = "High" if any(c > 70 for c in confidences.values()) else "Medium"
        risk_score = max(confidences.values()) / 100 if confidences else 0.0

        log_prediction(
            req.query,
            ",".join(labels),
            severity,
            risk_score,
            1
        )

        return result

    except Exception as e:
        return {"error": str(e)}


# ================= DASHBOARD =================
@app.get("/dashboard")
def dashboard():

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM incidents")
        total = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM incidents WHERE severity = 'High'")
        high_risk = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT prediction_label, COUNT(*) 
            FROM incidents 
            GROUP BY prediction_label 
            ORDER BY COUNT(*) DESC 
            LIMIT 1
        """)
        row = cursor.fetchone()
        common_fault = row[0] if row else "None"

        cursor.execute("SELECT AVG(is_correct) FROM incidents")
        acc = cursor.fetchone()[0] or 0
        accuracy = round(acc * 100, 2)

        cursor.close()
        conn.close()

        return {
            "total": total,
            "high_risk": high_risk,
            "common_fault": common_fault,
            "accuracy": accuracy
        }

    except Exception as e:
        return {"error": str(e)}