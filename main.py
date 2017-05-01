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

import os, sys, ast, cgi, webapp2, jinja2, urllib2, json
from xml.dom import minidom
from google.appengine.ext import db
from imdb import StarsToScore
reload(sys)
sys.setdefaultencoding('utf-8')

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
        count = entries.count()
        self.render("list.html", sort = sort, entries = entries, count = count)


class MainHandler(Handler):
    def get(self):
        whole = db.GqlQuery("SELECT * FROM Entry ORDER BY average DESC")
        count = whole.count()

        score = float(whole[49].average)
        # score = 8.8
        adj_score = str(score-0.005)
        top = db.GqlQuery("SELECT * FROM Entry WHERE average > '{0}' ORDER BY average DESC".format(adj_score))
        top_count = top.count()

        worst_number = int(count)-10
        #worst_score = float(whole[worst_number].average)
        worst_score = 5.0
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


class Step1Handler(Handler):
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
            self.render_form(title=title,error=error)
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

            scores['imdb'] = imdb_score

            if meta_score != "N/A":
                fixed_meta_score = float(meta_score)/10
                scores['meta'] = str(fixed_meta_score)

            ##Check if duplicate
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
                #THE MOVIE DB QUERY
                tmdb_page = urllib2.urlopen("https://api.themoviedb.org/3/find/{0}?api_key=25879c34855c16b1d1e71076dc10f991&language=en-US&external_source=imdb_id".format(id))
                tmdb_contents = tmdb_page.read()
                tmdb = json.loads(tmdb_contents)
                results = tmdb.get('movie_results')

                if results != []:
                    tmdb_score = results[0].get('vote_average')
                    tmdb_score = str(tmdb_score)
                    if tmdb_score != "0.0":
                        scores['tmdb'] = tmdb_score

                if movie_title == "Banshun":
                    movie_title = "Late Spring"
                    fixed_title = "Late+Spring"
                if movie_title == "Birdman or (The Unexpected Virtue of Ignorance)":
                    fixed_title = "Birdman"
                if movie_title == "E.T. the Extra-Terrestrial":
                    fixed_title = "E.T.+the+Extra-Terrestrial"

                self.render("step1.html",id=id,fixed_title=fixed_title,movie_title=movie_title,year=year,
                    director=director,actors=actors,country=country,genre=genre,plot=plot,poster=poster,
                    scores=scores,stars=stars,max_stars=max_stars)


class Step2Handler(Handler):
    def post(self):
        data = self.request.get("info1")
        data = data.encode('utf-8')
        info1 = data.split('","')

        fixed_title = info1[1]
        movie_title = info1[2]
        year = info1[3]

        ##Google Search
        try:
            google_page = urllib2.urlopen("https://www.googleapis.com/customsearch/v1?q={0}+{1}&cx=008457543585458637199:svut0j3qjew&key=AIzaSyAF28IZWqYyWjnHxNFoBzmWwl21h4JxhQE".format(fixed_title, year))
            google_contents = google_page.read()
            google = json.loads(google_contents)

            items = google.get('items')
            slant_list = []
            ebert_list = []
            if items != None:
                for item in items:
                    # Slant Magazine
                    if item["displayLink"] == "www.slantmagazine.com":
                        slant_list.append(item)

                    #Roger Ebert score
                    if item["displayLink"] == 'www.rogerebert.com':
                        ebert_list.append(item)
            self.render("step2.html", info1=data, slant_list=slant_list, ebert_list=ebert_list)

        except urllib2.HTTPError as err:
            if err.code == 403:
                error = "403 error: You have searched google 100 times today"
                self.render_form(error=error)
            else:
                error = "Unknown google error"
                self.render_form(error=error)


class MovieHandler(Handler):
    def get(self):
        self.redirect("/form/")

    def post(self):
        data = self.request.get("info1")
        info1 = data.split('","')
        id = info1[0]
        id = id.replace('"','')
        id = id.replace(' ','')
        fixed_title = info1[1]
        movie_title = info1[2]
        year = info1[3]
        director = info1[4]
        actors  = info1[5]
        country = info1[6]
        genre = info1[7]
        plot = info1[8]
        poster = info1[9]

        scores = info1[10].encode('utf-8')
        scores = ast.literal_eval(scores)
        stars = info1[11].encode('utf-8')
        stars = ast.literal_eval(stars)
        max_stars = info1[12].encode('utf-8')
        max_stars = max_stars.replace('"','')
        max_stars = ast.literal_eval(max_stars)

        #Slant
        slant = self.request.get("slant")
        if slant != "":
            slant = ast.literal_eval(slant)
            slant_max = slant['pagemap']['rating'][0]['bestrating']
            slant_stars = slant['pagemap']['rating'][0]['ratingvalue']
            slant_score = StarsToScore(slant_stars,slant_max)
            scores['slant'] = slant_score
            stars['slant'] = slant_stars
            max_stars['slant'] = slant_max

        # Ebert
        ebert = self.request.get("ebert")
        if ebert !="":
            ebert = ast.literal_eval(ebert)
            ebert_max = ebert['pagemap']['rating'][0]['bestrating']
            ebert_stars = ebert['pagemap']['rating'][0]['ratingvalue']
            ebert_score = StarsToScore(ebert_stars,ebert_max)
            scores['ebert'] = ebert_score
            stars['ebert'] = ebert_stars
            max_stars['ebert'] = ebert_max

        total = 0
        count = 0
        for site in scores:
            if scores[site] != "N/A":
                score = scores[site]
                total = total + float(score)
                count = count + 1
        average = total / count
        average = round(average,2)
        average = str(average)

        capped_title = movie_title.upper()
        capped_director = director.upper()

        plot2 =""
        if len(plot) >= 1500:
            plot2 = plot[1450:]
            plot = plot[:1450]

        a = Entry(year = year, title = movie_title, capped_title = capped_title, director = director,
            capped_director = capped_director, actors = actors, country = country, genre = genre,
            plot = plot, plot2 = plot2, imdb = scores['imdb'], meta = scores['meta'], tmdb = scores['tmdb'],
            ebert = stars['ebert'], ebert_max = max_stars['ebert'], slant = stars['slant'],
            slant_max = max_stars['slant'], average = average, poster = poster, imdb_id = id)
        a.put()

        self.redirect("/movie/{0}".format(a.key().id()))


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
        count = 0

        if title != "":
            fixed_title = "capped_title = " + "'" + title.upper() + "'"
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
            director = "'" + director.upper() + "'"
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
        count = entries.count()
        sort = search.replace("WHERE", "where")
        sort = sort.replace("AND", "and")
        sort = sort.replace('=', 'is')
        sort = sort.replace("'", " ")
        sort = "average " + sort
        if entries.count() > 0:
            self.render("list.html", entries = entries, sort=sort, count=count)
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
    ('/step1/', Step1Handler),
    ('/step2/', Step2Handler)
], debug=True)
