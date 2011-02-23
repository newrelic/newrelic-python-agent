/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_utilities.h"

#include "genericobject.h"
#include "web_transaction.h"

/* ------------------------------------------------------------------------- */

PyObject *NRUtilities_FormatException(PyObject *type, PyObject *value,
                                      PyObject *traceback)
{
    PyObject *module = NULL;
    PyObject *stack_trace = NULL;

    /*
     * If we don't believe we have been given value valid
     * exception info return None.
     */

    if (type == Py_None && value == Py_None && traceback == Py_None) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    /*
     * Generate a formatted stack trace with the details of
     * exception. We don't check the types of the arguments if
     * all are not None. If any are wrong that should be picked
     * up by the code below and they will flag the error.
     */

    module = PyImport_ImportModule("traceback");

    if (module) {
        PyObject *dict = NULL;
        PyObject *object = NULL;

        dict = PyModule_GetDict(module);
        object = PyDict_GetItemString(dict, "format_exception");

        if (object) {
            PyObject *args = NULL;
            PyObject *result = NULL;

            Py_INCREF(object);

            args = PyTuple_Pack(3, type, value, traceback);
            result = PyObject_Call(object, args, NULL);

            Py_DECREF(object);
            Py_DECREF(args);

            if (result) {
                PyObject *sep = NULL;

                sep = PyString_FromString("");
                stack_trace = _PyString_Join(sep, result);

                Py_DECREF(sep);
                Py_DECREF(result);
            }
        }

        Py_DECREF(module);
    }

    return stack_trace;
}

/* ------------------------------------------------------------------------- */

PyObject *NRUtilities_LookupCallable(const char *module_name,
                                     const char *class_name,
                                     const char *object_name,
                                     PyObject **parent_object,
                                     const char **attribute_name)
{
    PyObject *module_object = NULL;

    PyObject *callable_object = NULL;

    *parent_object = NULL;
    *attribute_name = NULL;

    if (!class_name && !object_name) {
        PyErr_SetString(PyExc_RuntimeError, "class or object name must be "
                        "supplied");
        return NULL;
    }

    module_object = PyImport_ImportModule(module_name);

    if (module_object) {
        PyObject *dict = NULL;

        PyObject *class_object = NULL;

        dict = PyModule_GetDict(module_object);

        if (class_name) {
            class_object = PyDict_GetItemString(dict, class_name);

            if (!class_object) {
                PyErr_SetString(PyExc_RuntimeError, "no such module "
                                "attribute");
                Py_DECREF(module_object);
                return NULL;
            }

            if (!PyType_Check(class_object) && !PyClass_Check(class_object)) {
                PyErr_Format(PyExc_RuntimeError, "not a valid class type, "
                             "found %s", class_object->ob_type->tp_name);
                Py_DECREF(module_object);
                return NULL;
            }

            if (!object_name) {
                /*
		 * In case of class name but no object name, the
		 * the parent object is the module and the
		 * callable object is the class object itself.
                 */

                Py_INCREF(module_object);
                *parent_object = module_object;

                *attribute_name = class_name;

                Py_INCREF(class_object);
                callable_object = class_object;
            }
            else {
                /*
                 * TODO This can't handle nested classes.
                 */

                callable_object = PyObject_GetAttrString(class_object,
                                                         object_name);

                if (!callable_object) {
                    PyErr_SetString(PyExc_RuntimeError, "no such class "
                                    "attribute");
                    Py_DECREF(module_object);
                    return NULL;
                }

                /*
		 * In case of class name and object name, the
		 * parent object is the class and the callable
		 * object is the object which is the attribute
		 * of the class.
                 */

                Py_INCREF(class_object);
                *parent_object = class_object;

                *attribute_name = object_name;

                Py_INCREF(callable_object);
            }
        }
        else {
            callable_object = PyDict_GetItemString(dict, object_name);

            if (!callable_object) {
                PyErr_SetString(PyExc_RuntimeError, "no such module "
                                "attribute");
                Py_DECREF(module_object);
                return NULL;
            }

            /*
             * In case of no class name and object name, the
             * parent object is the module and the callable
             * object is the object which is the attribute
             * of the module.
             */

            Py_INCREF(module_object);
            *parent_object = module_object;

            *attribute_name = object_name;

            Py_INCREF(callable_object);
        }

        Py_DECREF(module_object);
    }
    else {
        PyErr_SetString(PyExc_RuntimeError, "not a valid module");
        return NULL;
    }

    return callable_object;
}

/* ------------------------------------------------------------------------- */

PyObject *NRUtilities_ReplaceWithWrapper(PyObject *parent_object,
                                         const char *attribute_name,
                                         PyObject *wrapper_object)
{
    if (PyModule_Check(parent_object)) {
        /*
	 * For a module, need to access the module dictionary
	 * and replace the attribute.
         */

        PyObject *dict = NULL;

        dict = PyModule_GetDict(parent_object);

        PyDict_SetItemString(dict, attribute_name, wrapper_object);
    }
    else {
        /*
	 * For everything else we attempt to use the attribute
         * interface of an object to replace the attribute. If
         * that doesn't work then modify the objects dictionary
         * directly instead.
         */

        if (PyObject_SetAttrString(parent_object, attribute_name,
                               wrapper_object) == -1) {
            PyObject *dict = NULL;

            PyErr_Clear();

            dict = ((PyTypeObject *)parent_object)->tp_dict;

            PyDict_SetItemString(dict, attribute_name, wrapper_object);
        }
    }

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

void NRUtilities_MergeDictIntoParams(nrobj_t array, const char *name,
                                     PyObject *dict)
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

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
