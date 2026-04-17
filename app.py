import os
import pickle
import bs4 as bs
import numpy as np
import pandas as pd
import urllib.request
import requests
from flask import Flask, render_template, request, jsonify
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# =========================
# CONFIG & ENV VARIABLES
# =========================
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "d63082faf25460e9c63a799e3596aada47fa4e76c2811fe4")
TMDB_API_KEY = "5ce2ef2d7c461dea5b4e04900d1c561e" # Hardcoded for functionality, but better in Env Vars
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================
# LOAD MODELS
# =========================
clf, vectorizer = None, None
try:
    clf = pickle.load(open(os.path.join(BASE_DIR, "Artifacts", "nlp_model.pkl"), "rb"))
    vectorizer = pickle.load(open(os.path.join(BASE_DIR, "Artifacts", "tranform.pkl"), "rb"))
except Exception as e:
    print("⚠️ Sentiment model loading error:", e)

# =========================
# GLOBAL DATA (MEMORY SAFE)
# =========================
data, count_matrix = None, None 

def load_data():
    global data, count_matrix
    try:
        data_path = os.path.join(BASE_DIR, "Artifacts", "main_data.csv")
        data = pd.read_csv(data_path)
        data['movie_title'] = data['movie_title'].str.lower().str.strip()
        
        cv = CountVectorizer()
        count_matrix = cv.fit_transform(data["comb"].fillna(''))
        print("✅ Data and Matrix loaded")
    except Exception as e:
        print("❌ Loading error:", e)

load_data()

# =========================
# RECOMMENDATION ENGINE
# =========================
def rcmd(movie):
    movie = str(movie).lower().strip()
    if data is None or count_matrix is None or movie not in data["movie_title"].values:
        return []

    try:
        idx = data.loc[data["movie_title"] == movie].index[0]
        sig_score = cosine_similarity(count_matrix[idx], count_matrix)
        scores = list(enumerate(sig_score[0]))
        scores = sorted(scores, key=lambda x: x[1], reverse=True)
        
        # Get top 10 (excluding itself)
        return [data["title"].iloc[i] for i, s in scores if i != idx][:10]
    except Exception as e:
        print("❌ RCMD error:", e)
        return []

# =========================
# ROUTES
# =========================
@app.route("/")
@app.route("/home")
def home():
    suggestions = list(data["title"].str.title()) if data is not None else []
    return render_template("home.html", suggestions=suggestions)

@app.route("/similarity", methods=["POST"])
def similarity_route():
    movie = request.form.get("name")
    result = rcmd(movie)
    return "---".join(result) if result else "Movie not found"

# FIX FOR CORS: This route fetches data from TMDB on the server side
@app.route("/tmdb_proxy", methods=["GET"])
def tmdb_proxy():
    query = request.args.get("query")
    movie_id = request.args.get("id")
    person_id = request.args.get("person_id")
    endpoint = request.args.get("endpoint", "search")

    if endpoint == "search":
        url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={query}"
    elif endpoint == "details":
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}"
    elif endpoint == "credits":
        url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={TMDB_API_KEY}"
    elif endpoint == "person":
        url = f"https://api.themoviedb.org/3/person/{person_id}?api_key={TMDB_API_KEY}"
    
    res = requests.get(url)
    return jsonify(res.json())

@app.route("/recommend", methods=["POST"])
def recommend():
    # ... (Keep your existing logic for scraping IMDB reviews here)
    # Ensure you use the robust 'convert_to_list' helper provided before
    pass 

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=DEBUG_MODE)