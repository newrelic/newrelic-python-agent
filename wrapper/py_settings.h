#ifndef PY_WRAPPER_SETTINGS_H
#define PY_WRAPPER_SETTINGS_H

/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include <Python.h>

/* ------------------------------------------------------------------------- */

typedef struct {
    PyObject_HEAD
    int64_t transaction_threshold;
    int transaction_threshold_is_apdex_f;
} NRTracerSettingsObject;

extern PyTypeObject NRTracerSettings_Type;

typedef struct {
    PyObject_HEAD
    PyObject *ignore_errors;
} NRErrorsSettingsObject;

extern PyTypeObject NRErrorsSettings_Type;

typedef struct {
    PyObject_HEAD
    int auto_instrument;
} NRBrowserSettingsObject;

extern PyTypeObject NRBrowserSettings_Type;

typedef struct {
    PyObject_HEAD
} NRDebugSettingsObject;

extern PyTypeObject NRDebugSettings_Type;

typedef struct {
    PyObject_HEAD
    PyObject *config_file;
    PyObject *environment;
    NRTracerSettingsObject *tracer_settings;
    NRErrorsSettingsObject *errors_settings;
    NRBrowserSettingsObject *browser_settings;
    NRDebugSettingsObject *debug_settings;
    int monitor_mode;
    PyObject *ignored_params;
} NRSettingsObject;

extern PyTypeObject NRSettings_Type;

/* ------------------------------------------------------------------------- */

extern PyObject *NRSettings_Singleton(void);

/* ------------------------------------------------------------------------- */

#endif

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
