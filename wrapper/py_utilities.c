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

PyObject *NRUtilities_LookupCallable(PyObject *module,
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

    if (PyModule_Check(module)) {
        Py_INCREF(module);
        module_object = module;
    }
    else
        module_object = PyImport_ImportModule(PyString_AsString(module));

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
                 * TODO This doesn't attempt to deal with nested classes.
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

PyObject *NRUtilities_CallableName(PyObject *wrapped, PyObject *wrapper,
                                   PyObject *args)
{
    PyObject *module_name = NULL;
    PyObject *class_name = NULL;
    PyObject *object_name = NULL;

    const char *module_name_string = NULL;
    const char *class_name_string = NULL;
    const char *object_name_string = NULL;

    int len = 0;
    char *s = NULL;

    PyObject *class_object = NULL;
    PyObject *method_object = NULL;

    PyObject *object = NULL;

    /*
     * When a decorator is used on a class method, it isn't
     * bound to a class instance at the time and so within the
     * decorator we are not able to determine the class. To work
     * out the class we need to look at the class associated
     * with the first argument, ie., self argument passed to the
     * method. Because though we don't know if we are even being
     * called as a class method we have to do an elaborate check
     * whereby we see if the first argument is a class instance
     * possessing a bound method for which the associated function
     * is our wrapper function.
     */

    if (wrapper && args) {
        if (PyFunction_Check(wrapped) && PyTuple_Size(args) >= 1) {
            class_object = PyObject_GetAttrString(
                    PyTuple_GetItem(args, 0), "__class__");
            if (class_object) {
                object_name = PyObject_GetAttrString(wrapped, "__name__");
                if (object_name) {
                   method_object = PyObject_GetAttr(class_object, object_name);
                   if (method_object && PyMethod_Check(method_object) &&
                       ((PyMethodObject *)method_object)->im_func == wrapper) {
                       object = method_object;
                   }
                }
            }
        }

        Py_XDECREF(class_object);
        Py_XDECREF(method_object);
        Py_XDECREF(object_name);

        class_object = NULL;
        method_object = NULL;
        object_name = NULL;

        PyErr_Clear();
    }

    if (!object) {
        Py_INCREF(wrapped);
        object = wrapped;
    }

    /*
     * Derive, module, class and object name.
     *
     * TODO This doesn't attempt to deal with nested classes.
     *
     * TODO Should exceptions from PyObject_GetAttrString() be
     * cleared immediately.
     */

    module_name = PyObject_GetAttrString(object, "__module__");

    if (module_name && PyString_Check(module_name))
        module_name_string = PyString_AsString(module_name);

    class_name_string = "";
    object_name_string = "";

    if (PyType_Check(object) || PyClass_Check(object)) {
        class_name = PyObject_GetAttrString(object, "__name__");
        if (class_name && PyString_Check(class_name))
            class_name_string = PyString_AsString(class_name);
        object_name_string = "__init__";
    }
    else if (PyMethod_Check(object)) {
        class_name = PyObject_GetAttrString(((PyMethodObject *)
                                            object)->im_class, "__name__");
        if (class_name && PyString_Check(class_name))
            class_name_string = PyString_AsString(class_name);
        object_name = PyObject_GetAttrString(object, "__name__");
        if (object_name && PyString_Check(object_name))
            object_name_string = PyString_AsString(object_name);
    }
    else if (PyFunction_Check(object)) {
        class_name_string = NULL;
        object_name = PyObject_GetAttrString(object, "__name__");
        if (object_name && PyString_Check(object_name))
            object_name_string = PyString_AsString(object_name);
    }
    else if (PyInstance_Check(object)) {
        class_object = PyObject_GetAttrString(object, "__class__");
        if (class_object) {
            class_name = PyObject_GetAttrString(class_object, "__name__");
            if (class_name && PyString_Check(class_name))
                class_name_string = PyString_AsString(class_name);
        }
        object_name_string = "__call__";
    }
    else if ((class_object = PyObject_GetAttrString(object, "__class__"))) {
        class_name = PyObject_GetAttrString(class_object, "__name__");
        if (class_name && PyString_Check(class_name))
            class_name_string = PyString_AsString(class_name);
        object_name_string = "__call__";
    }
    else
    {
        class_name_string = NULL;
        object_name_string = NULL;
    }

    PyErr_Clear();

    /* Construct the composite name. */

    if (module_name_string)
        len += strlen(module_name_string);
    if (module_name_string && class_name_string)
        len += 1;
    if (class_name_string)
        len += strlen(class_name_string);

    len += 2;
    len += strlen(object_name_string);
    len += 1;

    s = alloca(len);
    *s = '\0';

    if (module_name_string)
        strcat(s, module_name_string);
    if (module_name_string && class_name_string)
        strcat(s, ".");
    if (class_name_string)
        strcat(s, class_name_string);

    strcat(s, "::");
    strcat(s, object_name_string);

    Py_XDECREF(module_name);
    Py_XDECREF(class_object);
    Py_XDECREF(class_name);
    Py_XDECREF(object_name);

    Py_XDECREF(object);

    return PyString_FromString(s);
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
         *
         * XXX Check this. The latter means the type as a whole
         * is being modified and so only should be done when
         * modifying the raw method functions of a C API class
         * implementation. Should perhaps check explicitly for
         * that scenario and only do it if sensible. If can't do
         * that then raise an error indicating can't wrap the
         * target object.
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

PyObject *NRUtilities_StackTrace(void)
{
    PyObject *module;
    PyObject *result = NULL;

    module = PyImport_ImportModule("traceback");

    if (module) {
        PyObject *dict = NULL;
        PyObject *object = NULL;

        dict = PyModule_GetDict(module);
        object = PyDict_GetItemString(dict, "format_stack");

        if (object) {
            PyObject *args = NULL;

            Py_INCREF(object);

            args = PyTuple_New(0);
            result = PyObject_Call(object, args, NULL);

            Py_DECREF(args);
            Py_DECREF(object);
        }

        Py_DECREF(module);
    }

    return result;
}

/* ------------------------------------------------------------------------- */

extern PyObject *NRUtilities_ObfuscateTransactionName(const char *name,
                                                      const char *license_key)
{
  PyObject *result = NULL;

  PyObject *module = NULL;
  PyObject *dict = NULL;
  PyObject *object = NULL;
  PyObject *args = NULL;

  int len = strlen(name);
  unsigned char *xored = alloca(len+1);
  int i;

  for (i = 0; i < len; i++) {
    int licenseIndex = i % 13;
    char c = name[i] ^ license_key[licenseIndex];
    xored[i] = c;
  }

  xored[len] = '\0';

  module = PyImport_ImportModule("base64");

  if (!module)
      return NULL;

  dict = PyModule_GetDict(module);

  object = PyDict_GetItemString(dict, "b64encode");

  if (!object) {
      Py_DECREF(module);
      return NULL;
  }

  Py_INCREF(object);

  args = Py_BuildValue("(s#)", (char *)xored, len);
  result = PyEval_CallObject(object, args);

  Py_DECREF(module);
  Py_DECREF(object);
  Py_DECREF(args);

  return result;
}

/* ------------------------------------------------------------------------- */

/*
 * vim: set cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
