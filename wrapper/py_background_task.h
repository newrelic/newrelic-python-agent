#ifndef PY_WRAPPER_BACKGROUND_TASK_H
#define PY_WRAPPER_BACKGROUND_TASK_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include <Python.h>

#include "application_data.h"
#include "web_transaction_data.h"

/* ------------------------------------------------------------------------- */

typedef struct {
    PyObject_HEAD
    nr_application *application;
    nr_web_transaction *web_transaction;
    PyObject *custom_parameters;
} NRBackgroundTaskObject;

extern PyTypeObject NRBackgroundTask_Type;

/* ------------------------------------------------------------------------- */

extern NRBackgroundTaskObject *NRBackgroundTask_New(
        nr_application *application, PyObject *path);

/* ------------------------------------------------------------------------- */

#endif
