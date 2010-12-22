/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_web_transaction.h"
#include "py_database_trace.h"
#include "py_external_trace.h"
#include "py_function_trace.h"
#include "py_memcache_trace.h"

#include "globals.h"
#include "logging.h"

#include "application_funcs.h"
#include "harvest_funcs.h"
#include "params_funcs.h"
#include "web_transaction_funcs.h"

/* ------------------------------------------------------------------------- */

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

/* ------------------------------------------------------------------------- */

NRWebTransactionObject *NRWebTransaction_New(nr_application *application,
                                             PyObject* environ)
{
    NRWebTransactionObject *self;
    PyObject *item;

    const char *path = "<unknown>";
    int path_type = NR_PATH_TYPE_URI;
    int64_t queue_start = 0;

    /*
     * If application and environ are NULL then indicates we are
     * creating a dummy transaction object due to the monitoring
     * of parent application being disabled.
     */

    if (environ) {
        /*
         * Extract from the WSGI environ dictionary details of the
         * URL path. This will be set as default path for the web
         * transaction. This can be overridden by framework to be
         * more specific to avoid metrics explosion problem resulting
         * from too many distinct URLs for same resource due to use
         * of REST style URL concepts or otherwise.
         *
         * TODO Note that we only pay attention to REQUEST_URI at
         * this time. In the PHP agent it is possible to base the
         * path on the filename of the resource, but this may not
         * necessarily be appropriate for WSGI. Instead may be
         * necessary to look at reconstructing equivalent of the
         * REQUEST_URI from SCRIPT_NAME and PATH_INFO instead where
         * REQUEST_URI is not available. Ultimately though expect
         * that path will be set to be something more specific by
         * higher level wrappers for a specific framework.
         */

        item = PyDict_GetItemString(environ, "REQUEST_URI");

        if (item && PyString_Check(item))
            path = PyString_AsString(item);
        else
            path_type = NR_PATH_TYPE_UNKNOWN;

        /*
         * See if the WSGI environ dictionary includes the special
         * 'X-NewRelic-Queue-Start' HTTP header. This header is an
         * optional header that can be set within the underlying web
         * server or WSGI server to indicate when the current
         * request was first received and ready to be processed. The
         * difference between this time and when application starts
         * processing the request is the queue time and represents
         * how long spent in any explicit request queuing system, or
         * how long waiting in connecting state against listener
         * sockets where request needs to be proxied between any
         * processes within the application server.
         */

        item = PyDict_GetItemString(environ, "HTTP_X_NEWRELIC_QUEUE_START");

        if (item && PyString_Check(item)) {
            const char *s = PyString_AsString(item);
            if (s[0] == 't' && s[1] == '=' )
                queue_start = (int64_t)strtoll(s+2, 0, 0);
        }
    }

    /*
     * Create transaction object and cache reference to the
     * internal agent client application object instance. Will
     * need the latter when doing some work arounds for lack
     * of thread safety in agent client code.
     */

    self = PyObject_New(NRWebTransactionObject, &NRWebTransaction_Type);
    if (self == NULL)
        return NULL;

    self->application = application;

    if (application) {
        self->web_transaction = nr_web_transaction__allocate();

        self->web_transaction->http_response_code = 200;

        self->web_transaction->path_type = path_type;
        self->web_transaction->path = nrstrdup(path);
        self->web_transaction->realpath = NULL;

        self->web_transaction->http_x_request_start = queue_start;
    }
    else
        self->web_transaction = NULL;

    self->transaction_errors = NULL;

    if (environ) {
        self->request_parameters = environ;
        Py_INCREF(self->request_parameters);
    }
    else
        self->request_parameters = NULL;

    self->custom_parameters = PyDict_New();

    self->transaction_active = 0;

    return self;
}

static PyObject *NRWebTransaction_exit(NRWebTransactionObject *self,
                                       PyObject *args);

static void NRWebTransaction_dealloc(NRWebTransactionObject *self)
{
    /*
     * If transaction still active when this object is begin
     * destroyed then force call of exit method to finalise the
     * transaction.
     */

    if (self->transaction_active) {
        PyObject *args;
        PyObject *result;

        args = Py_BuildValue("(OOO)", Py_None, Py_None, Py_None);

        result = NRWebTransaction_exit(self, args);

        Py_XDECREF(result);
        Py_DECREF(args);
    }

    Py_DECREF(self->custom_parameters);
    Py_XDECREF(self->request_parameters);

    PyObject_Del(self);
}

static PyObject *NRWebTransaction_enter(NRWebTransactionObject *self,
                                        PyObject *args)
{
    nr_node_header *save;

    if (self->transaction_active) {
        PyErr_SetString(PyExc_RuntimeError, "transaction already active");
        return NULL;
    }

    self->transaction_active = 1;

    if (!self->web_transaction) {
        Py_INCREF(self);
        return (PyObject *)self;
    }

    nr_node_header__record_starttime_and_push_current(
            (nr_node_header *)self->web_transaction, &save);

    Py_INCREF(self);
    return (PyObject *)self;
}

static PyObject *NRWebTransaction_exit(NRWebTransactionObject *self,
                                       PyObject *args)
{
    int keep_wt = 0;

    PyObject *type = NULL;
    PyObject *value = NULL;
    PyObject *traceback = NULL;

    /*
     * We parse out the required parameters for conformity but
     * don't do anything with them. Specifically, when passed in
     * exception details we don't attach the error details to
     * the transaction. Instead we rely on higher level catching
     * the exception and attaching it as easier to deal with it
     * at Python code level. Thus we return None which means that
     * caller responsible for re raising the exception if there
     * is one.
     */

    if (!PyArg_ParseTuple(args, "OOO:__exit__", &type, &value, &traceback))
        return NULL;

    if (!self->transaction_active) {
        PyErr_SetString(PyExc_RuntimeError, "transaction not active");
        return NULL;
    }

    if (!self->web_transaction) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    nr_node_header__record_stoptime_and_pop_current(
            (nr_node_header *)self->web_transaction, NULL);

    pthread_mutex_lock(&(nr_per_process_globals.harvest_data_mutex));

    nr__switch_to_application(self->application);

    keep_wt = nr__distill_web_transaction_into_harvest_data(
            self->web_transaction);

    /*
     * Only add request parameters and custom parameters into
     * web transaction object if the record is being kept due
     * to associated errors or because it is being tracked as
     * a slow transaction.
     */

    if (keep_wt || self->transaction_errors != NULL) {
        if (PyDict_Size(self->request_parameters) > 0) {
            Py_ssize_t pos = 0;

            PyObject *key;
            PyObject *value;

            PyObject *key_as_string;
            PyObject *value_as_string;

            while (PyDict_Next(self->request_parameters, &pos, &key,
                   &value)) {
                key_as_string = PyObject_Str(key);

                if (!key_as_string)
                   PyErr_Clear();

                value_as_string = PyObject_Str(value);

                if (!value_as_string)
                   PyErr_Clear();

                if (key_as_string && value_as_string) {
                    nr_param_array__set_string_in_hash_at(
                            self->web_transaction->params,
                            "request_parameters",
                            PyString_AsString(key_as_string),
                            PyString_AsString(value_as_string));
                }

                Py_XDECREF(key_as_string);
                Py_XDECREF(value_as_string);
            }
        }

        if (PyDict_Size(self->custom_parameters) > 0) {
            Py_ssize_t pos = 0;

            PyObject *key;
            PyObject *value;

            PyObject *key_as_string;
            PyObject *value_as_string;

            while (PyDict_Next(self->custom_parameters, &pos, &key,
                    &value)) {
                key_as_string = PyObject_Str(key);

                if (!key_as_string)
                   PyErr_Clear();

                value_as_string = PyObject_Str(value);

                if (!value_as_string)
                   PyErr_Clear();

                if (key_as_string && value_as_string) {
                    nr_param_array__set_string_in_hash_at(
                            self->web_transaction->params,
                            "custom_parameters",
                            PyString_AsString(key_as_string),
                            PyString_AsString(value_as_string));
                }

                Py_XDECREF(key_as_string);
                Py_XDECREF(value_as_string);
            }
        }
    }

    nr_transaction_error__process_errors(self->transaction_errors,
            self->application->pending_harvest->metrics);

    if (!keep_wt)
        nr_web_transaction__destroy(self->web_transaction);

    nr__merge_errors_from_to(&self->transaction_errors,
                             &self->application->pending_harvest->errors);

    pthread_mutex_unlock(&(nr_per_process_globals.harvest_data_mutex));

    self->web_transaction = NULL;
    self->transaction_errors = NULL;

    self->transaction_active = 0;

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *NRWebTransaction_function_trace(
        NRWebTransactionObject *self, PyObject *args)
{
    NRFunctionTraceObject *rv;

    const char *funcname = NULL;
    const char *classname = NULL;

    if (!PyArg_ParseTuple(args, "s|s:function_trace", &funcname, &classname))
        return NULL;

    if (!self->transaction_active) {
        PyErr_SetString(PyExc_RuntimeError, "transaction not active");
        return NULL;
    }

    if (self->web_transaction)
        rv = NRFunctionTrace_New(self->web_transaction, funcname, classname);
    else
        rv = NRFunctionTrace_New(NULL, NULL, NULL);

    if (rv == NULL)
        return NULL;

    return (PyObject *)rv;
}

static PyObject *NRWebTransaction_external_trace(
        NRWebTransactionObject *self, PyObject *args)
{
    NRExternalTraceObject *rv;

    const char *url = NULL;

    if (!PyArg_ParseTuple(args, "s:external_trace", &url))
        return NULL;

    if (!self->transaction_active) {
        PyErr_SetString(PyExc_RuntimeError, "transaction not active");
        return NULL;
    }

    if (self->web_transaction)
        rv = NRExternalTrace_New(self->web_transaction, url);
    else
        rv = NRExternalTrace_New(NULL, NULL);

    if (rv == NULL)
        return NULL;

    return (PyObject *)rv;
}

static PyObject *NRWebTransaction_memcache_trace(
        NRWebTransactionObject *self, PyObject *args)
{
    NRMemcacheTraceObject *rv;

    const char *metric_fragment = NULL;

    if (!PyArg_ParseTuple(args, "s:memcache_trace", &metric_fragment))
        return NULL;

    if (!self->transaction_active) {
        PyErr_SetString(PyExc_RuntimeError, "transaction not active");
        return NULL;
    }

    if (self->web_transaction)
        rv = NRMemcacheTrace_New(self->web_transaction, metric_fragment);
    else
        rv = NRMemcacheTrace_New(NULL, NULL);

    if (rv == NULL)
        return NULL;

    return (PyObject *)rv;
}

static PyObject *NRWebTransaction_database_trace(
        NRWebTransactionObject *self, PyObject *args)
{
    NRDatabaseTraceObject *rv;

    const char *sql = NULL;

    if (!PyArg_ParseTuple(args, "s:database_trace", &sql))
        return NULL;

    if (!self->transaction_active) {
        PyErr_SetString(PyExc_RuntimeError, "transaction not active");
        return NULL;
    }

    if (self->web_transaction)
        rv = NRDatabaseTrace_New(self->web_transaction, sql);
    else
        rv = NRDatabaseTrace_New(NULL, NULL);

    if (rv == NULL)
        return NULL;

    return (PyObject *)rv;
}

static PyObject *NRWebTransaction_runtime_error(
        NRWebTransactionObject *self, PyObject *args)
{
    nr_transaction_error* record;

    const char *error_message = NULL;
    const char *error_class = NULL;

    const char *stack_trace = NULL;

    const char *file_name = NULL;
    int line_number = 0;

    const char *source = NULL;

    PyObject *custom_parameters = NULL;

    if (!PyArg_ParseTuple(args, "s|zzzizO:runtime_error", &error_message,
                          &error_class, &stack_trace, &file_name,
                          &line_number, &source, &custom_parameters )) {
        return NULL;
    }

    if (custom_parameters && !PyDict_Check(custom_parameters)) {
        PyErr_SetString(PyExc_TypeError, "dictionary expected "
                        "for custom parameters");
        return NULL;
    }

    if (!self->transaction_active) {
        PyErr_SetString(PyExc_RuntimeError, "transaction not active");
        return NULL;
    }

    if (!error_class)
        error_class = "";

    record = nr_transaction_error__allocate(
            self->web_transaction, &(self->transaction_errors),
            "", 0, error_message, error_class, 0);

    if (file_name) {
        char buffer[123];

        sprintf(buffer, "%d", line_number);

        nr_param_array__set_string(record->params, "file_name", file_name);
        nr_param_array__set_string(record->params, "line_number", buffer);
    }

    if (source)
        nr_param_array__set_string(record->params, "source", source);

    if (stack_trace)
        nr_param_array__set_string(record->params, "stack_trace", stack_trace);

    if (custom_parameters && PyDict_Size(custom_parameters) > 0) {
        Py_ssize_t pos = 0;

        PyObject *key;
        PyObject *value;

        PyObject *key_as_string;
        PyObject *value_as_string;

        while (PyDict_Next(custom_parameters, &pos, &key, &value)) {
            key_as_string = PyObject_Str(key);

            if (!key_as_string)
               PyErr_Clear();

            value_as_string = PyObject_Str(value);

            if (!value_as_string)
               PyErr_Clear();

            if (key_as_string && value_as_string) {
                nr_param_array__set_string_in_hash_at(
                        record->params, "custom_parameters",
                        PyString_AsString(key_as_string),
                        PyString_AsString(value_as_string));
            }

            Py_XDECREF(key_as_string);
            Py_XDECREF(value_as_string);
        }
    }

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *NRWebTransaction_get_path(NRWebTransactionObject *self,
                                           void *closure)
{
    return PyString_FromString(self->web_transaction->path);
}

static int NRWebTransaction_set_path(NRWebTransactionObject *self,
                                     PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "can't delete URL path attribute");
        return -1;
    }

    if (!PyString_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected string for URL path");
        return -1;
    }

    nrfree(self->web_transaction->path);

    self->web_transaction->path = nrstrdup(PyString_AsString(value));

    return 0;
}

static PyObject *NRWebTransaction_get_response_code(
        NRWebTransactionObject *self, void *closure)
{
    return PyInt_FromLong(self->web_transaction->http_response_code);
}

static int NRWebTransaction_set_response_code(
        NRWebTransactionObject *self, PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "can't delete response code attribute");
        return -1;
    }

    if (!PyInt_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected integer for response code");
        return -1;
    }

    self->web_transaction->http_response_code = PyInt_AsLong(value);

    return 0;
}

static PyObject *NRWebTransaction_get_custom_parameters(
        NRWebTransactionObject *self, void *closure)
{
    Py_INCREF(self->custom_parameters);

    return self->custom_parameters;
}

static PyMethodDef NRWebTransaction_methods[] = {
    { "__enter__",  (PyCFunction)NRWebTransaction_enter,  METH_NOARGS, 0 },
    { "__exit__",   (PyCFunction)NRWebTransaction_exit,   METH_VARARGS, 0 },
    { "function_trace", (PyCFunction)NRWebTransaction_function_trace,   METH_VARARGS, 0 },
    { "external_trace", (PyCFunction)NRWebTransaction_external_trace,   METH_VARARGS, 0 },
    { "memcache_trace", (PyCFunction)NRWebTransaction_memcache_trace,   METH_VARARGS, 0 },
    { "database_trace", (PyCFunction)NRWebTransaction_database_trace,   METH_VARARGS, 0 },
    { "runtime_error", (PyCFunction)NRWebTransaction_runtime_error,   METH_VARARGS, 0 },
    { NULL, NULL }
};

static PyGetSetDef NRWebTransaction_getset[] = {
    { "path", (getter)NRWebTransaction_get_path, (setter)NRWebTransaction_set_path, 0 },
    { "response_code", (getter)NRWebTransaction_get_response_code, (setter)NRWebTransaction_set_response_code, 0 },
    { "custom_parameters", (getter)NRWebTransaction_get_custom_parameters, NULL, 0 },
    { NULL },
};

PyTypeObject NRWebTransaction_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.WebTransaction", /*tp_name*/
    sizeof(NRWebTransactionObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRWebTransaction_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    0,                      /*tp_call*/
    0,                      /*tp_str*/
    0,                      /*tp_getattro*/
    0,                      /*tp_setattro*/
    0,                      /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT,     /*tp_flags*/
    0,                      /*tp_doc*/
    0,                      /*tp_traverse*/
    0,                      /*tp_clear*/
    0,                      /*tp_richcompare*/
    0,                      /*tp_weaklistoffset*/
    0,                      /*tp_iter*/
    0,                      /*tp_iternext*/
    NRWebTransaction_methods, /*tp_methods*/
    0,                      /*tp_members*/
    NRWebTransaction_getset, /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    0,                      /*tp_init*/
    0,                      /*tp_alloc*/
    0,                      /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */
