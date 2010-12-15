/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_web_transaction.h"

#include "globals.h"
#include "logging.h"

#include "application_funcs.h"
#include "harvest_funcs.h"
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
     * REQUEST_URI is not available.
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

    self->web_transaction = nr_web_transaction__allocate();

    self->web_transaction->path_type = path_type;
    self->web_transaction->path = nrstrdup(path);
    self->web_transaction->realpath = NULL;

    self->web_transaction->http_x_request_start = queue_start;

    return self;
}

static void NRWebTransaction_dealloc(NRWebTransactionObject *self)
{
    /*
     * Don't need to destroy the transaction object as
     * the harvest will automatically destroy it when it
     * is done.
     */
}

static PyObject *NRWebTransaction_enter(NRWebTransactionObject *self,
                                        PyObject *args)
{
    nr_node_header *save;

    nr_node_header__record_starttime_and_push_current(
            (nr_node_header *)self->web_transaction, &save);

    Py_INCREF(self);
    return (PyObject *)self;
}

static PyObject *NRWebTransaction_exit(NRWebTransactionObject *self,
                                       PyObject *args)
{
    nr_node_header__record_stoptime_and_pop_current(
            (nr_node_header *)self->web_transaction, NULL);

    self->web_transaction->http_response_code = 200;

    pthread_mutex_lock(&(nr_per_process_globals.harvest_data_mutex));
    nr__switch_to_application(self->application);
    nr__distill_web_transaction_into_harvest_data(self->web_transaction);
    pthread_mutex_unlock(&(nr_per_process_globals.harvest_data_mutex));

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

static PyMethodDef NRWebTransaction_methods[] = {
    { "__enter__",  (PyCFunction)NRWebTransaction_enter,  METH_NOARGS, 0 },
    { "__exit__",   (PyCFunction)NRWebTransaction_exit,   METH_VARARGS, 0 },
    { NULL, NULL }
};

static PyGetSetDef NRWebTransaction_getset[] = {
    { "path", (getter)NRWebTransaction_get_path, (setter)NRWebTransaction_set_path, 0 },
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
