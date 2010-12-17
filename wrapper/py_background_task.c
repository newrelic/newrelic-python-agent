/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_background_task.h"
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

NRBackgroundTaskObject *NRBackgroundTask_New(nr_application *application,
                                             PyObject* path)
{
    NRBackgroundTaskObject *self;

    /*
     * Create transaction object and cache reference to the
     * internal agent client application object instance. Will
     * need the latter when doing some work arounds for lack
     * of thread safety in agent client code.
     */

    self = PyObject_New(NRBackgroundTaskObject, &NRBackgroundTask_Type);
    if (self == NULL)
        return NULL;

    self->application = application;

    if (application) {
        self->web_transaction = nr_web_transaction__allocate();

        self->web_transaction->http_response_code = 0;

        self->web_transaction->path_type = NR_PATH_TYPE_CUSTOM;
        self->web_transaction->path = nrstrdup(PyString_AsString(path));
        self->web_transaction->realpath = NULL;

        self->web_transaction->backgroundjob = 1;

        self->web_transaction->has_been_named = 1;
    }
    else
        self->web_transaction = NULL;

    self->custom_parameters = PyDict_New();

    return self;
}

static void NRBackgroundTask_dealloc(NRBackgroundTaskObject *self)
{
    Py_DECREF(self->custom_parameters);

    PyObject_Del(self);
}

static PyObject *NRBackgroundTask_enter(NRBackgroundTaskObject *self,
                                        PyObject *args)
{
    nr_node_header *save;

    if (!self->web_transaction) {
        Py_INCREF(self);
        return (PyObject *)self;
    }

    nr_node_header__record_starttime_and_push_current(
            (nr_node_header *)self->web_transaction, &save);

    Py_INCREF(self);
    return (PyObject *)self;
}

static PyObject *NRBackgroundTask_exit(NRBackgroundTaskObject *self,
                                       PyObject *args)
{
    PyObject *key;
    PyObject *value;

    Py_ssize_t pos = 0;

    PyObject *key_as_string;
    PyObject *value_as_string;

    if (!self->web_transaction) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    nr_node_header__record_stoptime_and_pop_current(
            (nr_node_header *)self->web_transaction, NULL);

    while (PyDict_Next(self->custom_parameters, &pos, &key, &value)) {
        key_as_string = PyObject_Str(key);

        if (!key_as_string)
           PyErr_Clear();

        value_as_string = PyObject_Str(value);

        if (!value_as_string)
           PyErr_Clear();

        if (key_as_string && value_as_string) {
            nr_param_array__set_string_in_hash_at(
                    self->web_transaction->params, "custom_parameters",
                    PyString_AsString(key_as_string),
                    PyString_AsString(value_as_string));
        }

        Py_XDECREF(key_as_string);
        Py_XDECREF(value_as_string);
    }

    pthread_mutex_lock(&(nr_per_process_globals.harvest_data_mutex));
    nr__switch_to_application(self->application);
    nr__distill_web_transaction_into_harvest_data(self->web_transaction);
    pthread_mutex_unlock(&(nr_per_process_globals.harvest_data_mutex));

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *NRBackgroundTask_function_trace(
        NRBackgroundTaskObject *self, PyObject *args)
{
    NRFunctionTraceObject *rv;

    const char *funcname = NULL;
    const char *classname = NULL;

    if (!PyArg_ParseTuple(args, "s|s:function_trace", &funcname, &classname))
        return NULL;

    if (self->web_transaction)
        rv = NRFunctionTrace_New(self->web_transaction, funcname, classname);
    else
        rv = NRFunctionTrace_New(NULL, NULL, NULL);

    if (rv == NULL)
        return NULL;

    return (PyObject *)rv;
}

static PyObject *NRBackgroundTask_external_trace(
        NRBackgroundTaskObject *self, PyObject *args)
{
    NRExternalTraceObject *rv;

    const char *url = NULL;

    if (!PyArg_ParseTuple(args, "s:external_trace", &url))
        return NULL;

    if (self->web_transaction)
        rv = NRExternalTrace_New(self->web_transaction, url);
    else
        rv = NRExternalTrace_New(NULL, NULL);

    if (rv == NULL)
        return NULL;

    return (PyObject *)rv;
}

static PyObject *NRBackgroundTask_memcache_trace(
        NRBackgroundTaskObject *self, PyObject *args)
{
    NRMemcacheTraceObject *rv;

    const char *metric_fragment = NULL;

    if (!PyArg_ParseTuple(args, "s:memcache_trace", &metric_fragment))
        return NULL;

    if (self->web_transaction)
        rv = NRMemcacheTrace_New(self->web_transaction, metric_fragment);
    else
        rv = NRMemcacheTrace_New(NULL, NULL);

    if (rv == NULL)
        return NULL;

    return (PyObject *)rv;
}

static PyObject *NRBackgroundTask_database_trace(
        NRBackgroundTaskObject *self, PyObject *args)
{
    NRDatabaseTraceObject *rv;

    const char *sql = NULL;

    if (!PyArg_ParseTuple(args, "s:database_trace", &sql))
        return NULL;

    if (self->web_transaction)
        rv = NRDatabaseTrace_New(self->web_transaction, sql);
    else
        rv = NRDatabaseTrace_New(NULL, NULL);

    if (rv == NULL)
        return NULL;

    return (PyObject *)rv;
}

static PyObject *NRBackgroundTask_get_path(NRBackgroundTaskObject *self,
                                           void *closure)
{
    return PyString_FromString(self->web_transaction->path);
}

static int NRBackgroundTask_set_path(NRBackgroundTaskObject *self,
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

static PyObject *NRBackgroundTask_get_custom_parameters(
        NRBackgroundTaskObject *self, void *closure)
{
    Py_INCREF(self->custom_parameters);

    return self->custom_parameters;
}

static PyMethodDef NRBackgroundTask_methods[] = {
    { "__enter__",  (PyCFunction)NRBackgroundTask_enter,  METH_NOARGS, 0 },
    { "__exit__",   (PyCFunction)NRBackgroundTask_exit,   METH_VARARGS, 0 },
    { "function_trace", (PyCFunction)NRBackgroundTask_function_trace,   METH_VARARGS, 0 },
    { "external_trace", (PyCFunction)NRBackgroundTask_external_trace,   METH_VARARGS, 0 },
    { "memcache_trace", (PyCFunction)NRBackgroundTask_memcache_trace,   METH_VARARGS, 0 },
    { "database_trace", (PyCFunction)NRBackgroundTask_database_trace,   METH_VARARGS, 0 },
    { NULL, NULL }
};

static PyGetSetDef NRBackgroundTask_getset[] = {
    { "path", (getter)NRBackgroundTask_get_path, (setter)NRBackgroundTask_set_path, 0 },
    { "custom_parameters", (getter)NRBackgroundTask_get_custom_parameters, NULL, 0 },
    { NULL },
};

PyTypeObject NRBackgroundTask_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.BackgroundTask", /*tp_name*/
    sizeof(NRBackgroundTaskObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRBackgroundTask_dealloc, /*tp_dealloc*/
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
    NRBackgroundTask_methods, /*tp_methods*/
    0,                      /*tp_members*/
    NRBackgroundTask_getset, /*tp_getset*/
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
