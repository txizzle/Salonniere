#!/usr/bin/env python3
"""
   ___       _  _      
  / __> ___ | || | _ _ 
  \__ \<_> || || || | |
  <___/<___||_||_|`_. |
                  <___'
"""
#
# Sally is an intelligent event planner on Facebook messenger. Facebook, Inc. approved
# the software as of November 3, 2016. This software may NOT be used without the consent
# and may NOT be used with warranty of MERCHATABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#

__version__ = '0.1'
 
import os
import sys
import json
import ast
from random import randint
from wit import Wit

import requests
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy

from flask_heroku import Heroku
from flask_mail import Mail, Message

from yelp.client import Client
from yelp.oauth1_authenticator import Oauth1Authenticator

from util import sim

SIM_THRESHOLD = .994

app = Flask(__name__)


#=================================================================================================
# Configurations
#=================================================================================================

# Setup Flask-Mail
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'salonniere.ai@gmail.com'
app.config['MAIL_PASSWORD'] = 'chatbotcollider'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

# Setup PostgreSQL Database
heroku = Heroku(app)
db = SQLAlchemy(app)

# Wit.ai Access Token
access_token = os.environ['WIT_TOKEN']

# Yelp Authentication
yelp_auth = Oauth1Authenticator(
    consumer_key=os.environ['YELP_CONSUMER_KEY'],
    consumer_secret=os.environ['YELP_CONSUMER_SECRET'],
    token=os.environ['YELP_TOKEN'],
    token_secret=os.environ['YELP_TOKEN_SECRET']
)


#=================================================================================================
# Server URL Handlers
#=================================================================================================

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
    animals = ['albatross', 'beaver', 'cougar', 'elephant', 'fox', 'hyena', 'lion', 'lynx', 'penguin', 'ram', 'wolf', 'zebra']
    token = ''
    token = animals[randint(0,len(animals)-1)] + ' ' + str(13*id % 29) + ' ' + animals[randint(0,len(animals)-1)]
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
            owner = db.session.query(User).filter(User.fb_id == owner_fb_id).first()
            event = db.session.query(Event).get(event_id)
            month, day = parse_datetime(event.start_time)
            send_email('You\'re Invited!',
                        'salonniere.ai@gmail.com',
                        guest_email,
                        # render_template("follower_email.txt", user=followed, follower=follower),
                        'Test message body from Salonniere',
                        render_template("invitation_email.html", owner=owner, guest_email=guest_email, event=event, month=month, day=day))
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
                    
                    if "text" not in messaging_event["message"]:
                        send_message(sender_id, 'Sorry, I only understand words!')
                    else:
                        message_text = messaging_event["message"]["text"]  # the message's text

                        # If the User doesn't exist, add them to the database. Else, find User from database.
                        if db.session.query(User).filter(User.fb_id == sender_id).count() == 0:
                            params = {
                                "access_token": os.environ["PAGE_ACCESS_TOKEN"]
                            }

                            r = requests.get("https://graph.facebook.com/v2.8/" + sender_id, params=params)
                            response = ast.literal_eval(r.text)
                            log('Response: ')
                            log(response)

                            first_name, last_name = response['first_name'], response['last_name']
                            initial_context = str({"fb_id": sender_id})

                            db.session.add(User(sender_id, first_name=first_name, last_name=last_name, context=initial_context))
                            db.session.commit()    
                        current_user = db.session.query(User).filter(User.fb_id == sender_id).first()
                        old_context = ast.literal_eval(current_user.context)

                        log('Old Context: ')
                        log(old_context)

                        # Hardcoding 'reset' for testing purposes
                        if message_text.lower() == 'reset':
                            # Delete all events I own
                            sender_uid = current_user.id
                            if db.session.query(Event).filter(Event.owner_id == sender_uid).count():
                                db.session.delete(db.session.query(Event).filter(Event.owner_id == sender_uid).first())
                                db.session.commit()
                            new_context = str({"fb_id": sender_id})
                            send_message(sender_id, 'Resetting context for testing')
                        elif message_text.lower() == 'reset convo':
                            new_context = str({"fb_id": sender_id})
                            send_message(sender_id, 'Resetting context for testing')
                        else:
                            new_context = wit_client.run_actions(sender_id, message_text, old_context)

                        # Save context
                        current_user.context = str(new_context)
                        db.session.commit()  

                        log('New Context: ')
                        log(new_context)

                if messaging_event.get("delivery"):  # delivery confirmation
                    pass

                if messaging_event.get("optin"):  # optin confirmation
                    pass

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    payload = messaging_event["postback"]["payload"]

                    # send_message(sender_id, 'Payload received: ' + str(payload))
                    log('Payload: ')
                    log(payload)


                    current_user = db.session.query(User).filter(User.fb_id == sender_id).first()
                    old_context = ast.literal_eval(current_user.context)

                    log('Old Context: ')
                    log(old_context)

                    new_context = wit_client.run_actions(sender_id, payload, old_context)

                    # Save context
                    current_user.context = str(new_context)
                    db.session.commit()  

                    log('New Context: ')
                    log(new_context)

    return "ok", 200

#=================================================================================================
# Server Actions
#=================================================================================================

# send message
def send(request, response):
    fb_id = request['session_id']
    text = response['text']
    # send message
    send_message(fb_id, text)

def setEventType(request):
    context = request['context']
    entities = request['entities']
    event_type = _get_entity_value(entities, 'event_type')
    if event_type == 'party':
        context['party'] = True
        # set this for when we create the event
        context['eventType'] = 'party'
    else:
        context['invalidEvent'] = True
        if context.get('party') is not None:
            del context['party']
    return context

def setEventTime(request):
    context = request['context']
    entities = request['entities']
    start_time = _get_entity_value(entities, 'datetime')
    log('start_time')
    log(start_time)
    if start_time:
        # set this for when we create the event
        context['valid_start'] = True
        context['eventStart'] = start_time
    else:
        context['invalid_start'] = True
        if context.get('valid_start') is not None:
            del context['valid_start']
    return context

def setEventName(request):
    context = request['context']
    entities = request['entities']
    event_name = _get_entity_value(entities, 'event_name')
    context['eventName'] = event_name
    return context

def setEventLocation(request):
    context = request['context']
    entities = request['entities']
    event_location = _get_entity_value(entities, 'location')
    if event_location:
        context['known-location'] = True
        # set internal event location for later use
        if context.get('unknown-location'):
            del context['unknown-location']
        context['eventLocation'] = event_location
    else:
        context['unknown-location'] = True
        if context.get('known-location'):
            del context['known-location']
    return context

def findYelpSuggestions(request):
    context = request['context']
    entities = request['entities']
    search_location = _get_entity_value(entities, 'location')
    search_params = {
        'term': 'attractions',
        'limit': 4,
        'lang': 'en'
    }

    yelp_client = Client(yelp_auth)
    results = yelp_client.search(search_location, **search_params)
    businesses = []
    for bus in results.businesses:
        bus_img_url = bus.image_url
        bus_img_highres = bus_img_url[:-6] + 'o' + bus_img_url[-4:]
        businesses.append([bus.name, bus.snippet_text, bus_img_highres, bus.url, bus.location.address])

    log('businesses')
    log(businesses)
    card_content = {
        "type": "template",
        "payload": {
            "template_type": "generic",
            "elements": [{
                "title": businesses[0][0],
                "subtitle": businesses[0][1],
                "image_url": businesses[0][2],
                "buttons": [{
                    "type": "web_url",
                    "url": businesses[0][3],
                    "title": "Website"
                }, {
                    "type": "postback",
                    "title": "Choose it!",
                    "payload": businesses[0][4][0],
                }],
            }, {
                "title": businesses[1][0],
                "subtitle": businesses[1][1],
                "image_url": businesses[1][2],
                "buttons": [{
                    "type": "web_url",
                    "url": businesses[1][3],
                    "title": "Website"
                }, {
                    "type": "postback",
                    "title": "Choose it!",
                    "payload": businesses[1][4][0],
                }],
            }, {
                "title": businesses[2][0],
                "subtitle": businesses[2][1],
                "image_url": businesses[2][2],
                "buttons": [{
                    "type": "web_url",
                    "url": businesses[2][3],
                    "title": "Website"
                }, {
                    "type": "postback",
                    "title": "Choose it!",
                    "payload": businesses[2][4][0],
                }],
            }, {
                "title": businesses[3][0],
                "subtitle": businesses[3][1],
                "image_url": businesses[3][2],
                "buttons": [{
                    "type": "web_url",
                    "url": businesses[3][3],
                    "title": "Website"
                }, {
                    "type": "postback",
                    "title": "Choose it!",
                    "payload": businesses[3][4][0],
                }],
            }]
        }
    }
    
    send_card(context['fb_id'], card_content)
    return context

def setEventFood(request):
    context = request['context']
    entities = request['entities']
    event_food = _get_entity_value(entities, 'food')
    if event_food:
        context['known-food'] = True
        if context.get('unknown-food'):
            del context['unknown-food']
        # set internal event food for later use
        context['eventFood'] = event_food
    else:
        context['unknown-food'] = True
        if context.get('known-food'):
            del context['known-food']
    return context

def getEventDetails(request):
    context = request['context']
    entities = request['entities']
    # event_token = _get_entity_value(entities, 'intent')
    animals = _get_entity_values(entities, 'animal')
    number = _get_entity_value(entities, 'number')
    log('animal1: {0}, animal2: {1}, number: {2}'.format(animals[0], animals[1], number))

    event_token = ''
    if animals and len(animals) == 2 and number:
        event_token = animals[0] + ' '+ str(number) + ' ' + animals[1]

    log('Event token')
    log(event_token)
    log('Context in getEventDetails')
    log(context)
    log('Entities in getEventDetails')
    log(entities)
    
    # Check if event_token corresponds to a real event with event_code
    if db.session.query(Event).filter(Event.token== event_token.lower()).count():
        event = db.session.query(Event).filter(Event.token == event_token.lower()).first()
        owner = db.session.query(User).get(event.owner_id)
        owner_name = owner.first_name + ' ' + owner.last_name
        context['event-owner'] = owner_name
        context['event-location'] = event.location
        context['event-food'] = event.food
        context['event-token'] = event_token
        context['valid'] = True

        # Hardcoding RSVP Update 
        guest = db.session.query(User).filter(User.fb_id == context['fb_id']).first()
        guest_name = guest.first_name + ' ' + guest.last_name
        send_message(owner.fb_id, guest_name + ' just RSVP\'d to your event! Yay!')
    return context

# Returns an answer to a nonessential question. This looks through all questions that
# were asked so far and compares the similarity between the current question and all
# other questions. If a match is found and the answer is known, it updates the context
# with the answer. If not, context['answer'] will be None, and askQuestionToHost will be
# called.
def answerOtherQuestion(request):
    context = request['context']
    entities = request['entities']

    log("Other - Context: {0}.\n Other - Entities: {1}".format(context, entities))

    question = _get_entity_values(entities, 'question')
    event_token = _get_entity_values(entities, 'event-token')
    event = db.session.query(Event).filter(Event.token == event_token.lower()).first()
    owner_id = context['owner_id']

    # If not a single question was not asked before
    if not event.other:
        event.other = str({ question:None })
        context['answer'] = None
#        askQuestionToHost(owner_id, question);
        log("New question - question: {0}".format(question))
        return context
    other = dict(event.other)

    # Check if question is close to any asked question
    for other_question in other:
        if sim(question, other_question) > SIM_THRESHOLD:    # If question matches
            context['answer'] = other[other_question]
#            if context['answer'] == None:
#                askQuestionToHost(owner_id, other_question)
            log("Similar question - {0} = {1}".format(question, other_question))
            return context
    
    # If question is not close to any asked question
    other[question] = None
    context['answer'] = None
    log("Not similar question - {0}".format(question))
#	askQuestionToHost(owner_id, question)
    return context

def askQuestionToHost(owner_id, question):
    # Get fb_id of host
    user = db.session.query(User).get(owner_id)
    fb_id = user.fb_id
    context = ast.literal_eval(user.context)

    # Return with context of question
    context['cur_question'] = question
    send_message(fb_id, question)
    
def setEventInvites(request):
    context = request['context']
    entities = request['entities']
    print('Context in setEventInvites')
    print(context)
    print('Entities in setEventInvites')
    print(entities)
    event_invites = _get_entity_values(entities, 'email')
    print(event_invites)

    # Get Event fields from context
    owner_fb_id, name, start_time, location, food = context['fb_id'], context['eventName'], context['eventStart'], context['eventLocation'], context['eventFood']

    # Add Event to database
    reg = Event(owner_fb_id, name, location=location, food=food, start_time=start_time)
    db.session.add(reg)
    db.session.commit()

    # Add invite token to event
    owner_id = User.query.filter(User.fb_id.match(owner_fb_id))[0].id
    new_event = db.session.query(Event).filter(Event.owner_id == owner_id).first()
    new_event.token = generate_token(new_event.id)
    db.session.commit()

    for guest_email in event_invites:
        owner = db.session.query(User).get(owner_id)
        event = db.session.query(Event).filter(Event.owner_id == owner_id).first()
        month, day = parse_datetime(event.start_time)
        # month, day = 'N O V', '5' # TODO: HARDCODED IN DATE. ADD TO WIT AI
        send_email('You\'re Invited!',
                    'salonniere.ai@gmail.com',
                    guest_email,
                    # render_template("follower_email.txt", user=followed, follower=follower), #This is for .txt email body
                    'Test message body from Salonniere',
                    render_template("invitation_email.html", owner=owner, guest_email=guest_email, event=event, month=month, day=day))
    return context # This might need to change

actions = {
    'send': send,
    'setEventType': setEventType,
    'setEventName': setEventName,
    'setEventTime': setEventTime,
    'setEventLocation': setEventLocation,
    'findYelpSuggestions': findYelpSuggestions,
    'setEventFood': setEventFood,
    'setEventInvites': setEventInvites,
    'getEventDetails': getEventDetails,
    'answerOtherQuestion': answerOtherQuestion
}

#=================================================================================================
# Utility Funcitons
#=================================================================================================


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






wit_client = Wit(access_token=access_token, actions=actions)

# Create our database model
# User model
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    fb_id = db.Column(db.String(120), unique=True)
    first_name = db.Column(db.String(120))
    last_name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True)
    context = db.Column(db.String(480)) # str representation of context dict
    events = db.relationship('Event', backref='owner')

    def __init__(self, fb_id, first_name=None, last_name=None, email=None, context=None):
        self.fb_id = fb_id
        self.email = email
        self.context = context
        self.first_name = first_name
        self.last_name = last_name

    def __repr__(self):
        return '<Facebook ID %r> <First Name %r> <Last Name %r> <Context %r>' % (self.fb_id, self.first_name, self.last_name, self.context)

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
        self.food = food
    def __repr__(self):
        return ('<Name %r> <Owner %r> <Event Type %r> <Location %r> <Start Time %r> <End Time %r> <Guests %r> <Attire %r> <Other %r>'
            % (self.name, self.owner.fb_id, self.event_type, self.location, self.start_time, self.end_time, self.num_guests, self.attire, self.other))


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

def send_card(recipient_id, card_content):
    log("sending card to {recipient}: {text}".format(recipient=recipient_id, text=str(card_content)))

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
            "attachment": card_content
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)

def log(message):  # simple wrapper for logging to stdout on heroku
    print(str(message))
    sys.stdout.flush()

# Privacy policy
@app.route('/privacy')
def privacy():
    return render_template('privacypolicy.html')

if __name__ == '__main__':
    app.run(debug=True)
