from google.appengine.ext import db

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
    
    #def __init__(self, user_id, **kwds):
    #    self.user_id = user_id
    #    super(Profile, self).__init__(key_name=user_id, **kwds)
    
class Ledger(db.Model):
    title = db.StringProperty()
    
    #def __init__(self, title, **kwds):
    #    self.title = title
    #    super(Ledger, self).__init__(**kwds)
    
    @property
    def profiles(self):
        return Profile.all()#.filter('ledgers', self.key())

class Transaction(db.Model):
    from_id = db.IntegerProperty(required=True)
    to_id = db.IntegerProperty(required=True)
    amount_cents = db.IntegerProperty(required=True)
    date = db.DateTimeProperty(auto_now_add=True)
    
    @property
    def amount_string(self):
        return '%i.%02i' % (self.amount_cents / 100, n % 100)
