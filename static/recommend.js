$(function() {
  const source = document.getElementById('autoComplete');
  const inputHandler = function(e) {
    $('.movie-button').attr('disabled', e.target.value=="");
  }
  source.addEventListener('input', inputHandler);

  $('.movie-button').on('click',function(){
    var title = $('.movie').val();
    if (title=="") {
      $('.results').css('display','none');
      $('.fail').css('display','block');
    } else {
      load_details(title);
    }
  });
});

function recommendcard(e){
  load_details(e.getAttribute('title'));
}

function load_details(title){
  $.ajax({
    type: 'GET',
    url:'/tmdb_proxy?endpoint=search&query='+title,
    success: function(movie){
      if(movie.results.length<1){
        $('.fail').css('display','block');
        $('.results').css('display','none');
        $("#loader").fadeOut();
      } else {
        $("#loader").fadeIn();
        $('.fail').css('display','none');
        $('.results').delay(1000).css('display','block');
        movie_recs(movie.results[0].original_title, movie.results[0].id);
      }
    },
    error: function(){
      alert('Invalid Request');
      $("#loader").fadeOut();
    },
  });
}

function movie_recs(movie_title, movie_id){
  $.ajax({
    type:'POST',
    url:"/similarity",
    data:{'name':movie_title},
    success: function(recs){
      if(recs=="Movie not found"){
        $('.fail').css('display','block');
        $('.results').css('display','none');
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
    type:'GET',
    url:'/tmdb_proxy?endpoint=details&id='+movie_id,
    success: function(movie_details){
      show_details(movie_details, arr, movie_title, movie_id);
    }
  });
}

function show_details(movie_details, arr, movie_title, movie_id){
  var imdb_id = movie_details.imdb_id;
  var poster = 'https://image.tmdb.org/t/p/original'+movie_details.poster_path;
  var overview = movie_details.overview;
  var genres = movie_details.genres;
  var rating = movie_details.vote_average;
  var vote_count = movie_details.vote_count;
  var release_date = new Date(movie_details.release_date);
  var runtime = parseInt(movie_details.runtime);
  var status = movie_details.status;
  var genre_list = [];
  for (var genre in genres){ genre_list.push(genres[genre].name); }
  var my_genre = genre_list.join(", ");
  if(runtime%60==0){ runtime = Math.floor(runtime/60)+" hour(s)" }
  else { runtime = Math.floor(runtime/60)+" hour(s) "+(runtime%60)+" min(s)" }
  
  var arr_poster = get_movie_posters(arr);
  var movie_cast = get_movie_cast(movie_id);
  var ind_cast = get_individual_cast(movie_cast);
  
  var details = {
    'title':movie_title, 'cast_ids':JSON.stringify(movie_cast.cast_ids),
    'cast_names':JSON.stringify(movie_cast.cast_names), 'cast_chars':JSON.stringify(movie_cast.cast_chars),
    'cast_profiles':JSON.stringify(movie_cast.cast_profiles), 'cast_bdays':JSON.stringify(ind_cast.cast_bdays),
    'cast_bios':JSON.stringify(ind_cast.cast_bios), 'cast_places':JSON.stringify(ind_cast.cast_places),
    'imdb_id':imdb_id, 'poster':poster, 'genres':my_genre, 'overview':overview,
    'rating':rating, 'vote_count':vote_count.toLocaleString(),
    'release_date':release_date.toDateString().split(' ').slice(1).join(' '),
    'runtime':runtime, 'status':status, 'rec_movies':JSON.stringify(arr), 'rec_posters':JSON.stringify(arr_poster),
  }

  $.ajax({
    type:'POST',
    data:details,
    url:"/recommend",
    dataType: 'html',
    complete: function(){ $("#loader").fadeOut(); },
    success: function(response) {
      $('.results').html(response);
      $('#autoComplete').val('');
      $(window).scrollTop(0);
    }
  });
}

function get_individual_cast(movie_cast) {
    var bdays = [], bios = [], places = [];
    for(var i in movie_cast.cast_ids){
      $.ajax({
        type:'GET',
        url:'/tmdb_proxy?endpoint=person&person_id='+movie_cast.cast_ids[i],
        async:false,
        success: function(details){
          bdays.push((new Date(details.birthday)).toDateString().split(' ').slice(1).join(' '));
          bios.push(details.biography);
          places.push(details.place_of_birth);
        }
      });
    }
    return {cast_bdays:bdays, cast_bios:bios, cast_places:places};
}

function get_movie_cast(movie_id){
    var ids=[], names=[], chars=[], profiles=[];
    $.ajax({
      type:'GET',
      url:"/tmdb_proxy?endpoint=credits&id="+movie_id,
      async:false,
      success: function(my_movie){
        var top = my_movie.cast.length >= 10 ? 10 : my_movie.cast.length;
        for(var i=0; i<top; i++){
          ids.push(my_movie.cast[i].id);
          names.push(my_movie.cast[i].name);
          chars.push(my_movie.cast[i].character);
          profiles.push("https://image.tmdb.org/t/p/original"+my_movie.cast[i].profile_path);
        }
      }
    });
    return {cast_ids:ids, cast_names:names, cast_chars:chars, cast_profiles:profiles};
}

function get_movie_posters(arr){
  var posters = [];
  for(var m in arr) {
    $.ajax({
      type:'GET',
      url:'/tmdb_proxy?endpoint=search&query='+arr[m],
      async: false,
      success: function(m_data){
        posters.push('https://image.tmdb.org/t/p/original'+m_data.results[0].poster_path);
      }
    })
  }
  return posters;
}