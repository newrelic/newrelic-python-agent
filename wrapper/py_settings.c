/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_settings.h"

#include "globals.h"
#include "logging.h"

/* ------------------------------------------------------------------------- */

static PyObject *NRSettingsObject_instance = NULL;

/* ------------------------------------------------------------------------- */

PyObject *NRSetting_Singleton(PyObject *self, PyObject *args)
{
    if (!NRSettingsObject_instance) {
        NRSettingsObject_instance = (PyObject *)PyObject_New(
                NRSettingsObject, &NRSettings_Type);

        if (NRSettingsObject_instance == NULL)
            return NULL;
    }

    Py_INCREF(NRSettingsObject_instance);

    return NRSettingsObject_instance;
}

/* ------------------------------------------------------------------------- */

static void NRSettings_dealloc(NRSettingsObject *self)
{
    PyObject_Del(self);
}

static PyObject *NRSettings_get_logfile(NRSettingsObject *self,
                                              void *closure)
{
    if (nr_per_process_globals.logfilename)
        return PyString_FromString(nr_per_process_globals.logfilename);

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static int NRSettings_set_logfile(NRSettingsObject *self,
                                        PyObject *value)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "can't delete logfile attribute");
        return -1;
    }

    if (!PyString_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected string for log file name");
        return -1;
    }

    if (nr_per_process_globals.logfilename)
        nrfree(nr_per_process_globals.logfilename);

    nr_per_process_globals.logfilename = nrstrdup(PyString_AsString(value));

    return 0;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRSettings_get_loglevel(NRSettingsObject *self,
                                               void *closure)
{
    return PyInt_FromLong(nr_per_process_globals.loglevel);
}

/* ------------------------------------------------------------------------- */

static int NRSettings_set_loglevel(NRSettingsObject *self,
                                        PyObject *value)
{
    int loglevel;

    if (value == NULL) {
        PyErr_SetString(PyExc_TypeError, "can't delete loglevel attribute");
        return -1;
    }

    if (!PyInt_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "expected integer for log level");
        return -1;
    }

    loglevel = PyInt_AsLong(value);

    /*
     * Constrain value as LOG_DUMP level in PHP code appears to
     * have problems and can get stuck in loop dumping lots of
     * blank lines into log file.
     */

    if (loglevel < LOG_ERROR || loglevel > LOG_VERBOSEDEBUG) {
        PyErr_SetString(PyExc_ValueError, "log level out of range");
        return -1;
    }

    nr_per_process_globals.loglevel = loglevel;

    return 0;
}

/* ------------------------------------------------------------------------- */

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

static PyMethodDef NRSettings_methods[] = {
    { NULL, NULL }
};

static PyGetSetDef NRSettings_getset[] = {
    { "logfile",            (getter)NRSettings_get_logfile,
                            (setter)NRSettings_set_logfile, 0 },
    { "loglevel",           (getter)NRSettings_get_loglevel,
                            (setter)NRSettings_set_loglevel, 0 },
    { NULL },
};

PyTypeObject NRSettings_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.Settings", /*tp_name*/
    sizeof(NRSettingsObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRSettings_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    0,                      /*tp_call*/
    0,                      /*tp_str*/
    0,                      /*tp_getattro*/
    0,                      /*tp_setattro*/
    0,                      /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT,     /*tp_flags*/
    0,                      /*tp_doc*/
    0,                      /*tp_traverse*/
    0,                      /*tp_clear*/
    0,                      /*tp_richcompare*/
    0,                      /*tp_weaklistoffset*/
    0,                      /*tp_iter*/
    0,                      /*tp_iternext*/
    NRSettings_methods,     /*tp_methods*/
    0,                      /*tp_members*/
    NRSettings_getset,      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    0,                      /*tp_init*/
    0,                      /*tp_alloc*/
    0,                      /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */;
