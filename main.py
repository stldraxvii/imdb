#!/usr/bin/env python
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
import webapp2
import jinja2
import os
import urllib2
from xml.dom import minidom
from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape=True)

class Entry(db.Model):
    year  = db.StringProperty(required = True)
    title = db.StringProperty(required = True)
    director = db.StringProperty(required = True)
    country = db.StringProperty(required = True)
    genre = db.StringProperty(required = True)
    imdb = db.StringProperty(required = True)
    meta = db.StringProperty(required = True)
    average = db.StringProperty(required = True)
    imdb_id = db.StringProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)


class Handler(webapp2.RequestHandler):
    def write (self, *a, **kw):
        self.response.out.write(*a,**kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template,**kw):
        self.write(self.render_str(template, **kw))

    def render_form(self, title="", error=""):
        self.render("form.html", title=title, error=error)

    def render_best(self):
        entries = db.GqlQuery("SELECT * FROM Entry ORDER BY average DESC")
        self.render("list.html", entries = entries)

    def render_newest(self):
        entries = db.GqlQuery("SELECT * FROM Entry ORDER BY year DESC")
        self.render("list.html", entries = entries)

    def render_oldest(self):
        entries = db.GqlQuery("SELECT * FROM Entry ORDER BY year ASC")
        self.render("list.html", entries = entries)

class MainHandler(Handler):
    def get(self):
        title = self.request.get("wrong-title")
        error = self.request.get("error")
        self.render_form(title=title, error=error)

    def post(self):
        title = self.request.get("title")
        year = self.request.get("year")
        formatted_title = title.replace(" ","-")

        self.redirect("/movie/?title="+formatted_title+"&year="+year)

class MovieHandler(Handler):
    def get(self):
        title = self.request.get("title")
        year = self.request.get("year")
        fixed_title = title.replace("-","+")

        if year == "":
            page = urllib2.urlopen("http://www.omdbapi.com/?t={0}&r=xml".format(fixed_title))
        else:
            page = urllib2.urlopen("http://www.omdbapi.com/?t={0}&y={1}&r=xml".format(fixed_title, year))

        contents = page.read()
        d = minidom.parseString(contents)

        if d.getElementsByTagName("error").item.__self__:
            error = "Please enter the correct title of a movie (check your spelling)!"
            self.redirect("/?wrong-title="+fixed_title+"&error="+error)
        else:
            imdb_id = d.getElementsByTagName("movie")[0].attributes.getNamedItem("imdbID").value
            movie_title = d.getElementsByTagName("movie")[0].attributes.getNamedItem("title").value
            director = d.getElementsByTagName("movie")[0].attributes.getNamedItem("director").value
            country = d.getElementsByTagName("movie")[0].attributes.getNamedItem("country").value
            genre = d.getElementsByTagName("movie")[0].attributes.getNamedItem("genre").value
            imdb_score = d.getElementsByTagName("movie")[0].attributes.getNamedItem("imdbRating").value
            meta_score = d.getElementsByTagName("movie")[0].attributes.getNamedItem("metascore").value
            year = d.getElementsByTagName("movie")[0].attributes.getNamedItem("year").value

            if meta_score != "N/A":
                imdb = float(imdb_score) * 10
                meta = float(meta_score)
                average = (imdb + meta) / 20
                average = str(average)
            else:
                average = imdb_score

            duplicate = False
            entries = db.GqlQuery("SELECT * FROM Entry")
            for entry in entries:
                if imdb_id == entry.imdb_id:
                    duplicate = True

            if duplicate == True:
                error = "This movie is already in the database!"
                self.redirect("/?wrong-title="+fixed_title+"&error="+error)
            else:
                a = Entry(year = year, title = movie_title, director = director, country = country, genre = genre, imdb = imdb_score, meta = meta_score, imdb_id = imdb_id, average = average)
                a.put()
                self.redirect("/movie/{0}".format(a.key().id()))

class ViewEntryHandler(Handler):
    def get(self, id):
        id = int(id)
        entry = Entry.get_by_id(id)
        self.render("movie.html",entry=entry)

class BestHandler(Handler):
    def get(self):
        self.render_best()

class NewestHandler(Handler):
    def get(self):
        self.render_newest()

class OldestHandler(Handler):
    def get(self):
        self.render_oldest()

app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/movie/', MovieHandler),
    webapp2.Route('/movie/<id:\d+>', ViewEntryHandler),
    ('/best/', BestHandler),
    ('/newest/', NewestHandler),
    ('/oldest/', OldestHandler)
], debug=True)
