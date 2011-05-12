#ifndef PY_WRAPPER_PYTHON_H
#define PY_WRAPPER_PYTHON_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include <Python.h>

/* ------------------------------------------------------------------------- */

#if !defined(PY_VERSION_HEX)
#error Sorry, Python developer package does not appear to be installed.
#endif

#if PY_VERSION_HEX <= 0x02040000
#error Sorry, require at least Python 2.4.0 for Python 2.X.
#endif

#if PY_VERSION_HEX >= 0x03000000 && PY_VERSION_HEX < 0x03010000
#error Sorry, require at least Python 3.1.0 for Python 3.X.
#endif

#if PY_MAJOR_VERSION >= 3
#error Sorry, do not support Python 3.X at this time.
#endif

/* ------------------------------------------------------------------------- */

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

/* ------------------------------------------------------------------------- */

#endif

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
