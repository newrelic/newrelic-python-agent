/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_post_function.h"

#include "py_utilities.h"

#include "structmember.h"

/* ------------------------------------------------------------------------- */

static PyObject *NRPostFunctionWrapper_new(PyTypeObject *type, PyObject *args,
                                           PyObject *kwds)
{
    NRPostFunctionWrapperObject *self;

    self = (NRPostFunctionWrapperObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->dict = NULL;
    self->next_object = NULL;
    self->last_object = NULL;
    self->function_object = NULL;
    self->run_once = 0;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRPostFunctionWrapper_init(NRPostFunctionWrapperObject *self,
                                      PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;
    PyObject *function_object = NULL;
    PyObject *run_once = NULL;

    PyObject *object = NULL;

    static char *kwlist[] = { "wrapped", "post_function", "run_once", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OO|O!:PostFunctionWrapper",
                                     kwlist, &wrapped_object, &function_object,
                                     &PyBool_Type, &run_once)) {
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

    self->run_once = (run_once == Py_True);

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRPostFunctionWrapper_dealloc(NRPostFunctionWrapperObject *self)
{
    Py_XDECREF(self->dict);

    Py_XDECREF(self->next_object);
    Py_XDECREF(self->last_object);

    Py_XDECREF(self->function_object);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRPostFunctionWrapper_call(NRPostFunctionWrapperObject *self,
                                            PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_result = NULL;

    PyObject *type = NULL;
    PyObject *value = NULL;
    PyObject *traceback = NULL;

    wrapped_result = PyObject_Call(self->next_object, args, kwds);

    /*
     * TODO Should the post function even be called if an error
     * occurs in the wrapped function. The post function would
     * need to deal with the problem that an error occurred but
     * it would know when called except by detecting that the
     * data that may have been set up by the wrapped function
     * isn't present.
     */

    if (self->function_object) {
        PyObject *function_result = NULL;

        if (!wrapped_result)
            PyErr_Fetch(&type, &value, &traceback);

        function_result = PyObject_Call(self->function_object, args, kwds);

        if (!function_result) {
            if (wrapped_result) {
                Py_DECREF(wrapped_result);
                return NULL;
            }
            else
              PyErr_WriteUnraisable(self->function_object);
        }
        else
            Py_DECREF(function_result);

        if (self->run_once) {
            self->run_once = 0;
            Py_DECREF(self->function_object);
            self->function_object = NULL;
        }

        if (!wrapped_result)
            PyErr_Restore(type, value, traceback);
    }

    return wrapped_result;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRPostFunctionWrapper_get_next(
        NRPostFunctionWrapperObject *self, void *closure)
{
    if (!self->next_object) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    Py_INCREF(self->next_object);
    return self->next_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRPostFunctionWrapper_get_last(
        NRPostFunctionWrapperObject *self, void *closure)
{
    if (!self->last_object) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    Py_INCREF(self->last_object);
    return self->last_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRPostFunctionWrapper_get_marker(
        NRPostFunctionWrapperObject *self, void *closure)
{
    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRPostFunctionWrapper_get_module(
        NRPostFunctionWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    return PyObject_GetAttrString(self->last_object, "__module__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRPostFunctionWrapper_get_name(
        NRPostFunctionWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    return PyObject_GetAttrString(self->last_object, "__name__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRPostFunctionWrapper_get_doc(
        NRPostFunctionWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    return PyObject_GetAttrString(self->last_object, "__doc__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRPostFunctionWrapper_get_dict(
        NRPostFunctionWrapperObject *self)
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

static PyObject *NRPostFunctionWrapper_getattro(
        NRPostFunctionWrapperObject *self, PyObject *name)
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

static int NRPostFunctionWrapper_setattro(
        NRPostFunctionWrapperObject *self, PyObject *name, PyObject *value)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return -1;
    }

    return PyObject_SetAttr(self->last_object, name, value);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRPostFunctionWrapper_descr_get(PyObject *function,
                                                PyObject *object,
                                                PyObject *type)
{
    if (object == Py_None)
        object = NULL;

    return PyMethod_New(function, object, type);
}

/* ------------------------------------------------------------------------- */

static PyGetSetDef NRPostFunctionWrapper_getset[] = {
    { "__next_object__",    (getter)NRPostFunctionWrapper_get_next,
                            NULL, 0 },
    { "__last_object__",    (getter)NRPostFunctionWrapper_get_last,
                            NULL, 0 },
    { "__newrelic__",       (getter)NRPostFunctionWrapper_get_marker,
                            NULL, 0 },
    { "__module__",         (getter)NRPostFunctionWrapper_get_module,
                            NULL, 0 },
    { "__name__",           (getter)NRPostFunctionWrapper_get_name,
                            NULL, 0 },
    { "__doc__",            (getter)NRPostFunctionWrapper_get_doc,
                            NULL, 0 },
    { "__dict__",           (getter)NRPostFunctionWrapper_get_dict,
                            NULL, 0 },
    { NULL },
};

PyTypeObject NRPostFunctionWrapper_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.PostFunctionWrapper", /*tp_name*/
    sizeof(NRPostFunctionWrapperObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRPostFunctionWrapper_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRPostFunctionWrapper_call, /*tp_call*/
    0,                      /*tp_str*/
    (getattrofunc)NRPostFunctionWrapper_getattro, /*tp_getattro*/
    (setattrofunc)NRPostFunctionWrapper_setattro, /*tp_setattro*/
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
    NRPostFunctionWrapper_getset, /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    NRPostFunctionWrapper_descr_get, /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    offsetof(NRPostFunctionWrapperObject, dict), /*tp_dictoffset*/
    (initproc)NRPostFunctionWrapper_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRPostFunctionWrapper_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRPostFunctionDecorator_new(PyTypeObject *type,
                                             PyObject *args, PyObject *kwds)
{
    NRPostFunctionDecoratorObject *self;

    self = (NRPostFunctionDecoratorObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->function_object = NULL;
    self->run_once = 0;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRPostFunctionDecorator_init(NRPostFunctionDecoratorObject *self,
                                        PyObject *args, PyObject *kwds)
{
    PyObject *function_object = NULL;
    PyObject *run_once = NULL;

    static char *kwlist[] = { "post_function", "run_once", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O|O!:PostFunctionDecorator",
                                     kwlist, &function_object, &PyBool_Type,
                                     &run_once)) {
        return -1;
    }

    Py_INCREF(function_object);
    Py_XDECREF(self->function_object);
    self->function_object = function_object;

    self->run_once = (run_once == Py_True);

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRPostFunctionDecorator_dealloc(NRPostFunctionDecoratorObject *self)
{
    Py_XDECREF(self->function_object);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRPostFunctionDecorator_call(
        NRPostFunctionDecoratorObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *function_object = NULL;

    static char *kwlist[] = { "post_function", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:PostFunctionDecorator",
                                     kwlist, &function_object)) {
        return NULL;
    }

    return PyObject_CallFunctionObjArgs(
            (PyObject *)&NRPostFunctionWrapper_Type,
            function_object, self->function_object,
            (self->run_once ? Py_True : Py_False), NULL);
}

/* ------------------------------------------------------------------------- */

PyTypeObject NRPostFunctionDecorator_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.PostFunctionDecorator", /*tp_name*/
    sizeof(NRPostFunctionDecoratorObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRPostFunctionDecorator_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRPostFunctionDecorator_call, /*tp_call*/
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
    (initproc)NRPostFunctionDecorator_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRPostFunctionDecorator_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

/*
 * vim: set cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
