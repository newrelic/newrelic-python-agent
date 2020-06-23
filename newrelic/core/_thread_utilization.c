/*
 * Copyright 2010 New Relic, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/* ------------------------------------------------------------------------- */

#include <Python.h>

#include <pythread.h>

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

/* ------------------------------------------------------------------------- */

typedef struct {
    int currently_active;
    double utilization_current;
    double utilization_previous;
    long long time_last_updated;
    long long time_last_fetched;
} UtilizationCount;

static void reset_utilization_count(UtilizationCount *self)
{
    struct timeval t;

    self->currently_active = 0;

    self->utilization_current = 0.0;
    self->utilization_previous = 0.0;

    gettimeofday(&t, NULL);

    self->time_last_updated = t.tv_sec * 1000000;
    self->time_last_updated += t.tv_usec;

    self->time_last_fetched = self->time_last_updated;
}

static double adjust_utilization_count(UtilizationCount *self, int adjustment)
{
    long long current_time;
    double utilization = self->utilization_current;

    struct timeval t;

    gettimeofday(&t, NULL);

    current_time = t.tv_sec * 1000000;
    current_time += t.tv_usec;

    utilization = (current_time - self->time_last_updated) / 1000000.0;

    if (utilization < 0)
        utilization = 0;

    utilization = self->currently_active * utilization;
    self->utilization_current += utilization;
    utilization = self->utilization_current;

    self->time_last_updated = current_time;
    self->currently_active += adjustment;

    if (adjustment == 0) {
        self->time_last_fetched = self->time_last_updated;
        self->utilization_previous = utilization;
    }

    return utilization;
}

static double fetch_utilization_count(UtilizationCount *self)
{
    long long time_last_fetched;
    long long time_last_updated;

    double utilization_current;
    double utilization_previous;

    double utilization_period;

    double elapsed_time;

    time_last_fetched = self->time_last_fetched;
    utilization_previous = self->utilization_previous;

    utilization_current = adjust_utilization_count(self, 0);

    utilization_period = utilization_current - utilization_previous;

    time_last_updated = self->time_last_updated;

    elapsed_time = self->time_last_updated - time_last_fetched;
    elapsed_time /= 1000000.0;

    if (elapsed_time <= 0)
        return 0.0;

    return utilization_period / elapsed_time;
}

#if 0
typedef struct {
    int sample_count;
    double total_value;
    double minimum_value;
    double maximum_value;
    double sum_of_squares;
} AggregateSample;

static void reset_aggregate_sample(AggregateSample *self)
{
    self->sample_count = 0;
    self->total_value = 0.0;
    self->minimum_value = 0.0;
    self->maximum_value = 0.0;
    self->sum_of_squares = 0.0;
}

static void add_to_aggregate_sample(AggregateSample *self, double value)
{
    self->total_value += value;

    if (!self->sample_count)
        self->minimum_value = value;
    else if (value < self->minimum_value)
        self->minimum_value = value;

    if (value > self->maximum_value)
        self->maximum_value = value;

    self->sum_of_squares += (value * value);

    self->sample_count += 1;
}
#endif

typedef struct {
    PyObject_HEAD

    PyThread_type_lock thread_mutex;

    PyObject *set_of_all_threads;

    UtilizationCount thread_capacity;

    int requests_current;
    double requests_utilization_count;
    long long requests_utilization_last;
} NRUtilizationObject;

extern PyTypeObject NRUtilization_Type;

static PyObject *NRUtilization_new(PyTypeObject *type,
        PyObject *args, PyObject *kwds)
{
    NRUtilizationObject *self;

    self = (NRUtilizationObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    /*
     * XXX Using a mutex for now just in case the calls to get
     * the current thread are causing release of GIL in a
     * multithreaded context. May explain why having issues with
     * object referred to by weakrefs being corrupted. The GIL
     * should technically be enough to protect us here.
     */

    self->thread_mutex = PyThread_allocate_lock();

    self->set_of_all_threads = PyDict_New();

    reset_utilization_count(&self->thread_capacity);

    self->requests_current = 0;
    self->requests_utilization_count = 0.0;
    self->requests_utilization_last = 0;

    return (PyObject *)self;
}

static void NRUtilization_dealloc(NRUtilizationObject *self)
{
    Py_DECREF(self->set_of_all_threads);

    PyThread_free_lock(self->thread_mutex);

    PyObject_Del(self);
}

static double NRUtilization_adjust(NRUtilizationObject *self, int adjustment)
{
    long long now;
    double utilization = self->requests_utilization_count;

    struct timeval t;

    gettimeofday(&t, NULL);

    now = ((long long)t.tv_sec) * 1000000 + ((long long)t.tv_usec);

    if (self->requests_utilization_last != 0.0) {
        utilization = (now - self->requests_utilization_last) / 1000000.0;

        if (utilization < 0)
            utilization = 0;

        utilization = self->requests_current * utilization;
        self->requests_utilization_count += utilization;
        utilization = self->requests_utilization_count;
    }

    self->requests_utilization_last = now;
    self->requests_current += adjustment;

    return utilization;
}

static PyObject *NRUtilization_enter(NRUtilizationObject *self, PyObject *args)
{
    PyObject *module = NULL;
    PyObject *thread = Py_None;

    if (!PyArg_ParseTuple(args, "|O:enter_transaction", &thread))
        return NULL;

    PyThread_acquire_lock(self->thread_mutex, 1);

    if (thread == Py_None) {
        module = PyImport_ImportModule("threading");

        if (!module)
            PyErr_Clear();

        if (module) {
            PyObject *dict = NULL;
            PyObject *func = NULL;

            dict = PyModule_GetDict(module);
#if PY_MAJOR_VERSION >= 3
            func = PyDict_GetItemString(dict, "current_thread");
#else
            func = PyDict_GetItemString(dict, "currentThread");
#endif
            if (func) {
                Py_INCREF(func);
                thread = PyEval_CallObject(func, (PyObject *)NULL);
                if (!thread)
                    PyErr_Clear();

                Py_DECREF(func);
            }
        }

        Py_XDECREF(module);
    }
    else
        Py_INCREF(thread);

    if (thread && thread != Py_None) {
        PyObject *ref = NULL;
        PyObject *callback = NULL;

        callback = PyObject_GetAttrString((PyObject *)self,
                "delete_from_all");
        ref = PyWeakref_NewRef(thread, callback);

        if (!PyDict_Contains(self->set_of_all_threads, ref)) {
            PyDict_SetItem(self->set_of_all_threads, ref, Py_None);
            adjust_utilization_count(&self->thread_capacity, 1);
        }

        Py_DECREF(ref);
        Py_DECREF(callback);
    }

    Py_XDECREF(thread);

    PyThread_release_lock(self->thread_mutex);

    return PyFloat_FromDouble(NRUtilization_adjust(self, 1));
}

static PyObject *NRUtilization_exit(NRUtilizationObject *self, PyObject *args)
{
    return PyFloat_FromDouble(NRUtilization_adjust(self, -1));
}

PyObject *NRUtilization_total(NRUtilizationObject *self, PyObject *args)
{
    PyObject *reset = Py_True;

    double utilization;

    if (!PyArg_ParseTuple(args, "|O!:total_threads",
                &PyBool_Type, &reset)) {
        return NULL;
    }

    utilization = fetch_utilization_count(&self->thread_capacity);

    return PyFloat_FromDouble(utilization);
}

PyObject *NRUtilization_utilization(NRUtilizationObject *self, PyObject *args)
{
    return PyFloat_FromDouble(NRUtilization_adjust(self, 0));
}

PyObject *NRUtilization_delete_all(NRUtilizationObject *self,
        PyObject *args)
{
    PyObject *ref = NULL;

    if (!PyArg_ParseTuple(args, "O!:delete_from_all",
                &_PyWeakref_RefType, &ref)) {
        return NULL;
    }

    PyThread_acquire_lock(self->thread_mutex, 1);

    if (PyDict_Contains(self->set_of_all_threads, ref)) {
        PyDict_DelItem(self->set_of_all_threads, ref);
        adjust_utilization_count(&self->thread_capacity, -1);
    }

    PyThread_release_lock(self->thread_mutex);

    Py_INCREF(Py_None);

    return Py_None;
}

static PyMethodDef NRUtilization_methods[] = {
    { "enter_transaction",  (PyCFunction)NRUtilization_enter,
                            METH_VARARGS, 0 },
    { "exit_transaction",   (PyCFunction)NRUtilization_exit,
                            METH_NOARGS, 0 },
    { "total_threads",      (PyCFunction)NRUtilization_total,
                            METH_VARARGS, 0 },
    { "utilization_count",  (PyCFunction)NRUtilization_utilization,
                            METH_NOARGS, 0 },
    { "delete_from_all",    (PyCFunction)NRUtilization_delete_all,
                            METH_VARARGS, 0 },
    { NULL, NULL}
};

PyTypeObject NRUtilization_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "ThreadUtilization",    /*tp_name*/
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

#if PY_MAJOR_VERSION >= 3
static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "_thread_utilization", /* m_name */
    NULL,                /* m_doc */
    -1,                  /* m_size */
    NULL,                /* m_methods */
    NULL,                /* m_reload */
    NULL,                /* m_traverse */
    NULL,                /* m_clear */
    NULL,                /* m_free */
};
#endif

static PyObject *
moduleinit(void)
{
    PyObject *module;

#if PY_MAJOR_VERSION >= 3
    module = PyModule_Create(&moduledef);
#else
    module = Py_InitModule3("_thread_utilization", NULL, NULL);
#endif

    if (module == NULL)
        return NULL;

    if (PyType_Ready(&NRUtilization_Type) < 0)
        return NULL;

    Py_INCREF(&NRUtilization_Type);
    PyModule_AddObject(module, "ThreadUtilization",
            (PyObject *)&NRUtilization_Type);

    return module;
}

#if PY_MAJOR_VERSION < 3
PyMODINIT_FUNC init_thread_utilization(void)
{
    moduleinit();
}
#else
PyMODINIT_FUNC PyInit__thread_utilization(void)
{
    return moduleinit();
}
#endif

/* ------------------------------------------------------------------------- */
