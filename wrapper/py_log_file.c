/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_log_file.h"

#include "globals.h"
#include "logging.h"

/* ------------------------------------------------------------------------- */

static PyObject *NRLogFile_new(PyTypeObject *type, PyObject *args,
                               PyObject *kwds)
{
    NRLogFileObject *self;

    self = (NRLogFileObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->level = 0;
    self->s = NULL;
    self->l = 0;
    self->softspace = 0;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRLogFile_init(NRLogFileObject *self, PyObject *args,
        PyObject *kwds)
{
    int level = 0;

    static char *kwlist[] = { "level", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "i:LogFile",
                                     kwlist, &level)) {
        return -1;
    }

    self->level = level;

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRLogFile_call(NRLogFileObject *self, const char *s, int l)
{
    Py_BEGIN_ALLOW_THREADS
    nr__log(self->level, "%s", s);
    Py_END_ALLOW_THREADS
}

/* ------------------------------------------------------------------------- */

static void NRLogFile_dealloc(NRLogFileObject *self)
{
    if (self->s) {
        NRLogFile_call(self, self->s, self->l);

        free(self->s);
    }

    PyObject_Del(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRLogFile_flush(NRLogFileObject *self, PyObject *args)
{
    if (self->s) {
        NRLogFile_call(self, self->s, self->l);

        free(self->s);
        self->s = NULL;
        self->l = 0;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRLogFile_close(NRLogFileObject *self, PyObject *args)
{
    PyObject *result = NULL;

    result = NRLogFile_flush(self, args);

    Py_XDECREF(result);

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRLogFile_isatty(NRLogFileObject *self, PyObject *args)
{
    Py_INCREF(Py_False);
    return Py_False;
}

/* ------------------------------------------------------------------------- */

static void NRLogFile_queue(NRLogFileObject *self, const char *msg, int len)
{
    const char *p = NULL;
    const char *q = NULL;
    const char *e = NULL;

    p = msg;
    e = p + len;

    /*
     * Break string on newline. This is on assumption
     * that primarily textual information being logged.
     */

    q = p;
    while (q != e) {
        if (*q == '\n')
            break;
        q++;
    }

    while (q != e) {
        /* Output each complete line. */

        if (self->s) {
            /* Need to join with buffered value. */

            int m = 0;
            int n = 0;
            char *s = NULL;

            m = self->l;
            n = m+q-p+1;

            s = (char *)malloc(n);
            memcpy(s, self->s, m);
            memcpy(s+m, p, q-p);
            s[n-1] = '\0';

            free(self->s);
            self->s = NULL;
            self->l = 0;

            NRLogFile_call(self, s, n-1);

            free(s);
        }
        else {
            int n = 0;
            char *s = NULL;

            n = q-p+1;

            s = (char *)malloc(n);
            memcpy(s, p, q-p);
            s[n-1] = '\0';

            NRLogFile_call(self, s, n-1);

            free(s);
        }

        p = q+1;

        /* Break string on newline. */

        q = p;
        while (q != e) {
            if (*q == '\n')
                break;
            q++;
        }
    }

    if (p != e) {
        /* Save away incomplete line. */

        if (self->s) {
            /* Need to join with buffered value. */

            int m = 0;
            int n = 0;

            m = self->l;
            n = m+e-p+1;

            self->s = (char *)realloc(self->s, n);
            memcpy(self->s+m, p, e-p);
            self->s[n-1] = '\0';
            self->l = n-1;
        }
        else {
            int n = 0;

            n = e-p+1;

            self->s = (char *)malloc(n);
            memcpy(self->s, p, n-1);
            self->s[n-1] = '\0';
            self->l = n-1;
        }
    }
}

/* ------------------------------------------------------------------------- */

static PyObject *NRLogFile_write(NRLogFileObject *self, PyObject *args)
{
    const char *msg = NULL;
    int len = -1;

    if (!PyArg_ParseTuple(args, "s#:write", &msg, &len))
        return NULL;

    NRLogFile_queue(self, msg, len);

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRLogFile_writelines(NRLogFileObject *self, PyObject *args)
{
    PyObject *sequence = NULL;
    PyObject *iterator = NULL;
    PyObject *item = NULL;

    if (!PyArg_ParseTuple(args, "O:writelines", &sequence))
        return NULL;

    iterator = PyObject_GetIter(sequence);

    if (iterator == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "argument must be sequence of strings");

        return NULL;
    }

    while ((item = PyIter_Next(iterator))) {
        PyObject *result = NULL;

        result = NRLogFile_write(self, item);

        if (!result) {
            Py_DECREF(iterator);

            PyErr_SetString(PyExc_TypeError,
                            "argument must be sequence of strings");

            return NULL;
        }
    }

    Py_DECREF(iterator);

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRLogFile_closed(NRLogFileObject *self, void *closure)
{
    Py_INCREF(Py_False);
    return Py_False;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRLogFile_get_softspace(NRLogFileObject *self, void *closure)
{
    return PyInt_FromLong(self->softspace);
}

/* ------------------------------------------------------------------------- */

static int NRLogFile_set_softspace(NRLogFileObject *self, PyObject *value)
{
    int new;

    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "can't delete softspace attribute");
        return -1;
    }

    new = PyInt_AsLong(value);
    if (new == -1 && PyErr_Occurred())
        return -1;

    self->softspace = new;

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyMethodDef NRLogFile_methods[] = {
    { "flush",      (PyCFunction)NRLogFile_flush,      METH_NOARGS, 0 },
    { "close",      (PyCFunction)NRLogFile_close,      METH_NOARGS, 0 },
    { "isatty",     (PyCFunction)NRLogFile_isatty,     METH_NOARGS, 0 },
    { "write",      (PyCFunction)NRLogFile_write,      METH_VARARGS, 0 },
    { "writelines", (PyCFunction)NRLogFile_writelines, METH_VARARGS, 0 },
    { NULL, NULL}
};

static PyGetSetDef NRLogFile_getset[] = {
    { "closed",         (getter)NRLogFile_closed, NULL, 0 },
    { "softspace",      (getter)NRLogFile_get_softspace,
                        (setter)NRLogFile_set_softspace, 0 },
    { NULL },
};

/* ------------------------------------------------------------------------- */

PyTypeObject NRLogFile_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.LogFile",     /*tp_name*/
    sizeof(NRLogFileObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRLogFile_dealloc, /*tp_dealloc*/
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
    NRLogFile_methods,      /*tp_methods*/
    0,                      /*tp_members*/
    NRLogFile_getset,       /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)NRLogFile_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRLogFile_new,          /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

/*
 * vim: set cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
