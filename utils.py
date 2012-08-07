import models

def _pay_matching(debtors, creditors, d):
    '''Try to pay off two balances at the same time.'''
    transactions = []
    for c in creditors:
        if debtors[d] + creditors[c] == 0:
            transactions.append(models.Transaction(from_profile=d,
                                                   to_profile=c,
                                                   amount_cents=-debtors[d]))
            debtors[d] = creditors[c] = 0
            return transactions
    return transactions

def _pay_forward(debtors, creditors, d):
    '''Try to pay off one balance now, and set up the creditor to be paid off fully in the next transaction.'''
    transactions = []
    for other_debtor in debtors:
        if d is not other_debtor:
            for c in creditors:
                if debtors[d] + debtors[other_debtor] + creditors[c] == 0:
                    transactions.append(models.Transaction(from_profile=d,
                                                            to_profile=c,
                                                            amount_cents=-debtors[d]))
                    creditors[c] += debtors[d]
                    debtors[d] = 0
                    return transactions
    return transactions

def _pay_any(debtors, creditors, d):
    '''Make payments to as many creditors as necessary to fully pay off the debtor's debt'''
    transactions = []
    for c in creditors:
        if creditors[c] > 0:
            if -debtors[d] < creditors[c]:
                transactions.append(models.Transaction(from_profile=d,
                                                        to_profile=c,
                                                        amount_cents=-debtors[d]))
                debtors[d] = creditors[c] = 0
                return transactions
            transactions.append(models.Transaction(from_profile=d,
                                                    to_profile=c,
                                                    amount_cents=creditors[c]))
            debtors[d] += creditors[c]
            creditors[c] = 0
        if debtors[d] == 0:
            return transactions
    return transactions

def minimize_transactions(transactions):
    '''Take a list of Transaction objects and return the shortest list of Transactions the will pay off all debts.'''
    
    balances = {}
    # find the ending balance after all transactions complete
    for t in transactions:
        balances[t.to_profile.key()] = balances.get(t.to_profile.key(), 0) - t.amount_cents
        balances[t.from_profile.key()] = balances.get(t.from_profile.key(), 0) + t.amount_cents
        
    # separate the balances into positive and negative balances
    creditors, debtors = {}, {}
    for k, v in balances.iteritems():
        if v > 0:
            creditors[k] = v
        if v < 0:
            debtors[k] = v
    
    transactions = []
    for d in debtors:
        for f in _pay_matching, _pay_forward, _pay_any:
            transactions += f(debtors, creditors, d)
            if debtors[d] == 0:
                break
        else:
            RuntimeError('Debt not fully paid off')
    
    return transactions
