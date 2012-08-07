import cgi
import datetime
import urllib
import webapp2
import os
import jinja2
import re
import decimal
import itertools as it

from google.appengine.api import users

import models
import utils

jinja_environment = jinja2.Environment(autoescape=True, extensions=['jinja2.ext.autoescape'],
        loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

class Handler(webapp2.RequestHandler):
    def get_profile(self):
        return  models.Profile.get_or_insert(users.get_current_user().user_id())
    
    def render(self, template, **kwargs):
        template = jinja_environment.get_template(template)
        self.response.out.write(template.render(**kwargs))

class MainPage(Handler):
    def get(self):
        user = users.get_current_user()
        if user is not None:
            #we don't use the profile here, but still put it as soon as the user logs in
            models.Profile.get_or_insert(user.user_id())
        
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
        profile = self.get_profile()
        self.render('profile.html', profile=profile, ledgers=profile.ledgers(), invite_ledgers=profile.invite_ledgers())
        
class ProfileEditPage(Handler):
    def post(self):
        profile = self.get_profile()
        
        nickname = self.request.get('nickname')
        if nickname:
            profile.nickname = nickname
            profile.put()
            
        ledger_title = self.request.get('title')
        accepted = self.request.get('accepted', None)
        
        if ledger_title and accepted is not None:
                models.prefetch_refprops(profile.invite_set, models.LedgerInvites.ledger)
                for invite in profile.invite_set:
                    if invite.ledger.title == ledger_title:
                            if accepted:
                                models.LedgerParticipants(profile=profile, ledger=invite.ledger).put()
                            invite.delete()
        
        self.redirect_to('profile')

class LedgerPage(Handler):
    def action(self, profile, ledger):
        return ''
    
    def create_page(self, name):
        profile = self.get_profile()
        ledger_title = name.replace('-', ' ')
        
        for ledger in profile.ledgers():
            if ledger.title == ledger_title:
                error_text = self.action(profile, ledger)
                transactions = models.Transaction.all().ancestor(ledger)
                payments = utils.minimize_transactions(transactions)
                
                self.render('ledger.html', ledger=ledger,
                            participants=ledger.participant_profiles(),
                            invites=ledger.invite_profiles(),
                            transactions=transactions,
                            payments=payments,
                            error_text=error_text)
                return
        #TODO: make this an actual page
        self.response.out.write('Ledger not found')
        
    def get(self, name):
        self.create_page(name)

class LedgerInvitePage(LedgerPage):
    def action(self, profile, ledger):
        nickname = self.request.get('nickname').strip()
        if nickname:
            invite_profile = models.Profile.all().filter('nickname =', nickname).get()
            if invite_profile:
                models.LedgerInvites(profile=invite_profile, ledger=ledger).put()
                return ''
        else:
            return 'Invalid nickname'
                
    def post(self, name):
        self.create_page(name)

class LedgerAddPage(LedgerPage):
    def action(self, profile, ledger):
        participant_profiles = ledger.participant_profiles()
        from_profile = models.Profile.get_by_key_name(self.request.get('from'))
        to_profile = models.Profile.get_by_key_name(self.request.get('to'))
        
        if (from_profile and to_profile and
            from_profile.key() != to_profile.key() and
            any(from_profile.key() == p.key() for p in participant_profiles) and
            any(to_profile.key() == p.key() for p in participant_profiles)):
            try:
                amount = decimal.Decimal(self.request.get('amount'))
                if amount <= 0:
                    raise TypeError
            except (decimal.InvalidOperation, TypeError):
                return 'Invalid transaction amount'
            else:
                models.Transaction(parent=ledger, from_profile=from_profile,
                                   to_profile=to_profile, amount_cents=int(amount*100),
                                   notes=self.request.get('notes')).put()
        else:
            return 'Invalid profile' #TODO: make this more descriptive
            
    def post(self, name):
        self.create_page(name)
        
        
class NewLedgerPage(Handler):
    title_validator = re.compile('\w[\w -]*\w')
    def get(self):
        self.render('add_ledger.html')
        
    def post(self):
        profile = self.get_profile()

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
                               ('/profile/edit', ProfileEditPage),
                               ('/ledger/add', NewLedgerPage),
                               ('/ledger/add/submit', NewLedgerPage),
                               webapp2.Route('/ledger/<name>', LedgerPage, 'ledger'),
                               webapp2.Route('/ledger/<name>/invite', LedgerInvitePage),
                               webapp2.Route('/ledger/<name>/add', LedgerAddPage)],
                              debug=True)

