/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_error_trace.h"

/* ------------------------------------------------------------------------- */

static PyObject *NRErrorTrace_new(PyTypeObject *type, PyObject *args,
                                  PyObject *kwds)
{
    NRErrorTraceObject *self;

    self = (NRErrorTraceObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->parent_transaction = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRErrorTrace_init(NRErrorTraceObject *self, PyObject *args,
                                PyObject *kwds)
{
    NRTransactionObject *transaction = NULL;

    static char *kwlist[] = { "transaction", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O!:ErrorTrace",
                                     kwlist, &NRTransaction_Type,
                                     &transaction)) {
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

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRErrorTrace_dealloc(NRErrorTraceObject *self)
{
    Py_XDECREF(self->parent_transaction);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRErrorTrace_enter(NRErrorTraceObject *self,
                                        PyObject *args)
{
    Py_INCREF(self);
    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRErrorTrace_exit(NRErrorTraceObject *self,
                                       PyObject *args)
{
    PyObject *type = NULL;
    PyObject *value = NULL;
    PyObject *traceback = NULL;

    if (!PyArg_ParseTuple(args, "OOO:__exit__", &type, &value, &traceback))
        return NULL;

    if (!self->parent_transaction->transaction) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    if (self->parent_transaction->transaction_state !=
        NR_TRANSACTION_STATE_RUNNING) {
        PyErr_SetString(PyExc_RuntimeError, "transaction not active");
        return NULL;
    }

    /*
     * Treat any exception passed in as being unhandled and
     * record details of exception against the transaction.
     * It is presumed that original error was not registered in
     * this context and so do not need to restore it when any
     * error here is cleared.
     */

    if (type != Py_None && value != Py_None && traceback != Py_None) {
        PyObject *object = NULL;

        object = PyObject_GetAttrString((PyObject *)self->parent_transaction,
                                        "notice_error");

        if (object) {
            PyObject *args = NULL;
            PyObject *result = NULL;

            args = PyTuple_Pack(3, type, value, traceback);
            result = PyObject_Call(object, args, NULL);

            Py_DECREF(args);
            Py_DECREF(object);
            Py_XDECREF(result);
        }
    }

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyMethodDef NRErrorTrace_methods[] = {
    { "__enter__",  (PyCFunction)NRErrorTrace_enter,  METH_NOARGS, 0 },
    { "__exit__",   (PyCFunction)NRErrorTrace_exit,   METH_VARARGS, 0 },
    { NULL, NULL }
};

PyTypeObject NRErrorTrace_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.ErrorTrace", /*tp_name*/
    sizeof(NRErrorTraceObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRErrorTrace_dealloc, /*tp_dealloc*/
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
    NRErrorTrace_methods, /*tp_methods*/
    0,                      /*tp_members*/
    0,                      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)NRErrorTrace_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRErrorTrace_new,       /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRErrorTraceWrapper_new(PyTypeObject *type, PyObject *args,
                                         PyObject *kwds)
{
    NRErrorTraceWrapperObject *self;

    self = (NRErrorTraceWrapperObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->wrapped_object = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRErrorTraceWrapper_init(NRErrorTraceWrapperObject *self,
                                       PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;

    static char *kwlist[] = { "wrapped", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:ErrorTraceWrapper",
                                     kwlist, &wrapped_object)) {
        return -1;
    }

    Py_INCREF(wrapped_object);
    Py_XDECREF(self->wrapped_object);
    self->wrapped_object = wrapped_object;

    /*
     * TODO This should set __module__, __name__, __doc__ and
     * update __dict__ to preserve introspection capabilities.
     * See @wraps in functools of recent Python versions.
     */

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRErrorTraceWrapper_dealloc(NRErrorTraceWrapperObject *self)
{
    Py_XDECREF(self->wrapped_object);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRErrorTraceWrapper_call(
        NRErrorTraceWrapperObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_result = NULL;

    PyObject *current_transaction = NULL;
    PyObject *error_trace = NULL;

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

    /* Create error trace context manager. */

    error_trace = PyObject_CallFunctionObjArgs((PyObject *)
            &NRErrorTrace_Type, current_transaction, NULL);

    /* Now call __enter__() on the context manager. */

    instance_method = PyObject_GetAttrString(error_trace, "__enter__");

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

    instance_method = PyObject_GetAttrString(error_trace, "__exit__");

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

    Py_DECREF(error_trace);

    return wrapped_result;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRErrorTraceWrapper_get_name(
        NRErrorTraceWrapperObject *self, void *closure)
{
    return PyObject_GetAttrString(self->wrapped_object, "__name__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRErrorTraceWrapper_get_module(
        NRErrorTraceWrapperObject *self, void *closure)
{
    return PyObject_GetAttrString(self->wrapped_object, "__module__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRErrorTraceWrapper_get_wrapped(
        NRErrorTraceWrapperObject *self, void *closure)
{
    Py_INCREF(self->wrapped_object);
    return self->wrapped_object;
}
 
/* ------------------------------------------------------------------------- */

static PyObject *NRErrorTraceWrapper_descr_get(PyObject *function,
                                                  PyObject *object,
                                                  PyObject *type)
{
    if (object == Py_None)
        object = NULL;

    return PyMethod_New(function, object, type);
}

/* ------------------------------------------------------------------------- */

static PyGetSetDef NRErrorTraceWrapper_getset[] = {
    { "__name__",           (getter)NRErrorTraceWrapper_get_name,
                            NULL, 0 },
    { "__module__",         (getter)NRErrorTraceWrapper_get_module,
                            NULL, 0 },
    { "__wrapped__",        (getter)NRErrorTraceWrapper_get_wrapped,
                            NULL, 0 },
    { NULL },
};

PyTypeObject NRErrorTraceWrapper_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.ErrorTraceWrapper", /*tp_name*/
    sizeof(NRErrorTraceWrapperObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRErrorTraceWrapper_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRErrorTraceWrapper_call, /*tp_call*/
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
    NRErrorTraceWrapper_getset, /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    NRErrorTraceWrapper_descr_get, /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)NRErrorTraceWrapper_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRErrorTraceWrapper_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRErrorTraceDecorator_new(PyTypeObject *type,
                                           PyObject *args, PyObject *kwds)
{
    NRErrorTraceDecoratorObject *self;

    self = (NRErrorTraceDecoratorObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRErrorTraceDecorator_init(NRErrorTraceDecoratorObject *self,
                                         PyObject *args, PyObject *kwds)
{
    static char *kwlist[] = { NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, ":ErrorTraceDecorator",
                                     kwlist)) {
        return -1;
    }

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRErrorTraceDecorator_dealloc(
        NRErrorTraceDecoratorObject *self)
{
    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRErrorTraceDecorator_call(
        NRErrorTraceDecoratorObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;

    static char *kwlist[] = { "wrapped", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:ErrorTraceDecorator",
                                     kwlist, &wrapped_object)) {
        return NULL;
    }

    return PyObject_CallFunctionObjArgs(
            (PyObject *)&NRErrorTraceWrapper_Type, wrapped_object, NULL);
}

/* ------------------------------------------------------------------------- */

PyTypeObject NRErrorTraceDecorator_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.ErrorTraceDecorator", /*tp_name*/
    sizeof(NRErrorTraceDecoratorObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRErrorTraceDecorator_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRErrorTraceDecorator_call, /*tp_call*/
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
    (initproc)NRErrorTraceDecorator_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRErrorTraceDecorator_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

/*
 * vim: set cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
