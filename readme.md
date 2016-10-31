# Salonniere Intelligent Event Organizer
Salonniere is an intelligent event organizer built for UC Berkeley's Chatbot Collider in Fall 2016. 

Salonniere's [Webpage](http://salonniere.herokuapp.com/)
Salonniere's [Facebook Page](https://www.facebook.com/SalonniereAI/)

# This repository
This repository contains static informational pages and endpoints for Facebook's Messenger Bot API.

Based on this [tutorial](https://blog.hartleybrody.com/fb-messenger-bot/) and this [guide](http://blog.sahildiwan.com/posts/flask-and-postgresql-app-deployed-on-heroku/)

# Starting Locally
Follow the instructions [here](http://blog.sahildiwan.com/posts/flask-and-postgresql-app-deployed-on-heroku/) with some small changes. Basically, follow the steps below (verify with the guide) with some small differences, which are specially marked below. 

1. Install dependencies. Do note that you can use `virtualenv` if you want; if you don't, you will have to manually edit requirements.txt later (as opposed to just `$ pip freeze > requirements.txt`). 

```
$ pip install Flask
$ pip install psycopg2
$ pip install Flask-SQLAlchemy
$ pip install gunicorn
$ pip install Flask-Heroku
```

2. Install [Postgress.app](http://postgresapp.com/).

Add this to your .bash_profile (*This is different from the guide because the latest version is 9.6 and not 9.3)
`export PATH="/Applications/Postgres.app/Contents/Versions/9.6/bin:$PATH"`

Run the downloaded app. Then, create a new database (for the main database I used locally, I called it `all-users`). In terminal, run: 
`$ createdb main`. 

You can verify that the database was created by running `=# \list` in psql (the downloaded App's terminal, or running psql in the terminal). If your database was created succesfully, you should see a database with the name `all-users`. 

3. Create database based off the model.
```
$ python
>>> from app import db
>>> db.create_all()
>>> exit()
```

4. Add DB URL to app.py
Uncomment line 12 in app.py (`# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://localhost/all-users'`) to let Flask know where the postgresql database is. Comment out line 14 (`heroku = Heroku(app)`).

5. Run it!
Try running `python app.py` and go to `localhost:5000/signup` and after inputting an email verify that it shows up in `localhost:5000/users`. 

6. To deploy to Heroku, undo step 3. You'll need to install the Heroku toolbelt and link it to your account, which should have access to our Heroku app (salonneire.herokuapp.com)




