import os
import pickle
import bs4 as bs
import numpy as np
import pandas as pd
import urllib.request
from flask import Flask, render_template, request
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer

# For environment variables
from dotenv import load_dotenv

# Load variables from .env file (for local testing)
load_dotenv()

app = Flask(__name__)

# =========================
# CONFIG & ENV VARIABLES
# =========================
# Uses environment variable from Render, or falls back to your generated key
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "d63082faf25460e9c63a799e3596aada47fa4e76c2811fe4")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
DEBUG_MODE = os.environ.get("FLASK_DEBUG", "False").lower() == "true"

# =========================
# BASE DIRECTORY
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================
# LOAD SENTIMENT MODELS
# =========================
clf = None
vectorizer = None

try:
    clf_path = os.path.join(BASE_DIR, "Artifacts", "nlp_model.pkl")
    vec_path = os.path.join(BASE_DIR, "Artifacts", "tranform.pkl")
    
    if os.path.exists(clf_path) and os.path.exists(vec_path):
        clf = pickle.load(open(clf_path, "rb"))
        vectorizer = pickle.load(open(vec_path, "rb"))
        print("✅ Sentiment models loaded successfully")
    else:
        print("⚠️ Sentiment model files not found in Artifacts/")
except Exception as e:
    print("❌ Model loading error:", e)

# =========================
# GLOBAL DATA (MEMORY SAFE)
# =========================
data = None
count_matrix = None 

def load_data():
    global data, count_matrix
    try:
        data_path = os.path.join(BASE_DIR, "Artifacts", "main_data.csv")
        if not os.path.exists(data_path):
            print(f"❌ Error: {data_path} not found!")
            return

        data = pd.read_csv(data_path)
        
        # Ensure movie_title column is clean (lowercase and no spaces)
        if 'movie_title' in data.columns:
            data['movie_title'] = data['movie_title'].str.lower().str.strip()
        elif 'title' in data.columns:
            data['movie_title'] = data['title'].str.lower().str.strip()
        
        # Fill missing values in 'comb' to prevent matrix errors
        if 'comb' in data.columns:
            data['comb'] = data['comb'].fillna('')
            cv = CountVectorizer()
            count_matrix = cv.fit_transform(data["comb"])
            print(f"✅ Data ({len(data)} movies) and sparse matrix loaded")
        else:
            print("❌ Error: 'comb' column missing. Run your fix_csv script.")
            
    except Exception as e:
        print("❌ Loading error:", e)

# Initial load at startup
load_data()

# =========================
# RECOMMENDATION ENGINE
# =========================
def rcmd(movie):
    # DEFENSIVE: Strip spaces and lowercase the search term
    movie = str(movie).lower().strip()

    if data is None or count_matrix is None:
        return []

    # Get the list of titles from the CSV
    titles = data["movie_title"].values

    if movie not in titles:
        print(f"DEBUG: '{movie}' not found in dataset")
        return []

    try:
        # Find index of the movie
        idx = data.loc[data["movie_title"] == movie].index[0]

        # LIVE CALCULATION: Calculate similarity ONLY for this movie (Memory Safe)
        sig_score = cosine_similarity(count_matrix[idx], count_matrix)

        # Get scores and sort them (Skip the first one as it's the same movie)
        scores = list(enumerate(sig_score[0]))
        scores = sorted(scores, key=lambda x: x[1], reverse=True)
        
        recommendations = []
        for i, score in scores:
            if i != idx: # Don't recommend the searched movie itself
                recommendations.append(data["title"].iloc[i])
            if len(recommendations) == 10: # Stop at 10
                break

        return recommendations

    except Exception as e:
        print("❌ Recommendation error:", e)
        return []

# =========================
# UTILS
# =========================
def convert_to_list(text):
    try:
        if not text: return []
        if '","' in text:
            return text.strip('[]"').split('","')
        return text.strip('[]').replace("'", "").split(', ')
    except:
        return []

def get_suggestions():
    try:
        # Returns the display titles for the autocomplete dropdown
        return list(data["title"].str.title())
    except:
        return []

# =========================
# ROUTES
# =========================
@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html", suggestions=get_suggestions())

@app.route("/similarity", methods=["POST"])
def similarity_route():
    movie = request.form.get("name")
    if not movie:
        return "No movie provided"
    
    result = rcmd(movie)
    
    if not result:
        return "Movie not found or data not loaded"
    
    # Return joined string as expected by the frontend JavaScript
    return "---".join(result)

@app.route("/recommend", methods=["POST"])
def recommend():
    try:
        # Extract movie details from AJAX request
        title = request.form.get("title")
        imdb_id = request.form.get("imdb_id")
        poster = request.form.get("poster")
        overview = request.form.get("overview")
        vote_average = request.form.get("rating")
        vote_count = request.form.get("vote_count")
        release_date = request.form.get("release_date")
        runtime = request.form.get("runtime")
        status = request.form.get("status")
        genres = request.form.get("genres")
        
        rec_movies = convert_to_list(request.form.get("rec_movies"))
        rec_posters = convert_to_list(request.form.get("rec_posters"))

        movie_cards = dict(zip(rec_posters, rec_movies))

        # IMDB SCRAPING & SENTIMENT ANALYSIS
        movie_reviews = {}
        if imdb_id:
            try:
                url = f"https://www.imdb.com/title/{imdb_id}/reviews"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                sauce = urllib.request.urlopen(req, timeout=5).read()
                soup = bs.BeautifulSoup(sauce, "lxml")
                reviews = soup.find_all("div", class_="text show-more__control")

                for r in reviews[:8]:
                    text = r.get_text(strip=True)
                    # Use models to predict sentiment
                    if clf and vectorizer:
                        vec = vectorizer.transform([text])
                        pred = clf.predict(vec)
                        status_label = "Good" if pred[0] == 1 else "Bad"
                    else:
                        status_label = "Unknown"
                    movie_reviews[text] = status_label
            except Exception as e:
                print("⚠️ IMDB scraping failed:", e)

        return render_template(
            "recommend.html", title=title, poster=poster, overview=overview,
            vote_average=vote_average, vote_count=vote_count, release_date=release_date,
            runtime=runtime, status=status, genres=genres, movie_cards=movie_cards, 
            reviews=movie_reviews
        )
    except Exception as e:
        print("❌ Recommend route error:", e)
        return "Something went wrong"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=DEBUG_MODE)