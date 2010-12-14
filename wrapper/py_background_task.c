/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_background_task.h"

#include "globals.h"
#include "logging.h"

#include "application_funcs.h"
#include "harvest_funcs.h"
#include "web_transaction_funcs.h"

/* ------------------------------------------------------------------------- */

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

/* ------------------------------------------------------------------------- */

NRBackgroundTaskObject *NRBackgroundTask_New(nr_application *application,
                                             PyObject* path)
{
    NRBackgroundTaskObject *self;

    /*
     * Create transaction object and cache reference to the
     * internal agent client application object instance. Will
     * need the latter when doing some work arounds for lack
     * of thread safety in agent client code.
     */

    self = PyObject_New(NRBackgroundTaskObject, &NRBackgroundTask_Type);
    if (self == NULL)
        return NULL;

    self->application = application;

    self->background_task = nr_web_transaction__allocate();

    self->background_task->path_type = NR_PATH_TYPE_CUSTOM;
    self->background_task->path = nrstrdup(PyString_AsString(path));
    self->background_task->realpath = NULL;

    self->background_task->http_x_request_start = 0;

    self->background_task->backgroundjob = 1;

    self->background_task->has_been_named = 1;

    return self;
}

static void NRBackgroundTask_dealloc(NRBackgroundTaskObject *self)
{
    /*
     * Don't need to destroy the transaction object as
     * the harvest will automatically destroy it when it
     * is done.
     */
}

static PyObject *NRBackgroundTask_enter(NRBackgroundTaskObject *self,
                                        PyObject *args)
{
    nr_node_header *save;

    nr_node_header__record_starttime_and_push_current(
            (nr_node_header *)self->background_task, &save);

    Py_INCREF(self);
    return (PyObject *)self;
}

static PyObject *NRBackgroundTask_exit(NRBackgroundTaskObject *self,
                                       PyObject *args)
{
    nr_node_header__record_stoptime_and_pop_current(
            (nr_node_header *)self->background_task, NULL);

    self->background_task->http_response_code = 0;

    pthread_mutex_lock(&(nr_per_process_globals.harvest_data_mutex));
    nr__switch_to_application(self->application);
    nr__distill_web_transaction_into_harvest_data(self->background_task);
    pthread_mutex_unlock(&(nr_per_process_globals.harvest_data_mutex));

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *NRBackgroundTask_get_path(NRBackgroundTaskObject *self,
                                           void *closure)
{
    return PyString_FromString(self->background_task->path);
}

static int NRBackgroundTask_set_path(NRBackgroundTaskObject *self,
                                     PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "can't delete URL path attribute");
        return -1;
    }

    if (!PyString_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected string for URL path");
        return -1;
    }

    nrfree(self->background_task->path);

    self->background_task->path = nrstrdup(PyString_AsString(value));

    return 0;
}

static PyMethodDef NRBackgroundTask_methods[] = {
    { "__enter__",  (PyCFunction)NRBackgroundTask_enter,  METH_NOARGS, 0 },
    { "__exit__",   (PyCFunction)NRBackgroundTask_exit,   METH_VARARGS, 0 },
    { NULL, NULL }
};

static PyGetSetDef NRBackgroundTask_getset[] = {
    { "path", (getter)NRBackgroundTask_get_path, (setter)NRBackgroundTask_set_path, 0 },
    { NULL },
};

PyTypeObject NRBackgroundTask_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.BackgroundTask", /*tp_name*/
    sizeof(NRBackgroundTaskObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRBackgroundTask_dealloc, /*tp_dealloc*/
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
    NRBackgroundTask_methods, /*tp_methods*/
    0,                      /*tp_members*/
    NRBackgroundTask_getset, /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    0,                      /*tp_init*/
    0,                      /*tp_alloc*/
    0,                      /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */
