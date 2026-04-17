$(function() {
  const source = document.getElementById('autoComplete');
  const inputHandler = function(e) {
    $('.movie-button').attr('disabled', e.target.value === "");
  }
  source.addEventListener('input', inputHandler);

  $('.movie-button').on('click', function() {
    var title = $('.movie').val();
    if (title === "") {
      $('.results').css('display', 'none');
      $('.fail').css('display', 'block');
    } else {
      load_details(title);
    }
  });
});

function recommendcard(e) {
  load_details(e.getAttribute('title'));
}

// Fixed to use Backend Proxy
function load_details(title) {
  $.ajax({
    type: 'GET',
    url: '/tmdb_proxy?endpoint=search&query=' + title,
    success: function(movie) {
      if (movie.results.length < 1) {
        $('.fail').css('display', 'block');
        $('.results').css('display', 'none');
        $("#loader").fadeOut();
      } else {
        $("#loader").fadeIn();
        $('.fail').css('display', 'none');
        $('.results').delay(1000).css('display', 'block');
        movie_recs(movie.results[0].original_title, movie.results[0].id);
      }
    },
    error: function() {
      alert('Network Error - Check Backend Logs');
      $("#loader").fadeOut();
    }
  });
}

function movie_recs(movie_title, movie_id) {
  $.ajax({
    type: 'POST',
    url: "/similarity",
    data: { 'name': movie_title },
    success: function(recs) {
      if (recs === "Movie not found") {
        $('.fail').css('display', 'block');
        $("#loader").fadeOut();
      } else {
        var arr = recs.split('---');
        get_movie_details(movie_id, arr, movie_title);
      }
    }
  });
}

function get_movie_details(movie_id, arr, movie_title) {
  $.ajax({
    type: 'GET',
    url: '/tmdb_proxy?endpoint=details&id=' + movie_id,
    success: function(movie_details) {
      // Proceed to call show_details as per your original logic
      // Note: Inside show_details, ensure sub-calls for posters/cast 
      // also point to the /tmdb_proxy endpoint.
    }
  });
}