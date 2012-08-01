import cgi
import datetime
import urllib
import webapp2
import os
import jinja2
import re
import itertools as it

from google.appengine.ext import db
from google.appengine.api import users

import models


jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

class Handler(webapp2.RequestHandler):
    def render(self, template, **kwargs):
        template = jinja_environment.get_template(template)
        self.response.out.write(template.render(**kwargs))

class MainPage(Handler):
    def get(self):
        user = users.get_current_user()
        if user:
            link_text = 'log out'
            link_url = users.create_logout_url(self.request.uri)
        else:
            link_text = 'log in'
            link_url = users.create_login_url(self.request.uri)
            
        self.render('index.html', 
            link_text=link_text,
            link_url=link_url)
            
class ProfilePage(Handler):
    def get(self):
        user = users.get_current_user()
        profile = models.Profile.get_or_insert(user.user_id())
        
        self.render('profile.html', user=user, ledgers=profile.ledgers(), invites=profile.invite_ledgers())
        
class InviteResponsePage(Handler):
    def get(self, name, accepted):
        # TODO: chenge this to a POST method, fix duplicated ledger participants
        
        ledger_title = name.replace('-', ' ')
        
        user = users.get_current_user()
        profile = models.Profile.get_or_insert(user.user_id())
        
        models.prefetch_refprops(profile.invite_set, models.LedgerInvites.ledger)
        for invite in profile.invite_set:
            if invite.ledger.title == ledger_title:
                if accepted in ['accepted', 'declined']:
                    if accepted == 'accepted':
                        models.LedgerParticipants(profile=profile, ledger=invite.ledger).put()
                    invite.delete()
                    return self.redirect_to('ledger', name=name)
                
        self.render('profile.html', user=user, ledgers=profile.ledgers(), invites=profile.invite_ledgers())

class LedgerPage(Handler):
    def get(self, name):
        user = users.get_current_user()
        profile = models.Profile.get_or_insert(user.user_id())
        
        ledger_title = name.replace('-', ' ')
        
        for l in profile.ledgers():
            if l.title == ledger_title:
                ledger = l
                break
        
        self.render('ledger.html', ledger=ledger,
                    profiles=[users.User(_user_id=profile.user_id) for profile in ledger.profiles()])
        
class NewLedgerPage(Handler):
    title_validator = re.compile('\w[\w -]*\w')
    def get(self):
        self.render('add_ledger.html')
        
    def post(self):
        user = users.get_current_user()
        profile = models.Profile.get_by_key_name(user.user_id())

        title = self.request.get('title')
        invites = self.request.get_all('invites')
        
        if title:
            if title in (ledger.title for ledger in profile.ledgers()):
                self.render('add_ledger.html', title=title, invites=invites,
                            error_text='A ledger with that title already exists')
            else:
                invalid_invites = []
                valid_invites = []
                for address in it.ifilter(None, invites):
                    result = models.Profile.all().filter('nickname =', address).get()
                    if result:
                        valid_invites.append(result)
                    else:
                        invalid_invites.append(address)
                if invalid_invites:
                    self.render('add_ledger.html', title=title, invites=invites,
                            error_text='The following users do not exist: %s' % ', '.join(invalid_invites))
                    return
                
                ledger = models.Ledger(title=title)
                ledger.put()
                
                models.LedgerParticipants(profile=profile, ledger=ledger).put()
                
                for invite_profile in valid_invites:
                    models.LedgerInvites(profile=invite_profile, ledger=ledger).put()
                    
                self.redirect_to('ledger', name=title.replace(' ', '-'))
                
                
            
        

        
app = webapp2.WSGIApplication([('/', MainPage),
                               webapp2.Route('/profile', ProfilePage, name='profile'),
                               webapp2.Route('/profile/<name>/<accepted>', InviteResponsePage),
                               ('/ledger/add', NewLedgerPage),
                               ('/ledger/add/submit', NewLedgerPage),
                               webapp2.Route('/ledger/<name>', LedgerPage, 'ledger')],
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
