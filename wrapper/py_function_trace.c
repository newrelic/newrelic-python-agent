/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_function_trace.h"

#include "py_utilities.h"

#include "globals.h"

#include "web_transaction.h"

#include "structmember.h"

/* ------------------------------------------------------------------------- */

static PyObject *NRFunctionTrace_new(PyTypeObject *type, PyObject *args,
                                     PyObject *kwds)
{
    NRFunctionTraceObject *self;

    /*
     * Allocate the transaction object and initialise it as per
     * normal.
     */

    self = (NRFunctionTraceObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->parent_transaction = NULL;
    self->transaction_trace = NULL;
    self->saved_trace_node = NULL;

    self->interesting = 1;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRFunctionTrace_init(NRFunctionTraceObject *self, PyObject *args,
                                PyObject *kwds)
{
    NRTransactionObject *transaction = NULL;

    PyObject *name = NULL;
    PyObject *scope = Py_None;
    PyObject *interesting = Py_True;

    static char *kwlist[] = { "transaction", "name", "scope",
                              "interesting", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O!O|OO!:FunctionTrace",
                                     kwlist, &NRTransaction_Type, &transaction,
                                     &name, &scope, &PyBool_Type,
                                     &interesting)) {
        return -1;
    }

    if (!PyString_Check(name) && !PyUnicode_Check(name)) {
        PyErr_Format(PyExc_TypeError, "expected string or Unicode for "
                     "name, found type '%s'", name->ob_type->tp_name);
        return -1;
    }

    if (!PyString_Check(scope) && !PyUnicode_Check(scope) &&
        scope != Py_None) {
        PyErr_Format(PyExc_TypeError, "scope argument must be string, "
                     "Unicode, or None, found type '%s'",
                     scope->ob_type->tp_name);
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
        PyObject *name_as_bytes = NULL;
        PyObject *scope_as_bytes = NULL;

        const char *name_as_char = NULL;
        const char *scope_as_char = NULL;

        if (PyUnicode_Check(name)) {
            name_as_bytes = PyUnicode_AsUTF8String(name);
            name_as_char = PyString_AsString(name_as_bytes);
        }
        else {
            Py_INCREF(name);
            name_as_bytes = name;
            name_as_char = PyString_AsString(name);
        }

        if (scope == Py_None) {
            scope_as_bytes = PyString_FromString("Function");
            scope_as_char = PyString_AsString(scope_as_bytes);
        }
        else if (PyUnicode_Check(scope)) {
            scope_as_bytes = PyUnicode_AsUTF8String(scope);
            scope_as_char = PyString_AsString(scope_as_bytes);
        }
        else {
            Py_INCREF(scope);
            scope_as_bytes = scope;
            scope_as_char = PyString_AsString(scope);
        }

        self->transaction_trace =
                nr_web_transaction__allocate_function_node(
                transaction->transaction, name_as_char, NULL,
                scope_as_char);

        Py_DECREF(name_as_bytes);
        Py_DECREF(scope_as_bytes);

        if (interesting == Py_True)
            self->interesting = 1;
        else
            self->interesting = 0;
    }

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRFunctionTrace_dealloc(NRFunctionTraceObject *self)
{
    Py_XDECREF(self->parent_transaction);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRFunctionTrace_enter(NRFunctionTraceObject *self,
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

static PyObject *NRFunctionTrace_exit(NRFunctionTraceObject *self,
                                       PyObject *args)
{
    nr_web_transaction *transaction;
    nr_transaction_node *transaction_trace;

    transaction_trace = self->transaction_trace;

    if (!transaction_trace) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    nr_node_header__record_stoptime_and_pop_current(
            (nr_node_header *)transaction_trace, &self->saved_trace_node);

    transaction = self->parent_transaction->transaction;

#if 0
    /*
     * XXX Not current needed. Leave as place marker in case
     * that changes.
     */

    nr__generate_function_metrics_for_node_1(transaction_trace, transaction);
#endif

    if (!nr_node_header__delete_if_not_slow_enough(
            (nr_node_header *)transaction_trace, self->interesting,
            transaction)) {
        nr_web_transaction__convert_from_stack_based(transaction_trace,
                transaction);
    }

    self->saved_trace_node = NULL;

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyMethodDef NRFunctionTrace_methods[] = {
    { "__enter__",  (PyCFunction)NRFunctionTrace_enter,  METH_NOARGS, 0 },
    { "__exit__",   (PyCFunction)NRFunctionTrace_exit,   METH_VARARGS, 0 },
    { NULL, NULL }
};

static PyGetSetDef NRFunctionTrace_getset[] = {
    { NULL },
};

PyTypeObject NRFunctionTrace_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.FunctionTrace", /*tp_name*/
    sizeof(NRFunctionTraceObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRFunctionTrace_dealloc, /*tp_dealloc*/
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
    NRFunctionTrace_methods, /*tp_methods*/
    0,                      /*tp_members*/
    NRFunctionTrace_getset, /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)NRFunctionTrace_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRFunctionTrace_new,    /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRFunctionTraceWrapper_new(PyTypeObject *type, PyObject *args,
                                           PyObject *kwds)
{
    NRFunctionTraceWrapperObject *self;

    self = (NRFunctionTraceWrapperObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->dict = NULL;
    self->wrapped_object = NULL;
    self->name = NULL;
    self->scope = NULL;
    self->interesting = 1;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRFunctionTraceWrapper_init(NRFunctionTraceWrapperObject *self,
                                       PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;

    PyObject *name = Py_None;
    PyObject *scope = Py_None;
    PyObject *interesting = Py_True;

    PyObject *wrapper = NULL;

    static char *kwlist[] = { "wrapped", "name", "scope",
                              "interesting", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O|OOO!:FunctionTraceWrapper",
                                     kwlist, &wrapped_object, &name, &scope,
                                     &PyBool_Type, &interesting)) {
        return -1;
    }

    Py_INCREF(wrapped_object);
    Py_XDECREF(self->wrapped_object);
    self->wrapped_object = wrapped_object;

    Py_INCREF(name);
    Py_XDECREF(self->name);
    self->name = name;

    Py_INCREF(scope);
    Py_XDECREF(self->scope);
    self->scope = scope;

    if (interesting == Py_True)
        self->interesting = 1;
    else
        self->interesting = 0;

    /* Perform equivalent of functools.wraps(). */

    wrapper = NRUtilities_UpdateWrapper((PyObject *)self, wrapped_object);

    if (!wrapper)
        return -1;

    Py_DECREF(wrapper);

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRFunctionTraceWrapper_dealloc(NRFunctionTraceWrapperObject *self)
{
    Py_XDECREF(self->dict);

    Py_XDECREF(self->wrapped_object);

    Py_XDECREF(self->name);
    Py_XDECREF(self->scope);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRFunctionTraceWrapper_call(
        NRFunctionTraceWrapperObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_result = NULL;

    PyObject *current_transaction = NULL;
    PyObject *function_trace = NULL;

    PyObject *instance_method = NULL;
    PyObject *method_args = NULL;
    PyObject *method_result = NULL;

    PyObject *name = NULL;

    /*
     * If there is no current transaction then we can call
     * the wrapped function and return immediately.
     */

    current_transaction = NRTransaction_CurrentTransaction();

    if (!current_transaction)
        return PyObject_Call(self->wrapped_object, args, kwds);

    /* Create function trace context manager. */

    if (self->name == Py_None) {
        name = NRUtilities_CallableName(self->wrapped_object,
                                        (PyObject *)self, args, ":");
    }
    else if (PyString_Check(self->name) || PyUnicode_Check(self->name)) {
        name = self->name;
        Py_INCREF(name);
    }
    else {
        /*
         * Name if actually a callable function to provide the
         * name based on arguments supplied to wrapped function.
         */

        name = PyObject_Call(self->name, args, kwds);

        if (!name)
            return NULL;
    }

    function_trace = PyObject_CallFunctionObjArgs((PyObject *)
            &NRFunctionTrace_Type, current_transaction, name,
            self->scope, self->interesting ? Py_True : Py_False, NULL);

    Py_DECREF(name);

    if (!function_trace)
        return NULL;

    /* Now call __enter__() on the context manager. */

    instance_method = PyObject_GetAttrString(function_trace, "__enter__");

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

    instance_method = PyObject_GetAttrString(function_trace, "__exit__");

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

    Py_DECREF(function_trace);

    return wrapped_result;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRFunctionTraceWrapper_get_wrapped(
        NRFunctionTraceWrapperObject *self, void *closure)
{
    Py_INCREF(self->wrapped_object);
    return self->wrapped_object;
}
 
/* ------------------------------------------------------------------------- */

static PyObject *NRFunctionTraceWrapper_get_dict(
        NRFunctionTraceWrapperObject *self)
{
    if (self->dict == NULL) {
        self->dict = PyDict_New();
        if (!self->dict)
            return NULL;
    }
    Py_INCREF(self->dict);
    return self->dict;
}

/* ------------------------------------------------------------------------- */

static int NRFunctionTraceWrapper_set_dict(
        NRFunctionTraceWrapperObject *self, PyObject *val)
{
    if (val == NULL) {
        PyErr_SetString(PyExc_TypeError, "__dict__ may not be deleted");
        return -1;
    }
    if (!PyDict_Check(val)) {
        PyErr_SetString(PyExc_TypeError, "__dict__ must be a dictionary");
        return -1;
    }
    Py_CLEAR(self->dict);
    Py_INCREF(val);
    self->dict = val;
    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRFunctionTraceWrapper_get_marker(
        NRFunctionTraceWrapperObject *self, void *closure)
{
    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRFunctionTraceWrapper_descr_get(PyObject *function,
                                                  PyObject *object,
                                                  PyObject *type)
{
    if (object == Py_None)
        object = NULL;

    return PyMethod_New(function, object, type);
}

/* ------------------------------------------------------------------------- */

static PyGetSetDef NRFunctionTraceWrapper_getset[] = {
    { "wrapped",            (getter)NRFunctionTraceWrapper_get_wrapped,
                            NULL, 0 },
    { "__dict__",           (getter)NRFunctionTraceWrapper_get_dict,
                            (setter)NRFunctionTraceWrapper_set_dict, 0 },
    { "__newrelic_wrapper__", (getter)NRFunctionTraceWrapper_get_marker,
                            NULL, 0 },
    { NULL },
};

PyTypeObject NRFunctionTraceWrapper_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.FunctionTraceWrapper", /*tp_name*/
    sizeof(NRFunctionTraceWrapperObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRFunctionTraceWrapper_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRFunctionTraceWrapper_call, /*tp_call*/
    0,                      /*tp_str*/
    PyObject_GenericGetAttr, /*tp_getattro*/
    PyObject_GenericSetAttr, /*tp_setattro*/
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
    NRFunctionTraceWrapper_getset, /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    NRFunctionTraceWrapper_descr_get, /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    offsetof(NRFunctionTraceWrapperObject, dict), /*tp_dictoffset*/
    (initproc)NRFunctionTraceWrapper_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRFunctionTraceWrapper_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRFunctionTraceDecorator_new(PyTypeObject *type,
                                              PyObject *args, PyObject *kwds)
{
    NRFunctionTraceDecoratorObject *self;

    self = (NRFunctionTraceDecoratorObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->name = NULL;
    self->scope = NULL;
    self->interesting = 1;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRFunctionTraceDecorator_init(NRFunctionTraceDecoratorObject *self,
                                         PyObject *args, PyObject *kwds)
{
    PyObject *name = Py_None;
    PyObject *scope = Py_None;
    PyObject *interesting = Py_True;

    static char *kwlist[] = { "name", "scope", "interesting", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|OOO!:FunctionTraceDecorator",
                                     kwlist, &name, &scope, &PyBool_Type,
                                     &interesting)) {
        return -1;
    }

    Py_INCREF(name);
    Py_XDECREF(self->name);
    self->name = name;

    Py_INCREF(scope);
    Py_XDECREF(self->scope);
    self->scope = scope;

    if (interesting == Py_True)
        self->interesting = 1;
    else
        self->interesting = 0;

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRFunctionTraceDecorator_dealloc(
        NRFunctionTraceDecoratorObject *self)
{
    Py_XDECREF(self->name);
    Py_XDECREF(self->scope);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRFunctionTraceDecorator_call(
        NRFunctionTraceDecoratorObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;

    static char *kwlist[] = { "wrapped", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:FunctionTraceDecorator",
                                     kwlist, &wrapped_object)) {
        return NULL;
    }

    return PyObject_CallFunctionObjArgs(
            (PyObject *)&NRFunctionTraceWrapper_Type, wrapped_object,
            self->name, self->scope, self->interesting ? Py_True : Py_False,
            NULL);
}

/* ------------------------------------------------------------------------- */

PyTypeObject NRFunctionTraceDecorator_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.FunctionTraceDecorator", /*tp_name*/
    sizeof(NRFunctionTraceDecoratorObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRFunctionTraceDecorator_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRFunctionTraceDecorator_call, /*tp_call*/
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
    (initproc)NRFunctionTraceDecorator_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRFunctionTraceDecorator_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

/*
 * vim: set cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
