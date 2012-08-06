class _Account(object):
    def __init__(self, name, balance=0):
        self.name = name
        self.balance = balance

def _pay_matching(d):
    for c in creditors:
        if d.balance + c.balance == 0:
            print '%s -> %s $%s' % (d.name, c.name, -d.balance)
            d.balance = c.balance = 0
            return True
    return False

def _pay_forward(d):
    for d2 in debtors:
        if d is not d2:
            for c in creditors:
                if d.balance + d2.balance + c.balance == 0:
                    print '%s -> %s $%s' % (d.name, c.name, -d.balance)
                    c.balance += d.balance
                    d.balance = 0
                    return True
    return False

def _pay_any(d):
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

def minimize_transactions(transactions):
    balances = {p.key():0 for p in ledger.participant_profiles()}
    # find the ending balance after all transactions complete
    for t in models.Transaction.all().ancestor(ledger):
        balances[t.to_profile.key()] += t.amount_cents
        balances[t.from_profile.key()] -= t.amount_cents
        
    # separate the balances into positive and negative balances
    creditors, debtors = [], []
    for k, v in balances.iteritems():
        if v > 0:
            creditors.append([k, v])
        if v < 0:
            debtors.append([k, v])
    
    for d in debtors:
        if not _pay_matching(d):
            if not _pay_forward(d):
                if not _pay_any(d):
                    raise RuntimeError('debtor balance is not paid')
