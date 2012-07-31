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

class Profile(db.Model):
    ledger_keys = db.ListProperty(db.Key)
    ledger_invite_keys = db.ListProperty(db.Key)
    
    def __init__(self, user_id, **kwargs):
        super(Profile, self).__init__(key_name=user_id, **kwargs)
        
    @property
    def user_id(self):
        return self.key().name()
    
    @property
    def ledgers(self):
        return db.get(self.ledger_keys)
    
    @property
    def ledger_invites(self):
        return db.get(self.ledger_invite_keys)
    
    def append_ledger(self, ledger):
        self.ledger_keys.append(ledger.key())
        
    
class Ledger(db.Model):
    @property
    def title(self):
        return self.key().name()
    
    def fetch_profiles(self, limit=100):
        return Profile.all().filter('ledgers =', self).fetch(limit)
    
    def iter_users(self):
        profiles = self.fetch_profiles()
        prefetch_refprops(profiles, 'ledgers')
        for profile in profiles:
            yield users.User(_user_id=profile.user_id)

class Transaction(db.Model):
    from_id = db.IntegerProperty(required=True)
    to_id = db.IntegerProperty(required=True)
    amount_cents = db.IntegerProperty(required=True)
    date = db.DateTimeProperty(auto_now_add=True)
    active = db.BooleanProperty(default=True)
    notes = db.StringProperty()
    
    @property
    def amount_string(self):
        return '%i.%02i' % (self.amount_cents / 100, n % 100)
