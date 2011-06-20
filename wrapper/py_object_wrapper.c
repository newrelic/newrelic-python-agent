/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_object_wrapper.h"

#include "py_utilities.h"

#include "structmember.h"

/* ------------------------------------------------------------------------- */

static PyObject *NRObjectWrapper_new(PyTypeObject *type,
                                          PyObject *args, PyObject *kwds)
{
    NRObjectWrapperObject *self;

    self = (NRObjectWrapperObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->dict = NULL;
    self->wrapped_object = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRObjectWrapper_init(NRObjectWrapperObject *self,
                                PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;

    PyObject *wrapper = NULL;

    static char *kwlist[] = { "wrapped", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:ObjectWrapper",
                                     kwlist, &wrapped_object)) {
        return -1;
    }

    Py_INCREF(wrapped_object);
    Py_XDECREF(self->wrapped_object);
    self->wrapped_object = wrapped_object;

    /* Perform equivalent of functools.wraps(). */

    wrapper = NRUtilities_UpdateWrapper((PyObject *)self, wrapped_object);

    if (!wrapper)
        return -1;

    Py_DECREF(wrapper);

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRObjectWrapper_dealloc(NRObjectWrapperObject *self)
{
    Py_XDECREF(self->dict);

    Py_XDECREF(self->wrapped_object);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRObjectWrapper_call(NRObjectWrapperObject *self,
                                           PyObject *args, PyObject *kwds)
{
    return PyObject_Call(self->wrapped_object, args, kwds);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRObjectWrapper_get_wrapped(
        NRObjectWrapperObject *self, void *closure)
{
    Py_INCREF(self->wrapped_object);
    return self->wrapped_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRObjectWrapper_get_dict(
        NRObjectWrapperObject *self)
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

static int NRObjectWrapper_set_dict(
        NRObjectWrapperObject *self, PyObject *val)
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

static PyObject *NRObjectWrapper_descr_get(PyObject *function,
                                                PyObject *object,
                                                PyObject *type)
{
    if (object == Py_None)
        object = NULL;

    return PyMethod_New(function, object, type);
}

/* ------------------------------------------------------------------------- */

static PyGetSetDef NRObjectWrapper_getset[] = {
    { "__wrapped__",        (getter)NRObjectWrapper_get_wrapped,
                            NULL, 0 },
    { "__dict__",           (getter)NRObjectWrapper_get_dict,
                            (setter)NRObjectWrapper_set_dict, 0 },
    { NULL },
};

PyTypeObject NRObjectWrapper_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.ObjectWrapper", /*tp_name*/
    sizeof(NRObjectWrapperObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRObjectWrapper_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRObjectWrapper_call, /*tp_call*/
    0,                      /*tp_str*/
    PyObject_GenericGetAttr, /*tp_getattro*/
    PyObject_GenericSetAttr, /*tp_setattro*/
    0,                      /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT |
    Py_TPFLAGS_BASETYPE,    /*tp_flags*/
    0,                      /*tp_doc*/
    0,                      /*tp_traverse*/
    0,                      /*tp_clear*/
    0,                      /*tp_richcompare*/
    0,                      /*tp_weaklistoffset*/
    0,                      /*tp_iter*/
    0,                      /*tp_iternext*/
    0,                      /*tp_methods*/
    0,                      /*tp_members*/
    NRObjectWrapper_getset, /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    NRObjectWrapper_descr_get, /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    offsetof(NRObjectWrapperObject, dict), /*tp_dictoffset*/
    (initproc)NRObjectWrapper_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRObjectWrapper_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

/*
 * vim: set cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
