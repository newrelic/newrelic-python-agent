/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_error_trace.h"

#include "py_utilities.h"

#include "structmember.h"

/* ------------------------------------------------------------------------- */

static PyObject *NRErrorTrace_new(PyTypeObject *type, PyObject *args,
                                  PyObject *kwds)
{
    NRErrorTraceObject *self;

    self = (NRErrorTraceObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->parent_transaction = NULL;
    self->ignore_errors = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRErrorTrace_init(NRErrorTraceObject *self, PyObject *args,
                                PyObject *kwds)
{
    NRTransactionObject *transaction = NULL;
    PyObject *ignore_errors = Py_None;

    static char *kwlist[] = { "transaction", "ignore_errors", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O!|O:ErrorTrace",
                                     kwlist, &NRTransaction_Type,
                                     &transaction, &ignore_errors)) {
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
     * Errors to ignored must implement sequence protocol.
     */

    if (ignore_errors != Py_None && !PySequence_Check(ignore_errors)) {
        PyErr_SetString(PyExc_TypeError,
                        "ignore_errors must be a sequence or None");
        return -1;
    }

    Py_INCREF(ignore_errors);
    Py_XDECREF(self->ignore_errors);
    self->ignore_errors = ignore_errors;

    /*
     * Keep reference to parent transaction to ensure that it
     * is not destroyed before any trace created against it.
     */

    Py_INCREF(transaction);
    Py_XDECREF(self->parent_transaction);
    self->parent_transaction = transaction;

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRErrorTrace_dealloc(NRErrorTraceObject *self)
{
    Py_XDECREF(self->parent_transaction);
    Py_XDECREF(self->ignore_errors);

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
        PyObject *method = NULL;
        PyObject *name = NULL;

        /*
         * Check whether this is an error type we should ignore.
         * Note that where the value is an instance type, the
         * name has to be obtained from the associated class
         * definition object. Only need do this of sequence of
         * errors to ignore has been defined.
         */

        if (self->ignore_errors != Py_None) {
            PyObject *module = NULL;
            PyObject *class = NULL;
            PyObject *object = NULL;

            class = PyObject_GetAttrString(value, "__class__");

            if (class) {
                module = PyObject_GetAttrString(class, "__module__");
                object = PyObject_GetAttrString(class, "__name__");

                if (module) {
                    name = PyString_FromFormat("%s.%s",
                                               PyString_AsString(module),
                                               PyString_AsString(object));
                }
                else if (object) {
                    Py_INCREF(object);
                    name = object;
                }
            }

            PyErr_Clear();

            Py_XDECREF(object);
            Py_XDECREF(class);
            Py_XDECREF(module);

            if (!name)
                name = PyString_FromString(Py_TYPE(value)->tp_name);

            if (PySequence_Contains(self->ignore_errors, name) == 1) {
                Py_DECREF(name);
                name = NULL;
            }

            PyErr_Clear();
        }

        if (self->ignore_errors == Py_None || name) {
            method = PyObject_GetAttrString(
                    (PyObject *)self->parent_transaction, "notice_error");
        }

        if (method) {
            PyObject *args = NULL;
            PyObject *result = NULL;

            args = PyTuple_Pack(3, type, value, traceback);
            result = PyObject_Call(method, args, NULL);

            Py_DECREF(args);
            Py_DECREF(method);
            Py_XDECREF(result);

            Py_XDECREF(name);
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

    self->dict = NULL;
    self->next_object = NULL;
    self->last_object = NULL;
    self->ignore_errors = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRErrorTraceWrapper_init(NRErrorTraceWrapperObject *self,
                                       PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;
    PyObject *ignore_errors = Py_None;

    PyObject *object = NULL;

    static char *kwlist[] = { "wrapped", "ignore_errors", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O|O:ErrorTraceWrapper",
                                     kwlist, &wrapped_object,
                                     &ignore_errors)) {
        return -1;
    }

    if (ignore_errors != Py_None && !PySequence_Check(ignore_errors)) {
        PyErr_SetString(PyExc_TypeError,
                        "ignore_errors must be a sequence or None");
        return -1;
    }

    Py_INCREF(wrapped_object);

    Py_XDECREF(self->dict);
    Py_XDECREF(self->next_object);
    Py_XDECREF(self->last_object);

    self->next_object = wrapped_object;
    self->last_object = NULL;

    object = PyObject_GetAttrString(wrapped_object, "__newrelic__");

    if (object) {
        Py_DECREF(object);

        object = PyObject_GetAttrString(wrapped_object, "__last_object__");

        if (object)
            self->last_object = object;
        else
            PyErr_Clear();
    }
    else
        PyErr_Clear();

    if (!self->last_object) {
        Py_INCREF(wrapped_object);
        self->last_object = wrapped_object;
    }

    object = PyObject_GetAttrString(self->last_object, "__dict__");

    if (object)
        self->dict = object;
    else
        PyErr_Clear();

    Py_INCREF(ignore_errors);
    Py_XDECREF(self->ignore_errors);
    self->ignore_errors = ignore_errors;

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRErrorTraceWrapper_dealloc(NRErrorTraceWrapperObject *self)
{
    Py_XDECREF(self->dict);

    Py_XDECREF(self->next_object);
    Py_XDECREF(self->last_object);

    Py_XDECREF(self->ignore_errors);

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
        return PyObject_Call(self->next_object, args, kwds);

    /* Create error trace context manager. */

    error_trace = PyObject_CallFunctionObjArgs((PyObject *)
            &NRErrorTrace_Type, current_transaction,
            self->ignore_errors, NULL);

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

    wrapped_result = PyObject_Call(self->next_object, args, kwds);

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

static PyObject *NRErrorTraceWrapper_get_next(
        NRErrorTraceWrapperObject *self, void *closure)
{
    if (!self->next_object) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    Py_INCREF(self->next_object);
    return self->next_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRErrorTraceWrapper_get_last(
        NRErrorTraceWrapperObject *self, void *closure)
{
    if (!self->last_object) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    Py_INCREF(self->last_object);
    return self->last_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRErrorTraceWrapper_get_marker(
        NRErrorTraceWrapperObject *self, void *closure)
{
    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRErrorTraceWrapper_get_module(
        NRErrorTraceWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    return PyObject_GetAttrString(self->last_object, "__module__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRErrorTraceWrapper_get_name(
        NRErrorTraceWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    return PyObject_GetAttrString(self->last_object, "__name__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRErrorTraceWrapper_get_doc(
        NRErrorTraceWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    return PyObject_GetAttrString(self->last_object, "__doc__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRErrorTraceWrapper_get_dict(
        NRErrorTraceWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    if (self->dict) {
        Py_INCREF(self->dict);
        return self->dict;
    }

    return PyObject_GetAttrString(self->last_object, "__dict__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRErrorTraceWrapper_getattro(
        NRErrorTraceWrapperObject *self, PyObject *name)
{
    PyObject *object = NULL;

    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    object = PyObject_GenericGetAttr((PyObject *)self, name);

    if (object)
        return object;

    PyErr_Clear();

    return PyObject_GetAttr(self->last_object, name);
}

/* ------------------------------------------------------------------------- */

static int NRErrorTraceWrapper_setattro(
        NRErrorTraceWrapperObject *self, PyObject *name, PyObject *value)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return -1;
    }

    return PyObject_SetAttr(self->last_object, name, value);
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
    { "__next_object__",    (getter)NRErrorTraceWrapper_get_next,
                            NULL, 0 },
    { "__last_object__",    (getter)NRErrorTraceWrapper_get_last,
                            NULL, 0 },
    { "__newrelic__",       (getter)NRErrorTraceWrapper_get_marker,
                            NULL, 0 },
    { "__module__",         (getter)NRErrorTraceWrapper_get_module,
                            NULL, 0 },
    { "__name__",           (getter)NRErrorTraceWrapper_get_name,
                            NULL, 0 },
    { "__doc__",            (getter)NRErrorTraceWrapper_get_doc,
                            NULL, 0 },
    { "__dict__",           (getter)NRErrorTraceWrapper_get_dict,
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
    (getattrofunc)NRErrorTraceWrapper_getattro, /*tp_getattro*/
    (setattrofunc)NRErrorTraceWrapper_setattro, /*tp_setattro*/
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
    offsetof(NRErrorTraceWrapperObject, dict), /*tp_dictoffset*/
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

    self->ignore_errors = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRErrorTraceDecorator_init(NRErrorTraceDecoratorObject *self,
                                         PyObject *args, PyObject *kwds)
{
    PyObject *ignore_errors = NULL;

    static char *kwlist[] = { "ignore_errors", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|O:ErrorTraceDecorator",
                                     kwlist, &ignore_errors)) {
        return -1;
    }

    if (ignore_errors != Py_None && !PySequence_Check(ignore_errors)) {
        PyErr_SetString(PyExc_TypeError,
                        "ignore_errors must be a sequence or None");
        return -1;
    }

    Py_INCREF(ignore_errors);
    Py_XDECREF(self->ignore_errors);
    self->ignore_errors = ignore_errors;

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRErrorTraceDecorator_dealloc(
        NRErrorTraceDecoratorObject *self)
{
    Py_XDECREF(self->ignore_errors);

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
            (PyObject *)&NRErrorTraceWrapper_Type, wrapped_object,
            self->ignore_errors, NULL);
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
