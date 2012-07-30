import cgi
import datetime
import urllib
import webapp2
import os
import jinja2

from google.appengine.ext import db
from google.appengine.api import users

import models


jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

class Greeting(db.Model):
  """Models an individual Guestbook entry with an author, content, and date."""
  author = db.StringProperty()
  content = db.StringProperty(multiline=True)
  date = db.DateTimeProperty(auto_now_add=True)


def guestbook_key(guestbook_name=None):
  """Constructs a Datastore key for a Guestbook entity with guestbook_name."""
  return db.Key.from_path('Guestbook', guestbook_name or 'default_guestbook')


class MainPage(webapp2.RequestHandler):
    def render(self, template, template_values):
        template = jinja_environment.get_template(template)
        self.response.out.write(template.render(template_values))
        
    def get(self):
        #guestbook_name=self.request.get('guestbook_name')
        #greetings_query = Greeting.all().ancestor(
        #    guestbook_key(guestbook_name)).order('-date')
        #greetings = greetings_query.fetch(10)
        user = users.get_current_user()
        if user:
            profile = models.Profile.get_or_insert(user.user_id())
            profile.put()
            
            profile2 = models.Profile.get_by_key_name(user.user_id())
            ledger = models.Ledger()
            ledger.name = 'Ledge'
            ledger.put()
            
            profile2.ledgers.append(ledger)
            
            self.render('index.html', {
                'output':users.User(_user_id=profile2.user_id).nickname(),
                'ledgers':ledger.profiles
            })
        else:
            url = users.create_login_url(self.request.uri)
            self.render('login.html', {
                'url':url
            })
            

        #template_values = {
        #    'greetings': greetings,
        #    'url': url,
        #    'url_linktext': url_linktext,
        #}

        


class Guestbook(webapp2.RequestHandler):
  def post(self):
    # We set the same parent key on the 'Greeting' to ensure each greeting is in
    # the same entity group. Queries across the single entity group will be
    # consistent. However, the write rate to a single entity group should
    # be limited to ~1/second.
    guestbook_name = self.request.get('guestbook_name')
    greeting = Greeting(parent=guestbook_key(guestbook_name))

    if users.get_current_user():
      greeting.author = users.User(_user_id=users.get_current_user().user_id()).nickname()

    greeting.content = self.request.get('content')
    greeting.put()
    self.redirect('/?' + urllib.urlencode({'guestbook_name': guestbook_name}))


app = webapp2.WSGIApplication([('/', MainPage),
                               ('/sign', Guestbook)],
                              debug=True)

'''
class Account(object):
    def __init__(self, name, balance=0):
        self.name = name
        self.balance = balance
        
    def __repr__(self):
        return '(%r, %r)' % (self.name, self.balance)

a,b,c,d,e,f = 'abcdef'
transactions = [
    [b,a,5],
    [b,c,20],
    [d,e,2],
    [d,f,1]
]

ledger = {l:0 for l in 'abcdef'}

for t in transactions:
    ledger[t[0]] += t[2]
    ledger[t[1]] -= t[2]
    
creditors, debtors = [], []
for k, v in ledger.iteritems():
    if v > 0:
        creditors.append(Account(k, v))
    elif v < 0:
        debtors.append(Account(k, v))
        
def pay_matching(d):
    for c in creditors:
        if d.balance + c.balance == 0:
            print '%s -> %s $%s' % (d.name, c.name, -d.balance)
            d.balance = c.balance = 0
            return True
    return False

def pay_forward(d):
    for d2 in debtors:
        if d is not d2:
            for c in creditors:
                if d.balance + d2.balance + c.balance == 0:
                    print '%s -> %s $%s' % (d.name, c.name, -d.balance)
                    c.balance += d.balance
                    d.balance = 0
                    return True
    return False

def pay_any(d):
    for c in creditors:
        if c.balance > 0:
            if -d.balance < c.balance:
                print '%s -> %s $%s' % (d.name, c.name, -d.balance)
                d.balance = c.balance = 0
                return True
            print '%s -> %s $%s' % (d.name, c.name, c.balance)
            d.balance += c.balance
            c.balance = 0
        if d.balance == 0:
            return True
    return False

for d in debtors:
    if not pay_matching(d):
        if not pay_forward(d):
            if not pay_any(d):
                raise RuntimeError('debtor balance is not paid')
'''
