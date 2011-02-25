/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_pass_function.h"

#include "py_utilities.h"

/* ------------------------------------------------------------------------- */

static PyObject *NRPassFunction_new(PyTypeObject *type, PyObject *args,
                                       PyObject *kwds)
{
    NRPassFunctionObject *self;

    self = (NRPassFunctionObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->wrapped_object = NULL;
    self->function_object = NULL;
    self->run_once = 0;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRPassFunction_init(NRPassFunctionObject *self, PyObject *args,
                              PyObject *kwds)
{
    PyObject *wrapped_object = NULL;
    PyObject *function_object = NULL;
    PyObject *run_once = NULL;

    static char *kwlist[] = { "wrapped", "function", "run_once", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OO|O!:PassFunction",
                                     kwlist, &wrapped_object, &function_object,
                                     &PyBool_Type, &run_once)) {
        return -1;
    }

    Py_INCREF(wrapped_object);
    Py_XDECREF(self->wrapped_object);
    self->wrapped_object = wrapped_object;

    Py_INCREF(function_object);
    Py_XDECREF(self->function_object);
    self->function_object = function_object;

    self->run_once = (run_once == Py_True);

    /*
     * TODO This should set __module__, __name__, __doc__ and
     * update __dict__ to preserve introspection capabilities.
     * See @wraps in functools of recent Python versions.
     */

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRPassFunction_dealloc(NRPassFunctionObject *self)
{
    Py_DECREF(self->wrapped_object);
    Py_XDECREF(self->function_object);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRPassFunction_call(NRPassFunctionObject *self,
                                        PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_result = NULL;

    wrapped_result = PyObject_Call(self->wrapped_object, args, kwds);

    if (!wrapped_result)
        return NULL;

    if (self->function_object) {
        PyObject *function_result = NULL;

        function_result = PyObject_CallFunctionObjArgs(self->function_object,
                                                       wrapped_result, NULL);

        if (self->run_once) {
            self->run_once = 0;
            Py_DECREF(self->function_object);
            self->function_object = NULL;
        }

        Py_DECREF(wrapped_result);

        return function_result;
    }

    return wrapped_result;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRPassFunction_get_wrapped(NRPassFunctionObject *self,
                                           void *closure)
{
    Py_INCREF(self->wrapped_object);
    return self->wrapped_object;
}
 
/* ------------------------------------------------------------------------- */

static PyObject *NRPassFunction_descr_get(PyObject *function,
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

static PyGetSetDef NRPassFunction_getset[] = {
    { "__wrapped__",        (getter)NRPassFunction_get_wrapped,
                            NULL, 0 },
    { NULL },
};

PyTypeObject NRPassFunction_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.PassFunction", /*tp_name*/
    sizeof(NRPassFunctionObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRPassFunction_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRPassFunction_call, /*tp_call*/
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
    NRPassFunction_getset,   /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    NRPassFunction_descr_get, /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)NRPassFunction_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRPassFunction_new,      /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
