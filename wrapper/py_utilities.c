/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_utilities.h"

#include "genericobject.h"
#include "web_transaction.h"

#include <string.h>

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

PyObject *NRUtilities_CallableName(PyObject *wrapped, PyObject *wrapper,
                                   PyObject *args)
{
    PyObject *context = NULL;

    PyObject *module_name = NULL;
    PyObject *object_name = NULL;

    PyObject *result = NULL;

    context = NRUtilities_ObjectContext(wrapped, wrapper, args);

    module_name = PyTuple_GetItem(context, 0);
    object_name = PyTuple_GetItem(context, 1);

    result = PyString_FromFormat("%s:%s",
            PyString_AsString(module_name),
            PyString_AsString(object_name));

    Py_DECREF(context);

    return result;
}

/* ------------------------------------------------------------------------- */

PyObject *NRUtilities_ResolveObject(PyObject *module,
                                    PyObject *object_name,
                                    PyObject **parent_object,
                                    PyObject **attribute_name)
{
    PyObject *dict = NULL;

    PyObject *node_object1 = NULL;
    PyObject *node_object2 = NULL;

    PyObject *attribute = NULL;

    const char *s = NULL;
    const char *p = NULL;

    *parent_object = NULL;
    *attribute_name = NULL;

    /*
     * If the module reference is not actually a module already
     * then assume being supplied a module name and import it.
     */

    if (PyModule_Check(module)) {
        Py_INCREF(module);
        node_object1 = module;
    }
    else
        node_object1 = PyImport_ImportModule(PyString_AsString(module));

    if (!node_object1) {
        PyErr_SetString(PyExc_RuntimeError, "not a valid module");
        return NULL;
    }

    /*
     * Now need to traverse the dotted path provided as object
     * name. The first lookup needs to be against the module
     * dictionary and subsequent to that will be lookups of
     * object attributes.
     */

    s = PyString_AsString(object_name);

    p = strchr(s, '.');

    if (p) {
        attribute = PyString_FromStringAndSize(s, p-s);
        s = p+1;
    }
    else {
        Py_INCREF(object_name);
        attribute = object_name;
        s = NULL;
    }

    dict = PyModule_GetDict(node_object1);

    node_object2 = PyDict_GetItem(dict, attribute);

    if (!node_object2) {
        PyErr_SetString(PyExc_RuntimeError, "no such module attribute");
        Py_DECREF(node_object1);
        Py_DECREF(attribute);
        return NULL;
    }

    Py_INCREF(node_object2);

    while (s) {
        Py_DECREF(attribute);

        p = strchr(s, '.');

        if (p) {
            attribute = PyString_FromStringAndSize(s, p-s);
            s = p+1;
        }
        else {
            attribute = PyString_FromString(s);
            s = NULL;
        }

        Py_DECREF(node_object1);
        node_object1 = node_object2;

        node_object2 = PyObject_GetAttr(node_object1, attribute);

        if (!node_object2) {
            Py_DECREF(node_object1);
            Py_DECREF(attribute);
            return NULL;
        }
    }

    *parent_object = node_object1;
    *attribute_name = attribute;

    return node_object2;
}

/* ------------------------------------------------------------------------- */

PyObject *NRUtilities_ObjectContext(PyObject *wrapped, PyObject *wrapper,
                                    PyObject *args)
{
    PyObject *module_name = NULL;
    PyObject *class_name = NULL;
    PyObject *object_name = NULL;

    PyObject *class_object = NULL;
    PyObject *method_object = NULL;

    PyObject *target = NULL;
    PyObject *object = NULL;

    PyObject *attribute_name = NULL;

    PyObject *result = NULL;

    /*
     * We need to deal with case where we may have wrapped a
     * wrapper. In that case we need to check for the
     * __wrapped__ attribute and follow the chain of these to
     * get to the inner most object which isn't marked as being
     * a wrapper.
     *
     * TODO Should we perhaps only follow __wrapped__ for our
     * own wrapper objects given that convention of using a
     * wrapped attribute exists for Python 3.2+.
     */

    target = wrapped;
    Py_INCREF(target);

    object = PyObject_GetAttrString(target, "__wrapped__");

    while (object) {
        Py_DECREF(target);
        target = object;
        object = PyObject_GetAttrString(target, "__wrapped__");
    }

    PyErr_Clear();

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
        if (PyFunction_Check(target) && PyTuple_Size(args) >= 1) {
            class_object = PyObject_GetAttrString(
                    PyTuple_GetItem(args, 0), "__class__");
            if (class_object) {
                object_name = PyObject_GetAttrString(target, "__name__");
                if (object_name) {
                   method_object = PyObject_GetAttr(class_object, object_name);
                   if (method_object && PyMethod_Check(method_object) &&
                       ((PyMethodObject *)method_object)->im_func == wrapper) {
                       object = method_object;
                   }
                }
            }
        }

        /*
	 * XXX This DECREF's method_object but then it is used
	 * below via object variable.
         */

        Py_XDECREF(class_object);
        Py_XDECREF(method_object);
        Py_XDECREF(object_name);

        class_object = NULL;
        method_object = NULL;
        object_name = NULL;

        PyErr_Clear();
    }

    if (!object) {
        Py_INCREF(target);
        object = target;
    }

    module_name = PyObject_GetAttrString(object, "__module__");

    if (PyType_Check(object) || PyClass_Check(object)) {
        class_name = PyObject_GetAttrString(object, "__name__");
    }
    else if (PyMethod_Check(object)) {
        class_name = PyObject_GetAttrString(((PyMethodObject *)
                                            object)->im_class, "__name__");
        object_name = PyObject_GetAttrString(object, "__name__");
    }
    else if (PyFunction_Check(object)) {
        object_name = PyObject_GetAttrString(object, "__name__");
    }
    else if (PyInstance_Check(object)) {
        class_object = PyObject_GetAttrString(object, "__class__");
        if (class_object)
            class_name = PyObject_GetAttrString(class_object, "__name__");
    }
    else if ((class_object = PyObject_GetAttrString(object, "__class__"))) {
        class_name = PyObject_GetAttrString(class_object, "__name__");
        object_name = PyObject_GetAttrString(object, "__name__");
    }

    PyErr_Clear();

    if (!module_name || !PyString_Check(module_name)) {
        module_name = PyString_FromString("<unknown>");
        attribute_name = PyString_FromString("<unknown>");
        result = PyTuple_Pack(2, module_name, attribute_name);
    }
    else if (class_name && !PyString_Check(class_name)) {
        module_name = PyString_FromString("<unknown>");
        attribute_name = PyString_FromString("<unknown>");
        result = PyTuple_Pack(2, module_name, attribute_name);
    }
    else if (object_name && !PyString_Check(object_name)) {
        module_name = PyString_FromString("<unknown>");
        attribute_name = PyString_FromString("<unknown>");
        result = PyTuple_Pack(2, module_name, attribute_name);
    }
    else if (class_name && object_name) {
        attribute_name = PyString_FromFormat("%s.%s",
                PyString_AsString(class_name),
                PyString_AsString(object_name));
        result = PyTuple_Pack(2, module_name, attribute_name);
    }
    else if (class_name && !object_name) {
        result = PyTuple_Pack(2, module_name, class_name);
    }
    else if (!class_name && object_name) {
        result = PyTuple_Pack(2, module_name, object_name);
    }
    else {
        attribute_name = PyString_FromString("<unknown>");
        result = PyTuple_Pack(2, module_name, attribute_name);
    }

    Py_XDECREF(module_name);
    Py_XDECREF(class_object);
    Py_XDECREF(class_name);
    Py_XDECREF(object_name);

    Py_XDECREF(object);

    Py_XDECREF(attribute_name);

    Py_DECREF(target);

    return result;
}

/* ------------------------------------------------------------------------- */

PyObject *NRUtilities_ReplaceWithWrapper(PyObject *parent_object,
                                         PyObject *attribute_name,
                                         PyObject *wrapper_object)
{
    if (PyModule_Check(parent_object)) {
        /*
         * For a module, need to access the module dictionary
         * and replace the attribute.
         */

        PyObject *dict = NULL;

        dict = PyModule_GetDict(parent_object);

        PyDict_SetItem(dict, attribute_name, wrapper_object);
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

        if (PyObject_SetAttr(parent_object, attribute_name,
                               wrapper_object) == -1) {
            PyObject *dict = NULL;

            PyErr_Clear();

            dict = ((PyTypeObject *)parent_object)->tp_dict;

            PyDict_SetItem(dict, attribute_name, wrapper_object);
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
