/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_in_function.h"

#include "py_utilities.h"

#include "structmember.h"

/* ------------------------------------------------------------------------- */

static PyObject *NRInFunctionWrapper_new(PyTypeObject *type, PyObject *args,
                                         PyObject *kwds)
{
    NRInFunctionWrapperObject *self;

    self = (NRInFunctionWrapperObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->dict = NULL;
    self->wrapped_object = NULL;
    self->function_object = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRInFunctionWrapper_init(NRInFunctionWrapperObject *self,
                                    PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;
    PyObject *function_object = Py_None;

    PyObject *wrapper = NULL;

    static char *kwlist[] = { "wrapped", "function", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OO:PassFunctionWrapper",
                                     kwlist, &wrapped_object,
                                     &function_object)) {
        return -1;
    }

    Py_INCREF(wrapped_object);
    Py_XDECREF(self->wrapped_object);
    self->wrapped_object = wrapped_object;

    Py_INCREF(function_object);
    Py_XDECREF(self->function_object);
    self->function_object = function_object;

    /* Perform equivalent of functools.wraps(). */

    wrapper = NRUtilities_UpdateWrapper((PyObject *)self, wrapped_object);

    if (!wrapper)
        return -1;

    Py_DECREF(wrapper);

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRInFunctionWrapper_dealloc(NRInFunctionWrapperObject *self)
{
    Py_XDECREF(self->dict);

    Py_XDECREF(self->wrapped_object);
    Py_XDECREF(self->function_object);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRInFunctionWrapper_call(NRInFunctionWrapperObject *self,
                                          PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_args = NULL;
    PyObject *wrapped_kwds = NULL;
    PyObject *wrapped_result = NULL;

    if (self->function_object != Py_None) {
        PyObject *function_result = NULL;

        function_result = PyObject_Call(self->function_object, args, kwds);

        if (!function_result)
            return NULL;

        if (!PyTuple_Check(function_result)) {
            PyErr_SetString(PyExc_TypeError, "result of in function must "
                            "be 2 tuple of args and kwds");
            return NULL;
        }

        if (PyTuple_Size(function_result) != 2) {
            PyErr_SetString(PyExc_TypeError, "result of in function must "
                            "be 2 tuple of args and kwds");
            return NULL;
        }

        wrapped_args = PyTuple_GetItem(function_result, 0);
        wrapped_kwds = PyTuple_GetItem(function_result, 1);

        if (!PyTuple_Check(wrapped_args)) {
            PyErr_SetString(PyExc_TypeError, "result of in function must "
                            "be 2 tuple of args and kwds");
            return NULL;
        }

        if (!PyDict_Check(wrapped_kwds)) {
            PyErr_SetString(PyExc_TypeError, "result of in function must "
                            "be 2 tuple of args and kwds");
            return NULL;
        }

        Py_INCREF(wrapped_args);
        Py_INCREF(wrapped_kwds);

        Py_DECREF(function_result);
    }
    else {
        Py_INCREF(args);
        wrapped_args = args;

        Py_XINCREF(kwds);
        wrapped_kwds = kwds;
    }

    wrapped_result = PyObject_Call(self->wrapped_object, wrapped_args,
                     wrapped_kwds);

    Py_DECREF(wrapped_args);
    Py_XDECREF(wrapped_kwds);

    return wrapped_result;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRInFunctionWrapper_get_wrapped(
        NRInFunctionWrapperObject *self, void *closure)
{
    Py_INCREF(self->wrapped_object);
    return self->wrapped_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRInFunctionWrapper_get_dict(
        NRInFunctionWrapperObject *self)
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

static int NRInFunctionWrapper_set_dict(
        NRInFunctionWrapperObject *self, PyObject *val)
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

static PyObject *NRInFunctionWrapper_descr_get(PyObject *function,
                                               PyObject *object,
                                               PyObject *type)
{
    if (object == Py_None)
        object = NULL;

    return PyMethod_New(function, object, type);
}

/* ------------------------------------------------------------------------- */

static PyGetSetDef NRInFunctionWrapper_getset[] = {
    { "__wrapped__",        (getter)NRInFunctionWrapper_get_wrapped,
                            NULL, 0 },
    { "__dict__",           (getter)NRInFunctionWrapper_get_dict,
                            (setter)NRInFunctionWrapper_set_dict, 0 },
    { NULL },
};

PyTypeObject NRInFunctionWrapper_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.PassFunctionWrapper", /*tp_name*/
    sizeof(NRInFunctionWrapperObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRInFunctionWrapper_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRInFunctionWrapper_call, /*tp_call*/
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
    NRInFunctionWrapper_getset, /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    NRInFunctionWrapper_descr_get, /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    offsetof(NRInFunctionWrapperObject, dict), /*tp_dictoffset*/
    (initproc)NRInFunctionWrapper_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRInFunctionWrapper_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRInFunctionDecorator_new(PyTypeObject *type,
                                           PyObject *args, PyObject *kwds)
{
    NRInFunctionDecoratorObject *self;

    self = (NRInFunctionDecoratorObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->function_object = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRInFunctionDecorator_init(NRInFunctionDecoratorObject *self,
                                      PyObject *args, PyObject *kwds)
{
    PyObject *function_object = Py_None;

    static char *kwlist[] = { "function", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:PassFunctionDecorator",
                                     kwlist, &function_object)) {
        return -1;
    }

    Py_INCREF(function_object);
    Py_XDECREF(self->function_object);
    self->function_object = function_object;

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRInFunctionDecorator_dealloc(NRInFunctionDecoratorObject *self)
{
    Py_XDECREF(self->function_object);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRInFunctionDecorator_call(
        NRInFunctionDecoratorObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;

    static char *kwlist[] = { "wrapped", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:PassFunctionDecorator",
                                     kwlist, &wrapped_object)) {
        return NULL;
    }

    return PyObject_CallFunctionObjArgs(
            (PyObject *)&NRInFunctionWrapper_Type, wrapped_object,
            self->function_object, NULL);
}

/* ------------------------------------------------------------------------- */

PyTypeObject NRInFunctionDecorator_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.PassFunctionDecorator", /*tp_name*/
    sizeof(NRInFunctionDecoratorObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRInFunctionDecorator_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRInFunctionDecorator_call, /*tp_call*/
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
    (initproc)NRInFunctionDecorator_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRInFunctionDecorator_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

/*
 * vim: set cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
