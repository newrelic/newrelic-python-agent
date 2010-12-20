#ifndef PY_WRAPPER_SETTINGS_H
#define PY_WRAPPER_SETTINGS_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include <Python.h>

/* ------------------------------------------------------------------------- */

typedef struct {
    PyObject_HEAD
} NRSettingsObject;

extern PyTypeObject NRSettings_Type;

/* ------------------------------------------------------------------------- */

extern NRSettingsObject *NRSettings_New(void);

/* ------------------------------------------------------------------------- */

#endif
