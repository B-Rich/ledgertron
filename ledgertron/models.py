import functools

from google.appengine.ext import db
from google.appengine.api import users

def prefetch_refprops(entities, *props):
    """Dereference Reference Properties to reduce Gets.
    
    See:    http://blog.notdot.net/2010/01/ReferenceProperty-prefetching-in-App-Engine
    """
    fields = [(entity, prop) for entity in entities for prop in props]
    ref_keys = [prop.get_value_for_datastore(x) for x, prop in fields]
    ref_entities = dict((x.key(), x) for x in db.get(set(ref_keys)))
    for (entity, prop), ref_key in zip(fields, ref_keys):
        prop.__set__(entity, ref_entities[ref_key])
    return entities

def dereference_props(query, prop, attr, fetch_size=100):
    entities = query.fetch(fetch_size)
    prefetch_refprops(entities, prop)
    return [getattr(entity, attr) for entity in entities]

class Profile(db.Model):
    nickname = db.StringProperty()
    
    def __init__(self, *args, **kwargs):
        if 'user_id' in kwargs:
            kwargs['key_name'] = kwargs['user_id']
            del kwargs['user_id']
        if 'key_name' in kwargs:
            kwargs['nickname'] = users.User(_user_id=kwargs['key_name']).nickname()
            
        super(Profile, self).__init__(*args, **kwargs)
        
    @property
    def user_id(self):
        return self.key().name()
    
    def ledgers(self):
        return dereference_props(self.ledger_set, LedgerParticipants.ledger, 'ledger')
    
    def invite_ledgers(self):
        return dereference_props(self.invite_set, LedgerInvites.ledger, 'ledger')
    
class Ledger(db.Model):
    title = db.StringProperty()
    
    def participant_profiles(self):
        return dereference_props(self.profile_set, LedgerParticipants.profile, 'profile')
    
    def invite_profiles(self):
        return dereference_props(self.invite_set, LedgerInvites.profile, 'profile')
            
class LedgerParticipants(db.Model):
    profile = db.ReferenceProperty(Profile, collection_name='ledger_set')
    ledger = db.ReferenceProperty(Ledger, collection_name='profile_set')
    
class LedgerInvites(db.Model):
    profile = db.ReferenceProperty(Profile, collection_name='invite_set')
    ledger = db.ReferenceProperty(Ledger, collection_name='invite_set')

class Transaction(db.Model):
    from_profile = db.ReferenceProperty(Profile, required=True, collection_name='outgoing_transactions')
    to_profile = db.ReferenceProperty(Profile, required=True, collection_name='incoming_transactions')
    amount_cents = db.IntegerProperty(required=True)
    date = db.DateTimeProperty(auto_now_add=True)
    active = db.BooleanProperty(default=True)
    notes = db.TextProperty()
    
    @property
    def amount_string(self):
        return '%i.%02i' % (self.amount_cents / 100, self.amount_cents % 100)
    
    def __repr__(self):
        return '<Transaction(from_profile=%r, to_profile=%r, amount=%s)>' % (self.from_profile.nickname,
                                                                           self.to_profile.nickname,
                                                                           self.amount_string)
