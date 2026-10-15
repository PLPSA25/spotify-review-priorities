"""Finalize verifier items independently and persist failures before continuing."""

from pipeline.calls import InvalidOutput


def finalize_batch(batch, send, predictions, terminal, monitor, persist):
    try:
        result = send(batch, False)
    except InvalidOutput as exc:
        result = {'valid': {}, 'errors': dict.fromkeys(batch, str(exc))}
    for rid, record in result['valid'].items():
        predictions[rid] = record
        persist()
        monitor.record(rid, False)
    for rid in result['errors']:
        try:
            repair = send({rid: batch[rid]}, True)
        except InvalidOutput as exc:
            repair = {'valid': {}, 'errors': {rid: str(exc)}}
        if rid in repair['valid']:
            predictions[rid] = repair['valid'][rid]
            persist()
            monitor.record(rid, False)
        else:
            terminal[rid] = {'status': 'terminally_failed', 'reason': 'invalid_output_after_permitted_repair',
                             'error': repair['errors'].get(rid, 'Missing valid repaired record')}
            persist()
            monitor.record(rid, True)
