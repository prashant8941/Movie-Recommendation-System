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
# Using your generated key as fallback; best to set this in Render Dashboard
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "d63082faf25460e9c63a799e3596aada47fa4e76c2811fe4")
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "your_default_key_here")
DEBUG_MODE = os.environ.get("FLASK_DEBUG", "False").lower() == "true"

# =========================
# BASE DIRECTORY
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================
# LOAD SENTIMENT MODELS
# =========================
try:
    clf = pickle.load(open(os.path.join(BASE_DIR, "Artifacts", "nlp_model.pkl"), "rb"))
    vectorizer = pickle.load(open(os.path.join(BASE_DIR, "Artifacts", "tranform.pkl"), "rb"))
except Exception as e:
    print("Model loading error:", e)
    clf, vectorizer = None, None

# =========================
# GLOBAL DATA (MEMORY SAFE)
# =========================
data = None
count_matrix = None 

def load_data():
    global data, count_matrix
    try:
        data_path = os.path.join(BASE_DIR, "Artifacts", "main_data.csv")
        data = pd.read_csv(data_path)
        
        # MEMORY OPTIMIZATION:
        # We only store the CountVectorizer sparse matrix.
        # We DO NOT calculate the N x N similarity matrix at startup.
        cv = CountVectorizer()
        count_matrix = cv.fit_transform(data["comb"])
        print("✅ Data and Count Matrix loaded successfully")
    except Exception as e:
        print("Loading error:", e)

# Load data into RAM once at startup
load_data()

# =========================
# RECOMMENDATION ENGINE
# =========================
def rcmd(movie):
    movie = movie.lower()

    if data is None or count_matrix is None:
        return []

    if movie not in data["movie_title"].values:
        return []

    try:
        # Find index of the movie
        idx = data.loc[data["movie_title"] == movie].index[0]

        # LIVE CALCULATION (MEMORY SAFE):
        # Calculate similarity ONLY for the searched movie against all others.
        # This creates a 1 x N vector (very light) instead of an N x N matrix (very heavy).
        sig_score = cosine_similarity(count_matrix[idx], count_matrix)

        # Get scores and sort them
        scores = list(enumerate(sig_score[0]))
        scores = sorted(scores, key=lambda x: x[1], reverse=True)[1:11]

        return [data["movie_title"][i[0]] for i in scores]

    except Exception as e:
        print("Recommendation engine error:", e)
        return []

# =========================
# UTILS
# =========================
def convert_to_list(text):
    try:
        if not text: return []
        return text.split('","')
    except:
        return []

def get_suggestions():
    try:
        # Return capitalized titles for the autocomplete dropdown
        return list(data["movie_title"].str.capitalize())
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
    
    return "---".join(result)

@app.route("/recommend", methods=["POST"])
def recommend():
    try:
        # Get data from AJAX request
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

        # =========================
        # IMDB SCRAPING & SENTIMENT
        # =========================
        reviews_list, reviews_status = [], []
        try:
            url = f"https://www.imdb.com/title/{imdb_id}/reviews"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            sauce = urllib.request.urlopen(req, timeout=5).read()
            soup = bs.BeautifulSoup(sauce, "lxml")
            reviews = soup.find_all("div", class_="text show-more__control")

            for r in reviews[:8]:
                text = r.get_text(strip=True)
                reviews_list.append(text)
                
                # Perform sentiment analysis if models are loaded
                if clf and vectorizer:
                    vec = vectorizer.transform([text])
                    pred = clf.predict(vec)
                    reviews_status.append("Good" if pred else "Bad")
                else:
                    reviews_status.append("Unknown")
        except Exception as e:
            print("IMDB scraping failed:", e)

        movie_reviews = dict(zip(reviews_list, reviews_status))

        return render_template(
            "recommend.html", 
            title=title, 
            poster=poster, 
            overview=overview,
            vote_average=vote_average, 
            vote_count=vote_count, 
            release_date=release_date,
            runtime=runtime, 
            status=status, 
            genres=genres, 
            movie_cards=movie_cards, 
            reviews=movie_reviews
        )
    except Exception as e:
        print("Recommend route error:", e)
        return "Something went wrong"

# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=DEBUG_MODE)