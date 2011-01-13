/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_config.h"

#include "py_application.h"
#include "py_background_task.h"
#include "py_web_transaction.h"

#include "globals.h"
#include "logging.h"

#include "application_funcs.h"
#include "daemon_protocol_funcs.h"
#include "generic_object_funcs.h"
#include "harvest_funcs.h"
#include "metric_table_funcs.h"

#include "php_newrelic.h"

/* ------------------------------------------------------------------------- */

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

/* ------------------------------------------------------------------------- */

static int NRApplication_instances = 0;

NRApplicationObject *NRApplication_New(const char *name)
{
    NRApplicationObject *self;

    /*
     * If this is the first instance, we need to (re)initialise
     * the harvest thread. It may be a reinitialisation where
     * all application objects had been destroyed and so the
     * harvest thread was shutdown. We hold the Python GIL here
     * so do not need to worry about separate mutex locking when
     * accessing global data.
     */

    if (!NRApplication_instances)
        nr__create_harvest_thread();

    NRApplication_instances++;

    /*
     * Create application object and cache reference to the
     * internal agent client application object instance. Will
     * need the latter when initiating a web transaction or
     * background task against this application instance as
     * need to pass that to those objects to work around thread
     * safety issue in PHP agent code when multithreading used.
     */

    self = PyObject_New(NRApplicationObject, &NRApplication_Type);
    if (self == NULL)
        return NULL;

    self->application = nr__find_or_create_application(name);

    /* Markup what version of the Python agent wrapper is being
     * used. This display in the agent configuration in the
     * RPM GUI.
     */

    nr_generic_object__add_string_to_hash(
            self->application->appconfig, "agent.binding",
            "Python");
    nr_generic_object__add_string_to_hash(
            self->application->appconfig, "agent.version",
            "library=" PHP_NEWRELIC_VERSION ", "
            "binding=" NR_PYTHON_AGENT_VERSION);

    /*
     * Monitoring of an application is enabled by default. If
     * this needs to be disabled, can be done by assigning the
     * 'enabled' attribute after creation. Note that the
     * 'enabled' flag is associated with the Python application
     * object and not the internal agent client application
     * object. This means that to have monitoring consistently
     * enabled/disabled across a whole interpreter, then Python
     * wrapper module needs to maintain a dictionary of named
     * application objects and return single instance for all
     * requests for application object for specific name and
     * not unique objects.
     */

    self->enabled = 1;

    return self;
}

static void NRApplication_dealloc(NRApplicationObject *self)
{
    /*
     * If this the last instance, we can force a harvest cycle
     * be run and then shutdown the harvest thread.  We hold the
     * Python GIL here so do not need to worry about separate
     * mutex locking when accessing global data but do release
     * the GIL when performing shutdown of the agent client code
     * as it may want to talk over the network.
     */

    NRApplication_instances--;

    if (!NRApplication_instances) {
        Py_BEGIN_ALLOW_THREADS
        nr__harvest_thread_body("shutdown");
        nr__stop_communication(&(nr_per_process_globals.daemon),
                               self->application);
        nr__destroy_harvest_thread();
        Py_END_ALLOW_THREADS
    }

    PyObject_Del(self);
}

static PyObject *NRApplication_get_name(NRApplicationObject *self,
                                        void *closure)
{
    return PyString_FromString(self->application->appname);
}

static PyObject *NRApplication_get_enabled(NRApplicationObject *self,
                                           void *closure)
{
    return PyBool_FromLong(self->enabled);
}

static int NRApplication_set_enabled(NRApplicationObject *self,
                                     PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "can't delete enabled attribute");
        return -1;
    }

    if (!PyBool_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected bool for enabled flag");
        return -1;
    }

    if (value == Py_True)
        self->enabled = 1;
    else
        self->enabled = 0;

    return 0;
}

static PyObject *NRApplication_web_transaction(NRApplicationObject *self,
                                               PyObject *args)
{
    NRWebTransactionObject *rv;

    PyObject *environ = NULL;

    if (!PyArg_ParseTuple(args, "O:web_transaction", &environ))
        return NULL;

    if (!PyDict_Check(environ)) {
        PyErr_Format(PyExc_TypeError, "expected WSGI environ dictionary");
        return NULL;
    }

    /*
     * If application monitoring has been disabled we want to
     * return a dummy web transaction object. Indicate that
     * by passing NULL for application.
     */

    if (self->enabled)
        rv = NRWebTransaction_New(self->application, environ);
    else
        rv = NRWebTransaction_New(NULL, NULL);

    if (rv == NULL)
        return NULL;

    return (PyObject *)rv;
}

static PyObject *NRApplication_background_task(NRApplicationObject *self,
                                               PyObject *args)
{
    NRBackgroundTaskObject *rv;

    PyObject *path = NULL;

    if (!PyArg_ParseTuple(args, "O:background_task", &path))
        return NULL;

    if (!PyString_Check(path)) {
        PyErr_Format(PyExc_TypeError, "expected string for URL path");
        return NULL;
    }

    /*
     * If application monitoring has been disabled we want to
     * return a dummy web transaction object. Indicate that
     * by passing NULL for application.
     */

    if (self->enabled)
        rv = NRBackgroundTask_New(self->application, path);
    else
        rv = NRBackgroundTask_New(NULL, NULL);

    if (rv == NULL)
        return NULL;

    return (PyObject *)rv;
}

static PyMethodDef NRApplication_methods[] = {
    { "web_transaction",   (PyCFunction)NRApplication_web_transaction,   METH_VARARGS, 0 },
    { "background_task",   (PyCFunction)NRApplication_background_task,   METH_VARARGS, 0 },
    { NULL, NULL}
};

static PyGetSetDef NRApplication_getset[] = {
    { "name", (getter)NRApplication_get_name, NULL, 0 },
    { "enabled", (getter)NRApplication_get_enabled, (setter)NRApplication_set_enabled, 0 },
    { NULL },
};

PyTypeObject NRApplication_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.Application", /*tp_name*/
    sizeof(NRApplicationObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRApplication_dealloc, /*tp_dealloc*/
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
    NRApplication_methods,  /*tp_methods*/
    0,                      /*tp_members*/
    NRApplication_getset,   /*tp_getset*/
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
