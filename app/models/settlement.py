import numpy as np


def Settlement(expenses: list[dict], users: list[str], tx_hist: list[tuple] = None):
    num_users  = len(users)
    matrix     = np.zeros((num_users,num_users))
    dict_users = {}

    for id,user in enumerate(users):
        dict_users[user] = id

    for expense in expenses:
        amount      = expense["amount"]
        sharers     = expense["sharers"]
        num_sharers = len(sharers)
        payer       = expense["payer"]
        payer_id    = dict_users[payer]

        amount_to_pay = amount/num_sharers

        for sharer in sharers:
            sharer_id = dict_users[sharer]
            if payer_id != sharer_id:
                matrix[payer_id,sharer_id] += amount_to_pay
                matrix[sharer_id,payer_id] += -amount_to_pay
    
    if tx_hist:
        for di, ci, amnt in tx_hist:
            matrix[ci,di] += amnt
            matrix[di,ci] += -amnt

    DC_vector = np.sum(matrix, axis=1)

    debtors   = [(i, -DC_vector[i]) for i in range(len(DC_vector)) if DC_vector[i] < 0]
    creditors = [(i,  DC_vector[i]) for i in range(len(DC_vector)) if DC_vector[i] > 0]

    tx = []
    di = ci = 0

    while di < len(debtors) and ci < len(creditors):
        d_idx, d_amt = debtors[di]
        c_idx, c_amt = creditors[ci]

        x = min(d_amt, c_amt) 
        tx.append((d_idx, c_idx, x))

        d_amt -= x
        c_amt -= x

        if d_amt <= 0:
            di += 1
        else:
            debtors[di] = (d_idx, d_amt)

        if c_amt <= 0:
            ci += 1
        else:
            creditors[ci] = (c_idx, c_amt)
    
    return tx





