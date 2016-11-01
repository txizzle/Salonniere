import os
import sys
import json
from random import randint
from wit import Wit

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
heroku = Heroku(app)
db = SQLAlchemy(app)

#if len(sys.argv) != 2:
#    print('usage: python ' + sys.argv[0] + ' <wit-token>')
#    exit(1)
access_token = "GCBTBJWTLXQBY6AFODUPLEBANMDTWMZ7"

# convenience function
def _get_entity_value(entities, entity):
    out = _get_entity_values(entities, entity)
    if out:
        return out[0]

def _get_entity_values(entities, entity):
    if entity not in entities:
        return None
    vals = list(i['value'] for i in entities[entity])
    if len(vals) == 0:
        return None
    return vals

def send(request, response):
    # print(response['text'])
    fb_id = request['session_id']
    # log(fb_id)
    text = response['text']
    # log(text)
    # send message
    send_message(fb_id, text)


def setEventType(request):
    context = request['context']
    entities = request['entities']
    event_type = _get_entity_value(entities, 'intent')
    if event_type == 'party':
        context['party'] = True
        # set this for when we create the event
        context['eventType'] = 'party'
    else:
        context['invalidEvent'] = True
        if context.get('party') is not None:
            del context['party']
    return context

def setEventLocation(request):
    context = request['context']
    entities = request['entities']
    event_location = _get_entity_value(entities, 'location')
    if event_location:
        context['known-location'] = True
        # set internal event location for later use
        context['eventLocation'] = event_location
    else:
        context['unknown-location'] = True
        if context.get('known-location'):
            del context['known-location']
    return context

def setEventFood(request):
    context = request['context']
    entities = request['entities']
    event_food = _get_entity_value(entities, 'intent')
    # set internal event food for later use
    context['eventFood'] = event_food
    return context

def setEventInvites(request):
    context = request['context']
    entities = request['entities']
    print('Context in setEventInvites')
    print(context)
    print('Entities in setEventInvites')
    print(entities)
    event_invites = _get_entity_values(entities, 'email')
    print(event_invites)
    # TODO: send out email invites
    owner_fb_id, name, location, food = context['fb_id'], 'Party', context['eventLocation'], context['eventFood']
    reg = Event(fb_id, name, location=location, food=food)
    db.session.add(reg)
    db.session.commit()
    return context

actions = {
    'send': send,
    'setEventType': setEventType,
    'setEventLocation': setEventLocation,
    'setEventFood': setEventFood,
    'setEventInvites': setEventInvites
}

client = Wit(access_token=access_token, actions=actions)
# client.interactive() # comment this line to turn off interactive mode

# Create our database model
# User model
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    fb_id = db.Column(db.String(120), unique=True)
    email = db.Column(db.String(120), unique=True)
    events = db.relationship('Event', backref='owner')

    def __init__(self, fb_id, email=None):
        self.fb_id = fb_id
        self.email = email

    def __repr__(self):
        return '<Facebook ID %r>' % self.fb_id

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
    food = db.Column(db.String(240))
    start_time = db.Column(db.DateTime(timezone=False)) # May need to set timezone=True in the future
    end_time = db.Column(db.DateTime(timezone=False))
    num_guests = db.Column(db.Integer)
    attire = db.Column(db.String(240))
    other = db.Column(db.String(2400)) # Store dictionary as JSON String. Better way: Store a pickled dictionary as a db.Blob
    token = db.Column(db.String(240))

    def __init__(self, owner_fb_id, name, event_type=None, location=None, food=None, start_time=None, end_time=None,
        num_guests=None, attire=None, other=None, token=None):
        self.owner_id = User.query.filter(User.fb_id.match(owner_fb_id))[0].id
        self.name = name
        self.event_type = event_type
        self.location = location
        self.start_time = start_time
        self.end_time = end_time
        self.num_guests = num_guests
        self.attire = attire
        self.other = other
        self.token = token
    def __repr__(self):
        return ('<Name %r> <Owner %r> <Event Type %r> <Location %r> <Start Time %r> <End Time %r> <Guests %r> <Attire %r> <Other %r>'
            % (self.name, self.owner.fb_id, self.event_type, self.location, self.start_time, self.end_time, self.num_guests, self.attire, self.other))

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
    fb_id = None
    if request.method == 'POST':
        fb_id = request.form['fb_id']
        print(fb_id)
        # Check that facebook id does not already exist (not a great query, but works)
        if not db.session.query(User).filter(User.fb_id == fb_id).count():
            reg = User(fb_id)
            db.session.add(reg)
            db.session.commit()
            return render_template('success.html')
    return render_template('index.html')

@app.route('/events_prereg', methods=['POST'])
def events_prereg():
    owner_fb_id = None
    name = None
    if request.method == 'POST':
        owner_fb_id = request.form['owner_fb_id']
        name = request.form['name']
        start_time = request.form['start_time']
        # Check that the owner is a real user
        # TODO: If not, should we register them as a new user?
        if db.session.query(User).filter(User.fb_id == owner_fb_id).count():
            reg = Event(owner_fb_id, name, start_time=start_time)
            db.session.add(reg)
            db.session.commit()
            new_event = db.session.query(Event).filter(Event.name == name).first()
            new_event.token = generate_token(new_event.id)
            db.session.commit()
            return render_template('success.html')
        else:
            return render_template('fail.html')
    return render_template('index.html')

# Helper function to generate a 3 word unique token per event.
def generate_token(id):
    animals = ['albatross', 'beaver', 'cougar', 'cow', 'elephant', 'fox', 'horse', 'hyena', 'lion', 'monkey', 'penguin', 'ram', 'wolf', 'zebra']
    token = ''
    mod_values = [2, 5]
    for mod in mod_values:
        token += animals[randint(0,len(animals)-1)]
        token += ' '
    token += str(13*id % 29)
    return token

@app.route('/email')
def email_index():
    return render_template('email.html')

# Test route to send an email
@app.route('/send_invite', methods=['POST'])
def send_invite():
    owner_fb_id, event_id, guest_email = None, None, None
    if request.method == 'POST':
        owner_fb_id = request.form['owner_fb_id']
        event_id = request.form['event_id']
        guest_email= request.form['guest_email']
        if db.session.query(User).filter(User.fb_id == owner_fb_id).count() and db.session.query(Event).filter(Event.id == event_id).count():
            event = db.session.query(Event).get(event_id)
            month, day = parse_datetime(event.start_time)
            send_email('You\'re Invited!',
                        'salonniere.ai@gmail.com',
                        guest_email,
                        # render_template("follower_email.txt", user=followed, follower=follower),
                        'Test message body from Salonniere',
                        render_template("invitation_email.html", owner_email=owner_fb_id, guest_email=guest_email, event=event, month=month, day=day))
            return render_template('success.html')
        else:
            return render_template('fail.html')
    return render_template('index.html')

def send_email(subject, sender, recipient, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=[recipient])
    msg.body = text_body
    msg.html = html_body
    mail.send(msg)

def parse_datetime(d):
    months = ['J A N', 'F E B', 'M A R', 'A P R', 'M A Y', 'J U N', 'J U L', 'A U G', 'S E P', 'O C T', 'N O V', 'D E C']
    return (months[d.month - 1], str(d.day))

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

                    # if the user doesn't exist, add them to the db
                    if db.session.query(User).filter(User.fb_id == sender_id).count() == 0:
                        db.session.add(User(sender_id))
                        db.session.commit()

                    # wit_resp = client.message(message_text)
                    new_context = client.run_actions(sender_id, message_text, {"fb_id": sender_id})
                    # wit_resp = client.converse(str(int(sender_id) + 7), message_text, new_context)
                    
                    # log(new_context)
                    # if 'msg' in wit_resp:
                    #     send_message(sender_id, wit_resp['msg'])
                    # else:
                    #     log(wit_resp)
                    #     send_message(sender_id, 'Sorry, I couldn\'t quite catch that. Could you rephrase that?')

                    #if 'hello' in message_text.lower() or 'hi' in message_text.lower() or 'yo' in message_text.lower():
                    #    send_message(sender_id, "Hello! I'm Salonniere, your go-to intelligent event organizer. How can I help you?")

                    #elif'ted' in message_text.lower():
                    #    send_message(sender_id, "Ted is a god.")

                    #else:
                    #    send_message(sender_id, "idk how to respond to that... o.o")

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
