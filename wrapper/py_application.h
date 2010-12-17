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
    int enabled;
} NRApplicationObject;

extern PyTypeObject NRApplication_Type;

/* ------------------------------------------------------------------------- */

NRApplicationObject *NRApplication_New(const char *name,
                                       const char *framework);

/* ------------------------------------------------------------------------- */

#endif
