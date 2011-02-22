/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_wrapped_object.h"

/* ------------------------------------------------------------------------- */

static PyObject *NRWrappedObject_LookupCallable(const char *module_name,
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

PyObject *NRWrappedObject_WrapPreFunction(const char *module_name,
                                          const char *class_name,
                                          const char *name,
                                          PyObject *function)
{
    PyObject *callable_object = NULL;

    PyObject *parent_object = NULL;
    const char *attribute_name = NULL;

    callable_object = NRWrappedObject_LookupCallable(module_name, class_name,
                                                     name, &parent_object,
                                                     &attribute_name);

    if (!callable_object)
        return NULL;

    Py_DECREF(parent_object);

    return callable_object;
}

/* ------------------------------------------------------------------------- */

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */;
