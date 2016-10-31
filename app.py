import os
import sys
import json #import simplejson as json

import requests
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy

from flask_heroku import Heroku
from flask_mail import Mail, Message

app = Flask(__name__)

# Setup Flask-Mail
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'salonniere.ai@gmail.com'
app.config['MAIL_PASSWORD'] = 'chatbotcollider'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

# Setup PostgreSQL Database
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://localhost/main'
#app.config['SQLALCHEMY_BINDS'] = {
#    'users': 'postgresql://localhost/all-users',
#    'events': 'postgresql://localhost/all-events'
#}
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
heroku = Heroku(app)
db = SQLAlchemy(app)

# User model
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    events = db.relationship('Event', backref='owner')

    def __init__(self, email):
        self.email = email

    def __repr__(self):
        return '<E-mail %r>' % self.email

# Event model
class Event(db.Model):
    # An Event consists of an event name, owner, event type, event location, 
    #   starting time, end time, expected guests, attire, and other attributes.
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(240))
    event_type = db.Column(db.String(240))
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    location = db.Column(db.String(240))
    start_time = db.Column(db.DateTime(timezone=False)) # May need to set timezone=True in the future
    end_time = db.Column(db.DateTime(timezone=False))
    num_guests = db.Column(db.Integer)
    attire = db.Column(db.String(240))
    other = db.Column(db.String(2400)) # Store dictionary as JSON String. Better way: Store a pickled dictionary as a db.Blob

    def __init__(self, owner_email, name, event_type=None, location=None, start_time=None, end_time=None, 
        num_guests=None, attire=None, other=None):
        self.owner_id = User.query.filter(User.email.match(owner_email))[0].id
        self.name = name
        self.event_type = event_type
        self.location = location
        self.start_time = start_time
        self.end_time = end_time
        self.num_guests = num_guests
        self.attire = attire
        self.other = other

    def __repr__(self):
        return ('<Name %r> <Owner %r> <Event Type %r> <Location %r> <Start Time %r> <End Time %r> <Guests %r> <Attire %r> <Other %r>'
            % (self.name, self.owner.email, self.event_type, self.location, self.start_time, self.end_time, self.num_guests, self.attire, self.other))

# Index route for main landing page
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# View to list Users table
@app.route('/users', methods=['GET'])
def users_index():
    return render_template(
       'users.html',
       users=User.query.all())

# View to list Events table
@app.route('/events', methods=['GET'])
def events_index():
    return render_template(
        'events.html',
        events=Event.query.all())

# View to signup a new User
@app.route('/signup', methods=['GET'])
def signup_index():
    return render_template('signup_index.html')

# View to create a new Event with an existing User
@app.route('/create_event', methods=['GET'])
def create_event_index():
    return render_template('event_signup_index.html')

# Save e-mail to database and send to success page
@app.route('/prereg', methods=['POST'])
def prereg():
    email = None
    if request.method == 'POST':
        email = request.form['email']
        # Check that email does not already exist (not a great query, but works)
        if not db.session.query(User).filter(User.email == email).count():
            reg = User(email)
            db.session.add(reg)
            db.session.commit()
            return render_template('success.html')
    return render_template('index.html')

@app.route('/events_prereg', methods=['POST'])
def events_prereg():
    owner_email = None
    name = None
    if request.method == 'POST':
        owner_email = request.form['owner_email']
        name = request.form['name']
        # Check that the owner is a real user
        # TODO: If not, should we register them as a new user?
        if db.session.query(User).filter(User.email == owner_email).count():
            reg = Event(owner_email, name)
            db.session.add(reg)
            db.session.commit()
            return render_template('success.html')
        else:
            return render_template('fail.html')
    return render_template('index.html')

# Test route to send an email
@app.route('/mail_test')
def send_mail():
    msg = Message(
      'Hello',
       sender='salonniere.ai@gmail.com',
       recipients=
       ['t.xiao@berkeley.edu'])
    msg.body = "Test message from Salonniere!"
    msg.html = render_template('invitation_email.html')
    mail.send(msg)
    return "Sent"

@app.route('/facebook/webhook/', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Facebook Webhook URL", 200


@app.route('/facebook/webhook/', methods=['POST'])
def webhook():

    # endpoint for processing incoming messaging events

    data = request.get_json()
    log(data)  # you may not want to log every incoming message in production, but it's good for testing

    if data["object"] == "page":

        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:

                if messaging_event.get("message"):  # someone sent us a message

                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    message_text = messaging_event["message"]["text"]  # the message's text

                    if 'hello' in message_text.lower() or 'hi' in message_text.lower() or 'yo' in message_text.lower():
                        send_message(sender_id, "Hello! I'm Salonniere, your go-to intelligent event organizer. How can I help you?")

                    elif'ted' in message_text.lower():
                        send_message(sender_id, "Ted is a god.")

                    else:
                        send_message(sender_id, "idk how to respond to that... o.o")

                if messaging_event.get("delivery"):  # delivery confirmation
                    pass

                if messaging_event.get("optin"):  # optin confirmation
                    pass

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    pass

    return "ok", 200


def send_message(recipient_id, message_text):

    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def log(message):  # simple wrapper for logging to stdout on heroku
    print str(message)
    sys.stdout.flush()


if __name__ == '__main__':
    app.run(debug=True)
