# Salonniere Intelligent Event Organizer
Salonniere is an intelligent event organizer built for UC Berkeley's Chatbot Collider in Fall 2016. 

Salonniere's [Webpage](http://salonneire.herokuapp.com/)
Salonniere's [Facebook Page](https://www.facebook.com/SalonniereAI/)

# This repository
This repository contains static informational pages and endpoints for Facebook's Messenger Bot API.

Based on this [tutorial](https://blog.hartleybrody.com/fb-messenger-bot/) and this [guide](http://blog.sahildiwan.com/posts/flask-and-postgresql-app-deployed-on-heroku/)

# Starting
`$ pip install Flask
$ pip install psycopg2
$ pip install Flask-SQLAlchemy
$ pip install gunicorn
$ pip install Flask-Heroku`

`$ python
>>> from app import db
>>> db.create_all()
>>> exit()`

Currently running locally will only support static pages but not the PostgreSQL database, as that URI is encoded for production right now with Flask-Heroku. See [this](http://blog.sahildiwan.com/posts/flask-and-postgresql-app-deployed-on-heroku/) for more details if you want to run the database locally.



