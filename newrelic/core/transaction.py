"""This module provides class types used in the construction of the raw
transaction trace hierarchy from which metrics are then to be generated.

The higher level instrumentation layer will construct a tree for each web
transaction or background task. The root node should be an instance of the
TransactionNode class. This would be passed to the agent core via the
record_transaction() method of the Agent class instance which in turn gets
passed to the process_raw_transaction() function of this module. In
processing to generic metric data, each node and its children would in turn
be processed as necessary. The base metric data would then be injected
into the application object.

For a TransactionNode the 'type' attribute will be either 'WebTransaction'
or 'OtherTransaction' corresponding to a web transaction or background task.

The 'group' attribute of both TransactionNode and FunctionNode can consist
of multiple path segments representing a primary category and any sub
categories to which the transaction is being associated. For example:

    Uri
    Function
    Script/Import
    Script/Execute
    Template/Compile
    Template/Render

The 'name' attribute is then the actual name being associated with the web
transaction, background task or function trace node.

The final composite metric path for a transaction may then be as example:

    WebTransaction/Uri/some/url
    WebTransaction/Function/module:class.function

    OtherTransaction/Script/Import//absolute/path/to/some/module.py
    OtherTransaction/Script/Import/relative/path/to/some/module.py

The rule for constructing the metric path for a transaction is:

    if group == 'Uri' and name[:1] == '/':
        path = '%s/%s%s' % (type, group, name)
    else:
        path = '%s/%s/%s' % (type, group, name)

The special case for 'Uri' with a leading slash on name is necessary to
maintain compatibility with how existing agents and core application appear
to behave.

The 'type' and 'group' attributes are separate to allow easier construction
of rollup and apdex metrics based on the categories/sub categories.

For a function trace node the final composite metric path may be:

    Function/module:class.function
    Template/Render//absolute/path/to/template.py
    Template/Render/relative/path/to/template.py

The rule for construction the metric path for a function trace node is:

    path = '%s/%s' % (group, name)

"""

import collections

DatabaseNode = collections.namedtuple('DatabaseNode',
        ['database_module', 'connect_params', 'sql', 'children',
        'start_time', 'end_time', 'duration', 'exclusive',
        'stack_trace'])

ExternalNode = collections.namedtuple('ExternalNode',
        ['library', 'url', 'children', 'start_time', 'end_time',
        'duration', 'exclusive'])

FunctionNode = collections.namedtuple('FunctionNode',
        ['group', 'name', 'children', 'start_time', 'end_time',
        'duration', 'exclusive'])

MemcacheNode = collections.namedtuple('MemcacheNode',
        ['command', 'children', 'start_time', 'end_time', 'duration',
        'exclusive'])

TransactionNode = collections.namedtuple('TransactionNode',
        ['type', 'group', 'name', 'request_uri', 'response_code',
        'request_params', 'custom_params', 'queue_start', 'start_time',
        'end_time', 'duration', 'exclusive', 'children', 'errors',
        'slow_sql', 'ignore_apdex'])
        
ErrorNode = collections.namedtuple('ErrorNode',
        ['type', 'message', 'stack_trace', 'custom_params',
        'file_name', 'line_number', 'source'])

def process_raw_transaction(application, data):
    # FIXME This is where the raw transaction data needs to be processed
    # and turned into metrics which are then injected into the application
    # object supplied as argument.

    # FIXME The application object perhaps needs to maintain an
    # activation counter. This would be incremented after each connect
    # to core application and updated server side configuration
    # available. The counter number should then be pushed into the
    # application specific settings object and the higher level
    # instrumentation layer should then supply the counter value in the
    # TransactionNode root object for the raw transaction data. That way
    # the code here could make a decision whether the data should be
    # thrown away as it relates to a transaction that started when the
    # application was previously active, but got restarted in between
    # then and when the transaction completed. If we don't do this then
    # we could push through transaction data accumulated based on an
    # old set of application specific configuration settings. This may
    # not be an issue given in most cases the server side configuration
    # wouldn't change but should be considered. No harm in adding the
    # counter even if not ultimately needed. The core application could
    # even be what doles out the counter or identifying value for that
    # configuration snapshot and record it against the agent run details
    # stored in core application database rather than it be generated
    # internally using a counter. The value could change on each request
    # or only increment when server side sees a change in server side
    # application configuration. If only changes when configuration
    # changes, wouldn't matter then that request started with one
    # configuration and finished after application had been restarted.

    print 'TRANSACTION', application.name, data
