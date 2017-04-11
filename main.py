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

class MainHandler(Handler):
    def get(self):
        title = self.request.get("wrong-title")
        error = self.request.get("error")
        self.render_form(title=title, error=error)

    def post(self):
        title = self.request.get("title")
        formatted_title = title.replace(" ","-")

        self.redirect("/movie/?title="+formatted_title)

class MovieHandler(Handler):
    def get(self):
        title = self.request.get("title")
        fixed_title = title.replace("-","+")
        page = urllib2.urlopen("http://www.omdbapi.com/?t={0}&r=xml".format(fixed_title))
        contents = page.read()
        d = minidom.parseString(contents)

        if d.getElementsByTagName("error").item.__self__:
            error = "Please enter the correct title of a movie (check your spelling)!"
            self.redirect("/?wrong-title="+fixed_title+"&error="+error)
        else:
            id = d.getElementsByTagName("movie")[0].attributes.getNamedItem("imdbID").value
            movie_title = d.getElementsByTagName("movie")[0].attributes.getNamedItem("title").value
            director = d.getElementsByTagName("movie")[0].attributes.getNamedItem("director").value
            country = d.getElementsByTagName("movie")[0].attributes.getNamedItem("country").value
            genre = d.getElementsByTagName("movie")[0].attributes.getNamedItem("genre").value
            imdb_score = d.getElementsByTagName("movie")[0].attributes.getNamedItem("imdbRating").value
            meta_score = d.getElementsByTagName("movie")[0].attributes.getNamedItem("metascore").value
            date = d.getElementsByTagName("movie")[0].attributes.getNamedItem("released").value
            day, month, year = date.split()

            self.render("movie.html", title=movie_title, director=director, country=country, genre=genre, imdb_score=imdb_score, meta_score=meta_score, year=year)

app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/movie/', MovieHandler)
], debug=True)
