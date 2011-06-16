/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_name_transaction.h"

#include "py_utilities.h"

#include "globals.h"

#include "structmember.h"

/* ------------------------------------------------------------------------- */

static PyObject *NRNameTransactionWrapper_new(PyTypeObject *type,
                                              PyObject *args,
                                              PyObject *kwds)
{
    NRNameTransactionWrapperObject *self;

    self = (NRNameTransactionWrapperObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->dict = NULL;
    self->wrapped_object = NULL;
    self->name = NULL;
    self->scope = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRNameTransactionWrapper_init(NRNameTransactionWrapperObject *self,
                                       PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;

    PyObject *name = Py_None;
    PyObject *scope = Py_None;

    PyObject *wrapper = NULL;

    static char *kwlist[] = { "wrapped", "name", "scope", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O|OO:NameTransactionWrapper",
                                     kwlist, &wrapped_object, &name, &scope)) {
        return -1;
    }

    if (!PyString_Check(scope) && !PyUnicode_Check(scope) &&
        scope != Py_None) {
        PyErr_Format(PyExc_TypeError, "scope argument must be string, "
                     "Unicode, or None, found type '%s'",
                     scope->ob_type->tp_name);
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

    /* Perform equivalent of functools.wraps(). */

    wrapper = NRUtilities_UpdateWrapper((PyObject *)self, wrapped_object);

    if (!wrapper)
        return -1;

    Py_DECREF(wrapper);

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRNameTransactionWrapper_dealloc(
        NRNameTransactionWrapperObject *self)
{
    Py_XDECREF(self->dict);

    Py_XDECREF(self->wrapped_object);

    Py_XDECREF(self->name);
    Py_XDECREF(self->scope);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRNameTransactionWrapper_call(
        NRNameTransactionWrapperObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *current_transaction = NULL;
    PyObject *name = NULL;

    /*
     * If there is no current transaction then we can call
     * the wrapped function and return immediately.
     */

    current_transaction = NRTransaction_CurrentTransaction();

    if (current_transaction) {
        PyObject *method = NULL;
        PyObject *result = NULL;

        method = PyObject_GetAttrString(current_transaction,
                                        "name_transaction");

        if (!method)
            return NULL;

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

        result = PyObject_CallFunctionObjArgs(method, name,
                                              self->scope, NULL);

        Py_DECREF(method);
        Py_DECREF(name);

        if (!result)
            return NULL;
    }

    return PyObject_Call(self->wrapped_object, args, kwds);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRNameTransactionWrapper_get_wrapped(
        NRNameTransactionWrapperObject *self, void *closure)
{
    Py_INCREF(self->wrapped_object);
    return self->wrapped_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRNameTransactionWrapper_get_dict(
        NRNameTransactionWrapperObject *self)
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

static int NRNameTransactionWrapper_set_dict(
        NRNameTransactionWrapperObject *self, PyObject *val)
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

static PyObject *NRNameTransactionWrapper_descr_get(PyObject *function,
                                                  PyObject *object,
                                                  PyObject *type)
{
    if (object == Py_None)
        object = NULL;

    return PyMethod_New(function, object, type);
}

/* ------------------------------------------------------------------------- */

static PyGetSetDef NRNameTransactionWrapper_getset[] = {
    { "__wrapped__",        (getter)NRNameTransactionWrapper_get_wrapped,
                            NULL, 0 },
    { "__dict__",           (getter)NRNameTransactionWrapper_get_dict,
                            (setter)NRNameTransactionWrapper_set_dict, 0 },
    { NULL },
};

PyTypeObject NRNameTransactionWrapper_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.NameTransactionWrapper", /*tp_name*/
    sizeof(NRNameTransactionWrapperObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRNameTransactionWrapper_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRNameTransactionWrapper_call, /*tp_call*/
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
    NRNameTransactionWrapper_getset, /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    NRNameTransactionWrapper_descr_get, /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    offsetof(NRNameTransactionWrapperObject, dict), /*tp_dictoffset*/
    (initproc)NRNameTransactionWrapper_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRNameTransactionWrapper_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRNameTransactionDecorator_new(PyTypeObject *type,
                                                PyObject *args, PyObject *kwds)
{
    NRNameTransactionDecoratorObject *self;

    self = (NRNameTransactionDecoratorObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->name = NULL;
    self->scope = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRNameTransactionDecorator_init(
        NRNameTransactionDecoratorObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *name = Py_None;
    PyObject *scope = Py_None;

    static char *kwlist[] = { "name", "scope", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds,
                                     "|OO:NameTransactionDecorator",
                                     kwlist, &name, &scope)) {
        return -1;
    }

    if (!PyString_Check(name) && !PyUnicode_Check(name) &&
        name != Py_None) {
        PyErr_Format(PyExc_TypeError, "name argument must be string, Unicode, "
                     "or None, found type '%s'", name->ob_type->tp_name);
        return -1;
    }

    if (!PyString_Check(scope) && !PyUnicode_Check(scope) &&
        scope != Py_None) {
        PyErr_Format(PyExc_TypeError, "scope argument must be string, Unicode, "
                     "or None, found type '%s'", scope->ob_type->tp_name);
        return -1;
    }

    Py_INCREF(name);
    Py_XDECREF(self->name);
    self->name = name;

    Py_INCREF(scope);
    Py_XDECREF(self->scope);
    self->scope = scope;

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRNameTransactionDecorator_dealloc(
        NRNameTransactionDecoratorObject *self)
{
    Py_XDECREF(self->name);
    Py_XDECREF(self->scope);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRNameTransactionDecorator_call(
        NRNameTransactionDecoratorObject *self,
        PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;

    static char *kwlist[] = { "wrapped", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:NameTransactionDecorator",
                                     kwlist, &wrapped_object)) {
        return NULL;
    }

    return PyObject_CallFunctionObjArgs(
            (PyObject *)&NRNameTransactionWrapper_Type,
            wrapped_object, self->name, self->scope, NULL);
}

/* ------------------------------------------------------------------------- */

PyTypeObject NRNameTransactionDecorator_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.NameTransactionDecorator", /*tp_name*/
    sizeof(NRNameTransactionDecoratorObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRNameTransactionDecorator_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRNameTransactionDecorator_call, /*tp_call*/
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
    (initproc)NRNameTransactionDecorator_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRNameTransactionDecorator_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

/*
 * vim: set cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
