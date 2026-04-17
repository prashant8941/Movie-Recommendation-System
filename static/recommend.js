// 1. Updated show_details (Now an 'async' function)
async function show_details(movie_details, arr, movie_title, movie_id) {
  var imdb_id = movie_details.imdb_id;
  var poster = 'https://image.tmdb.org/t/p/original' + movie_details.poster_path;
  var overview = movie_details.overview;
  var genres = movie_details.genres;
  var rating = movie_details.vote_average;
  var vote_count = movie_details.vote_count;
  var release_date = new Date(movie_details.release_date);
  var runtime = parseInt(movie_details.runtime);
  var status = movie_details.status;
  
  var genre_list = [];
  for (var genre in genres) { genre_list.push(genres[genre].name); }
  var my_genre = genre_list.join(", ");
  
  if (runtime % 60 == 0) { runtime = Math.floor(runtime / 60) + " hour(s)" }
  else { runtime = Math.floor(runtime / 60) + " hour(s) " + (runtime % 60) + " min(s)" }

  // FIX: We 'await' these now so the browser doesn't freeze
  var arr_poster = await get_movie_posters(arr);
  var movie_cast = await get_movie_cast(movie_id);
  var ind_cast = await get_individual_cast(movie_cast);
  
  var details = {
    'title': movie_title,
    'cast_ids': JSON.stringify(movie_cast.cast_ids),
    'cast_names': JSON.stringify(movie_cast.cast_names),
    'cast_chars': JSON.stringify(movie_cast.cast_chars),
    'cast_profiles': JSON.stringify(movie_cast.cast_profiles),
    'cast_bdays': JSON.stringify(ind_cast.cast_bdays),
    'cast_bios': JSON.stringify(ind_cast.cast_bios),
    'cast_places': JSON.stringify(ind_cast.cast_places),
    'imdb_id': imdb_id,
    'poster': poster,
    'genres': my_genre,
    'overview': overview,
    'rating': rating,
    'vote_count': vote_count.toLocaleString(),
    'release_date': release_date.toDateString().split(' ').slice(1).join(' '),
    'runtime': runtime,
    'status': status,
    'rec_movies': JSON.stringify(arr),
    'rec_posters': JSON.stringify(arr_poster),
  };

  $.ajax({
    type: 'POST',
    data: details,
    url: "/recommend",
    dataType: 'html',
    complete: function() { $("#loader").fadeOut(); },
    success: function(response) {
      $('.results').html(response);
      $('#autoComplete').val('');
      $(window).scrollTop(0);
    }
  });
}

// 2. Updated Cast Details (Async version)
async function get_individual_cast(movie_cast) {
    var bdays = [], bios = [], places = [];
    
    // We use a loop that waits for each request without blocking the main thread
    for (var i = 0; i < movie_cast.cast_ids.length; i++) {
      await $.ajax({
        type: 'GET',
        url: '/tmdb_proxy?endpoint=person&person_id=' + movie_cast.cast_ids[i],
        success: function(details) {
          bdays.push(details.birthday ? (new Date(details.birthday)).toDateString().split(' ').slice(1).join(' ') : "N/A");
          bios.push(details.biography || "No biography available.");
          places.push(details.place_of_birth || "N/A");
        }
      });
    }
    return { cast_bdays: bdays, cast_bios: bios, cast_places: places };
}

// 3. Updated Movie Cast (Async version)
async function get_movie_cast(movie_id) {
    var ids = [], names = [], chars = [], profiles = [];
    await $.ajax({
      type: 'GET',
      url: "/tmdb_proxy?endpoint=credits&id=" + movie_id,
      success: function(my_movie) {
        var top = my_movie.cast.length >= 10 ? 10 : my_movie.cast.length;
        for (var i = 0; i < top; i++) {
          ids.push(my_movie.cast[i].id);
          names.push(my_movie.cast[i].name);
          chars.push(my_movie.cast[i].character);
          profiles.push("https://image.tmdb.org/t/p/original" + my_movie.cast[i].profile_path);
        }
      }
    });
    return { cast_ids: ids, cast_names: names, cast_chars: chars, cast_profiles: profiles };
}

// 4. Updated Posters (Async version)
async function get_movie_posters(arr) {
  var posters = [];
  for (var m = 0; m < arr.length; m++) {
    await $.ajax({
      type: 'GET',
      url: '/tmdb_proxy?endpoint=search&query=' + encodeURIComponent(arr[m]),
      success: function(m_data) {
        var path = m_data.results[0] ? m_data.results[0].poster_path : '';
        posters.push('https://image.tmdb.org/t/p/original' + path);
      }
    });
  }
  return posters;
}