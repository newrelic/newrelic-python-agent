/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_database_trace.h"

#include "py_utilities.h"

#include "globals.h"

#include "genericobject.h"
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

    PyObject *sql = NULL;

    static char *kwlist[] = { "transaction", "sql", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O!O:DatabaseTrace",
                                     kwlist, &NRTransaction_Type,
                                     &transaction, &sql)) {
        return -1;
    }

    if (!PyString_Check(sql) && !PyUnicode_Check(sql)) {
        PyErr_Format(PyExc_TypeError, "expected string or Unicode for "
                     "sql, found type '%s'", sql->ob_type->tp_name);
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
        if (PyUnicode_Check(sql)) {
            PyObject *bytes = NULL;

            bytes = PyUnicode_AsUTF8String(sql);
            self->transaction_trace = nr_web_transaction__allocate_sql_node(
                    transaction->transaction, PyString_AsString(bytes));
            Py_DECREF(bytes);
        }
        else {
            self->transaction_trace = nr_web_transaction__allocate_sql_node(
                    transaction->transaction, PyString_AsString(sql));
        }
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
    nrapp_t *application;
    nr_web_transaction *transaction;
    nr_transaction_node *transaction_trace;

    transaction_trace = self->transaction_trace;

    if (!transaction_trace) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    nr_node_header__record_stoptime_and_pop_current(
            (nr_node_header *)transaction_trace, &self->saved_trace_node);

    /*
     * Generate the essential metrics for this node. We generate
     * them here because we might be about to throw this node
     * away if it's not slow enough to qualify for saving in the
     * call tree.
     */

    transaction = self->parent_transaction->transaction;
    application = self->parent_transaction->application->application;

    nr__generate_sql_metrics_for_node_1(transaction_trace, transaction);

    /* Record stack trace if this was a slow sql transaction. */

    if (!nr_node_header__delete_if_not_slow_enough(
            (nr_node_header *)transaction_trace, 1, transaction)) {
        if (nr_per_process_globals.slow_sql_stacktrace >= 0) {
            if (transaction_trace->header.times.duration >
                nr_per_process_globals.slow_sql_stacktrace) {

                PyObject *stack_trace = NULL;

                stack_trace = NRUtilities_FormatStackTrace();

                if (stack_trace) {
                    int i;

                    transaction_trace->u.s.stacktrace_params = nro__new(
                            NR_OBJECT_HASH);

                    for (i=0; i<PyList_Size(stack_trace); i++) {
                        nro__set_in_array_at(
                                transaction_trace->u.s.stacktrace_params,
                                "stack_trace", nro__new_string(
                                PyString_AsString(PyList_GetItem(
                                stack_trace, i))));
                    }
                    Py_DECREF(stack_trace);
                }
                else {
                    /*
                     * Obtaining the stack trace should never fail. In
                     * the unlikely event that it does, then propogate
                     * the error back through to the caller.
                     */

                    self->saved_trace_node = NULL;
                    return NULL;
                }
            }
        }

        nr_web_transaction__convert_from_stack_based(transaction_trace,
                transaction);
    }

    /* XXX Not doing specific recording of database errors. */

    self->saved_trace_node = NULL;

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

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

static PyObject *NRDatabaseTraceWrapper_new(PyTypeObject *type, PyObject *args,
                                           PyObject *kwds)
{
    NRDatabaseTraceWrapperObject *self;

    self = (NRDatabaseTraceWrapperObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->wrapped_object = NULL;
    self->sql = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRDatabaseTraceWrapper_init(NRDatabaseTraceWrapperObject *self,
                                       PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;
    PyObject *sql = NULL;

    static char *kwlist[] = { "wrapped", "sql", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OO:DatabaseTraceWrapper",
                                     kwlist, &wrapped_object, &sql)) {
        return -1;
    }

    Py_INCREF(wrapped_object);
    Py_XDECREF(self->wrapped_object);
    self->wrapped_object = wrapped_object;

    Py_INCREF(sql);
    Py_XDECREF(self->sql);
    self->sql = sql;

    /*
     * TODO This should set __module__, __name__, __doc__ and
     * update __dict__ to preserve introspection capabilities.
     * See @wraps in functools of recent Python versions.
     */

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRDatabaseTraceWrapper_dealloc(NRDatabaseTraceWrapperObject *self)
{
    Py_DECREF(self->wrapped_object);
    Py_DECREF(self->sql);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRDatabaseTraceWrapper_call(
        NRDatabaseTraceWrapperObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_result = NULL;

    PyObject *current_transaction = NULL;
    PyObject *database_trace = NULL;

    PyObject *instance_method = NULL;
    PyObject *method_args = NULL;
    PyObject *method_result = NULL;

    PyObject *sql = NULL;

    /*
     * If there is no current transaction then we can call
     * the wrapped function and return immediately.
     */

    current_transaction = NRTransaction_CurrentTransaction();

    if (!current_transaction)
        return PyObject_Call(self->wrapped_object, args, kwds);

    /* Create database trace context manager. */

    if (PyString_Check(self->sql) || PyUnicode_Check(self->sql)) {
        sql = self->sql;
        Py_INCREF(sql);
    }
    else {
        /*
         * Name if actually a callable function to provide the
         * name based on arguments supplied to wrapped function.
         */

        sql = PyObject_Call(self->sql, args, kwds);

        if (!sql)
            return NULL;
    }

    database_trace = PyObject_CallFunctionObjArgs((PyObject *)
            &NRDatabaseTrace_Type, current_transaction, sql, NULL);

    Py_DECREF(sql);

    /* Now call __enter__() on the context manager. */

    instance_method = PyObject_GetAttrString(database_trace, "__enter__");

    method_args = PyTuple_Pack(0);
    method_result = PyObject_Call(instance_method, method_args, NULL);

    if (!method_result)
        PyErr_WriteUnraisable(instance_method);
    else
        Py_DECREF(method_result);

    Py_DECREF(method_args);
    Py_DECREF(instance_method);

    /*
     * Now call the actual wrapped function with the original
     * position and keyword arguments.
     */

    wrapped_result = PyObject_Call(self->wrapped_object, args, kwds);

    /*
     * Now call __exit__() on the context manager. If the call
     * of the wrapped function is successful then pass all None
     * objects, else pass exception details.
     */

    instance_method = PyObject_GetAttrString(database_trace, "__exit__");

    if (wrapped_result) {
        method_args = PyTuple_Pack(3, Py_None, Py_None, Py_None);
        method_result = PyObject_Call(instance_method, method_args, NULL);

        if (!method_result)
            PyErr_WriteUnraisable(instance_method);
        else
            Py_DECREF(method_result);

        Py_DECREF(method_args);
        Py_DECREF(instance_method);
    }
    else {
        PyObject *type = NULL;
        PyObject *value = NULL;
        PyObject *traceback = NULL;

        PyErr_Fetch(&type, &value, &traceback);

        if (!value) {
            value = Py_None;
            Py_INCREF(value);
        }

        if (!traceback) {
            traceback = Py_None;
            Py_INCREF(traceback);
        }

        PyErr_NormalizeException(&type, &value, &traceback);

        method_args = PyTuple_Pack(3, type, value, traceback);
        method_result = PyObject_Call(instance_method, method_args, NULL);

        if (!method_result)
            PyErr_WriteUnraisable(instance_method);
        else
            Py_DECREF(method_result);

        Py_DECREF(method_args);
        Py_DECREF(instance_method);

        PyErr_Restore(type, value, traceback);
    }

    Py_DECREF(database_trace);

    return wrapped_result;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRDatabaseTraceWrapper_get_wrapped(
        NRDatabaseTraceWrapperObject *self, void *closure)
{
    Py_INCREF(self->wrapped_object);
    return self->wrapped_object;
}
 
/* ------------------------------------------------------------------------- */

static PyObject *NRDatabaseTraceWrapper_descr_get(PyObject *function,
                                                  PyObject *object,
                                                  PyObject *type)
{
    if (object == Py_None)
        object = NULL;

    return PyMethod_New(function, object, type);
}

/* ------------------------------------------------------------------------- */

static PyGetSetDef NRDatabaseTraceWrapper_getset[] = {
    { "__wrapped__",        (getter)NRDatabaseTraceWrapper_get_wrapped,
                            NULL, 0 },
    { NULL },
};

PyTypeObject NRDatabaseTraceWrapper_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.DatabaseTraceWrapper", /*tp_name*/
    sizeof(NRDatabaseTraceWrapperObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRDatabaseTraceWrapper_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRDatabaseTraceWrapper_call, /*tp_call*/
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
    0,                      /*tp_methods*/
    0,                      /*tp_members*/
    NRDatabaseTraceWrapper_getset, /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    NRDatabaseTraceWrapper_descr_get, /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)NRDatabaseTraceWrapper_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRDatabaseTraceWrapper_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRDatabaseTraceDecorator_new(PyTypeObject *type,
                                              PyObject *args, PyObject *kwds)
{
    NRDatabaseTraceDecoratorObject *self;

    self = (NRDatabaseTraceDecoratorObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->sql = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRDatabaseTraceDecorator_init(NRDatabaseTraceDecoratorObject *self,
                                         PyObject *args, PyObject *kwds)
{
    PyObject *sql = NULL;

    static char *kwlist[] = { "sql", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:DatabaseTraceDecorator",
                                     kwlist, &sql)) {
        return -1;
    }

    Py_INCREF(sql);
    Py_XDECREF(self->sql);
    self->sql = sql;

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRDatabaseTraceDecorator_dealloc(
        NRDatabaseTraceDecoratorObject *self)
{
    Py_DECREF(self->sql);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRDatabaseTraceDecorator_call(
        NRDatabaseTraceDecoratorObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;

    static char *kwlist[] = { "wrapped", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:DatabaseTraceDecorator",
                                     kwlist, &wrapped_object)) {
        return NULL;
    }

    return PyObject_CallFunctionObjArgs(
            (PyObject *)&NRDatabaseTraceWrapper_Type,
            wrapped_object, self->sql, NULL);
}

/* ------------------------------------------------------------------------- */

PyTypeObject NRDatabaseTraceDecorator_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.DatabaseTraceDecorator", /*tp_name*/
    sizeof(NRDatabaseTraceDecoratorObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRDatabaseTraceDecorator_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRDatabaseTraceDecorator_call, /*tp_call*/
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
    0,                      /*tp_methods*/
    0,                      /*tp_members*/
    0,                      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)NRDatabaseTraceDecorator_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRDatabaseTraceDecorator_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

/*
 * vim: set cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
