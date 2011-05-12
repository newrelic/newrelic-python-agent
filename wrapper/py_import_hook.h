#ifndef PY_WRAPPER_IMPORT_HOOK_H
#define PY_WRAPPER_IMPORT_HOOK_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_python.h"

/* ------------------------------------------------------------------------- */

typedef struct {
    PyObject_HEAD
    PyObject *skip;
} NRImportHookFinderObject;

extern PyTypeObject NRImportHookFinder_Type;

typedef struct {
    PyObject_HEAD
} NRImportHookLoaderObject;

extern PyTypeObject NRImportHookLoader_Type;

typedef struct {
    PyObject_HEAD
    PyObject *name;
} NRImportHookDecoratorObject;

extern PyTypeObject NRImportHookDecorator_Type;

/* ------------------------------------------------------------------------- */

PyObject *NRImport_GetImportHooks(void);

PyObject *NRImport_RegisterImportHook(PyObject *name, PyObject *callable);

PyObject *NRImport_NotifyHooks(PyObject *name, PyObject *module);

/* ------------------------------------------------------------------------- */

#endif

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
