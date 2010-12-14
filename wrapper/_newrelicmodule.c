/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include <Python.h>

#include "py_application.h"
#include "py_background_task.h"
#include "py_web_transaction.h"

/* ------------------------------------------------------------------------- */

static PyMethodDef newrelic_methods[] = {
    { "Application", NRApplication_New, METH_VARARGS, 0 },
    { NULL, NULL }
};

PyMODINIT_FUNC
init_newrelic(void)
{
    PyObject *m;

    m = Py_InitModule3("_newrelic", newrelic_methods, NULL);
    if (m == NULL)
        return;

    if (PyType_Ready(&NRApplication_Type) < 0)
        return;
    if (PyType_Ready(&NRBackgroundTask_Type) < 0)
        return;
    if (PyType_Ready(&NRWebTransaction_Type) < 0)
        return;
}

/* ------------------------------------------------------------------------- */
