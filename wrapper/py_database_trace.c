/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_database_trace.h"

#include "globals.h"

#include "web_transaction.h"

/* ------------------------------------------------------------------------- */

static PyObject *NRDatabaseTrace_new(PyTypeObject *type, PyObject *args,
                                     PyObject *kwds)
{
    NRDatabaseTraceObject *self;

    /*
     * Allocate the transaction object and initialise it as per
     * normal.
     */

    self = (NRDatabaseTraceObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->parent_transaction = NULL;
    self->transaction_trace = NULL;
    self->saved_trace_node = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRDatabaseTrace_init(NRDatabaseTraceObject *self, PyObject *args,
                                PyObject *kwds)
{
    NRTransactionObject *transaction = NULL;

    const char *sql = NULL;

    static char *kwlist[] = { "transaction", "sql", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O!s:DatabaseTrace",
                                     kwlist, &NRTransaction_Type,
                                     &transaction, &sql)) {
        return -1;
    }

    /*
     * Validate that this method hasn't been called previously.
     */

    if (self->parent_transaction) {
        PyErr_SetString(PyExc_TypeError, "trace already initialized");
        return -1;
    }

    /*
     * Validate that the parent transaction has been started.
     */

    if (transaction->transaction_state != NR_TRANSACTION_STATE_RUNNING) {
        PyErr_SetString(PyExc_RuntimeError, "transaction not active");
        return -1;
    }

    /*
     * Keep reference to parent transaction to ensure that it
     * is not destroyed before any trace created against it.
     */

    Py_INCREF(transaction);
    self->parent_transaction = transaction;

    /*
     * Don't need to create the inner agent transaction trace
     * node when executing against a dummy transaction.
     */

    if (transaction->transaction) {
        self->transaction_trace = nr_web_transaction__allocate_sql_node(
                transaction->transaction, sql, strlen(sql));
    }

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRDatabaseTrace_dealloc(NRDatabaseTraceObject *self)
{
    Py_XDECREF(self->parent_transaction);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRDatabaseTrace_enter(NRDatabaseTraceObject *self,
                                        PyObject *args)
{
    if (!self->transaction_trace) {
        Py_INCREF(self);
        return (PyObject *)self;
    }

    nr_node_header__record_starttime_and_push_current(
            (nr_node_header *)self->transaction_trace,
            &self->saved_trace_node);

    Py_INCREF(self);
    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRDatabaseTrace_exit(NRDatabaseTraceObject *self,
                                       PyObject *args)
{
    if (!self->transaction_trace) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    nr_node_header__record_stoptime_and_pop_current(
            (nr_node_header *)self->transaction_trace,
            &self->saved_trace_node);

    self->saved_trace_node = NULL;

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

static PyMethodDef NRDatabaseTrace_methods[] = {
    { "__enter__",  (PyCFunction)NRDatabaseTrace_enter,  METH_NOARGS, 0 },
    { "__exit__",   (PyCFunction)NRDatabaseTrace_exit,   METH_VARARGS, 0 },
    { NULL, NULL }
};

static PyGetSetDef NRDatabaseTrace_getset[] = {
    { NULL },
};

PyTypeObject NRDatabaseTrace_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.DatabaseTrace", /*tp_name*/
    sizeof(NRDatabaseTraceObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRDatabaseTrace_dealloc, /*tp_dealloc*/
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
    NRDatabaseTrace_methods, /*tp_methods*/
    0,                      /*tp_members*/
    NRDatabaseTrace_getset, /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)NRDatabaseTrace_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRDatabaseTrace_new,    /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
