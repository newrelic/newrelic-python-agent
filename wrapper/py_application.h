#ifndef PY_WRAPPER_APPLICATION_H
#define PY_WRAPPER_APPLICATION_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "nrtypes.h"

#include "py_python.h"

/* ------------------------------------------------------------------------- */

typedef struct {
    PyObject_HEAD
    nrapp_t *application;
    PyObject *secondaries;
    int enabled;
} NRApplicationObject;

extern PyTypeObject NRApplication_Type;

/* ------------------------------------------------------------------------- */

extern PyObject *NRApplication_Singleton(PyObject *args, PyObject *kwds);

/* ------------------------------------------------------------------------- */

#endif

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
