#ifndef PY_WRAPPER_APPLICATION_H
#define PY_WRAPPER_APPLICATION_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include <Python.h>

#include "nrtypes.h"

/* ------------------------------------------------------------------------- */

typedef struct {
    PyObject_HEAD
    nrapp_t *application;
    int enabled;
} NRApplicationObject;

extern PyTypeObject NRApplication_Type;

/* ------------------------------------------------------------------------- */

extern PyObject *NRApplication_Singleton(PyObject *args, PyObject *kwds);

/* ------------------------------------------------------------------------- */

#endif
