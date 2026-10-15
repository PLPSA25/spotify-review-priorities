"""Pure proposed migration; never reads or writes live state or resets a window."""
import copy


def split_legacy_terminal_history(receipt, jev_failed_keys):
    """Recognize this exact history shape; retain original history verbatim.

    Classification failures already exist in classification history/seen keys.
    Legacy finalization history was prefixed by those failures alone. Do not
    guess ordering, remove real finalization errors or modify connection history.
    Returned proposal requires explicit approval before any persistence.
    """
    original = copy.deepcopy(receipt)
    keys = set(jev_failed_keys)
    legacy = original['terminal_window']
    if not keys <= set(original['classification_window']['seen']) or not keys <= set(legacy['seen']):
        raise ValueError('Cannot prove duplicate stage attribution')
    if legacy['outcomes'] != [True]*len(keys)+[False]*(len(legacy['outcomes'])-len(keys)):
        raise ValueError('Unrecognized history; do not discard possible finalization failures')
    return {'original_windows':{k:original[k] for k in ('classification_window','terminal_window','connection_window')},
            'classification_window':original['classification_window'],
            'connection_window':original['connection_window'],
            'terminal_window':{'outcomes':legacy['outcomes'][len(keys):],
                               'seen':sorted(set(legacy['seen'])-keys)},
            'reassigned_duplicate_jev_failures':sorted(keys),
            'applied':False,'requires_explicit_approval':True}
