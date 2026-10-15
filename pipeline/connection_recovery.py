"""Offline, idempotent pessimistic settlement; never contacts a provider."""

import json

REASON = 'connection error, charge unknown, accounted as charged'


def resolve(state, ledger, request_ids):
    receipts = []
    for request_id in request_ids:
        with state.connect() as db:
            event = json.loads(db.execute('SELECT event FROM calls WHERE request_id=?', (request_id,)).fetchone()[0])
        with ledger.connect() as db:
            row = db.execute('SELECT amount,state,spent,accounting FROM reservations WHERE id=?', (request_id,)).fetchone()
        if row is None or (row[1] != 'reserved' and (row[2] != row[0] or row[3] != 'pessimistic_unknown_charge')):
            raise ValueError('Recovery reservation is not unresolved or already pessimistically settled')
        if event.get('response') is not None or event.get('outcome') != 'failed':
            raise ValueError('Recovery requires a failed call without response')
        if row[1] == 'reserved':
            ledger.settle(request_id, row[0], 'pessimistic_unknown_charge')
        event.setdefault('original_error', event.get('error'))
        event.update(outcome='failed', error=REASON, reason=REASON,
                     accounting='pessimistic_unknown_charge', cost_nanodollars=row[0],
                     cost_basis='reserved_worst_case_not_measured', reservation_settled=True)
        state.save_call(event)
        with state.connect() as db:
            items = [dict(item) for item in db.execute('SELECT key,lease FROM work WHERE origin_id=? AND status=\'pending\' AND lease IS NOT NULL', (event['review_ids'][0],))]
        for item in items:
            state.release(item)
        receipts.append({'request_id': request_id, 'review_ids': event['review_ids'],
                         'charged_nanodollars': row[0], 'reason': REASON,
                         'latency_seconds': event.get('latency_seconds'),
                         'original_error': event['original_error'], 'provider': event['provider']})
    return receipts
