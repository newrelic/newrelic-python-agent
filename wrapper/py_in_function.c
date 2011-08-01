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
    self->descr_object = NULL;
    self->self_object = NULL;
    self->next_object = NULL;
    self->last_object = NULL;
    self->function_object = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRInFunctionWrapper_init(NRInFunctionWrapperObject *self,
                                    PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;
    PyObject *function_object = Py_None;

    PyObject *object = NULL;

    static char *kwlist[] = { "wrapped", "function", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OO:PassFunctionWrapper",
                                     kwlist, &wrapped_object,
                                     &function_object)) {
        return -1;
    }

    Py_INCREF(wrapped_object);

    Py_XDECREF(self->descr_object);
    Py_XDECREF(self->self_object);

    self->descr_object = NULL;
    self->self_object = NULL;

    Py_XDECREF(self->dict);
    Py_XDECREF(self->next_object);
    Py_XDECREF(self->last_object);

    self->next_object = wrapped_object;
    self->last_object = NULL;
    self->dict = NULL;

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

static void NRInFunctionWrapper_dealloc(NRInFunctionWrapperObject *self)
{
    Py_XDECREF(self->dict);

    Py_XDECREF(self->descr_object);
    Py_XDECREF(self->self_object);

    Py_XDECREF(self->next_object);
    Py_XDECREF(self->last_object);

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

        if (self->descr_object) {
            PyObject *newargs = NULL;

            int i = 0;

            /*
	     * Where calling via a descriptor object, we
	     * need to reconstruct the arguments such
	     * that the original object self reference
	     * is included once more.
             */

            newargs = PyTuple_New(PyTuple_Size(args)+1);

            Py_INCREF(self->self_object);
            PyTuple_SetItem(newargs, 0, self->self_object);

            for (i=0; i<PyTuple_Size(args); i++) {
                PyObject *item = NULL;

                item = PyTuple_GetItem(args, i);
                Py_INCREF(item);
                PyTuple_SetItem(newargs, i+1, item);
            }

            function_result = PyObject_Call(self->function_object,
                    newargs, kwds);

            Py_DECREF(newargs);
        }
        else {
            function_result = PyObject_Call(self->function_object,
                    args, kwds);
        }

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

    if (self->descr_object) {
        wrapped_result = PyObject_Call(self->descr_object,
                wrapped_args, wrapped_kwds);
    }
    else {
        wrapped_result = PyObject_Call(self->next_object,
                wrapped_args, wrapped_kwds);
    }

    Py_DECREF(wrapped_args);
    Py_XDECREF(wrapped_kwds);

    return wrapped_result;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRInFunctionWrapper_get_next(
        NRInFunctionWrapperObject *self, void *closure)
{
    if (!self->next_object) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    Py_INCREF(self->next_object);
    return self->next_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRInFunctionWrapper_get_last(
        NRInFunctionWrapperObject *self, void *closure)
{
    if (!self->last_object) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    Py_INCREF(self->last_object);
    return self->last_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRInFunctionWrapper_get_marker(
        NRInFunctionWrapperObject *self, void *closure)
{
    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRInFunctionWrapper_get_module(
        NRInFunctionWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    return PyObject_GetAttrString(self->last_object, "__module__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRInFunctionWrapper_get_name(
        NRInFunctionWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    return PyObject_GetAttrString(self->last_object, "__name__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRInFunctionWrapper_get_doc(
        NRInFunctionWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    return PyObject_GetAttrString(self->last_object, "__doc__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRInFunctionWrapper_get_dict(
        NRInFunctionWrapperObject *self)
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

static PyObject *NRInFunctionWrapper_getattro(
        NRInFunctionWrapperObject *self, PyObject *name)
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

static int NRInFunctionWrapper_setattro(
        NRInFunctionWrapperObject *self, PyObject *name, PyObject *value)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return -1;
    }

    return PyObject_SetAttr(self->last_object, name, value);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRInFunctionWrapper_descr_get(
        NRInFunctionWrapperObject *self, PyObject *object, PyObject *type)
{
    PyObject *method = NULL;

#if 0
    if (object == Py_None) {
        Py_INCREF(self);
        return (PyObject *)self;
    }
#endif

    method = PyObject_GetAttrString(self->next_object, "__get__");

    if (method) {
        PyObject *descr = NULL;

        NRInFunctionWrapperObject *result;

        /*
	 * When wrapper used around a class method, object is
	 * passed as NULL. Don't know what else to do but in
	 * turn pass it as None because if pass NULL then it is
	 * actually terminates the argument list and it returns
	 * NULL with no error set.
         */

        if (!object)
            object = Py_None;

        descr = PyObject_CallFunctionObjArgs(method, object, type, NULL);

        if (!descr)
            return NULL;

        /*
         * We are circumventing new/init here for object but
         * easier than duplicating all the code to create a
         * special descriptor version of wrapper.
         */

        result = (NRInFunctionWrapperObject *)
                (&NRInFunctionWrapper_Type)->tp_alloc(
                &NRInFunctionWrapper_Type, 0);

        if (!result)
            return NULL;

        Py_XINCREF(self->dict);
        result->dict = self->dict;

        Py_XINCREF(descr);
        result->descr_object = descr;

        Py_XINCREF(object);
        result->self_object = object;

        Py_XINCREF(self->next_object);
        result->next_object = self->next_object;

        Py_XINCREF(self->last_object);
        result->last_object = self->last_object;

        Py_XINCREF(self->function_object);
        result->function_object = self->function_object;

        Py_XDECREF(descr);
        Py_DECREF(method);

        return (PyObject *)result;
    }
    else {
        PyErr_Clear();

        Py_INCREF(self);
        return (PyObject *)self;
    }
}

/* ------------------------------------------------------------------------- */

static PyGetSetDef NRInFunctionWrapper_getset[] = {
    { "__next_object__",    (getter)NRInFunctionWrapper_get_next,
                            NULL, 0 },
    { "__last_object__",    (getter)NRInFunctionWrapper_get_last,
                            NULL, 0 },
    { "__newrelic__",       (getter)NRInFunctionWrapper_get_marker,
                            NULL, 0 },
    { "__module__",         (getter)NRInFunctionWrapper_get_module,
                            NULL, 0 },
    { "__name__",           (getter)NRInFunctionWrapper_get_name,
                            NULL, 0 },
    { "__doc__",            (getter)NRInFunctionWrapper_get_doc,
                            NULL, 0 },
    { "__dict__",           (getter)NRInFunctionWrapper_get_dict,
                            NULL, 0 },
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
    (getattrofunc)NRInFunctionWrapper_getattro, /*tp_getattro*/
    (setattrofunc)NRInFunctionWrapper_setattro, /*tp_setattro*/
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
    (descrgetfunc)NRInFunctionWrapper_descr_get, /*tp_descr_get*/
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
