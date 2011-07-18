/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_version.h"

#include "py_application.h"

#include "py_settings.h"

#include "globals.h"
#include "logging.h"

#include "application.h"
#include "genericobject.h"
#include "harvest.h"
#include "metric_table.h"
#include "daemon_protocol.h"

#include "nr_version.h"

/* ------------------------------------------------------------------------- */

static PyObject *NRApplication_instances = NULL;

/* ------------------------------------------------------------------------- */

PyObject *NRApplication_Singleton(PyObject *args, PyObject *kwds)
{
    PyObject *result = NULL;
    PyObject *name = Py_None;

    PyObject *name_as_bytes = NULL;

    static char *kwlist[] = { "name", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|O:Application",
                                     kwlist, &name)) {
        return NULL;
    }

    if (!PyString_Check(name) && !PyUnicode_Check(name) &&
            name != Py_None) {
        PyErr_Format(PyExc_TypeError, "expected string, Unicode or None "
                        "for application name, found type '%s'",
                        name->ob_type->tp_name);
        return NULL;
    }

    /*
     * If this is the first application object instance we
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

    if (!NRApplication_instances)
        NRApplication_instances = PyDict_New();

    /*
     * The name can be optional. Where specified need to convert
     * a Unicode string to bytes. For None we use the default
     * application name as dictated by configuration.
     */

    if (PyString_Check(name)) {
        Py_INCREF(name);
        name_as_bytes = name;
    }
    else if (PyUnicode_Check(name)) {
        name_as_bytes = PyUnicode_AsUTF8String(name);
    }
    else {
        NRSettingsObject *settings = NULL;

        settings = (NRSettingsObject *)NRSettings_Singleton();

        name_as_bytes = PyString_FromString(settings->app_name);

        Py_DECREF(settings);
    }

    /*
     * Check for existing application object instance with the
     * specified name in the global dictionary and return it if
     * it exists.
     */

    result = PyDict_GetItem(NRApplication_instances, name_as_bytes);

    if (result) {
        Py_DECREF(name_as_bytes);
        Py_INCREF(result);
        return result;
    }

    /*
     * Otherwise we will need to create a new application object
     * instance, store it in the dictionary and then return it.
     */

#ifdef NR_AGENT_DEBUG
    nr__log(LOG_VERBOSEDEBUG, "create application %s",
            PyString_AsString(name_as_bytes));
#endif

    result = PyObject_CallFunctionObjArgs((PyObject *)&NRApplication_Type,
            name_as_bytes, NULL);

    PyDict_SetItem(NRApplication_instances, name_as_bytes, result);

    Py_DECREF(name_as_bytes);

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
     * An application initially represents an agent instance.
     * When additional names are added as secondaries it has the
     * affect of creating an agent cluster whereby metrics data
     * will be sent to the primary application as well as the
     * secondaries. Any server side configuration is sourced
     * from the primary application.
     */

    self->secondaries = PyDict_New();

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
    PyObject *name = NULL;

    const char **names = NULL;

    static char *kwlist[] = { "name", NULL };

    /*
     * This constructor should only be called from within the
     * agent code itself at a point where any Unicode string
     * used for application name has been converted to a normal
     * byte string. Thus only need to check for a string type
     * being supplied. We don't convert to a character string
     * because that would silently convert a Unicode string with
     * the default encoding if somehow called with one and we
     * are better noting that Unicode string wrongly got
     * through.
     */

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "S:Application",
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
     * Cache a reference to the internal agent client
     * application object instance. Internal agent code leaves
     * the application specific lock locked and so need to
     * unlock it.
     */

    names = (const char **)nrcalloc(1, sizeof(char *));
    names[0] = PyString_AsString(name);

    self->application = nr__find_or_create_application(names, 1);

    nrthread_mutex_unlock(&self->application->lock);

    /*
     * Any secondary application names, creating a cluster agent
     * will only be added later. We will thus need to go back and
     * update the application names associated with application
     * at that time.
     */

    PyDict_Clear(self->secondaries);

    /*
     * Markup what version of the Python agent wrapper is being
     * used. This displays in the agent configuration in the
     * RPM GUI.
     */

    nro__set_hash_string(self->application->appconfig,
            "library.version", NEWRELIC_AGENT_LIBRARY_VERSION);

    nro__set_hash_string(self->application->appconfig,
            "binding.language", "Python");
    nro__set_hash_string(self->application->appconfig,
            "binding.version", NEWRELIC_AGENT_LONG_VERSION);

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRApplication_dealloc(NRApplicationObject *self)
{
    /*
     * The destructor should never be required as
     * instances are always held in global dictionary
     * for subsequent lookup.
     */

    Py_TYPE(self)->tp_free(self);

    Py_DECREF(self->secondaries);
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

static PyObject *NRApplication_get_secondaries(NRApplicationObject *self,
                                               void *closure)
{
    if (!self->application) {
        PyErr_SetString(PyExc_TypeError, "application not initialized");
        return NULL;
    }

    return PyDict_Keys(self->secondaries);
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
        PyErr_SetString(PyExc_TypeError, "expected bool for enabled "
                        "attribute");
        return -1;
    }

    if (value == Py_True)
        self->enabled = 1;
    else
        self->enabled = 0;

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRApplication_get_running(NRApplicationObject *self,
                                           void *closure)
{
    int result = 0;

    nrthread_mutex_lock(&self->application->lock);
    result = self->application->agent_run_id != 0;
    nrthread_mutex_unlock(&self->application->lock);

    return PyBool_FromLong(result);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRApplication_activate(NRApplicationObject *self,
                                        PyObject *args, PyObject *kwds)
{
    nrdaemon_t *dconn = &nr_per_process_globals.nrdaemon;

    PyObject *sync_startup = Py_False;

    int retry_connection = 0;

    int active = 1;

    static char *kwlist[] = { "wait", NULL };

    if (!self->application) {
        PyErr_SetString(PyExc_TypeError, "application not initialized");
        return NULL;
    }

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|O!:activate", kwlist,
            &PyBool_Type, &sync_startup)) {
        return NULL;
    }

    /* Start harvest thread if not already running. */

    if (nr_per_process_globals.harvest_thread_valid == 0) {
#ifdef NR_AGENT_DEBUG
        nr__log(LOG_VERBOSEDEBUG, "start harvest thread");
#endif
        nr__create_harvest_thread();

        active = 0;
    }

    /* Trigger start for application if not already running. */

    nrthread_mutex_lock(&self->application->lock);
    if (self->application->agent_run_id == 0)
        retry_connection = 1;
    nrthread_mutex_unlock(&self->application->lock);

    if (retry_connection) {
        nr__start_communication(dconn, self->application,
                nr_per_process_globals.env, (sync_startup == Py_True));

        active = 0;
    }

    return PyBool_FromLong(active);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRApplication_shutdown(NRApplicationObject *self,
                                        PyObject *args, PyObject *kwds)
{
    nrdaemon_t *dconn = &nr_per_process_globals.nrdaemon;

    static char *kwlist[] = { NULL };

    if (!self->application) {
        PyErr_SetString(PyExc_TypeError, "application not initialized");
        return NULL;
    }

    if (!PyArg_ParseTupleAndKeywords(args, kwds, ":shutdown", kwlist))
        return NULL;

    nr__stop_communication(dconn, self->application);

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRApplication_map_to_secondary(NRApplicationObject *self,
                                                PyObject *args, PyObject *kwds)
{
    PyObject *name = NULL;

    PyObject *name_as_bytes = NULL;

    PyObject *keys = NULL;

    PyObject *iter = NULL;
    PyObject *item = NULL;

    int i = 0;

    static char *kwlist[] = { "name", NULL };

    if (!self->application) {
        PyErr_SetString(PyExc_TypeError, "application not initialized");
        return NULL;
    }

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:map_to_secondary",
                                     kwlist, &name)) {
        return NULL;
    }

    if (!PyString_Check(name) && !PyUnicode_Check(name)) {
        PyErr_Format(PyExc_TypeError, "expected string or Unicode "
                        "for secondary application name, found type '%s'",
                        name->ob_type->tp_name);
        return NULL;
    }

    if (PyUnicode_Check(name)) {
        name_as_bytes = PyUnicode_AsUTF8String(name);
    }
    else {
        Py_INCREF(name);
        name_as_bytes = name;
    }

    /*
     * Add name to list of secondaries. The collector enforces
     * a limit on the number. Currently that is 3, but do not
     * enforce that here.
     */

    PyDict_SetItem(self->secondaries, name_as_bytes, Py_True);

    /*
     * Update the list of all application names against the
     * application object.
     */

    for (i=1; i<self->application->nappnames; i++)
        nrfree(self->application->appnames[i]);

    nrfree(self->application->appnames);

    self->application->nappnames = PyDict_Size(self->secondaries)+1;
    self->application->appnames = (char **)nrcalloc(
            self->application->nappnames, sizeof(char *));

    self->application->appnames[0] = nrstrdup(self->application->appname);

    keys = PyDict_Keys(self->secondaries);
    iter = PyObject_GetIter(keys);

    i = 1;
    while ((item = PyIter_Next(iter)))
        self->application->appnames[i++] = nrstrdup(PyString_AsString(item));

    Py_DECREF(iter);
    Py_DECREF(keys);

    Py_DECREF(name_as_bytes);

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRApplication_record_metric(NRApplicationObject *self,
                                             PyObject *args, PyObject *kwds)
{
    PyObject *name = NULL;
    double value = 0.0;

    nrdaemon_t *dconn = &nr_per_process_globals.nrdaemon;

    NRSettingsObject *settings = NULL;

    int retry_connection = 0;

    static char *kwlist[] = { "name", "value", NULL };

    if (!self->application) {
        PyErr_SetString(PyExc_TypeError, "application not initialized");
        return NULL;
    }

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "Od:record_metric",
                                     kwlist, &name, &value)) {
        return NULL;
    }

    if (!PyString_Check(name) && !PyUnicode_Check(name)) {
        PyErr_Format(PyExc_TypeError, "expected string or Unicode "
                        "for custom metric name, found type '%s'",
                        name->ob_type->tp_name);
        return NULL;
    }

    /* Start harvest thread if not already running. */

    if (nr_per_process_globals.harvest_thread_valid == 0) {
#ifdef NR_AGENT_DEBUG
        nr__log(LOG_VERBOSEDEBUG, "start harvest thread");
#endif
        nr__create_harvest_thread();
    }

    /* Trigger start for application if not already running. */

    settings = (NRSettingsObject *)NRSettings_Singleton();

    nrthread_mutex_lock(&self->application->lock);
    if (self->application->agent_run_id == 0)
        retry_connection = 1;
    nrthread_mutex_unlock(&self->application->lock);

    if (retry_connection) {
        nr__start_communication(dconn, self->application,
                nr_per_process_globals.env,
                settings->daemon_settings->sync_startup);
    }

    /*
     * Don't record any custom metrics if the application has
     * been disabled or startup for application with local
     * daemon not completed.
     */

    nrthread_mutex_lock(&self->application->lock);

    if (self->application->agent_run_id != 0) {
        if (self->enabled) {
            if (PyUnicode_Check(name)) {
                PyObject *name_as_bytes = NULL;

                name_as_bytes = PyUnicode_AsUTF8String(name);

                if (!name_as_bytes)
                    return NULL;

                nr_metric_table__force_add_metric_double(
                        self->application->pending_harvest->metrics,
                        PyString_AsString(name_as_bytes), NULL, value);

                Py_DECREF(name_as_bytes);
            }
            else {
                nr_metric_table__force_add_metric_double(
                        self->application->pending_harvest->metrics,
                        PyString_AsString(name), NULL, value);
            }
        }
    }

    nrthread_mutex_unlock(&self->application->lock);

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyMethodDef NRApplication_methods[] = {
    { "activate",           (PyCFunction)NRApplication_activate,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "shutdown",           (PyCFunction)NRApplication_shutdown,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "map_to_secondary",   (PyCFunction)NRApplication_map_to_secondary,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "record_metric",      (PyCFunction)NRApplication_record_metric,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { NULL, NULL}
};

static PyGetSetDef NRApplication_getset[] = {
    { "name",               (getter)NRApplication_get_name,
                            NULL, 0 },
    { "secondaries",        (getter)NRApplication_get_secondaries,
                            NULL, 0 },
    { "enabled",            (getter)NRApplication_get_enabled,
                            (setter)NRApplication_set_enabled, 0 },
    { "running",            (getter)NRApplication_get_running,
                            NULL, 0 },
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
 * vim: set cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
