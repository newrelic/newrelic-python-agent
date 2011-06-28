#ifndef PY_WRAPPER_LOG_FILE_H
#define PY_WRAPPER_LOG_FILE_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_python.h"

/* ------------------------------------------------------------------------- */

typedef struct {
    PyObject_HEAD
    int level;
    char *s;
    int l;
    int softspace;
} NRLogFileObject;

extern PyTypeObject NRLogFile_Type;

/* ------------------------------------------------------------------------- */

extern PyObject *NRLogFile_LogException(PyObject *etype, PyObject *value,
                                        PyObject *tb, PyObject *limit,
                                        PyObject *file);

/* ------------------------------------------------------------------------- */

#endif

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
