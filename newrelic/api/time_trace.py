import logging
import random
import time
import sys
import newrelic.packages.six as six
import traceback
from newrelic.core.trace_cache import trace_cache
from newrelic.core.attribute import (
        process_user_attribute, MAX_NUM_USER_ATTRIBUTES)
from newrelic.api.settings import STRIP_EXCEPTION_MESSAGE

_logger = logging.getLogger(__name__)


class TimeTrace(object):

    def __init__(self, parent=None):
        self.parent = parent
        self.root = None
        self.child_count = 0
        self.children = []
        self.start_time = 0.0
        self.end_time = 0.0
        self.duration = 0.0
        self.exclusive = 0.0
        self.thread_id = None
        self.activated = False
        self.exited = False
        self.is_async = False
        self.has_async_children = False
        self.min_child_start_time = float('inf')
        self.exc_data = (None, None, None)
        self.should_record_segment_params = False
        # 16-digit random hex. Padded with zeros in the front.
        self.guid = '%016x' % random.getrandbits(64)
        self.agent_attributes = {}
        self.user_attributes = {}

    @property
    def transaction(self):
        return self.root and self.root.transaction

    @property
    def settings(self):
        transaction = self.transaction
        return transaction and transaction.settings

    def _is_leaf(self):
        return self.child_count == len(self.children)

    def __enter__(self):
        self.parent = parent = self.parent or current_trace()
        if not parent:
            return self

        # The parent may be exited if the stack is not consistent. This
        # can occur when using ensure_future to schedule coroutines
        # instead of using async/await keywords. In those cases, we
        # must not trace.
        #
        # Don't do any tracing if parent is designated
        # as a terminal node.
        if parent.exited or parent.terminal_node():
            self.parent = None
            return parent

        transaction = parent.root.transaction

        # Don't do further tracing of transaction if
        # it has been explicitly stopped.
        if transaction.stopped or not transaction.enabled:
            self.parent = None
            return self

        parent.increment_child_count()

        self.root = parent.root
        self.should_record_segment_params = (
                transaction.should_record_segment_params)

        # Record start time.

        self.start_time = time.time()

        cache = trace_cache()
        self.thread_id = cache.current_thread_id()

        # Push ourselves as the current node and store parent.
        try:
            cache.save_trace(self)
        except:
            self.parent = None
            raise

        self.activated = True

        return self

    def __exit__(self, exc, value, tb):
        if not self.parent:
            return

        # Check for violation of context manager protocol where
        # __exit__() is called before __enter__().

        if not self.activated:
            _logger.error('Runtime instrumentation error. The __exit__() '
                    'method of %r was called prior to __enter__() being '
                    'called. Report this issue to New Relic support.\n%s',
                    self, ''.join(traceback.format_stack()[:-1]))

            return

        transaction = self.root.transaction

        # If the transaction has gone out of scope (recorded), there's not much
        # we can do at this point.
        if not transaction:
            return

        # If recording of time for transaction has already been
        # stopped, then that time has to be used.

        if transaction.stopped:
            self.end_time = transaction.end_time
        else:
            self.end_time = time.time()

        # Ensure end time is greater. Should be unless the
        # system clock has been updated.

        if self.end_time < self.start_time:
            self.end_time = self.start_time

        # Calculate duration and exclusive time. Up till now the
        # exclusive time value had been used to accumulate
        # duration from child nodes as negative value, so just
        # add duration to that to get our own exclusive time.

        self.duration = self.end_time - self.start_time

        self.exclusive += self.duration

        if self.exclusive < 0:
            self.exclusive = 0

        self.exited = True

        self.exc_data = (exc, value, tb)

        # in all cases except async, the children will have exited
        # so this will create the node

        if self._ready_to_complete():
            self._complete_trace()
        else:
            # Since we're exited we can't possibly schedule more children but
            # we may have children still running if we're async
            trace_cache().pop_current(self)

    def add_custom_attribute(self, key, value):
        settings = self.settings
        if not settings:
            return

        if settings.high_security:
            _logger.debug('Cannot add custom parameter in High Security Mode.')
            return

        if len(self.user_attributes) >= MAX_NUM_USER_ATTRIBUTES:
            _logger.debug('Maximum number of custom attributes already '
                    'added. Dropping attribute: %r=%r', key, value)
            return

        self.user_attributes[key] = value

    def _observe_exception(self, exc_info=None, ignore_errors=[]):
        # Bail out if the transaction is not active or
        # collection of errors not enabled.

        transaction = self.transaction
        settings = transaction and transaction.settings

        if not settings:
            return

        if not settings.error_collector.enabled:
            return

        # At least one destination for error events must be enabled
        if not (
                settings.collect_traces or
                settings.collect_span_events or
                settings.collect_errors or
                settings.collect_error_events):
            return

        # If no exception details provided, use current exception.

        if exc_info and None not in exc_info:
            exc, value, tb = exc_info
        else:
            exc, value, tb = sys.exc_info()

        # Has to be an error to be logged.

        if exc is None or value is None or tb is None:
            return

        # Where ignore_errors is a callable it should return a
        # tri-state variable with the following behavior.
        #
        #   True - Ignore the error.
        #   False- Record the error.
        #   None - Use the default ignore rules.

        should_ignore = None

        if hasattr(transaction, '_ignore_errors'):
            should_ignore = transaction._ignore_errors(exc, value, tb)
            if should_ignore:
                return

        if callable(ignore_errors):
            should_ignore = ignore_errors(exc, value, tb)
            if should_ignore:
                return

        module = value.__class__.__module__
        name = value.__class__.__name__

        if should_ignore is None:
            # We need to check for module.name and module:name.
            # Originally we used module.class but that was
            # inconsistent with everything else which used
            # module:name. So changed to use ':' as separator, but
            # for backward compatibility need to support '.' as
            # separator for time being. Check that with the ':'
            # last as we will use that name as the exception type.

            if module:
                names = ('%s:%s' % (module, name), '%s.%s' % (module, name))
            else:
                names = (name)

            for fullname in names:
                if not callable(ignore_errors) and fullname in ignore_errors:
                    return

                if fullname in settings.error_collector.ignore_errors:
                    return

            fullname = names[0]

        else:
            if module:
                fullname = '%s:%s' % (module, name)
            else:
                fullname = name

        # Check to see if we need to strip the message before recording it.

        if (settings.strip_exception_messages.enabled and
                fullname not in settings.strip_exception_messages.whitelist):
            message = STRIP_EXCEPTION_MESSAGE
        else:
            try:

                # Favor unicode in exception messages.

                message = six.text_type(value)

            except Exception:
                try:

                    # If exception cannot be represented in unicode, this means
                    # that it is a byte string encoded with an encoding
                    # that is not compatible with the default system encoding.
                    # So, just pass this byte string along.

                    message = str(value)

                except Exception:
                    message = '<unprintable %s object>' % type(value).__name__

        # Record a supportability metric if error attributes are being
        # overiden.
        if 'error.class' in self.agent_attributes:
            transaction._record_supportability(
                    'Supportability/'
                    'SpanEvent/Errors/Dropped')
        # Add error details as agent attributes to span event.
        self._add_agent_attribute('error.class', fullname)
        self._add_agent_attribute('error.message', message)
        return fullname, message, tb

    def record_exception(self, exc_info=None,
                         params={}, ignore_errors=[]):

        recorded = self._observe_exception(exc_info, ignore_errors)
        if recorded:
            fullname, message, tb = recorded
            transaction = self.transaction
            settings = transaction and transaction.settings

            # Only add params if High Security Mode is off.

            custom_params = {}

            if settings.high_security:
                if params:
                    _logger.debug('Cannot add custom parameters in '
                            'High Security Mode.')
            else:
                try:
                    for k, v in params.items():
                        name, val = process_user_attribute(k, v)
                        if name:
                            custom_params[name] = val
                except Exception:
                    _logger.debug('Parameters failed to validate for unknown '
                            'reason. Dropping parameters for error: %r. Check '
                            'traceback for clues.', fullname, exc_info=True)
                    custom_params = {}

            transaction._create_error_node(
                    settings, fullname, message, custom_params, self.guid, tb)

    def _add_agent_attribute(self, key, value):
        self.agent_attributes[key] = value

    def has_outstanding_children(self):
        return len(self.children) != self.child_count

    def _ready_to_complete(self):
        # we shouldn't continue if we're still running
        if not self.exited:
            return False

        # defer node completion until all children have exited
        if self.has_outstanding_children():
            return False

        return True

    def complete_trace(self):
        # This function is called only by children in the case that the node
        # creation has been deferred. _ready_to_complete should only return
        # True once the final child has completed.
        if self._ready_to_complete():
            self._complete_trace()

    def _complete_trace(self):
        # transaction already completed, this is an error
        if self.parent is None:
            _logger.error('Runtime instrumentation error. The transaction '
                    'already completed meaning a child called complete trace '
                    'after the trace had been finalized. Trace: %r \n%s',
                    self, ''.join(traceback.format_stack()[:-1]))

            return

        parent = self.parent

        # Check to see if we're async
        if parent.exited or parent.has_async_children:
            self.is_async = True

        # Pop ourselves as current node. If deferred, we have previously exited
        # and are being completed by a child trace.
        trace_cache().pop_current(self)

        # Wipe out parent reference so can't use object
        # again. Retain reference as local variable for use in
        # this call though.
        self.parent = None

        # wipe out exc data
        exc_data = self.exc_data
        self.exc_data = (None, None, None)

        # Observe errors on the span only if record_exception hasn't been
        # called already
        if exc_data[0] and 'error.class' not in self.agent_attributes:
            self._observe_exception(exc_data)

        # Wipe out root reference as well
        transaction = self.root.transaction
        self.root = None

        # Give chance for derived class to finalize any data in
        # this object instance. The transaction is passed as a
        # parameter since the transaction object on this instance
        # will have been cleared above.

        self.finalize_data(transaction, *exc_data)
        exc_data = None

        # Give chance for derived class to create a standin node
        # object to be used in the transaction trace. If we get
        # one then give chance for transaction object to do
        # something with it, as well as our parent node.

        node = self.create_node()

        if node:
            transaction._process_node(node)
            parent.process_child(node, self.is_async)

        # ----------------------------------------------------------------------
        # SYNC  | The parent will not have exited yet, so no node will be
        #       | created. This operation is a NOP.
        # ----------------------------------------------------------------------
        # Async | The parent may have exited already while the child was
        #       | running. If this trace is the last node that's running, this
        #       | complete_trace will create the parent node.
        # ----------------------------------------------------------------------
        parent.complete_trace()

    def finalize_data(self, transaction, exc=None, value=None, tb=None):
        pass

    def create_node(self):
        return self

    def terminal_node(self):
        return False

    def update_async_exclusive_time(self, min_child_start_time,
            exclusive_duration):
        # if exited and the child started after, there's no overlap on the
        # exclusive time
        if self.exited and (self.end_time < min_child_start_time):
            exclusive_delta = 0.0
        # else there is overlap and we need to compute it
        elif self.exited:
            exclusive_delta = (self.end_time -
                    min_child_start_time)

            # we don't want to double count the partial exclusive time
            # attributed to this trace, so we should reset the child start time
            # to after this trace ended
            min_child_start_time = self.end_time
        # we're still running so all exclusive duration is taken by us
        else:
            exclusive_delta = exclusive_duration

        # update the exclusive time
        self.exclusive -= exclusive_delta

        # pass any remaining exclusive duration up to the parent
        exclusive_duration_remaining = exclusive_duration - exclusive_delta

        if self.parent and exclusive_duration_remaining > 0.0:
            # call parent exclusive duration delta
            self.parent.update_async_exclusive_time(min_child_start_time,
                    exclusive_duration_remaining)

    def process_child(self, node, is_async):
        self.children.append(node)
        if is_async:

            # record the lowest start time
            self.min_child_start_time = min(self.min_child_start_time,
                    node.start_time)

            # if there are no children running, finalize exclusive time
            if self.child_count == len(self.children):

                exclusive_duration = node.end_time - self.min_child_start_time

                self.update_async_exclusive_time(self.min_child_start_time,
                        exclusive_duration)

                # reset time range tracking
                self.min_child_start_time = float('inf')
        else:
            self.exclusive -= node.duration

    def increment_child_count(self):
        self.child_count += 1

        # if there's more than 1 child node outstanding
        # then the children are async w.r.t each other
        if (self.child_count - len(self.children)) > 1:
            self.has_async_children = True
        # else, the current trace that's being scheduled is not going to be
        # async. note that this implies that all previous traces have
        # completed
        else:
            self.has_async_children = False

    def get_linking_metadata(self):
        metadata = {
            "entity.type": "SERVICE",
        }
        txn = self.transaction
        if txn:
            metadata["span.id"] = self.guid
            metadata["trace.id"] = txn.trace_id
            settings = txn.settings
            if settings:
                metadata["entity.name"] = settings.app_name
                entity_guid = settings.entity_guid
                if entity_guid:
                    metadata["entity.guid"] = entity_guid
        return metadata


def add_custom_span_attribute(key, value):
    trace = current_trace()
    if trace:
        trace.add_custom_attribute(key, value)


def current_trace():
    return trace_cache().current_trace()


def get_linking_metadata():
    trace = current_trace()
    if trace:
        return trace.get_linking_metadata()
    else:
        return {
            "entity.type": "SERVICE",
        }


def record_exception(exc=None, value=None, tb=None, params={},
        ignore_errors=[], application=None):
    if application is None:
        trace = current_trace()
        if trace:
            trace.record_exception((exc, value, tb), params,
                    ignore_errors)
    else:
        if application.enabled:
            application.record_exception(exc, value, tb, params,
                    ignore_errors)
