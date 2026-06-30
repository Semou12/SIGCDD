from django.dispatch import Signal

# Signal sent whenever status is changed for a Payment. This usually happens
# when a transaction is either accepted or rejected.
op_status_changed = Signal()

projet_status_changed=Signal()

cancel_op_process_call=Signal()