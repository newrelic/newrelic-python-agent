/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_settings.h"

#include "globals.h"
#include "logging.h"

#include "daemon_protocol.h"

/* ------------------------------------------------------------------------- */

static PyObject *NRTracerSettings_new(PyTypeObject *type, PyObject *args,
                                      PyObject *kwds)
{
    NRTracerSettingsObject *self;

    self = (NRTracerSettingsObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->transaction_threshold = 0;
    self->transaction_threshold_is_apdex_f = 1;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static void NRTracerSettings_dealloc(NRTracerSettingsObject *self)
{
    PyObject_Del(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRTracerSettings_get_enabled(NRTracerSettingsObject *self,
                                              void *closure)
{
    return PyBool_FromLong(nr_per_process_globals.tt_enabled);
}

/* ------------------------------------------------------------------------- */

static int NRTracerSettings_set_enabled(NRTracerSettingsObject *self,
                                        PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "can't delete enabled attribute");
        return -1;
    }

    if (!PyBool_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected bool for enabled");
        return -1;
    }

    if (value == Py_True)
        nr_per_process_globals.tt_enabled = 1;
    else
        nr_per_process_globals.tt_enabled = 0;

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRTracerSettings_get_threshold(NRTracerSettingsObject *self,
                                                void *closure)
{
    /*
     * We use a None value to indicate that threshold is being
     * calculated from apdex_f value.
     */

    /*
     * TODO Use of global for transaction_threshold is broken in the
     * PHP agent core. We need to workaround that by storing the
     * values in this object and updating transaction threshold
     * values on each request before distilling metrics. See
     * https://www.pivotaltracker.com/story/show/12771611.
     */

#if 0
    if (nr_per_process_globals.tt_threshold_is_apdex_f) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    return PyFloat_FromDouble((double)
            nr_per_process_globals.tt_threshold/1000000.0);
#endif

    if (self->transaction_threshold_is_apdex_f) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    return PyFloat_FromDouble((double)self->transaction_threshold/1000000.0);
}

/* ------------------------------------------------------------------------- */

static int NRTracerSettings_set_threshold(NRTracerSettingsObject *self,
                                          PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "can't delete transaction_threshold attribute");
        return -1;
    }

    if (value != Py_None && !PyFloat_Check(value) && !PyInt_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected int, float or None for "
                        "transaction_threshold");
        return -1;
    }

    /*
     * We use a None value to indicate that threshold should be
     * set based on apdex_f calculation. Need to ensure flag it
     * is apdex calculation so that retreival of value also
     * returns None in that case. For case where actual time
     * value is used, we accept value in seconds and PHP agent
     * core expects microseconds so need to adjust appropriately.
     */

    /*
     * TODO Use of global for transaction_threshold is broken in the
     * PHP agent core. We need to workaround that by storing the
     * values in this object and updating transaction threshold
     * values on each request before distilling metrics. See
     * https://www.pivotaltracker.com/story/show/12771611.
     */

#if 0
    if (value == Py_None) {
        nr_per_process_globals.tt_threshold_is_apdex_f = 1;
        nr_initialize_global_tt_threshold_from_apdex(NULL);
    }
    else {
        nr_per_process_globals.tt_threshold_is_apdex_f = 0;
        if (PyFloat_Check(value))
            nr_per_process_globals.tt_threshold = PyFloat_AsDouble(value) * 1000000;
        else
            nr_per_process_globals.tt_threshold = PyInt_AsLong(value) * 1000000;
        if (nr_per_process_globals.tt_threshold < 0)
            nr_per_process_globals.tt_threshold = 0;
    }
#endif

    if (value == Py_None) {
        self->transaction_threshold_is_apdex_f = 1;
        self->transaction_threshold = 0;
    }
    else {
        self->transaction_threshold_is_apdex_f = 0;
        if (PyFloat_Check(value))
            self->transaction_threshold = PyFloat_AsDouble(value) * 1000000;
        else
            self->transaction_threshold = PyInt_AsLong(value) * 1000000;
        if (self->transaction_threshold < 0)
            self->transaction_threshold = 0;
    }

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRTracerSettings_get_record_sql(NRTracerSettingsObject *self,
                                                 void *closure)
{
    return PyInt_FromLong(nr_per_process_globals.tt_recordsql);
}

/* ------------------------------------------------------------------------- */

static int NRTracerSettings_set_record_sql(NRTracerSettingsObject *self,
                                           PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "can't delete record_sql attribute");
        return -1;
    }

    if (!PyInt_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected int for record_sql");
        return -1;
    }

    nr_per_process_globals.tt_recordsql = PyInt_AsLong(value);

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRTracerSettings_get_sql_threshold(
        NRTracerSettingsObject *self, void *closure)
{
    return PyFloat_FromDouble((double)
            nr_per_process_globals.slow_sql_stacktrace/1000000.0);
}

/* ------------------------------------------------------------------------- */

static int NRTracerSettings_set_sql_threshold(NRTracerSettingsObject *self,
                                              PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "can't delete stack_trace_threshold attribute");
        return -1;
    }

    if (!PyFloat_Check(value) && !PyInt_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected int or float for "
                        "stack_transaction_threshold");
        return -1;
    }

    if (PyFloat_Check(value)) {
        nr_per_process_globals.slow_sql_stacktrace =
                PyFloat_AsDouble(value) * 1000000;
    }
    else {
        nr_per_process_globals.slow_sql_stacktrace =
                PyInt_AsLong(value) * 1000000;
    }

    if (nr_per_process_globals.slow_sql_stacktrace < 0)
        nr_per_process_globals.slow_sql_stacktrace = -1;

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRTracerSettings_get_expensive_limit(
        NRTracerSettingsObject *self, void *closure)
{
    return PyInt_FromLong(nr_per_process_globals.expensive_nodes_size);
}

/* ------------------------------------------------------------------------- */

static int NRTracerSettings_set_expensive_limit(NRTracerSettingsObject *self,
                                                PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "can't delete expensive_nodes_limit attribute");
        return -1;
    }

    if (!PyInt_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected int for "
                        "expensive_nodes_limit");
        return -1;
    }

    nr_per_process_globals.expensive_nodes_size = PyInt_AsLong(value);

    if (nr_per_process_globals.expensive_nodes_size < 1)
        nr_per_process_globals.expensive_nodes_size = 1;

    if (nr_per_process_globals.expensive_nodes_size >
            NR_EXPENSIVE_NODE_LIMIT_MAX) {
        nr_per_process_globals.expensive_nodes_size =
                NR_EXPENSIVE_NODE_LIMIT_MAX;
    }

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRTracerSettings_get_expensive_min(
        NRTracerSettingsObject *self, void *closure)
{
    return PyFloat_FromDouble((double)
            nr_per_process_globals.expensive_node_minimum/1000000.0);
}

/* ------------------------------------------------------------------------- */

static int NRTracerSettings_set_expensive_min(NRTracerSettingsObject *self,
                                              PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "can't delete expensive_node_minimum attribute");
        return -1;
    }

    if (!PyFloat_Check(value) && !PyInt_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected int or float for "
                        "expensive_node_minimum");
        return -1;
    }

    if (PyFloat_Check(value)) {
        nr_per_process_globals.expensive_node_minimum =
                PyFloat_AsDouble(value) * 1000000;
    }
    else {
        nr_per_process_globals.expensive_node_minimum =
                PyInt_AsLong(value) * 1000000;
    }

    if (nr_per_process_globals.expensive_node_minimum < 0)
        nr_per_process_globals.expensive_node_minimum = 0;

    return 0;
}

/* ------------------------------------------------------------------------- */

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

static PyMethodDef NRTracerSettings_methods[] = {
    { NULL, NULL }
};

static PyGetSetDef NRTracerSettings_getset[] = {
    { "enabled",            (getter)NRTracerSettings_get_enabled,
                            (setter)NRTracerSettings_set_enabled, 0 },
    { "transaction_threshold", (getter)NRTracerSettings_get_threshold,
                            (setter)NRTracerSettings_set_threshold, 0 },
    { "record_sql",         (getter)NRTracerSettings_get_record_sql,
                            (setter)NRTracerSettings_set_record_sql, 0 },
    { "stack_trace_threshold", (getter)NRTracerSettings_get_sql_threshold,
                            (setter)NRTracerSettings_set_sql_threshold, 0 },
    { "expensive_nodes_limit", (getter)NRTracerSettings_get_expensive_limit,
                            (setter)NRTracerSettings_set_expensive_limit, 0 },
    { "expensive_node_minimum", (getter)NRTracerSettings_get_expensive_min,
                            (setter)NRTracerSettings_set_expensive_min, 0 },
    { NULL },
};

PyTypeObject NRTracerSettings_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.TracerSettings", /*tp_name*/
    sizeof(NRTracerSettingsObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRTracerSettings_dealloc, /*tp_dealloc*/
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
    NRTracerSettings_methods,     /*tp_methods*/
    0,                      /*tp_members*/
    NRTracerSettings_getset,      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    0,                      /*tp_init*/
    0,                      /*tp_alloc*/
    NRTracerSettings_new,         /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRErrorsSettings_new(PyTypeObject *type, PyObject *args,
                                      PyObject *kwds)
{
    NRErrorsSettingsObject *self;

    self = (NRErrorsSettingsObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->ignore_errors = PyDict_New();

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static void NRErrorsSettings_dealloc(NRErrorsSettingsObject *self)
{
    Py_DECREF(self->ignore_errors);

    PyObject_Del(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRErrorsSettings_get_enabled(NRErrorsSettingsObject *self,
                                              void *closure)
{
    return PyBool_FromLong(nr_per_process_globals.tt_enabled);
}

/* ------------------------------------------------------------------------- */

static int NRErrorsSettings_set_enabled(NRErrorsSettingsObject *self,
                                        PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "can't delete enabled attribute");
        return -1;
    }

    if (!PyBool_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected bool for enabled");
        return -1;
    }

    if (value == Py_True)
        nr_per_process_globals.errors_enabled = 1;
    else
        nr_per_process_globals.errors_enabled = 0;

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRErrorsSettings_get_ignore_errors(
        NRErrorsSettingsObject *self, void *closure)
{
    return PyDict_Keys(self->ignore_errors);
}

/* ------------------------------------------------------------------------- */

static int NRErrorsSettings_set_ignore_errors(
        NRErrorsSettingsObject *self, PyObject *value)
{
    PyObject *iter = NULL;
    PyObject *item = NULL;

    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "can't delete ignore_errors attribute");
        return -1;
    }

    if (!PyList_Check(value)) {
        PyErr_SetString(PyExc_TypeError,
                        "expected list for ignore_errors");
        return -1;
    }

    PyDict_Clear(self->ignore_errors);

    iter = PyObject_GetIter(value);

    while ((item = PyIter_Next(iter)))
        PyDict_SetItem(self->ignore_errors, item, Py_None);

    Py_DECREF(iter);

    return 0;
}

/* ------------------------------------------------------------------------- */

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

static PyMethodDef NRErrorsSettings_methods[] = {
    { NULL, NULL }
};

static PyGetSetDef NRErrorsSettings_getset[] = {
    { "enabled",            (getter)NRErrorsSettings_get_enabled,
                            (setter)NRErrorsSettings_set_enabled, 0 },
    { "ignore_errors",      (getter)NRErrorsSettings_get_ignore_errors,
                            (setter)NRErrorsSettings_set_ignore_errors, 0 },
    { NULL },
};

PyTypeObject NRErrorsSettings_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.ErrorsSettings", /*tp_name*/
    sizeof(NRErrorsSettingsObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRErrorsSettings_dealloc, /*tp_dealloc*/
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
    NRErrorsSettings_methods,     /*tp_methods*/
    0,                      /*tp_members*/
    NRErrorsSettings_getset,      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    0,                      /*tp_init*/
    0,                      /*tp_alloc*/
    NRErrorsSettings_new,         /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRBrowserSettings_new(PyTypeObject *type, PyObject *args,
                                       PyObject *kwds)
{
    NRBrowserSettingsObject *self;

    self = (NRBrowserSettingsObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->auto_instrument = 1;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static void NRBrowserSettings_dealloc(NRBrowserSettingsObject *self)
{
    PyObject_Del(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRBrowserSettings_get_auto_instrument(
        NRBrowserSettingsObject *self, void *closure)
{
    return PyBool_FromLong(self->auto_instrument);
}

/* ------------------------------------------------------------------------- */

static int NRBrowserSettings_set_auto_instrument(
        NRBrowserSettingsObject *self, PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "can't delete auto_instrument attribute");
        return -1;
    }

    if (!PyBool_Check(value)) {
        PyErr_SetString(PyExc_TypeError,
                        "expected bool for auto_instrument");
        return -1;
    }

    if (value == Py_True)
        self->auto_instrument = 1;
    else
        self->auto_instrument = 0;

    return 0;
}

/* ------------------------------------------------------------------------- */

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

static PyMethodDef NRBrowserSettings_methods[] = {
    { NULL, NULL }
};

static PyGetSetDef NRBrowserSettings_getset[] = {
    { "auto_instrument",    (getter)NRBrowserSettings_get_auto_instrument,
                            (setter)NRBrowserSettings_set_auto_instrument, 0 },
    { NULL },
};

PyTypeObject NRBrowserSettings_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.DebugSettings", /*tp_name*/
    sizeof(NRBrowserSettingsObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRBrowserSettings_dealloc, /*tp_dealloc*/
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
    NRBrowserSettings_methods, /*tp_methods*/
    0,                      /*tp_members*/
    NRBrowserSettings_getset, /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    0,                      /*tp_init*/
    0,                      /*tp_alloc*/
    NRBrowserSettings_new,  /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRDebugSettings_new(PyTypeObject *type, PyObject *args,
                                     PyObject *kwds)
{
    NRDebugSettingsObject *self;

    self = (NRDebugSettingsObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static void NRDebugSettings_dealloc(NRDebugSettingsObject *self)
{
    PyObject_Del(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRDebugSettings_get_dump_metric_table(
        NRDebugSettingsObject *self, void *closure)
{
    return PyBool_FromLong(nr_per_process_globals.special_flags &
                           NR_SPECIAL_SHOW_METRIC_TABLE);
}

/* ------------------------------------------------------------------------- */

static int NRDebugSettings_set_dump_metric_table(
        NRDebugSettingsObject *self, PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "can't delete dump_metric_table attribute");
        return -1;
    }

    if (!PyBool_Check(value)) {
        PyErr_SetString(PyExc_TypeError,
                        "expected bool for dump_metric_table");
        return -1;
    }

    if (value == Py_True)
        nr_per_process_globals.special_flags |= NR_SPECIAL_SHOW_METRIC_TABLE;
    else
        nr_per_process_globals.special_flags &= ~NR_SPECIAL_SHOW_METRIC_TABLE;

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRDebugSettings_get_sql_parsing(
        NRDebugSettingsObject *self, void *closure)
{
    return PyBool_FromLong(nr_per_process_globals.special_flags &
                           NR_SPECIAL_NO_SQL_PARSING);
}

/* ------------------------------------------------------------------------- */

static int NRDebugSettings_set_sql_parsing(
        NRDebugSettingsObject *self, PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "can't delete sql_statement_parsing attribute");
        return -1;
    }

    if (!PyBool_Check(value)) {
        PyErr_SetString(PyExc_TypeError,
                        "expected bool for sql_statement_parsing");
        return -1;
    }

    /*
     * Note that the flag has opposite logic to what the bit mask
     * flag records.
     */

    if (value == Py_True)
        nr_per_process_globals.special_flags &= ~NR_SPECIAL_NO_SQL_PARSING;
    else
        nr_per_process_globals.special_flags |= NR_SPECIAL_NO_SQL_PARSING;

    return 0;
}

/* ------------------------------------------------------------------------- */

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

static PyMethodDef NRDebugSettings_methods[] = {
    { NULL, NULL }
};

static PyGetSetDef NRDebugSettings_getset[] = {
    { "dump_metric_table",  (getter)NRDebugSettings_get_dump_metric_table,
                            (setter)NRDebugSettings_set_dump_metric_table, 0 },
    { "sql_statement_parsing", (getter)NRDebugSettings_get_sql_parsing,
                            (setter)NRDebugSettings_set_sql_parsing, 0 },
    { NULL },
};

PyTypeObject NRDebugSettings_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.DebugSettings", /*tp_name*/
    sizeof(NRDebugSettingsObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRDebugSettings_dealloc, /*tp_dealloc*/
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
    NRDebugSettings_methods,     /*tp_methods*/
    0,                      /*tp_members*/
    NRDebugSettings_getset,      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    0,                      /*tp_init*/
    0,                      /*tp_alloc*/
    NRDebugSettings_new,         /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRSettingsObject_instance = NULL;

/* ------------------------------------------------------------------------- */

PyObject *NRSettings_Singleton(void)
{
    if (!NRSettingsObject_instance) {
        NRSettingsObject_instance = PyObject_CallFunctionObjArgs(
                (PyObject *)&NRSettings_Type, NULL);

        if (NRSettingsObject_instance == NULL)
            return NULL;
    }

    Py_INCREF(NRSettingsObject_instance);

    return NRSettingsObject_instance;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRSettings_new(PyTypeObject *type, PyObject *args,
                                PyObject *kwds)
{
    NRSettingsObject *self;

    self = (NRSettingsObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->config_file = Py_None;
    Py_INCREF(self->config_file);

    self->environment = Py_None;
    Py_INCREF(self->environment);

    self->tracer_settings = (NRTracerSettingsObject *)
            PyObject_CallFunctionObjArgs(
            (PyObject *)&NRTracerSettings_Type, NULL);
    self->errors_settings = (NRErrorsSettingsObject *)
            PyObject_CallFunctionObjArgs(
            (PyObject *)&NRErrorsSettings_Type, NULL);
    self->browser_settings = (NRBrowserSettingsObject *)
            PyObject_CallFunctionObjArgs(
            (PyObject *)&NRBrowserSettings_Type, NULL);
    self->debug_settings = (NRDebugSettingsObject *)
            PyObject_CallFunctionObjArgs(
            (PyObject *)&NRDebugSettings_Type, NULL);

    self->monitor_mode = 1;
    self->ignored_params = PyList_New(0);

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static void NRSettings_dealloc(NRSettingsObject *self)
{
    Py_DECREF(self->config_file);
    Py_DECREF(self->environment);

    Py_DECREF(self->ignored_params);

    Py_DECREF(self->tracer_settings);
    Py_DECREF(self->errors_settings);
    Py_DECREF(self->browser_settings);
    Py_DECREF(self->debug_settings);

    PyObject_Del(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRSettings_get_config_file(NRSettingsObject *self,
                                            void *closure)
{
    Py_INCREF(self->config_file);
    return self->config_file;
}

/* ------------------------------------------------------------------------- */

static int NRSettings_set_config_file(NRSettingsObject *self, PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "can't delete config_file attribute");
        return -1;
    }

    if (!PyString_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected string for config_file");
        return -1;
    }

    if (self->config_file != Py_None) {
        PyErr_SetString(PyExc_RuntimeError, "config_file already updated");
        return -1;
    }

    Py_INCREF(value);
    Py_DECREF(self->config_file);
    self->config_file = value;

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRSettings_get_environment(NRSettingsObject *self,
                                            void *closure)
{
    Py_INCREF(self->environment);
    return self->environment;
}

/* ------------------------------------------------------------------------- */

static int NRSettings_set_environment(NRSettingsObject *self, PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "can't delete environment attribute");
        return -1;
    }

    if (!PyString_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected string for environment");
        return -1;
    }

    if (self->environment != Py_None) {
        PyErr_SetString(PyExc_RuntimeError, "environment already updated");
        return -1;
    }

    Py_INCREF(value);
    Py_DECREF(self->environment);
    self->environment = value;

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRSettings_get_app_name(NRSettingsObject *self, void *closure)
{
    if (nr_per_process_globals.appname)
        return PyString_FromString(nr_per_process_globals.appname);

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static int NRSettings_set_app_name(NRSettingsObject *self, PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "can't delete app_name attribute");
        return -1;
    }

    if (!PyString_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected string for app_name");
        return -1;
    }

    if (nr_per_process_globals.appname)
        nrfree(nr_per_process_globals.appname);

    nr_per_process_globals.appname = nrstrdup(PyString_AsString(value));

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRSettings_get_monitor_mode(NRSettingsObject *self,
                                             void *closure)
{
    return PyBool_FromLong(self->monitor_mode);
}

/* ------------------------------------------------------------------------- */

static int NRSettings_set_monitor_mode(NRSettingsObject *self, PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "can't delete monitor_mode attribute");
        return -1;
    }

    if (!PyBool_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected bool for monitor_mode");
        return -1;
    }

    if (value == Py_True)
        self->monitor_mode = 1;
    else
        self->monitor_mode = 0;

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRSettings_get_log_file(NRSettingsObject *self, void *closure)
{
    if (nr_per_process_globals.logfilename)
        return PyString_FromString(nr_per_process_globals.logfilename);

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static int NRSettings_set_log_file(NRSettingsObject *self, PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "can't delete log_file attribute");
        return -1;
    }

    if (!PyString_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected string for log_file");
        return -1;
    }

    if (nr_per_process_globals.logfilename)
        nrfree(nr_per_process_globals.logfilename);

    nr_per_process_globals.logfilename = nrstrdup(PyString_AsString(value));

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRSettings_get_log_level(NRSettingsObject *self, void *closure)
{
    return PyInt_FromLong(nr_per_process_globals.loglevel);
}

/* ------------------------------------------------------------------------- */

static int NRSettings_set_log_level(NRSettingsObject *self, PyObject *value)
{
    int log_level;

    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "can't delete log_level attribute");
        return -1;
    }

    if (!PyInt_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected integer for log_level");
        return -1;
    }

    log_level = PyInt_AsLong(value);

    /*
     * Constrain value as LOG_DUMP level in PHP code appears to
     * have problems and can get stuck in loop dumping lots of
     * blank lines into log file.
     */

    if (log_level < LOG_ERROR || log_level > LOG_VERBOSEDEBUG) {
        PyErr_SetString(PyExc_ValueError, "log level out of range");
        return -1;
    }

    nr_per_process_globals.loglevel = log_level;

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRSettings_get_capture_params(NRSettingsObject *self,
                                               void *closure)
{
    return PyInt_FromLong(nr_per_process_globals.enable_params);
}

/* ------------------------------------------------------------------------- */

static int NRSettings_set_capture_params(NRSettingsObject *self,
                                         PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "can't delete capture_params attribute");
        return -1;
    }

    if (!PyBool_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected bool for capture_params");
        return -1;
    }

    if (value == Py_True)
        nr_per_process_globals.enable_params = 1;
    else
        nr_per_process_globals.enable_params = 0;

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRSettings_get_ignored_params(NRSettingsObject *self,
                                               void *closure)
{
    Py_INCREF(self->ignored_params);
    return self->ignored_params;
}

/* ------------------------------------------------------------------------- */

static int NRSettings_set_ignored_params(NRSettingsObject *self,
                                         PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "can't delete ignored_params attribute");
        return -1;
    }

    if (!PyList_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected list for ignored_params");
        return -1;
    }

    Py_INCREF(value);
    Py_DECREF(self->ignored_params);
    self->ignored_params = value;

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRSettings_get_transaction_tracer(NRSettingsObject *self,
                                                   void *closure)
{
    Py_INCREF(self->tracer_settings);
    return (PyObject *)self->tracer_settings;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRSettings_get_error_collector(NRSettingsObject *self,
                                                void *closure)
{
    Py_INCREF(self->errors_settings);
    return (PyObject *)self->errors_settings;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRSettings_get_browser_monitoring(NRSettingsObject *self,
                                                   void *closure)
{
    Py_INCREF(self->browser_settings);
    return (PyObject *)self->browser_settings;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRSettings_get_debug_settings(NRSettingsObject *self,
                                               void *closure)
{
    Py_INCREF(self->debug_settings);
    return (PyObject *)self->debug_settings;
}

/* ------------------------------------------------------------------------- */

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

static PyMethodDef NRSettings_methods[] = {
    { NULL, NULL }
};

static PyGetSetDef NRSettings_getset[] = {
    { "config_file",        (getter)NRSettings_get_config_file,
                            (setter)NRSettings_set_config_file, 0 },
    { "environment",        (getter)NRSettings_get_environment,
                            (setter)NRSettings_set_environment, 0 },
    { "app_name",           (getter)NRSettings_get_app_name,
                            (setter)NRSettings_set_app_name, 0 },
    { "monitor_mode",       (getter)NRSettings_get_monitor_mode,
                            (setter)NRSettings_set_monitor_mode, 0 },
    { "log_file",           (getter)NRSettings_get_log_file,
                            (setter)NRSettings_set_log_file, 0 },
    { "log_level",          (getter)NRSettings_get_log_level,
                            (setter)NRSettings_set_log_level, 0 },
    { "capture_params",     (getter)NRSettings_get_capture_params,
                            (setter)NRSettings_set_capture_params, 0 },
    { "ignored_params",     (getter)NRSettings_get_ignored_params,
                            (setter)NRSettings_set_ignored_params, 0 },
    { "transaction_tracer", (getter)NRSettings_get_transaction_tracer,
                            NULL, 0 },
    { "error_collector",    (getter)NRSettings_get_error_collector,
                            NULL, 0 },
    { "browser_monitoring", (getter)NRSettings_get_browser_monitoring,
                            NULL, 0 },
    { "debug",              (getter)NRSettings_get_debug_settings,
                            NULL, 0 },
    { NULL },
};

PyTypeObject NRSettings_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.Settings", /*tp_name*/
    sizeof(NRSettingsObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRSettings_dealloc, /*tp_dealloc*/
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
    NRSettings_methods,     /*tp_methods*/
    0,                      /*tp_members*/
    NRSettings_getset,      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    0,                      /*tp_init*/
    0,                      /*tp_alloc*/
    NRSettings_new,         /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

/*
 * vim: set cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
