#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os, sys, cgi, webapp2, jinja2, urllib2, json
from xml.dom import minidom
from google.appengine.ext import db
from imdb import StarsToScore, FixStarWars

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape=True)

class Entry(db.Model):
    year  = db.StringProperty(required = True)
    title = db.StringProperty(required = True)
    capped_title = db.StringProperty(required = True)
    director = db.StringProperty(required = True)
    capped_director = db.StringProperty(required = True)
    actors = db.StringProperty(required = True)
    country = db.StringProperty(required = True)
    genre = db.StringProperty(required = True)
    plot = db.StringProperty(required = True)
    plot2 = db.StringProperty()
    imdb = db.StringProperty(required = True)
    meta = db.StringProperty(required = True)
    tmdb = db.StringProperty(required = True)
    ebert = db.StringProperty(required = True)
    ebert_max = db.StringProperty(required = True)
    slant = db.StringProperty(required = True)
    slant_max = db.StringProperty(required = True)
    average = db.StringProperty(required = True)
    imdb_id = db.StringProperty(required = True)
    poster = db.StringProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)


class Handler(webapp2.RequestHandler):
    def write (self, *a, **kw):
        self.response.out.write(*a,**kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template,**kw):
        self.write(self.render_str(template, **kw))

    def render_form(self, title="", error="", error2="", link=""):
        self.render("form.html", title=title, error=error, error2=error2, link=link)

    def render_list(self, sort, order="ASC"):
        entries = db.GqlQuery("SELECT * FROM Entry ORDER BY {0} {1}".format(sort, order))
        self.render("list.html", sort = sort, entries = entries)


class MainHandler(Handler):
    def get(self):
        whole = db.GqlQuery("SELECT * FROM Entry ORDER BY average DESC")
        count = whole.count()
        #score = float(whole[9].average)
        score = 8.5
        adj_score = str(score-0.005)
        top = db.GqlQuery("SELECT * FROM Entry WHERE average > '{0}' ORDER BY average DESC".format(adj_score))
        top_count = top.count()

        worst_number = int(count)-10
        #worst_score = float(whole[worst_number].average)
        worst_score = 4.0
        worst_score_adj = str(worst_score+0.005)
        worst = db.GqlQuery("SELECT * FROM Entry WHERE average < '{0}' ORDER BY average ASC".format(worst_score_adj))
        worst_count = worst.count()

        newest = db.GqlQuery("SELECT * FROM Entry ORDER BY created DESC LIMIT 10")

        self.render("main.html",  count = count, score = score, top = top, top_count = top_count,
            newest = newest, worst = worst, worst_count = worst_count, worst_score = worst_score)


class FormHandler(Handler):
    def get(self):
        title = self.request.get("wrong-title")
        error = self.request.get("error")
        self.render_form(title=title, error=error)

    def post(self):
        title = self.request.get("title")
        year = self.request.get("year")
        title = title.replace('&','%26')
        fixed_title = title.replace(" ","+")
        scores = {"imdb":"N/A","tmdb":"N/A","meta":"N/A","ebert":"N/A","slant":"N/A"}
        stars = {"ebert":"N/A","slant":"N/A"}
        max_stars = {"ebert":"N/A","slant":"N/A"}

        ##IMDB API QUERY
        if year == "":
            imdb_page = urllib2.urlopen("http://www.omdbapi.com/?t={0}&plot=full&r=xml".format(fixed_title))
        else:
            imdb_page = urllib2.urlopen("http://www.omdbapi.com/?t={0}&y={1}&plot=full&r=xml".format(fixed_title, year))

        imdb_contents = imdb_page.read()
        imdb = minidom.parseString(imdb_contents)

        if imdb.getElementsByTagName("error").item.__self__:
            error = "Please enter the correct title of a movie (check your spelling)!"
            self.render_form (title=title,error=error)
        else:
            id = imdb.getElementsByTagName("movie")[0].attributes.getNamedItem("imdbID").value
            movie_title = imdb.getElementsByTagName("movie")[0].attributes.getNamedItem("title").value
            director = imdb.getElementsByTagName("movie")[0].attributes.getNamedItem("director").value
            actors = imdb.getElementsByTagName("movie")[0].attributes.getNamedItem("actors").value
            country = imdb.getElementsByTagName("movie")[0].attributes.getNamedItem("country").value
            genre = imdb.getElementsByTagName("movie")[0].attributes.getNamedItem("genre").value
            imdb_score = imdb.getElementsByTagName("movie")[0].attributes.getNamedItem("imdbRating").value
            meta_score = imdb.getElementsByTagName("movie")[0].attributes.getNamedItem("metascore").value
            year = imdb.getElementsByTagName("movie")[0].attributes.getNamedItem("year").value
            plot = imdb.getElementsByTagName("movie")[0].attributes.getNamedItem("plot").value
            poster = imdb.getElementsByTagName("movie")[0].attributes.getNamedItem("poster").value

            #THE MOVIE DB QUERY
            tmdb_page = urllib2.urlopen("https://api.themoviedb.org/3/find/{0}?api_key=25879c34855c16b1d1e71076dc10f991&language=en-US&external_source=imdb_id".format(id))
            tmdb_contents = tmdb_page.read()
            tmdb = json.loads(tmdb_contents)

            results = tmdb.get('movie_results')
            tmdb_score = results[0].get('vote_average')

            scores['imdb'] = imdb_score

            if meta_score != "N/A":
                fixed_meta_score = float(meta_score)/10
                scores['meta'] = fixed_meta_score

            if str(tmdb_score) != "0.0":
                scores['tmdb'] = str(tmdb_score)

            duplicate = False
            entries = db.GqlQuery("SELECT * FROM Entry")
            for entry in entries:
                if id == entry.imdb_id:
                    duplicate = True

            if duplicate == True:
                entries = db.GqlQuery("SELECT * FROM Entry WHERE imdb_id ='{0}'".format(id))
                error1 = "{0} is already in the database!".format(entries[0].title)
                link = str(entries[0].key().id())
                link = "/movie/" + link
                error2 = "You can find {0} here".format(entries[0].title)
                self.render_form(error=error1, link = link, error2=error2)
            else:
                self.render("step1.html",title=title,year=year,director=director,poster=poster,plot=plot,actors=actors)

class Step1Handler(Handler):
    def post(self):
        title = self.request.get("title")
        year = self.request.get("year")
        director = self.request.get("director")
        poster = self.request.get("poster")
        plot = self.request.get("plot")
        actors = self.request.get("actors")
        self.render("step1.html",title=title,year=year,director=director,poster=poster,plot=plot,actors=actors)
                # if movie_title == "Banshun":
                #     movie_title = "Late Spring"
                #     fixed_title = "Late+Spring"
                # if movie_title == "Birdman or (The Unexpected Virtue of Ignorance)":
                #     fixed_title = "Birdman"
                # if movie_title == "E.T. the Extra-Terrestrial":
                #     fixed_title = "E.T.+the+Extra-Terrestrial"
                # ##Google Search
                # try:
                #     google_page = urllib2.urlopen("https://www.googleapis.com/customsearch/v1?q={0}+{1}&cx=008457543585458637199:svut0j3qjew&key=AIzaSyAF28IZWqYyWjnHxNFoBzmWwl21h4JxhQE".format(fixed_title, year))
                #     google_contents = google_page.read()
                #     google = json.loads(google_contents)
                #
                #     items = google.get('items')
                #     if items != None:
                #         for item in items:
                #             # Slant Magazine
                #             if item["displayLink"] == "www.slantmagazine.com":
                #                 slant_title = movie_title.replace(" or (The Unexpected Virtue of Ignorance)","")
                #                 slant_title = slant_title.replace(": Love's Struggle Throughout the Ages","")
                #                 slant_title = slant_title.replace("E.T. ", "E T ")
                #                 slant_title = slant_title.replace("L.A.", "L A")
                #                 slant_title = slant_title.replace(u'é', 'e')
                #                 slant_title = slant_title.replace("Journey to Italy", "Voyage to Italy")
                #                 slant_title = slant_title.replace("The Spirit of the Beehive", "Spirit of the Beehive")
                #                 slant_title = slant_title.replace("Fellini's", "Fellini")
                #                 slant_title = slant_title.replace(u"WALL·E","wall-e")
                #                 slant_title = slant_title.replace("Hellboy II", "hellboy ii")
                #                 slant_title = slant_title.replace("Dead II", "Dead 2")
                #                 slant_title = slant_title.replace("&", "and")
                #                 slant_title = slant_title.replace(" ", "-")
                #                 slant_title = slant_title.replace("---", "-")
                #                 slant_title = slant_title.replace("'", "")
                #                 slant_title = slant_title.replace(":", "")
                #                 slant_title = slant_title.replace(".", "")
                #                 slant_title = slant_title.replace("!", "")
                #                 slant_title = slant_title.replace("?", "")
                #                 slant_title = slant_title.replace(",", "")
                #                 slant_title = slant_title.lower()
                #
                #                 url = "http://www.slantmagazine.com/film/review/"+slant_title
                #                 url2 = "http://www.slantmagazine.com/film/review/"+slant_title.replace("the-", "")
                #                 url3 = "http://www.slantmagazine.com/film/review/"+"the-"+slant_title
                #                 url4 = "http://www.slantmagazine.com/film/review/"+slant_title.replace("-", "")
                #                 url5 = "http://www.slantmagazine.com/film/review/"+slant_title+"-"+year
                #                 url6 = "http://www.slantmagazine.com/film/review/"+slant_title+"-1136"
                #                 url7 = "http://www.slantmagazine.com/film/review/"+slant_title+"-5754"
                #                 url8 = "http://www.slantmagazine.com/film/review/slant_title"+slant_title.replace("Dr.", "Drive")
                #                 if (item['link'] == url or item['link'] == url2 or item['link'] == url3 or item['link'] == url4 or
                #                     item['link'] == url5 or item['link'] == url6 or item['link'] == url7 or item['link'] == url8):
                #                     slant_pagemap = item.get('pagemap')
                #                     slant_rating_section = slant_pagemap.get('rating')
                #                     slant_max = slant_rating_section[0].get('bestrating')
                #                     slant_max = str(slant_max)
                #                     slant_stars = slant_rating_section[0].get('ratingvalue')
                #                     slant_stars = str(slant_stars)
                #
                #                     slant_score = StarsToScore(slant_stars,slant_max)
                #                     scores['slant'] = slant_score
                #                     stars['slant'] = slant_stars
                #                     max_stars['slant'] = slant_max
                #
                #                 #Pull a DVD review if no film review available
                #                 if scores['slant'] != 'N/A':
                #                     break
                #                 elif scores['slant'] == 'N/A':
                #                     url = "http://www.slantmagazine.com/dvd/review/"+slant_title
                #                     url2 = "http://www.slantmagazine.com/dvd/review/"+slant_title.replace("the-", "")
                #                     url3 = "http://www.slantmagazine.com/dvd/review/"+"the-"+slant_title
                #                     url4 = "http://www.slantmagazine.com/dvd/review/"+slant_title.replace("-", "")
                #                     url5 = "http://www.slantmagazine.com/dvd/review/"+slant_title+"-2048"
                #                     url6 = "http://www.slantmagazine.com/dvd/review/"+slant_title+"-"+year
                #                     url7 = "http://www.slantmagazine.com/dvd/review/"+slant_title+"-"+year+"-br"
                #                     url8 = "http://www.slantmagazine.com/dvd/review/"+slant_title+"-bd"
                #                     url9 = "http://www.slantmagazine.com/dvd/review/"+slant_title+"-2016"
                #                     url10 = "http://www.slantmagazine.com/film/review/slant_title"+slant_title.replace("Dr.", "Drive")
                #                     if (item['link'] == url or item['link'] == url2 or item['link'] == url3 or item['link'] == url4 or
                #                         item['link'] == url5 or item['link'] == url6 or item['link'] == url7 or item['link'] == url8 or
                #                         item['link'] == url9 or item['link'] == url10):
                #                         slant_pagemap = item.get('pagemap')
                #                         slant_rating_section = slant_pagemap.get('rating')
                #                         slant_max = slant_rating_section[0].get('bestrating')
                #                         slant_max = str(slant_max)
                #                         slant_stars = slant_rating_section[0].get('ratingvalue')
                #                         slant_stars = str(slant_stars)
                #
                #                         slant_score = StarsToScore(slant_stars,slant_max)
                #                         scores['slant'] = slant_score
                #                         stars['slant'] = slant_stars
                #                         max_stars['slant'] = slant_max
                #                         break
                #         for item in items:
                #             #Roger Ebert score
                #             if item["displayLink"] == 'www.rogerebert.com':
                #                 ebert_pagemap = item.get('pagemap')
                #                 result = ebert_pagemap.get("movie")
                #
                #                 if result != None:
                #                     if (ebert_pagemap.get('review')[1].get("name") == movie_title or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.title() or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace("The ", "") or
                #                     ebert_pagemap.get('review')[1].get("name") == "The " + movie_title.replace("Thieves", "Thief") or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace("Hard 2", "Hard 2: Die Harder") or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace("The City of Lost Children", "City Of Lost Children") or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace(u'Léon: ',"") or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace('Three Colors: ',"") or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace('MASH',"M*A*S*H") or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace('Twelve',"12") or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace(u"WALL·E","Wall-E") or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace('Chain Saw',"Chainsaw") or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace(u'é','e') or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace("La Grande Illusion", "Grand Illusion") or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace("La Haine", "Hate (La Haine)") or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace("Kill Bill: Vol. ", "Kill Bill, Volume ") or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace("Fellini's", "Fellini") or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace("Dead II", "Dead 2: Dead by Dawn") or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace("Goodfellas", "GoodFellas") or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace("The Lord of", "Lord of") or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace("The Force Awakens", "Episode VII - The Force Awakens") or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace(" Is ", " is ") or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace(" or (The Unexpected Virtue of Ignorance)","") or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace(' n ',' N ') or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace('.','') or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace(':','') or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace(':',',') or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace('!','') or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace("'",u'’') or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace('-','--') or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace(' ','/') or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace(' with ', ' With ') or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace(' vs. ', ' Vs. ') or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace('Se7en', 'Seven') or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace(' or:', ' Or:') or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace(': Episode IV - A New Hope', '') or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace('Star Wars: Episode V - ', '') or
                #                     ebert_pagemap.get('review')[1].get("name") == movie_title.replace('Star Wars: Episode VI - ', '') or
                #                     ebert_pagemap.get('review')[1].get("name") == FixStarWars(movie_title) or
                #                     ebert_pagemap.get('review')[1].get("name") == FixStarWars(movie_title).replace(' of the ', ' Of The ')):
                #                         ebert_rating_section = ebert_pagemap.get('rating')
                #                         if ebert_rating_section != None:
                #                             ebert_max = ebert_rating_section[0].get('bestrating')
                #                             ebert_max = str(ebert_max)
                #                             ebert_stars = ebert_rating_section[0].get('ratingvalue')
                #                             ebert_stars = str(ebert_stars)
                #
                #                             ebert_score = StarsToScore(ebert_stars,ebert_max)
                #                             scores['ebert'] = ebert_score
                #                             stars['ebert'] = ebert_stars
                #                             max_stars['ebert'] = ebert_max
                #                         break
                #     total = 0
                #     count = 0
                #     for site in scores:
                #         if scores[site] != "N/A":
                #             score = scores[site]
                #             total = total + float(score)
                #             count = count + 1
                #
                #     average = total / count
                #     average = round(average,2)
                #     average = str(average)
                #
                #     capped_title = movie_title.upper()
                #     capped_director = director.upper()
                #     tmdb_score = str(tmdb_score)
                #
                #     plot2 =""
                #     if len(plot) >= 1500:
                #         plot2 = plot[1450:]
                #         plot = plot[:1450]
                #
                #     a = Entry(year = year, title = movie_title, capped_title = capped_title, director = director,
                #         capped_director = capped_director, actors = actors, country = country, genre = genre,
                #         plot = plot, plot2 = plot2, imdb = imdb_score, meta = meta_score, tmdb = scores['tmdb'],
                #         ebert = stars['ebert'], ebert_max = max_stars['ebert'], slant = stars['slant'],
                #         slant_max = max_stars['slant'], average = average, poster = poster, imdb_id = id)
                #
                #     a.put()
                #     self.redirect("/movie/{0}".format(a.key().id()))
                # except urllib2.HTTPError as err:
                #     if err.code == 403:
                #         error = "403 error: You have searched google 100 times today"
                #         self.render_form(error=error)
                #     else:
                #         error = "Unknown google error"
                #         self.render_form(error=error)


class MovieHandler(Handler):
    def get(self):
        self.redirect("/form/")


class ViewEntryHandler(Handler):
    def get(self, id):
        id = int(id)
        entry = Entry.get_by_id(id)
        self.render("movie.html",entry=entry)


class BestHandler(Handler):
    def get(self):
        self.render_list("average", "DESC")


class NewestHandler(Handler):
    def get(self):
        self.render_list("year", "DESC")


class OldestHandler(Handler):
    def get(self):
        self.render_list("year")


class AlphaFilmHandler(Handler):
    def get(self):
        self.render_list("title")


class AlphaDirHandler(Handler):
    def get(self):
        self.render_list("director")


class PrintHandler(Handler):
    def get(self):
        entries = db.GqlQuery("SELECT * FROM Entry ORDER BY title")
        list = []
        for entry in entries:
            list.append(entry.title)
        self.write(list)


class SearchHandler(Handler):
    def get(self):
        self.render("search.html")

    def post(self):
        title = self.request.get("title")
        year = self.request.get("year")
        director = self.request.get("director")
        entries = ''
        count = 0

        if title != "":
            fixed_title = title.upper()
            fixed_title = "'" + fixed_title + "'"
            fixed_title = "capped_title = " + fixed_title
            count = count + 1
        else:
            fixed_title = ""

        if year != "":
            year ="'" + year + "'"

            if count == 1:
                year = "AND year = " + year
                count = 0
            else:
                year = "year = " + year
            count = count + 1

        if director != "":
            director = director.upper()
            director = "'" + director + "'"

            if count == 1:
                director = "AND capped_director = "  + director
                count = 0
            else:
                director = "capped_director = "  + director
            count = count + 1

        if title != "" or director != "" or year != "":
            search = "WHERE " + fixed_title + year + director
        else:
            search = ""

        entries = db.GqlQuery("SELECT * FROM Entry {0} ORDER BY average DESC".format(search))
        sort = search.replace("WHERE", "where")
        sort = sort.replace("AND", "and")
        sort = sort.replace('=', 'is')
        sort = sort.replace("'", " ")
        sort = "average " + sort
        if entries.count() > 0:
            self.render("list.html", entries = entries, sort=sort)
        else:
            error = "Sorry, but we could not find your {0}. Try checking your spelling, or adding your movie to the database!".format(fixed_title)
            self.render("search.html", title = title, error = error)


class YearSearch(Handler):
    def get(self):
        self.redirect('/search/')

    def post(self):
        start_year = self.request.get("start-year")
        end_year = self.request.get("end-year")

        if start_year == "" or end_year == "":
            error2 = "Please enter years in both fields."
            self.render("search.html", error2 = error2)

        elif not start_year.isdigit() or not end_year.isdigit():
            error2 = "Please enter numbers for the years"
            self.render("search.html", error2 = error2)

        elif int(start_year) < 1880 or int(end_year) < 1880:
            error2 = "Please enter years after the invention of cinema."
            self.render("search.html", error2 = error2)

        elif int(start_year) >= int(end_year):
            error2 = "Please make sure the end year is later than the start year."
            self.render("search.html", error2 = error2)

        else:
            sort = "year between " + start_year + " and  " + end_year
            sort = sort.replace("'", "")

            start_year = int(start_year) - 1
            start_year = "'" + str(start_year) + "'"
            end_year = int(end_year) + 1
            end_year = "'" + str(end_year) + "'"
            entries = db.GqlQuery("SELECT * FROM Entry WHERE year > {0} AND year < {1} ORDER BY year, average DESC".format(start_year, end_year))

            if entries.count() != 0:
                self.render("list.html", entries = entries, sort = sort)
            else:
                error2 = "Sorry, but we couldn't find any movies between these years, please try again!"
                self.render("search.html", error2 = error2)


app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/form/', FormHandler),
    ('/movie/', MovieHandler),
    webapp2.Route('/movie/<id:\d+>', ViewEntryHandler),
    ('/best/', BestHandler),
    ('/newest/', NewestHandler),
    ('/oldest/', OldestHandler),
    ('/search/', SearchHandler),
    ('/alphafilm/', AlphaFilmHandler),
    ('/alphadir/', AlphaDirHandler),
    ('/year/', YearSearch),
    ('/print/', PrintHandler),
    ('/step1/', Step1Handler)
], debug=True)
