import sys

def StarsToScore(stars,max):
    if float(max) == 4.0:
        score = (float(stars) / 4) * 10
        score = str(score)

    elif float(max) == 5.0:
        score = float(stars)*2
        score = str(score)

    return score

def FixStarWars(title):
    title = title.replace(':'," --")
    title = title.replace(' - ',': ')
    return title


def main():

    movie = input("Please enter the name of a movie:")
    movie = movie.title()
    fixed_movie = movie.replace(" ", "+")

    scores = {"imdb":"N/A","tmdb":"N/A","meta":"N/A","ebert":"N/A","slant":"N/A"}
    stars = {"ebert":"N/A","slant":"N/A"}
    max_stars = {"ebert":"N/A","slant":"N/A"}

    ##IMDB API QUERY
    imdb_page = urlopen("http://www.omdbapi.com/?t={0}&plot=full&r=xml".format(fixed_movie))
    imdb_contents = imdb_page.read()
    imdb = minidom.parseString(imdb_contents)

    if imdb.getElementsByTagName("error").item.__self__:
        print ("Please enter the correct title of a movie")
    else:
        id = imdb.getElementsByTagName("movie")[0].attributes.getNamedItem("imdbID").value
        movie_title = imdb.getElementsByTagName("movie")[0].attributes.getNamedItem("title").value
        director = imdb.getElementsByTagName("movie")[0].attributes.getNamedItem("director").value
        country = imdb.getElementsByTagName("movie")[0].attributes.getNamedItem("country").value
        genre = imdb.getElementsByTagName("movie")[0].attributes.getNamedItem("genre").value
        imdb_score = imdb.getElementsByTagName("movie")[0].attributes.getNamedItem("imdbRating").value
        meta_score = imdb.getElementsByTagName("movie")[0].attributes.getNamedItem("metascore").value
        year = d.getElementsByTagName("movie")[0].attributes.getNamedItem("year").value
        plot = d.getElementsByTagName("movie")[0].attributes.getNamedItem("plot").value
        poster = d.getElementsByTagName("movie")[0].attributes.getNamedItem("poster").value

        #THE MOVIE DB QUERY
        tmdb_page = urlopen("https://api.themoviedb.org/3/find/{0}?api_key=25879c34855c16b1d1e71076dc10f991&language=en-US&external_source=imdb_id".format(id))
        tmdb_contents = tmdb_page.read()
        tmdb = json.loads(tmdb_contents)

        results = tmdb.get('movie_results')
        tmdb_score = results[0].get('vote_average')

        scores['tmdb'] = tmdb_score
        scores['imdb'] = imdb_score
        if meta_score != "N/A":
            fixed_meta_score = float(meta_score)/10
            scores['meta'] = fixed_meta_score

    #Google Search
    google_page = urlopen("https://www.googleapis.com/customsearch/v1?q={0}&hq=film%2C+reviews&cx=008457543585458637199:svut0j3qjew&key=AIzaSyAF28IZWqYyWjnHxNFoBzmWwl21h4JxhQE".format(fixed_movie))
    google_contents = google_page.read()
    google = json.loads(google_contents)

    errors = google.get('error')
    if errors["code"] == 403:
        print ("403 error, you've used google too many times")
    else:
        items = google.get('items')
        for item in items:

            # Slant Magazine
            if item["displayLink"] == "www.slantmagazine.com":
                slant_title = movie_title.replace(" ", "-")
                slant_title = fix_french(slant_title)
                slant_title = slant_title.replace("'","")
                slant_title = slant_title.replace(":","")
                slant_title = slant_title.replace(".","")
                slant_title = slant_title.replace(",","")
                slant_title = slant_title.lower()

                url = "http://www.slantmagazine.com/film/review/"+slant_title
                url2 = "http://www.slantmagazine.com/film/review/"+slant_title.replace("the-", "")
                url3 = "http://www.slantmagazine.com/film/review/"+"the-"+slant_title
                url4 = "http://www.slantmagazine.com/film/review/"+slant_title.replace("-", "")

                if item['link'] == url or item['link'] == url2 or item['link'] == url3 or item['link'] == url4:
                    slant_pagemap = item.get('pagemap')
                    slant_rating_section = slant_pagemap.get('rating')
                    slant_max = slant_rating_section[0].get('bestrating')
                    slant_max = float(slant_max)
                    slant_stars = slant_rating_section[0].get('ratingvalue')
                    slant_stars = float(slant_stars)

                    slant_score = StarsToScore(slant_stars,slant_max)
                    scores['slant'] = slant_score
                    stars['slant'] = slant_stars
                    max_stars['slant'] = slant_max

                #Pull a DVD review if no film review available
                if scores['slant'] == 'N/A':
                    url = "http://www.slantmagazine.com/dvd/review/"+slant_title
                    url2 = "http://www.slantmagazine.com/dvd/review/"+slant_title.replace("the-", "")
                    url3 = "http://www.slantmagazine.com/dvd/review/"+"the-"+slant_title
                    url4 = "http://www.slantmagazine.com/dvd/review/"+slant_title.replace("-", "")
                    if item['link'] == url or item['link'] == url2 or item['link'] == url3 or item['link'] == url4:
                        slant_pagemap = item.get('pagemap')
                        slant_rating_section = slant_pagemap.get('rating')
                        slant_max = slant_rating_section[0].get('bestrating')
                        slant_max = float(slant_max)
                        slant_stars = slant_rating_section[0].get('ratingvalue')
                        slant_stars = float(slant_stars)

                        slant_score = StarsToScore(slant_stars,slant_max)
                        scores['slant'] = slant_score
                        stars['slant'] = slant_stars
                        max_stars['slant'] = slant_max

            #Rogert Ebert score
            if item["displayLink"] == 'www.rogerebert.com':
                ebert_pagemap = item.get('pagemap')
                result = ebert_pagemap.get("movie")

                if result != None:
                    title = result[0].get("name")

                    if (ebert_pagemap.get('review')[1].get("name") == movie_title or
                    ebert_pagemap.get('review')[1].get("name") == fix_french(movie_title) or
                    ebert_pagemap.get('review')[1].get("name") == movie_title.replace('.','') or
                    ebert_pagemap.get('review')[1].get("name") == movie_title.replace(':','') or
                    ebert_pagemap.get('review')[1].get("name") == movie_title.replace(' with ', ' With ') or
                    ebert_pagemap.get('review')[1].get("name") == "The " + movie_title or
                    ebert_pagemap.get('review')[1].get("name") == movie_title.replace(' or:', ' Or:')) :
                        ebert_rating_section = ebert_pagemap.get('rating')
                        ebert_max = ebert_rating_section[0].get('bestrating')
                        ebert_max = float(ebert_max)
                        ebert_stars = ebert_rating_section[0].get('ratingvalue')
                        ebert_stars = float(ebert_stars)

                        ebert_score = StarsToScore(ebert_stars,ebert_max)
                        scores['ebert'] = ebert_score
                        stars['ebert'] = ebert_stars
                        max_stars['ebert'] = ebert_max

            #Rotten tomatoes score
            # if item['link'] == "https://www.rottentomatoes.com/m/{0}/".format(fixed_movie):
            #     print(item['snippet'])

        total = 0
        count = 0
        for site in scores:
            if scores[site] != "N/A":
                score = scores[site]
                total = total + float(score)
                count = count + 1

        average = total / count
        average = round(average,2)

        print (movie_title + " (" + year + ") directed by " + director)
        print (genre + " from " + country)
        print ("The IMDB rating is " + imdb_score)
        print ("The Metacritic score is " + meta_score)
        print ("The Movie Database score is " + str(tmdb_score))
        print ("Roger Ebert gave it " + str(stars['ebert']) + " stars")
        print ("Slant Magazine gave it " + str(stars['slant']) + " stars")
        print ("The average is " + str(average))


if __name__ == '__main__':
    main()
