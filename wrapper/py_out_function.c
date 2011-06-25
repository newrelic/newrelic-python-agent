/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_out_function.h"

#include "py_utilities.h"

#include "structmember.h"

/* ------------------------------------------------------------------------- */

static PyObject *NROutFunctionWrapper_new(PyTypeObject *type, PyObject *args,
                                          PyObject *kwds)
{
    NROutFunctionWrapperObject *self;

    self = (NROutFunctionWrapperObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->dict = NULL;
    self->next_object = NULL;
    self->last_object = NULL;
    self->function_object = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NROutFunctionWrapper_init(NROutFunctionWrapperObject *self,
                                     PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;
    PyObject *function_object = Py_None;

    PyObject *object = NULL;

    static char *kwlist[] = { "wrapped", "function", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OO:OutFunctionWrapper",
                                     kwlist, &wrapped_object,
                                     &function_object)) {
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

    Py_INCREF(function_object);
    Py_XDECREF(self->function_object);
    self->function_object = function_object;

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NROutFunctionWrapper_dealloc(NROutFunctionWrapperObject *self)
{
    Py_XDECREF(self->dict);

    Py_XDECREF(self->next_object);
    Py_XDECREF(self->last_object);

    Py_XDECREF(self->function_object);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NROutFunctionWrapper_call(NROutFunctionWrapperObject *self,
                                           PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_result = NULL;

    wrapped_result = PyObject_Call(self->next_object, args, kwds);

    if (!wrapped_result)
        return NULL;

    if (self->function_object != Py_None) {
        PyObject *function_result = NULL;

        function_result = PyObject_CallFunctionObjArgs(
                self->function_object, wrapped_result, NULL);

        Py_DECREF(wrapped_result);

        return function_result;
    }

    return wrapped_result;
}

/* ------------------------------------------------------------------------- */

static PyObject *NROutFunctionWrapper_get_next(
        NROutFunctionWrapperObject *self, void *closure)
{
    if (!self->next_object) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    Py_INCREF(self->next_object);
    return self->next_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *NROutFunctionWrapper_get_last(
        NROutFunctionWrapperObject *self, void *closure)
{
    if (!self->last_object) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    Py_INCREF(self->last_object);
    return self->last_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *NROutFunctionWrapper_get_marker(
        NROutFunctionWrapperObject *self, void *closure)
{
    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyObject *NROutFunctionWrapper_get_module(
        NROutFunctionWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    return PyObject_GetAttrString(self->last_object, "__module__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NROutFunctionWrapper_get_name(
        NROutFunctionWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    return PyObject_GetAttrString(self->last_object, "__name__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NROutFunctionWrapper_get_doc(
        NROutFunctionWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    return PyObject_GetAttrString(self->last_object, "__doc__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NROutFunctionWrapper_get_dict(
        NROutFunctionWrapperObject *self)
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

static PyObject *NROutFunctionWrapper_getattro(
        NROutFunctionWrapperObject *self, PyObject *name)
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

static int NROutFunctionWrapper_setattro(
        NROutFunctionWrapperObject *self, PyObject *name, PyObject *value)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return -1;
    }

    return PyObject_SetAttr(self->last_object, name, value);
}

/* ------------------------------------------------------------------------- */

static PyObject *NROutFunctionWrapper_descr_get(PyObject *function,
                                                PyObject *object,
                                                PyObject *type)
{
    if (object == Py_None)
        object = NULL;

    return PyMethod_New(function, object, type);
}

/* ------------------------------------------------------------------------- */

static PyGetSetDef NROutFunctionWrapper_getset[] = {
    { "__next_object__",    (getter)NROutFunctionWrapper_get_next,
                            NULL, 0 },
    { "__last_object__",    (getter)NROutFunctionWrapper_get_last,
                            NULL, 0 },
    { "__newrelic__",       (getter)NROutFunctionWrapper_get_marker,
                            NULL, 0 },
    { "__module__",         (getter)NROutFunctionWrapper_get_module,
                            NULL, 0 },
    { "__name__",           (getter)NROutFunctionWrapper_get_name,
                            NULL, 0 },
    { "__doc__",            (getter)NROutFunctionWrapper_get_doc,
                            NULL, 0 },
    { "__dict__",           (getter)NROutFunctionWrapper_get_dict,
                            NULL, 0 },
    { NULL },
};

PyTypeObject NROutFunctionWrapper_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.OutFunctionWrapper", /*tp_name*/
    sizeof(NROutFunctionWrapperObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NROutFunctionWrapper_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NROutFunctionWrapper_call, /*tp_call*/
    0,                      /*tp_str*/
    (getattrofunc)NROutFunctionWrapper_getattro, /*tp_getattro*/
    (setattrofunc)NROutFunctionWrapper_setattro, /*tp_setattro*/
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
    NROutFunctionWrapper_getset, /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    NROutFunctionWrapper_descr_get, /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    offsetof(NROutFunctionWrapperObject, dict), /*tp_dictoffset*/
    (initproc)NROutFunctionWrapper_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NROutFunctionWrapper_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NROutFunctionDecorator_new(PyTypeObject *type,
                                            PyObject *args, PyObject *kwds)
{
    NROutFunctionDecoratorObject *self;

    self = (NROutFunctionDecoratorObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->function_object = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NROutFunctionDecorator_init(NROutFunctionDecoratorObject *self,
                                       PyObject *args, PyObject *kwds)
{
    PyObject *function_object = Py_None;

    static char *kwlist[] = { "function", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:OutFunctionDecorator",
                                     kwlist, &function_object)) {
        return -1;
    }

    Py_INCREF(function_object);
    Py_XDECREF(self->function_object);
    self->function_object = function_object;

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NROutFunctionDecorator_dealloc(NROutFunctionDecoratorObject *self)
{
    Py_XDECREF(self->function_object);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NROutFunctionDecorator_call(
        NROutFunctionDecoratorObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;

    static char *kwlist[] = { "wrapped", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:OutFunctionDecorator",
                                     kwlist, &wrapped_object)) {
        return NULL;
    }

    return PyObject_CallFunctionObjArgs(
            (PyObject *)&NROutFunctionWrapper_Type, wrapped_object,
            self->function_object, NULL);
}

/* ------------------------------------------------------------------------- */

PyTypeObject NROutFunctionDecorator_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.OutFunctionDecorator", /*tp_name*/
    sizeof(NROutFunctionDecoratorObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NROutFunctionDecorator_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NROutFunctionDecorator_call, /*tp_call*/
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
    (initproc)NROutFunctionDecorator_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NROutFunctionDecorator_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

/*
 * vim: set cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
