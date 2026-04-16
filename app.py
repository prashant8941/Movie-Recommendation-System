import os
import json
import pickle
import requests
import bs4 as bs
import numpy as np
import pandas as pd
import urllib.request
from flask import Flask, render_template, request
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer

app = Flask(__name__)

# ✅ Correct paths (relative paths)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    clf = pickle.load(open(os.path.join(BASE_DIR, "Artifacts", "nlp_model.pkl"), 'rb'))
    vectorizer = pickle.load(open(os.path.join(BASE_DIR, "Artifacts", "tranform.pkl"), 'rb'))
except Exception as e:
    print("Error loading models:", e)

# ✅ Create similarity
def create_similarity():
    try:
        data_path = os.path.join(BASE_DIR, "Artifacts", "main_data.csv")
        data = pd.read_csv(data_path)

        cv = CountVectorizer()
        count_matrix = cv.fit_transform(data['comb'])
        similarity = cosine_similarity(count_matrix)

        return data, similarity
    except Exception as e:
        print("Similarity error:", e)

# ✅ Recommendation logic
def rcmd(m):
    m = m.lower()
    global data, similarity

    try:
        data.head()
    except:
        data, similarity = create_similarity()

    if m not in data['movie_title'].unique():
        return "Movie not found"

    i = data.loc[data['movie_title'] == m].index[0]
    lst = list(enumerate(similarity[i]))
    lst = sorted(lst, key=lambda x: x[1], reverse=True)[1:11]

    return [data['movie_title'][x[0]] for x in lst]

# ✅ Utils
def convert_to_list(my_list):
    my_list = my_list.split('","')
    my_list[0] = my_list[0].replace('["','')
    my_list[-1] = my_list[-1].replace('"]','')
    return my_list

def get_suggestions():
    data_path = os.path.join(BASE_DIR, "Artifacts", "main_data.csv")
    data = pd.read_csv(data_path)
    return list(data['movie_title'].str.capitalize())

# ✅ Routes
@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html', suggestions=get_suggestions())

@app.route("/similarity", methods=["POST"])
def similarity_route():
    movie = request.form['name']
    rc = rcmd(movie)

    if isinstance(rc, str):
        return rc
    return "---".join(rc)

@app.route("/recommend", methods=["POST"])
def recommend():
    title = request.form['title']
    imdb_id = request.form['imdb_id']
    poster = request.form['poster']
    overview = request.form['overview']
    vote_average = request.form['rating']
    vote_count = request.form['vote_count']
    release_date = request.form['release_date']
    runtime = request.form['runtime']
    status = request.form['status']
    genres = request.form['genres']

    rec_movies = convert_to_list(request.form['rec_movies'])
    rec_posters = convert_to_list(request.form['rec_posters'])

    # Movie cards
    movie_cards = {rec_posters[i]: rec_movies[i] for i in range(len(rec_posters))}

    # ✅ Scraping reviews
    reviews_list = []
    reviews_status = []

    try:
        sauce = urllib.request.urlopen(
            f'https://www.imdb.com/title/{imdb_id}/reviews?ref_=tt_ov_rt'
        ).read()

        soup = bs.BeautifulSoup(sauce, 'lxml')
        soup_result = soup.find_all("div", {"class": "text show-more__control"})

        for review in soup_result:
            if review.string:
                reviews_list.append(review.string)

                movie_vector = vectorizer.transform([review.string])
                pred = clf.predict(movie_vector)

                reviews_status.append('Good' if pred else 'Bad')

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

# ✅ IMPORTANT (for Render)
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)