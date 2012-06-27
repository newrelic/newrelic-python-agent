/* ------------------------------------------------------------------------- */

#include <Python.h>

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

/* ------------------------------------------------------------------------- */

typedef struct {
    PyObject_HEAD
    int active_requests;
    double utilization_count;
    long long utilization_last;
    int maximum_concurrency;
} NRUtilizationObject;

extern PyTypeObject NRUtilization_Type;

static PyObject *NRUtilization_new(PyTypeObject *type,
        PyObject *args, PyObject *kwds)
{
    NRUtilizationObject *self;

    self = (NRUtilizationObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->active_requests = 0;
    self->utilization_count = 0.0;
    self->utilization_last = 0;
    self->maximum_concurrency = 0;

    return (PyObject *)self;
}

static void NRUtilization_dealloc(NRUtilizationObject *self)
{
    PyObject_Del(self);
}

static double NRUtilization_adjust(NRUtilizationObject *self, int adjustment)
{
    long long now;
    double utilization = self->utilization_count;

    struct timeval t;

    gettimeofday(&t, NULL);

    now = ((long long)t.tv_sec) * 1000000 + ((long long)t.tv_usec);

    if (self->utilization_last != 0.0) {
        utilization = (now - self->utilization_last) / 1000000.0;

        if (utilization < 0)
            utilization = 0;

        utilization = self->active_requests * utilization;
        self->utilization_count += utilization;
        utilization = self->utilization_count;
    }

    self->utilization_last = now;
    self->active_requests += adjustment;

    if (adjustment > 0 && self->active_requests > self->maximum_concurrency)
        self->maximum_concurrency = self->active_requests;

    return utilization;
}

static PyObject *NRUtilization_enter(NRUtilizationObject *self, PyObject *args)
{
    return PyFloat_FromDouble(NRUtilization_adjust(self, 1));
}

static PyObject *NRUtilization_exit(NRUtilizationObject *self, PyObject *args)
{
    return PyFloat_FromDouble(NRUtilization_adjust(self, -1));
}

PyObject *NRUtilization_utilization(NRUtilizationObject *self, PyObject *args)
{
    return PyFloat_FromDouble(NRUtilization_adjust(self, 0));
}

PyObject *NRUtilization_concurrency(NRUtilizationObject *self, PyObject *args)
{
    PyObject *reset = Py_True;

    int maximum_concurrency;

    if (!PyArg_ParseTuple(args, "|O!:maximum_concurrency",
                &PyBool_Type, &reset)) {
        return NULL;
    }

    maximum_concurrency = self->maximum_concurrency;

    if (reset == Py_True)
        self->maximum_concurrency = self->active_requests;

    return PyInt_FromLong(maximum_concurrency);
}

static PyMethodDef NRUtilization_methods[] = {
    { "enter_transaction",  (PyCFunction)NRUtilization_enter,
                            METH_NOARGS, 0 },
    { "exit_transaction",   (PyCFunction)NRUtilization_exit,
                            METH_NOARGS, 0 },
    { "utilization_count", (PyCFunction)NRUtilization_utilization,
                            METH_NOARGS, 0 },
    { "maximum_concurrency",(PyCFunction)NRUtilization_concurrency,
                            METH_VARARGS, 0 },
    { NULL, NULL}
};

PyTypeObject NRUtilization_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "newrelic.core._thread_utilization.ThreadUtilization", /*tp_name*/
    sizeof(NRUtilizationObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRUtilization_dealloc, /*tp_dealloc*/
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
    NRUtilization_methods,  /*tp_methods*/
    0,                      /*tp_members*/
    0,                      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    0,                      /*tp_init*/
    0,                      /*tp_alloc*/
    NRUtilization_new,      /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

PyMODINIT_FUNC
init_thread_utilization(void)
{
    PyObject *module;

    module = Py_InitModule3("_thread_utilization", NULL, NULL);

    if (module == NULL)
        return;

    if (PyType_Ready(&NRUtilization_Type) < 0)
        return;

    Py_INCREF(&NRUtilization_Type);
    PyModule_AddObject(module, "ThreadUtilization",
            (PyObject *)&NRUtilization_Type);
}

/* ------------------------------------------------------------------------- */
