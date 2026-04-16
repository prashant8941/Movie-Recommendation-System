import os
import pickle
import bs4 as bs
import numpy as np
import pandas as pd
import urllib.request
from flask import Flask, render_template, request
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer

app = Flask(__name__)

# ✅ Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ✅ Load models safely
try:
    clf = pickle.load(open(os.path.join(BASE_DIR, "Artifacts", "nlp_model.pkl"), 'rb'))
    vectorizer = pickle.load(open(os.path.join(BASE_DIR, "Artifacts", "tranform.pkl"), 'rb'))
except Exception as e:
    print("Error loading models:", e)
    clf, vectorizer = None, None

# ✅ Load data once (IMPORTANT for performance)
data = None
similarity = None

def create_similarity():
    global data, similarity
    try:
        data_path = os.path.join(BASE_DIR, "Artifacts", "main_data.csv")
        data = pd.read_csv(data_path)

        cv = CountVectorizer()
        count_matrix = cv.fit_transform(data['comb'])
        similarity = cosine_similarity(count_matrix)

    except Exception as e:
        print("Similarity error:", e)

# Load at startup
create_similarity()

# ✅ Recommendation logic
def rcmd(m):
    m = m.lower()

    if data is None or similarity is None:
        return "Data not loaded properly"

    if m not in data['movie_title'].unique():
        return "Movie not found"

    try:
        i = data.loc[data['movie_title'] == m].index[0]
        lst = list(enumerate(similarity[i]))
        lst = sorted(lst, key=lambda x: x[1], reverse=True)[1:11]

        return [data['movie_title'][x[0]] for x in lst]
    except Exception as e:
        print("Recommendation error:", e)
        return "Error generating recommendations"

# ✅ Utils
def convert_to_list(my_list):
    try:
        my_list = my_list.split('","')
        my_list[0] = my_list[0].replace('["','')
        my_list[-1] = my_list[-1].replace('"]','')
        return my_list
    except:
        return []

def get_suggestions():
    try:
        return list(data['movie_title'].str.capitalize())
    except:
        return []

# ✅ Routes
@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html', suggestions=get_suggestions())

@app.route("/similarity", methods=["POST"])
def similarity_route():
    movie = request.form.get('name')

    if not movie:
        return "No movie provided"

    rc = rcmd(movie)

    if isinstance(rc, str):
        return rc

    return "---".join(rc)

@app.route("/recommend", methods=["POST"])
def recommend():
    try:
        title = request.form.get('title')
        imdb_id = request.form.get('imdb_id')
        poster = request.form.get('poster')
        overview = request.form.get('overview')
        vote_average = request.form.get('rating')
        vote_count = request.form.get('vote_count')
        release_date = request.form.get('release_date')
        runtime = request.form.get('runtime')
        status = request.form.get('status')
        genres = request.form.get('genres')

        rec_movies = convert_to_list(request.form.get('rec_movies', ''))
        rec_posters = convert_to_list(request.form.get('rec_posters', ''))

        movie_cards = {
            rec_posters[i]: rec_movies[i]
            for i in range(min(len(rec_posters), len(rec_movies)))
        }

        # ✅ Scraping reviews (safe)
        reviews_list = []
        reviews_status = []

        try:
            sauce = urllib.request.urlopen(
                f'https://www.imdb.com/title/{imdb_id}/reviews'
            ).read()

            soup = bs.BeautifulSoup(sauce, 'lxml')
            soup_result = soup.find_all("div", {"class": "text show-more__control"})

            for review in soup_result[:10]:  # limit for speed
                if review.string:
                    reviews_list.append(review.string)

                    if vectorizer and clf:
                        movie_vector = vectorizer.transform([review.string])
                        pred = clf.predict(movie_vector)
                        reviews_status.append('Good' if pred else 'Bad')
                    else:
                        reviews_status.append('Unknown')

        except Exception as e:
            print("Review scraping error:", e)

        movie_reviews = {
            reviews_list[i]: reviews_status[i]
            for i in range(len(reviews_list))
        }

        return render_template(
            'recommend.html',
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
        return "Error loading recommendation page"

# ✅ For Render
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)