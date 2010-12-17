#ifndef PY_WRAPPER_GLOBAL_SETTINGS_H
#define PY_WRAPPER_GLOBAL_SETTINGS_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include <Python.h>

/* ------------------------------------------------------------------------- */

typedef struct {
    PyObject_HEAD
} NRGlobalSettingsObject;

extern PyTypeObject NRGlobalSettings_Type;

/* ------------------------------------------------------------------------- */

extern NRGlobalSettingsObject *NRGlobalSettings_New(void);

/* ------------------------------------------------------------------------- */

#endif
