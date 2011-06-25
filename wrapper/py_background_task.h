#ifndef PY_WRAPPER_BACKGROUND_TASK_H
#define PY_WRAPPER_BACKGROUND_TASK_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_transaction.h"

/* ------------------------------------------------------------------------- */

extern PyTypeObject NRBackgroundTask_Type;

typedef struct {
    PyObject_HEAD
    PyObject *dict;
    PyObject *next_object;
    PyObject *last_object;
    PyObject *application;
    PyObject *name;
    PyObject *scope;
} NRBackgroundTaskWrapperObject;

extern PyTypeObject NRBackgroundTaskWrapper_Type;

typedef struct {
    PyObject_HEAD
    PyObject *application;
    PyObject *name;
    PyObject *scope;
} NRBackgroundTaskDecoratorObject;

extern PyTypeObject NRBackgroundTaskDecorator_Type;

/* ------------------------------------------------------------------------- */

#endif

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
