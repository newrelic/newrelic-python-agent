/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_memcache_trace.h"

#include "globals.h"

#include "web_transaction.h"

/* ------------------------------------------------------------------------- */

static PyObject *NRMemcacheTrace_new(PyTypeObject *type, PyObject *args,
                                     PyObject *kwds)
{
    NRMemcacheTraceObject *self;

    /*
     * Allocate the transaction object and initialise it as per
     * normal.
     */

    self = (NRMemcacheTraceObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->parent_transaction = NULL;
    self->transaction_trace = NULL;
    self->saved_trace_node = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRMemcacheTrace_init(NRMemcacheTraceObject *self, PyObject *args,
                                PyObject *kwds)
{
    NRTransactionObject *transaction = NULL;

    const char *command = NULL;

    static char *kwlist[] = { "transaction", "command", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O!s:MemcacheTrace",
                                     kwlist, &NRTransaction_Type,
                                     &transaction, &command)) {
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
        self->transaction_trace = nr_web_transaction__allocate_memcache_node(
                transaction->transaction, command);
    }

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRMemcacheTrace_dealloc(NRMemcacheTraceObject *self)
{
    Py_XDECREF(self->parent_transaction);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRMemcacheTrace_enter(NRMemcacheTraceObject *self,
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

static PyObject *NRMemcacheTrace_exit(NRMemcacheTraceObject *self,
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

static PyMethodDef NRMemcacheTrace_methods[] = {
    { "__enter__",  (PyCFunction)NRMemcacheTrace_enter,  METH_NOARGS, 0 },
    { "__exit__",   (PyCFunction)NRMemcacheTrace_exit,   METH_VARARGS, 0 },
    { NULL, NULL }
};

static PyGetSetDef NRMemcacheTrace_getset[] = {
    { NULL },
};

PyTypeObject NRMemcacheTrace_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.MemcacheTrace", /*tp_name*/
    sizeof(NRMemcacheTraceObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRMemcacheTrace_dealloc, /*tp_dealloc*/
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
    NRMemcacheTrace_methods, /*tp_methods*/
    0,                      /*tp_members*/
    NRMemcacheTrace_getset, /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)NRMemcacheTrace_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRMemcacheTrace_new,    /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRMemcacheTraceWrapper_new(PyTypeObject *type, PyObject *args,
                                           PyObject *kwds)
{
    NRMemcacheTraceWrapperObject *self;

    self = (NRMemcacheTraceWrapperObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->wrapped_object = NULL;
    self->command = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRMemcacheTraceWrapper_init(NRMemcacheTraceWrapperObject *self,
                                       PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;
    PyObject *command = NULL;

    static char *kwlist[] = { "wrapped", "command", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OS:MemcacheTraceWrapper",
                                     kwlist, &wrapped_object, &command)) {
        return -1;
    }

    Py_INCREF(wrapped_object);
    Py_XDECREF(self->wrapped_object);
    self->wrapped_object = wrapped_object;

    Py_INCREF(command);
    Py_XDECREF(self->command);
    self->command = command;

    /*
     * TODO This should set __module__, __name__, __doc__ and
     * update __dict__ to preserve introspection capabilities.
     * See @wraps in functools of recent Python versions.
     */

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRMemcacheTraceWrapper_dealloc(NRMemcacheTraceWrapperObject *self)
{
    Py_DECREF(self->wrapped_object);
    Py_DECREF(self->command);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRMemcacheTraceWrapper_call(
        NRMemcacheTraceWrapperObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_result = NULL;

    PyObject *current_transaction = NULL;
    PyObject *memcache_trace = NULL;

    PyObject *instance_method = NULL;
    PyObject *method_args = NULL;
    PyObject *method_result = NULL;

    /*
     * If there is no current transaction then we can call
     * the wrapped function and return immediately.
     */

    current_transaction = NRTransaction_CurrentTransaction();

    if (!current_transaction)
        return PyObject_Call(self->wrapped_object, args, kwds);

    /* Create database trace context manager. */

    memcache_trace = PyObject_CallFunctionObjArgs((PyObject *)
            &NRMemcacheTrace_Type, current_transaction,
            self->command, NULL);

    /* Now call __enter__() on the context manager. */

    instance_method = PyObject_GetAttrString(memcache_trace, "__enter__");

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

    instance_method = PyObject_GetAttrString(memcache_trace, "__exit__");

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

    Py_DECREF(memcache_trace);

    return wrapped_result;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRMemcacheTraceWrapper_get_wrapped(
        NRMemcacheTraceWrapperObject *self, void *closure)
{
    Py_INCREF(self->wrapped_object);
    return self->wrapped_object;
}
 
/* ------------------------------------------------------------------------- */

static PyObject *NRMemcacheTraceWrapper_descr_get(PyObject *function,
                                                  PyObject *object,
                                                  PyObject *type)
{
    if (object == Py_None)
        object = NULL;

    return PyMethod_New(function, object, type);
}

/* ------------------------------------------------------------------------- */

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

static PyGetSetDef NRMemcacheTraceWrapper_getset[] = {
    { "__wrapped__",        (getter)NRMemcacheTraceWrapper_get_wrapped,
                            NULL, 0 },
    { NULL },
};

PyTypeObject NRMemcacheTraceWrapper_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.MemcacheTraceWrapper", /*tp_name*/
    sizeof(NRMemcacheTraceWrapperObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRMemcacheTraceWrapper_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRMemcacheTraceWrapper_call, /*tp_call*/
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
    NRMemcacheTraceWrapper_getset, /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    NRMemcacheTraceWrapper_descr_get, /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)NRMemcacheTraceWrapper_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRMemcacheTraceWrapper_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRMemcacheTraceDecorator_new(PyTypeObject *type,
                                              PyObject *args, PyObject *kwds)
{
    NRMemcacheTraceDecoratorObject *self;

    self = (NRMemcacheTraceDecoratorObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->command = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRMemcacheTraceDecorator_init(NRMemcacheTraceDecoratorObject *self,
                                         PyObject *args, PyObject *kwds)
{
    PyObject *command = NULL;

    static char *kwlist[] = { "command", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "S:MemcacheTraceDecorator",
                                     kwlist, &command)) {
        return -1;
    }

    Py_INCREF(command);
    Py_XDECREF(self->command);
    self->command = command;

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRMemcacheTraceDecorator_dealloc(
        NRMemcacheTraceDecoratorObject *self)
{
    Py_DECREF(self->command);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRMemcacheTraceDecorator_call(
        NRMemcacheTraceDecoratorObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;

    static char *kwlist[] = { "wrapped", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:MemcacheTraceDecorator",
                                     kwlist, &wrapped_object)) {
        return NULL;
    }

    return PyObject_CallFunctionObjArgs(
            (PyObject *)&NRMemcacheTraceWrapper_Type,
            wrapped_object, self->command, NULL);
}

/* ------------------------------------------------------------------------- */

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

PyTypeObject NRMemcacheTraceDecorator_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.MemcacheTraceDecorator", /*tp_name*/
    sizeof(NRMemcacheTraceDecoratorObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRMemcacheTraceDecorator_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRMemcacheTraceDecorator_call, /*tp_call*/
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
    (initproc)NRMemcacheTraceDecorator_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRMemcacheTraceDecorator_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
