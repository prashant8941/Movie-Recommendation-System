import os
import pickle
import bs4 as bs
import numpy as np
import pandas as pd
import urllib.request
from flask import Flask, render_template, request
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer

# NEW: Import for environment variables
from dotenv import load_dotenv

# Load variables from .env file (for local testing)
load_dotenv()

app = Flask(__name__)

# =========================
# CONFIG & ENV VARIABLES
# =========================
# Flask Secret Key for security (Sessions, CSRF, etc.)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "optional-local-fallback-key")

# API Keys and Debug settings
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "your_default_key_here")
DEBUG_MODE = os.environ.get("FLASK_DEBUG", "False").lower() == "true"

# =========================
# BASE DIRECTORY
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================
# LOAD MODELS SAFELY
# =========================
try:
    clf = pickle.load(open(os.path.join(BASE_DIR, "Artifacts", "nlp_model.pkl"), "rb"))
    vectorizer = pickle.load(open(os.path.join(BASE_DIR, "Artifacts", "tranform.pkl"), "rb"))
except Exception as e:
    print("Model loading error:", e)
    clf, vectorizer = None, None

# =========================
# GLOBAL DATA
# =========================
data = None
similarity = None

def create_similarity():
    global data, similarity
    try:
        data_path = os.path.join(BASE_DIR, "Artifacts", "main_data.csv")
        data = pd.read_csv(data_path)

        cv = CountVectorizer()
        count_matrix = cv.fit_transform(data["comb"])

        similarity = cosine_similarity(count_matrix)

        print("✅ Similarity matrix created")

    except Exception as e:
        print("Similarity error:", e)

# Load once at startup
create_similarity()

# =========================
# RECOMMENDATION ENGINE
# =========================
def rcmd(movie):
    movie = movie.lower()

    if data is None or similarity is None:
        return []

    if movie not in data["movie_title"].values:
        return []

    try:
        idx = data.loc[data["movie_title"] == movie].index[0]

        scores = list(enumerate(similarity[idx]))
        scores = sorted(scores, key=lambda x: x[1], reverse=True)[1:11]

        return [data["movie_title"][i[0]] for i in scores]

    except Exception as e:
        print("RCMD error:", e)
        return []

# =========================
# UTILS
# =========================
def convert_to_list(text):
    try:
        if not text:
            return []
        return text.split('","')
    except:
        return []

def get_suggestions():
    try:
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
        # IMDB SCRAPING (SAFE MODE)
        # =========================
        reviews_list = []
        reviews_status = []

        try:
            url = f"https://www.imdb.com/title/{imdb_id}/reviews"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"}
            )

            sauce = urllib.request.urlopen(req, timeout=5).read()

            soup = bs.BeautifulSoup(sauce, "lxml")
            reviews = soup.find_all("div", class_="text show-more__control")

            for r in reviews[:8]:
                text = r.get_text(strip=True)
                reviews_list.append(text)

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
        print("Recommend error:", e)
        return "Something went wrong"

# =========================
# RUN APP (RENDER SAFE)
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Use DEBUG_MODE from environment variable
    app.run(host="0.0.0.0", port=port, debug=DEBUG_MODE)