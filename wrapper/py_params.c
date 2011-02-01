/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_params.h"

#include "genericobject.h"

/* ------------------------------------------------------------------------- */

void nrpy__merge_dict_into_params_at(nrobj_t array,
                                     const char *name, PyObject *dict)
{
    Py_ssize_t pos = 0;

    PyObject *key;
    PyObject *value;

    if (!PyDict_Check(dict))
        return;

    if (PyDict_Size(dict) == 0)
        return;

    while (PyDict_Next(dict, &pos, &key, &value)) {
        PyObject *key_as_string = NULL;
        PyObject *value_as_string = NULL;

        key_as_string = PyObject_Str(key);

        if (!key_as_string)
           PyErr_Clear();

        value_as_string = PyObject_Str(value);

        if (!value_as_string)
           PyErr_Clear();

        if (key_as_string && value_as_string) {
            nro__set_in_hash_at(array, name,
                    PyString_AsString(key_as_string),
                    nro__new_string(PyString_AsString(value_as_string)));
        }

        Py_XDECREF(key_as_string);
        Py_XDECREF(value_as_string);
    }
}

/* ------------------------------------------------------------------------- */
