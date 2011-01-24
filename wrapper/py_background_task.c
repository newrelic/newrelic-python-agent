/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_background_task.h"
#include "py_database_trace.h"
#include "py_external_trace.h"
#include "py_function_trace.h"
#include "py_memcache_trace.h"

#include "globals.h"
#include "logging.h"

#include "application_funcs.h"
#include "harvest_funcs.h"
#include "params_funcs.h"
#include "web_transaction_funcs.h"

/* ------------------------------------------------------------------------- */

static int NRBackgroundTask_init(NRTransactionObject *self, PyObject *args,
                                 PyObject *kwds)
{
    NRApplicationObject *application = NULL;
    char const *path = NULL;

    PyObject *newargs = NULL;

    static char *kwlist[] = { "application", "path", NULL };

    /*
     * For the case that no argument was provided then the new
     * method would have returned a reference to an existing
     * in progress transaction instance which has already been
     * initialised. We check for this case and skip doing any
     * initialisation a second time. We also return here if the
     * init method has been called twice when it should not
     * have been.
     */

    if (self->application)
        return 0;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O!s:BackgroundTask",
                                     kwlist, &NRApplication_Type,
                                     &application, &path)) {
        return -1;
    }

    newargs = PySequence_GetSlice(args, 0, 1);

    if (NRTransaction_Type.tp_init((PyObject *)self, newargs, kwds) < 0) {
        Py_DECREF(newargs);
        return -1;
    }

    Py_DECREF(newargs);

    /*
     * Setup the background task specific attributes of the
     * transaction. Note that mark it as being named but do
     * not currently check that and prevent the name from
     * being overridden as the PHP code seems to do. The PHP
     * code may only do that as may only attach the name at
     * the end of the transaction and not at the start. Since
     * we do it at the start, then user can still override it.
     */

    if (self->transaction) {
        self->transaction->path_type = NR_PATH_TYPE_CUSTOM;
        self->transaction->path = nrstrdup(path);
        self->transaction->realpath = NULL;

        self->transaction->backgroundjob = 1;
        self->transaction->has_been_named = 1;
    }

    return 0;
}


/* ------------------------------------------------------------------------- */

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

PyTypeObject NRBackgroundTask_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.BackgroundTask", /*tp_name*/
    sizeof(NRTransactionObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    0,                      /*tp_dealloc*/
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
    0,                      /*tp_methods*/
    0,                      /*tp_members*/
    0,                      /*tp_getset*/
    &NRTransaction_Type,    /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)NRBackgroundTask_init, /*tp_init*/
    0,                      /*tp_alloc*/
    0,                      /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */
