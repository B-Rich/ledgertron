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
        user = users.get_current_user()
        if user:
            link_text = 'Log out'
            link_url = users.create_logout_url('/')
        else:
            link_text = 'Log in'
            link_url = '/profile'
        self.response.out.write(template.render(link_url=link_url, link_text=link_text, **kwargs))

class MainPage(Handler):
    def get(self):
        user = users.get_current_user()
        if user is not None:
            profile = models.Profile.get_or_insert(user.user_id())
            return self.render('index.html', profile=profile)
        self.render('index.html')
            
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
        clicked_btn = self.request.get('accept', None)
        if clicked_btn is None:
            clicked_btn = self.request.get('decline', None)
        
        if ledger_title and clicked_btn in ('accept', 'decline'):
                models.prefetch_refprops(profile.invite_set, models.LedgerInvites.ledger)
                for invite in profile.invite_set:
                    if invite.ledger.title == ledger_title:
                            if clicked_btn == 'accept':
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
                kwargs = self.action(profile, ledger) or {}
                transactions = models.Transaction.all().ancestor(ledger)
                payments = utils.minimize_transactions(transactions)
                
                self.render('ledger.html', ledger=ledger,
                            participants=ledger.participant_profiles(),
                            invites=ledger.invite_profiles(),
                            transactions=transactions,
                            payments=payments,
                            profile=profile,
                            **kwargs)
                return
        #TODO: make this an actual page
        self.response.out.write('Ledger not found')
        
    def get(self, name):
        self.create_page(name)

class LedgerInvitePage(LedgerPage):
    def action(self, profile, ledger):
        nickname = self.request.get('nickname').strip()
        #If the nickname field is blank, just pretend like they didn't click submit
        if nickname:
            invite_profile = models.Profile.all().filter('nickname =', nickname).get()
            if invite_profile:
                if invite_profile.key() in [l.key() for l in ledger.participant_profiles()]:
                    return {'invite_error:''That user is already a particiapnt.'}
                if invite_profile.key() in [l.key() for l in ledger.invite_profiles()]:
                    return {'invite_error':'That user is already invited.'}
                models.LedgerInvites(profile=invite_profile, ledger=ledger).put()
            else:
                return {'invite_error':"That user doesn't exist"}
                
    def post(self, name):
        self.create_page(name)

class LedgerAddPage(LedgerPage):
    def action(self, profile, ledger):
        participant_profiles = ledger.participant_profiles()
        creditor_profile = models.Profile.get_by_key_name(self.request.get('creditor'))
        debtor_profile = models.Profile.get_by_key_name(self.request.get('debtor'))
        
        if not (creditor_profile and debtor_profile):
            return {'add_error':'User can not be found'}
        if creditor_profile.key() == debtor_profile.key():
            return {'add_error':'From and To profiles cannot be the same'}
        if not (any(creditor_profile.key() == p.key() for p in participant_profiles) and
                any(debtor_profile.key() == p.key() for p in participant_profiles)):
            return {'add_error':'Profile is not a member of this ledger'}
        try:
            amount = decimal.Decimal(self.request.get('amount'))
            if amount <= 0:
                raise TypeError
        except (decimal.InvalidOperation, TypeError):
            return {'add_error':'Invalid transaction amount'}
        else:
            models.Transaction(parent=ledger, from_profile=creditor_profile,
                               to_profile=debtor_profile, amount_cents=int(amount*100),
                               notes=self.request.get('notes')).put()
            
    def post(self, name):
        self.create_page(name)
        
class LedgerBillPage(LedgerPage):
    def action(self, profile, ledger):
        participant_profiles = ledger.participant_profiles()
        from_profile = models.Profile.get_by_key_name(self.request.get('from'))
        
        if not from_profile:
            return {'bill_error':'Invalid profile'}
        if not any(from_profile.key() == p.key() for p in participant_profiles):
            return {'bill_error':'Profile is not a member of this ledger'}
        try:
            amount = decimal.Decimal(self.request.get('amount'))
            if amount <= 0:
                raise TypeError
        except (decimal.InvalidOperation, TypeError):
            return {'bill_error':'Invalid transaction amount'}
        else:
            amount_cents = int(amount * 100 / len(participant_profiles))
            for to_profile in participant_profiles:
                if from_profile.key() != to_profile.key():
                    models.Transaction(parent=ledger, from_profile=from_profile,
                                       to_profile=to_profile, amount_cents=amount_cents,
                                       notes=self.request.get('notes')).put()
        
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
                self.render('add_ledger.html', title=title, invites=invites, profile=profile,
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
                    self.render('add_ledger.html', title=title, invites=invites, profile=profile,
                            error_text='The following users do not exist: %s' % ', '.join(invalid_invites))
                    return
                
                ledger = models.Ledger(title=title)
                ledger.put()
                
                models.LedgerParticipants(profile=profile, ledger=ledger).put()
                
                for invite_profile in valid_invites:
                    models.LedgerInvites(profile=invite_profile, ledger=ledger).put()
                    
                self.redirect_to('ledger', name=title.replace(' ', '-'))
        else:
            self.render('add_ledger.html',
                        title=title, invites=invites, profile=profile,
                        error_text='Invalid title: %s' % title)


app = webapp2.WSGIApplication([('/', MainPage),
                               webapp2.Route('/profile', ProfilePage, name='profile'),
                               ('/profile/edit', ProfileEditPage),
                               ('/ledger/add', NewLedgerPage),
                               ('/ledger/add/submit', NewLedgerPage),
                               webapp2.Route('/ledger/<name>', LedgerPage, 'ledger'),
                               webapp2.Route('/ledger/<name>/invite', LedgerInvitePage),
                               webapp2.Route('/ledger/<name>/add', LedgerAddPage),
                               webapp2.Route('/ledger/<name>/bill', LedgerBillPage)],
                              debug=True)

