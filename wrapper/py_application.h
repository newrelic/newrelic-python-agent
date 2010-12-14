#ifndef PY_WRAPPER_APPLICATION_H
#define PY_WRAPPER_APPLICATION_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include <Python.h>

#include "application_data.h"

/* ------------------------------------------------------------------------- */

typedef struct {
    PyObject_HEAD
    nr_application *application;
} NRApplicationObject;

extern PyTypeObject NRApplication_Type;

/* ------------------------------------------------------------------------- */

PyObject *NRApplication_New(PyObject *self, PyObject *args);

/* ------------------------------------------------------------------------- */

#endif
