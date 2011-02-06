#ifndef PY_WRAPPER_SETTINGS_H
#define PY_WRAPPER_SETTINGS_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include <Python.h>

/* ------------------------------------------------------------------------- */

typedef struct {
    PyObject_HEAD
} NRSettingsObject;

extern PyTypeObject NRSettings_Type;

/* ------------------------------------------------------------------------- */

extern PyObject *NRSetting_Singleton(PyObject *self, PyObject *args);

/* ------------------------------------------------------------------------- */

#endif

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */;
