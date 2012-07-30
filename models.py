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
    user_id = db.StringProperty()
    ledgers = db.ListProperty(db.Key)
    ledger_invites = db.ListProperty(db.Key)
    
    @classmethod
    def _get_profile_transaction(cls, user_id):
        profile = cls.all().filter('user_id =', user_id).get()
        if profile is None:
            profile = cls(user_id=user_id)
            profile.put()
        return profile
    
    @classmethod
    def from_user(cls, user):
        return db.run_in_transaction(cls._get_profile_transaction, user.user_id())
    
class Ledger(db.Model):
    title = db.StringProperty()
    
    def fetch_profiles(self, limit=500):
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
