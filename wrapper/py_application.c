/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_version.h"

#include "py_application.h"

#include "globals.h"

#include "application.h"
#include "genericobject.h"
#include "harvest.h"
#include "metric_table.h"

#include "nr_version.h"

/* ------------------------------------------------------------------------- */

static PyObject *NRApplication_instances = NULL;

/* ------------------------------------------------------------------------- */

PyObject *NRApplication_Singleton(PyObject *args, PyObject *kwds)
{
    PyObject *result = NULL;
    const char *name = NULL;

    static char *kwlist[] = { "name", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "s:Application",
                                     kwlist, &name)) {
        return NULL;
    }

    /*
     * If this is the first application object instance being
     * created, we need to initialise the harvest thread. This
     * is only done here when first application object created
     * so that we allow for global settings to be first set.
     *
     * In addition to starting the harvest thread, we also
     * create a global dictionary to hold all application object
     * instances keyed by name. Application object instances
     * will be cached in this dictionary and successive calls to
     * create an application object instance for a named
     * application that already exists will result in the
     * application object instance from the global dictionary
     * being returned instead of a new instance being created.
     * Because this global dictionary is shared between the main
     * Python interpreter and all of the sub interpreters, this
     * means that a specific application object instance may be
     * used at same time from different interpreters. As the
     * attributes of the application object are simple, this
     * sharing should be okay.
     */

    if (!NRApplication_instances) {
        nr__create_harvest_thread();
        NRApplication_instances = PyDict_New();
    }

    /*
     * Check for existing application object instance with the
     * specified name in the global dictionary and return it if
     * it exists.
     */

    result = PyDict_GetItemString(NRApplication_instances, name);

    if (result) {
        Py_INCREF(result);
        return result;
    }

    /*
     * Otherwise we will need to create a new application object
     * instance, store it in the dictionary and then return it.
     */

    result = PyObject_Call((PyObject *)&NRApplication_Type, args, kwds);

    PyDict_SetItemString(NRApplication_instances, name, result);

    /*
     * Force a harvest to be performed at this point. This will
     * ensure early notification is received by the local daemon
     * agent and details of the application passed on with the
     * application then being registered with the RPM server.
     * This hopefully allows local daemon to get back a response
     * from the RPM server in time for first true metrics
     * harvest. If it doesn't then the metrics data from the
     * first harvest can be lost because of the local daemon
     * agent not yet having received from the RPM server the
     * configuration options for this specific application. This
     * can be a problem with short lived processes. See issue
     * https://www.pivotaltracker.com/projects/???????.
     */

#if 0
    /*
     * XXX Don't force a harvest now as local daemon is supposed
     * to be making a greater effort to ensure that metric data
     * is not lost.
     */

    nr__harvest_thread_body(name);
#endif

    return result;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRApplication_new(PyTypeObject *type, PyObject *args,
                                   PyObject *kwds)
{
    NRApplicationObject *self;

    self = (NRApplicationObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    /*
     * The internal agent client application object isn't
     * initialised here but in the init method. Calling of the
     * init method is therefore mandatory and if not done by the
     * time a transaction is created or a custom metric
     * associated with the application then the transaction will
     * fail.
     */

    self->application = NULL;

    /*
     * Monitoring of an application is enabled by default. If
     * this needs to be disabled, can be done by assigning the
     * 'enabled' attribute after creation.
     */

    self->enabled = 1;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRApplication_init(NRApplicationObject *self, PyObject *args,
                              PyObject *kwds)
{
    const char *name = NULL;

    static char *kwlist[] = { "name", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "s:Application",
                                     kwlist, &name)) {
        return -1;
    }

    /*
     * Validate that this method hasn't been called previously.
     */

    if (self->application) {
        PyErr_SetString(PyExc_TypeError, "application already initialized");
        return -1;
    }

    /*
     * Cache reference to the internal agent client application
     * object instance. Will need the latter when initiating a
     * web transaction or background task against this
     * application instance as need to pass that to those
     * objects to work around thread safety issue in PHP agent
     * code when multithreading used.
     */

    self->application = nr__find_or_create_application(name);

    /*
     * Internal agent code leaves the application specific lock
     * locked and so need to unlock it.
     */

    nrthread_mutex_unlock(&self->application->lock);

    /*
     * Markup what version of the Python agent wrapper is being
     * used. This displays in the agent configuration in the
     * RPM GUI.
     */

    nro__set_hash_string(self->application->appconfig,
            "binding.language", "Python");
    nro__set_hash_string(self->application->appconfig,
            "binding.version", NEWRELIC_PYTHON_AGENT_VERSION);

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRApplication_dealloc(NRApplicationObject *self)
{
    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRApplication_get_name(NRApplicationObject *self,
                                        void *closure)
{
    if (!self->application) {
        PyErr_SetString(PyExc_TypeError, "application not initialized");
        return NULL;
    }

    return PyString_FromString(self->application->appname);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRApplication_get_enabled(NRApplicationObject *self,
                                           void *closure)
{
    return PyBool_FromLong(self->enabled);
}

/* ------------------------------------------------------------------------- */

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

/* ------------------------------------------------------------------------- */

static PyObject *NRApplication_custom_metric(NRApplicationObject *self,
                                             PyObject *args, PyObject *kwds)
{
    const char *key = NULL;
    double value = 0.0;

    static char *kwlist[] = { "key", "value", NULL };

    if (!self->application) {
        PyErr_SetString(PyExc_TypeError, "application not initialized");
        return NULL;
    }

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "sd:custom_metric",
                                     kwlist, &key, &value)) {
        return NULL;
    }

    /*
     * Don't record any custom metrics if the application has
     * been disabled.
     */

    if (self->enabled) {
        nrthread_mutex_lock(&self->application->lock);
        nr_metric_table__add_metric_double(
                self->application->pending_harvest->metrics, key, NULL, value);
        nrthread_mutex_unlock(&self->application->lock);
    }

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

static PyMethodDef NRApplication_methods[] = {
    { "custom_metric",      (PyCFunction)NRApplication_custom_metric,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { NULL, NULL}
};

static PyGetSetDef NRApplication_getset[] = {
    { "name",               (getter)NRApplication_get_name,
                            NULL, 0 },
    { "enabled",            (getter)NRApplication_get_enabled,
                            (setter)NRApplication_set_enabled, 0 },
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
    (initproc)NRApplication_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRApplication_new,      /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
