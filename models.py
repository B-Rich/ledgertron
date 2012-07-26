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

class Account(db.Model):
    user_id = db.IntegerProperty(required=True)
    ledgers = db.ListProperty(db.Key)
    
class Ledger(db.Model):
    title = db.StringProperty(required=True)
    
    @property
    def accounts(self):
        return prefetch_refprops(Account.all().filter('ledgers', self.key()))

class Transaction(db.Model):
    from_id = db.IntegerProperty(required=True)
    to_id = db.IntegerProperty(required=True)
    amount_cents = db.IntegerProperty(required=True)
    
    @property
    def amount_string(self):
        return '%i.%02i' % (self.amount_cents / 100, n % 100)
