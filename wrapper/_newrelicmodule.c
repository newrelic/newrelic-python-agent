/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include <Python.h>

#include "py_settings.h"

#include "py_application.h"

#include "py_background_task.h"
#include "py_database_trace.h"
#include "py_error_trace.h"
#include "py_external_trace.h"
#include "py_function_trace.h"
#include "py_memcache_trace.h"
#include "py_name_transaction.h"
#include "py_transaction.h"
#include "py_web_transaction.h"

#include "py_in_function.h"
#include "py_out_function.h"
#include "py_post_function.h"
#include "py_pre_function.h"

#include "py_import_hook.h"

#include "py_utilities.h"

#include "globals.h"
#include "logging.h"

#include "nrthread.h"
#include "nrtypes.h"

#include "application.h"
#include "daemon_protocol.h"
#include "genericobject.h"
#include "harvest.h"
#include "metric_table.h"
#include "web_transaction.h"

#include "samplers.h"

/* ------------------------------------------------------------------------- */

static void newrelic_populate_environment(void)
{
    PyObject *module = NULL;

    /*
     * Gather together Python configuration information that is
     * usually exposed in the 'sys' module. We don't include
     * 'sys.path' as that can be different for each sub
     * interpreter and can also change over the lifetime of the
     * process.
     */

    nro__set_hash_string(nr_per_process_globals.env,
                         "Python Program Name", Py_GetProgramName());
    nro__set_hash_string(nr_per_process_globals.env,
                         "Python Home", Py_GetPythonHome());

    nro__set_hash_string(nr_per_process_globals.env,
                         "Python Program Full Path", Py_GetProgramFullPath());
    nro__set_hash_string(nr_per_process_globals.env,
                         "Python Prefix", Py_GetPrefix());
    nro__set_hash_string(nr_per_process_globals.env,
                         "Python Exec Prefix", Py_GetPrefix());
    nro__set_hash_string(nr_per_process_globals.env,
                         "Python Version", Py_GetVersion());
    nro__set_hash_string(nr_per_process_globals.env,
                         "Python Platform", Py_GetPlatform());
    nro__set_hash_string(nr_per_process_globals.env,
                         "Python Compiler", Py_GetCompiler());
    nro__set_hash_string(nr_per_process_globals.env,
                         "Python Build Info", Py_GetBuildInfo());
    
    /*
     * Also try and obtain the options supplied to the
     * 'configure' script when Python was built. It may not be
     * possible to get hold of this if the 'dev' variant of
     * Python package isn't installed as it relies on using
     * 'distutils' to extract the value of the 'CONFIG_ARGS'
     * variable from the 'Makefile' installed as part of the
     * 'dev' package for Python. If full installation of Python
     * has be done from source code, should be available. Is
     * only an issue when binary packages installed from a
     * repository are being used.
     */

    module = PyImport_ImportModule("distutils.sysconfig");

    if (module) {
        PyObject *dict = NULL;
        PyObject *object = NULL;

        dict = PyModule_GetDict(module);
        object = PyDict_GetItemString(dict, "get_config_var");

        if (object) {
            PyObject *args = NULL;
            PyObject *arg0 = NULL;
            PyObject *result = NULL;

            Py_INCREF(object);

            arg0 = PyString_FromString("CONFIG_ARGS");
            args = PyTuple_Pack(1, arg0);

            result = PyObject_Call(object, args, NULL);

            if (result && result != Py_None) {
                nro__set_hash_string(nr_per_process_globals.env,
                                     "Python Config Args",
                                     PyString_AsString(result));
            }
            else
                PyErr_Clear();

            Py_XDECREF(result);

            Py_DECREF(arg0);
            Py_DECREF(args);
            Py_DECREF(object);
        }
    }
    else
      PyErr_Clear();
}

/* ------------------------------------------------------------------------- */

static void newrelic_populate_plugin_list(void)
{
    /*
     * Closest we can get to a list of plugins in the list of
     * builtin modules. We can't use what is in sys.modules as
     * that will be different per sub interpreter and can change
     * over time due to dynamic loading of modules. Only gather
     * list of modules in 'sys.modules' when have an error we are
     * reporting.
     */

    int i;
    nrobj_t plugins;

    plugins = nro__new(NR_OBJECT_ARRAY);
    nro__set_hash_array(nr_per_process_globals.env, "Plugin List", plugins);

    for (i = 0; PyImport_Inittab[i].name != NULL; i++) {
        if (!PyImport_Inittab[i].name)
            break;

        nro__set_array_string (plugins, 0, PyImport_Inittab[i].name);
    }
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_application(PyObject *self, PyObject *args,
                                      PyObject *kwds)
{
    return NRApplication_Singleton(args, kwds);
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_settings(PyObject *self, PyObject *args)
{
    return NRSettings_Singleton();
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_log(PyObject *self, PyObject *args, PyObject *kwds)
{
    int level = 0;
    const char *message = NULL;

    static char *kwlist[] = { "level", "message", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "is:log",
                                     kwlist, &level, &message)) {
        return NULL;
    }

    Py_BEGIN_ALLOW_THREADS
    nr__log(level, "%s", message);
    Py_END_ALLOW_THREADS

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_harvest(PyObject *self, PyObject *args,
                                  PyObject *kwds)
{
    const char *reason = NULL;

    static char *kwlist[] = { "reason", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|z:harvest",
                                     kwlist, &reason)) {
        return NULL;
    }

    if (!reason)
        reason = "flush";

    Py_BEGIN_ALLOW_THREADS
    nr__harvest_thread_body(reason);
    Py_END_ALLOW_THREADS

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_transaction(PyObject *self, PyObject *args)
{
    PyObject *result;

    result = NRTransaction_CurrentTransaction();

    if (result) {
        Py_INCREF(result);
        return result;
    }

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_callable_name(PyObject *self, PyObject *args,
                                        PyObject *kwds)
{
    PyObject *object = NULL;

    static char *kwlist[] = { "object", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:callable_name",
                                     kwlist, &object)) {
        return NULL;
    }

    return NRUtilities_CallableName(object, NULL, NULL);
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_resolve_object(PyObject *self, PyObject *args,
                                         PyObject *kwds)
{
    PyObject *module = NULL;
    PyObject *object_name = NULL;

    PyObject *parent_object = NULL;
    PyObject *attribute_name = NULL;
    PyObject *object = NULL;

    PyObject *result = NULL;

    static char *kwlist[] = { "module", "object_name", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OS:resolve_object",
                                     kwlist, &module, &object_name)) {
        return NULL;
    }

    object = NRUtilities_ResolveObject(module, object_name, &parent_object,
                                       &attribute_name);

    if (!object)
        return NULL;

    result = PyTuple_Pack(3, parent_object, attribute_name, object);

    Py_DECREF(parent_object);
    Py_DECREF(attribute_name);
    Py_DECREF(object);

    return result;
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_object_context(PyObject *self, PyObject *args,
                                         PyObject *kwds)
{
    PyObject *object = NULL;

    static char *kwlist[] = { "object", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:object_context",
                                     kwlist, &object)) {
        return NULL;
    }

    return NRUtilities_ObjectContext(object, NULL, NULL);
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_web_transaction(PyObject *self, PyObject *args,
                                          PyObject *kwds)
{
    PyObject *application = Py_None;

    static char *kwlist[] = { "application", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|O:web_transaction",
                                     kwlist, &application)) {
        return NULL;
    }

    if (application != Py_None &&
        Py_TYPE(application) != &NRApplication_Type &&
        !PyString_Check(application) && !PyUnicode_Check(application)) {
        PyErr_Format(PyExc_TypeError, "application argument must be None, "
                     "str, unicode, or application object, found type '%s'",
                     application->ob_type->tp_name);
        return NULL;
    }

    return PyObject_CallFunctionObjArgs((PyObject *)
            &NRWebTransactionDecorator_Type, application, NULL);
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_wrap_web_transaction(PyObject *self, PyObject *args,
                                               PyObject *kwds)
{
    PyObject *module = NULL;
    const char *class_name = NULL;
    const char *object_name = NULL;

    PyObject *application = Py_None;

    PyObject *wrapped_object = NULL;
    PyObject *parent_object = NULL;
    const char *attribute_name = NULL;

    PyObject *wrapper_object = NULL;

    PyObject *result = NULL;

    static char *kwlist[] = { "module", "class_name", "object_name",
                              "application", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds,
                                     "Ozz|O:wrap_web_transaction",
                                     kwlist, &module, &class_name,
                                     &object_name, &application)) {
        return NULL;
    }

    if (!PyModule_Check(module) && !PyString_Check(module)) {
        PyErr_SetString(PyExc_TypeError, "module reference must be "
                        "module or string");
        return NULL;
    }

    if (!class_name && !object_name) {
        PyErr_SetString(PyExc_RuntimeError, "class or object name must be "
                        "supplied");
        return NULL;
    }

    if (application != Py_None &&
        Py_TYPE(application) != &NRApplication_Type &&
        !PyString_Check(application) && !PyUnicode_Check(application)) {
        PyErr_Format(PyExc_TypeError, "application argument must be None, "
                     "str, unicode, or application object, found type '%s'",
                     application->ob_type->tp_name);
        return NULL;
    }

    wrapped_object = NRUtilities_LookupCallable(module, class_name,
                                                object_name, &parent_object,
                                                &attribute_name);

    if (!wrapped_object)
        return NULL;

    wrapper_object = PyObject_CallFunctionObjArgs((PyObject *)
            &NRWebTransactionWrapper_Type, wrapped_object, application,
            NULL);

    result = NRUtilities_ReplaceWithWrapper(parent_object, attribute_name,
                                            wrapper_object);

    Py_DECREF(parent_object);
    Py_DECREF(wrapped_object);

    if (!result)
        return NULL;

    return wrapper_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_background_task(PyObject *self, PyObject *args,
                                          PyObject *kwds)
{
    PyObject *application = Py_None;
    PyObject *name = Py_None;

    static char *kwlist[] = { "application", "name", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|OO:background_task",
                                     kwlist, &application, &name)) {
        return NULL;
    }

    if (!PyString_Check(name) && !PyUnicode_Check(name) &&
        name != Py_None) {
        PyErr_Format(PyExc_TypeError, "name argument must be str, unicode, "
                     "or None, found type '%s'", name->ob_type->tp_name);
        return NULL;
    }

    if (application != Py_None &&
        Py_TYPE(application) != &NRApplication_Type &&
        !PyString_Check(application) && !PyUnicode_Check(application)) {
        PyErr_Format(PyExc_TypeError, "application argument must be None, "
                     "str, unicode, or application object, found type '%s'",
                     application->ob_type->tp_name);
        return NULL;
    }

    return PyObject_CallFunctionObjArgs((PyObject *)
            &NRBackgroundTaskDecorator_Type, application, name, NULL);
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_wrap_background_task(PyObject *self, PyObject *args,
                                               PyObject *kwds)
{
    PyObject *module = NULL;
    const char *class_name = NULL;
    const char *object_name = NULL;

    PyObject *application = Py_None;
    PyObject *name = Py_None;

    PyObject *wrapped_object = NULL;
    PyObject *parent_object = NULL;
    const char *attribute_name = NULL;

    PyObject *wrapper_object = NULL;

    PyObject *result = NULL;

    static char *kwlist[] = { "module", "class_name", "object_name",
                              "application", "name", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds,
                                     "Ozz|OO:wrap_background_task",
                                     kwlist, &module, &class_name,
                                     &object_name, &application, &name)) {
        return NULL;
    }

    if (!PyModule_Check(module) && !PyString_Check(module)) {
        PyErr_SetString(PyExc_TypeError, "module reference must be "
                        "module or string");
        return NULL;
    }

    if (!class_name && !object_name) {
        PyErr_SetString(PyExc_RuntimeError, "class or object name must be "
                        "supplied");
        return NULL;
    }

    if (!PyString_Check(name) && !PyUnicode_Check(name) &&
        name != Py_None) {
        PyErr_Format(PyExc_TypeError, "name argument must be str, unicode, "
                     "or None, found type '%s'", name->ob_type->tp_name);
        return NULL;
    }

    if (application != Py_None &&
        Py_TYPE(application) != &NRApplication_Type &&
        !PyString_Check(application) && !PyUnicode_Check(application)) {
        PyErr_Format(PyExc_TypeError, "application argument must be None, "
                     "str, unicode, or application object, found type '%s'",
                     application->ob_type->tp_name);
        return NULL;
    }

    wrapped_object = NRUtilities_LookupCallable(module, class_name,
                                                object_name, &parent_object,
                                                &attribute_name);

    if (!wrapped_object)
        return NULL;

    if (name == Py_None) {
        int len = 0;
        char *s = NULL;

        const char *module_name = NULL;

        if (PyModule_Check(module))
            module_name = PyModule_GetName(module);
        else
            module_name = PyString_AsString(module);

        if (module_name)
            len += strlen(module_name);
        if (module_name && class_name)
            len += 1;
        if (class_name)
            len += strlen(class_name);

        len += 2;
        len += strlen(object_name);
        len += 1;

        s = alloca(len);
        *s = '\0';

        if (module_name)
            strcat(s, module_name);
        if (module_name && class_name)
            strcat(s, ".");
        if (class_name)
            strcat(s, class_name);

        strcat(s, "::");
        strcat(s, object_name);

        name = PyString_FromString(s);
    }
    else
        Py_INCREF(name);

    wrapper_object = PyObject_CallFunctionObjArgs((PyObject *)
            &NRBackgroundTaskWrapper_Type, wrapped_object, application,
            name, NULL);

    result = NRUtilities_ReplaceWithWrapper(parent_object, attribute_name,
                                            wrapper_object);

    Py_DECREF(parent_object);
    Py_DECREF(wrapped_object);

    Py_DECREF(name);

    if (!result)
        return NULL;

    return wrapper_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_database_trace(PyObject *self, PyObject *args,
                                         PyObject *kwds)
{
    PyObject *sql = NULL;

    static char *kwlist[] = { "sql", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:database_trace",
                                     kwlist, &sql)) {
        return NULL;
    }

    return PyObject_CallFunctionObjArgs((PyObject *)
            &NRDatabaseTraceDecorator_Type, sql, NULL);
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_wrap_database_trace(PyObject *self, PyObject *args,
                                              PyObject *kwds)
{
    PyObject *module = NULL;
    const char *class_name = NULL;
    const char *object_name = NULL;
    PyObject *sql = NULL;

    PyObject *wrapped_object = NULL;
    PyObject *parent_object = NULL;
    const char *attribute_name = NULL;

    PyObject *wrapper_object = NULL;

    PyObject *result = NULL;

    static char *kwlist[] = { "module", "class_name", "object_name",
                              "sql", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OzzO:wrap_database_trace",
                                     kwlist, &module, &class_name,
                                     &object_name, &sql)) {
        return NULL;
    }

    if (!PyModule_Check(module) && !PyString_Check(module)) {
        PyErr_SetString(PyExc_TypeError, "module reference must be "
                        "module or string");
        return NULL;
    }

    if (!class_name && !object_name) {
        PyErr_SetString(PyExc_RuntimeError, "class or object name must be "
                        "supplied");
        return NULL;
    }

    wrapped_object = NRUtilities_LookupCallable(module, class_name,
                                                object_name, &parent_object,
                                                &attribute_name);

    if (!wrapped_object)
        return NULL;

    wrapper_object = PyObject_CallFunctionObjArgs((PyObject *)
            &NRDatabaseTraceWrapper_Type, wrapped_object, sql, NULL);

    result = NRUtilities_ReplaceWithWrapper(parent_object, attribute_name,
                                            wrapper_object);

    Py_DECREF(parent_object);
    Py_DECREF(wrapped_object);

    if (!result)
        return NULL;

    return wrapper_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_external_trace(PyObject *self, PyObject *args,
                                         PyObject *kwds)
{
    PyObject *url = NULL;

    static char *kwlist[] = { "url", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:external_trace",
                                     kwlist, &url)) {
        return NULL;
    }

    return PyObject_CallFunctionObjArgs((PyObject *)
            &NRExternalTraceDecorator_Type, url, NULL);
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_wrap_external_trace(PyObject *self, PyObject *args,
                                              PyObject *kwds)
{
    PyObject *module = NULL;
    const char *class_name = NULL;
    const char *object_name = NULL;
    PyObject *url = NULL;

    PyObject *wrapped_object = NULL;
    PyObject *parent_object = NULL;
    const char *attribute_name = NULL;

    PyObject *wrapper_object = NULL;

    PyObject *result = NULL;

    static char *kwlist[] = { "module", "class_name", "object_name",
                              "url", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OzzO:wrap_external_trace",
                                     kwlist, &module, &class_name,
                                     &object_name, &url)) {
        return NULL;
    }

    if (!PyModule_Check(module) && !PyString_Check(module)) {
        PyErr_SetString(PyExc_TypeError, "module reference must be "
                        "module or string");
        return NULL;
    }

    if (!class_name && !object_name) {
        PyErr_SetString(PyExc_RuntimeError, "class or object name must be "
                        "supplied");
        return NULL;
    }

    wrapped_object = NRUtilities_LookupCallable(module, class_name,
                                                object_name, &parent_object,
                                                &attribute_name);

    if (!wrapped_object)
        return NULL;

    wrapper_object = PyObject_CallFunctionObjArgs((PyObject *)
            &NRExternalTraceWrapper_Type, wrapped_object, url, NULL);

    result = NRUtilities_ReplaceWithWrapper(parent_object, attribute_name,
                                            wrapper_object);

    Py_DECREF(parent_object);
    Py_DECREF(wrapped_object);

    if (!result)
        return NULL;

    return wrapper_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_error_trace(PyObject *self, PyObject *args,
                                      PyObject *kwds)
{
    static char *kwlist[] = { NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, ":error_trace", kwlist))
        return NULL;

    return PyObject_CallFunctionObjArgs((PyObject *)
            &NRErrorTraceDecorator_Type, NULL);
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_wrap_error_trace(PyObject *self, PyObject *args,
                                           PyObject *kwds)
{
    PyObject *module = NULL;
    const char *class_name = NULL;
    const char *object_name = NULL;

    PyObject *wrapped_object = NULL;
    PyObject *parent_object = NULL;
    const char *attribute_name = NULL;

    PyObject *wrapper_object = NULL;

    PyObject *result = NULL;

    static char *kwlist[] = { "module", "class_name", "object_name",
                              NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "Ozz:wrap_error_trace",
                                     kwlist, &module, &class_name,
                                     &object_name)) {
        return NULL;
    }

    if (!PyModule_Check(module) && !PyString_Check(module)) {
        PyErr_SetString(PyExc_TypeError, "module reference must be "
                        "module or string");
        return NULL;
    }

    if (!class_name && !object_name) {
        PyErr_SetString(PyExc_RuntimeError, "class or object name must be "
                        "supplied");
        return NULL;
    }

    wrapped_object = NRUtilities_LookupCallable(module, class_name,
                                                object_name, &parent_object,
                                                &attribute_name);

    if (!wrapped_object)
        return NULL;

    wrapper_object = PyObject_CallFunctionObjArgs((PyObject *)
            &NRErrorTraceWrapper_Type, wrapped_object, NULL);

    result = NRUtilities_ReplaceWithWrapper(parent_object, attribute_name,
                                            wrapper_object);

    Py_DECREF(parent_object);
    Py_DECREF(wrapped_object);

    if (!result)
        return NULL;

    return wrapper_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_function_trace(PyObject *self, PyObject *args,
                                         PyObject *kwds)
{
    PyObject *name = Py_None;

    static char *kwlist[] = { "name", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|O:function_trace",
                                     kwlist, &name)) {
        return NULL;
    }

#if 0
    if (!PyString_Check(name) && !PyUnicode_Check(name) &&
        name != Py_None) {
        PyErr_Format(PyExc_TypeError, "name argument must be str, unicode, "
                     "or None, found type '%s'", name->ob_type->tp_name);
        return NULL;
    }
#endif

    return PyObject_CallFunctionObjArgs((PyObject *)
            &NRFunctionTraceDecorator_Type, name, NULL);
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_wrap_function_trace(PyObject *self, PyObject *args,
                                              PyObject *kwds)
{
    PyObject *module = NULL;
    const char *class_name = NULL;
    const char *object_name = NULL;

    PyObject *name = Py_None;

    PyObject *wrapped_object = NULL;
    PyObject *parent_object = NULL;
    const char *attribute_name = NULL;

    PyObject *wrapper_object = NULL;

    PyObject *result = NULL;

    static char *kwlist[] = { "module", "class_name", "object_name",
                              "name", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds,
                                     "Ozz|O:wrap_function_trace",
                                     kwlist, &module, &class_name,
                                     &object_name, &name)) {
        return NULL;
    }

    if (!PyModule_Check(module) && !PyString_Check(module)) {
        PyErr_SetString(PyExc_TypeError, "module reference must be "
                        "module or string");
        return NULL;
    }

    if (!class_name && !object_name) {
        PyErr_SetString(PyExc_RuntimeError, "class or object name must be "
                        "supplied");
        return NULL;
    }

#if 0
    if (!PyString_Check(name) && !PyUnicode_Check(name) &&
        name != Py_None) {
        PyErr_Format(PyExc_TypeError, "name argument must be str, unicode, "
                     "or None, found type '%s'", name->ob_type->tp_name);
        return NULL;
    }
#endif

    wrapped_object = NRUtilities_LookupCallable(module, class_name,
                                                object_name, &parent_object,
                                                &attribute_name);

    if (!wrapped_object)
        return NULL;

    if (name == Py_None) {
        int len = 0;
        char *s = NULL;

        const char *module_name = NULL;

        if (PyModule_Check(module))
            module_name = PyModule_GetName(module);
        else
            module_name = PyString_AsString(module);

        if (module_name)
            len += strlen(module_name);
        if (module_name && class_name)
            len += 1;
        if (class_name)
            len += strlen(class_name);

        len += 2;
        len += strlen(object_name);
        len += 1;

        s = alloca(len);
        *s = '\0';

        if (module_name)
            strcat(s, module_name);
        if (module_name && class_name)
            strcat(s, ".");
        if (class_name)
            strcat(s, class_name);

        strcat(s, "::");
        strcat(s, object_name);

        name = PyString_FromString(s);
    }
    else
        Py_INCREF(name);

    wrapper_object = PyObject_CallFunctionObjArgs((PyObject *)
            &NRFunctionTraceWrapper_Type, wrapped_object, name, NULL);

    result = NRUtilities_ReplaceWithWrapper(parent_object, attribute_name,
                                            wrapper_object);

    Py_DECREF(parent_object);
    Py_DECREF(wrapped_object);

    Py_DECREF(name);

    if (!result)
        return NULL;

    return wrapper_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_memcache_trace(PyObject *self, PyObject *args,
                                         PyObject *kwds)
{
    PyObject *command = NULL;

    static char *kwlist[] = { "command", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "S:memcache_trace",
                                     kwlist, &command)) {
        return NULL;
    }

    return PyObject_CallFunctionObjArgs((PyObject *)
            &NRMemcacheTraceDecorator_Type, command, NULL);
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_wrap_memcache_trace(PyObject *self, PyObject *args,
                                              PyObject *kwds)
{
    PyObject *module = NULL;
    const char *class_name = NULL;
    const char *object_name = NULL;
    PyObject *command = NULL;

    PyObject *wrapped_object = NULL;
    PyObject *parent_object = NULL;
    const char *attribute_name = NULL;

    PyObject *wrapper_object = NULL;

    PyObject *result = NULL;

    static char *kwlist[] = { "module", "class_name", "object_name",
                              "command", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OzzS:wrap_memcache_trace",
                                     kwlist, &module, &class_name,
                                     &object_name, &command)) {
        return NULL;
    }

    if (!PyModule_Check(module) && !PyString_Check(module)) {
        PyErr_SetString(PyExc_TypeError, "module reference must be "
                        "module or string");
        return NULL;
    }

    if (!class_name && !object_name) {
        PyErr_SetString(PyExc_RuntimeError, "class or object name must be "
                        "supplied");
        return NULL;
    }

    wrapped_object = NRUtilities_LookupCallable(module, class_name,
                                                object_name, &parent_object,
                                                &attribute_name);

    if (!wrapped_object)
        return NULL;

    wrapper_object = PyObject_CallFunctionObjArgs((PyObject *)
            &NRMemcacheTraceWrapper_Type, wrapped_object, command, NULL);

    result = NRUtilities_ReplaceWithWrapper(parent_object, attribute_name,
                                            wrapper_object);

    Py_DECREF(parent_object);
    Py_DECREF(wrapped_object);

    if (!result)
        return NULL;

    return wrapper_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_name_transaction(PyObject *self, PyObject *args,
                                           PyObject *kwds)
{
    PyObject *name = Py_None;

    static char *kwlist[] = { "name", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|O:name_transaction",
                                     kwlist, &name)) {
        return NULL;
    }

    return PyObject_CallFunctionObjArgs((PyObject *)
            &NRNameTransactionDecorator_Type, name, NULL);
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_wrap_name_transaction(PyObject *self, PyObject *args,
                                                PyObject *kwds)
{
    PyObject *module = NULL;
    const char *class_name = NULL;
    const char *object_name = NULL;

    PyObject *name = Py_None;

    PyObject *wrapped_object = NULL;
    PyObject *parent_object = NULL;
    const char *attribute_name = NULL;

    PyObject *wrapper_object = NULL;

    PyObject *result = NULL;

    static char *kwlist[] = { "module", "class_name", "object_name",
                              "name", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds,
                                     "Ozz|O:wrap_name_transaction",
                                     kwlist, &module, &class_name,
                                     &object_name, &name)) {
        return NULL;
    }

    if (!PyModule_Check(module) && !PyString_Check(module)) {
        PyErr_SetString(PyExc_TypeError, "module reference must be "
                        "module or string");
        return NULL;
    }

    if (!class_name && !object_name) {
        PyErr_SetString(PyExc_RuntimeError, "class or object name must be "
                        "supplied");
        return NULL;
    }

    wrapped_object = NRUtilities_LookupCallable(module, class_name,
                                                object_name, &parent_object,
                                                &attribute_name);

    if (!wrapped_object)
        return NULL;

    if (name == Py_None) {
        int len = 0;
        char *s = NULL;

        const char *module_name = NULL;

        if (PyModule_Check(module))
            module_name = PyModule_GetName(module);
        else
            module_name = PyString_AsString(module);

        if (module_name)
            len += strlen(module_name);
        if (module_name && class_name)
            len += 1;
        if (class_name)
            len += strlen(class_name);

        len += 2;
        len += strlen(object_name);
        len += 1;

        s = alloca(len);
        *s = '\0';

        if (module_name)
            strcat(s, module_name);
        if (module_name && class_name)
            strcat(s, ".");
        if (class_name)
            strcat(s, class_name);

        strcat(s, "::");
        strcat(s, object_name);

        name = PyString_FromString(s);
    }
    else
        Py_INCREF(name);

    wrapper_object = PyObject_CallFunctionObjArgs((PyObject *)
            &NRNameTransactionWrapper_Type, wrapped_object, name, NULL);

    result = NRUtilities_ReplaceWithWrapper(parent_object, attribute_name,
                                            wrapper_object);

    Py_DECREF(parent_object);
    Py_DECREF(wrapped_object);

    Py_DECREF(name);

    if (!result)
        return NULL;

    return wrapper_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_in_function(PyObject *self, PyObject *args,
                                      PyObject *kwds)
{
    PyObject *function_object = Py_None;

    static char *kwlist[] = { "in_function", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:in_function",
                                     kwlist, &function_object)) {
        return NULL;
    }

    return PyObject_CallFunctionObjArgs((PyObject *)
            &NRInFunctionDecorator_Type, function_object, NULL);
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_wrap_in_function(PyObject *self, PyObject *args,
                                           PyObject *kwds)
{
    PyObject *module = NULL;
    const char *class_name = NULL;
    const char *object_name = NULL;
    PyObject *function_object = Py_None;

    PyObject *wrapped_object = NULL;
    PyObject *parent_object = NULL;
    const char *attribute_name = NULL;

    PyObject *wrapper_object = NULL;

    PyObject *result = NULL;

    static char *kwlist[] = { "module", "class_name", "object_name",
                              "in_function", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OzzO:wrap_in_function",
                                     kwlist, &module, &class_name,
                                     &object_name, &function_object)) {
        return NULL;
    }

    if (!PyModule_Check(module) && !PyString_Check(module)) {
        PyErr_SetString(PyExc_TypeError, "module reference must be "
                        "module or string");
        return NULL;
    }

    if (!class_name && !object_name) {
        PyErr_SetString(PyExc_RuntimeError, "class or object name must be "
                        "supplied");
        return NULL;
    }

    wrapped_object = NRUtilities_LookupCallable(module, class_name,
                                                object_name, &parent_object,
                                                &attribute_name);

    if (!wrapped_object)
        return NULL;

    wrapper_object = PyObject_CallFunctionObjArgs((PyObject *)
            &NRInFunctionWrapper_Type, wrapped_object,
            function_object, NULL);

    result = NRUtilities_ReplaceWithWrapper(parent_object, attribute_name,
                                            wrapper_object);

    Py_DECREF(parent_object);
    Py_DECREF(wrapped_object);

    if (!result)
        return NULL;

    return wrapper_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_out_function(PyObject *self, PyObject *args,
                                       PyObject *kwds)
{
    PyObject *function_object = Py_None;

    static char *kwlist[] = { "out_function", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:out_function",
                                     kwlist, &function_object)) {
        return NULL;
    }

    return PyObject_CallFunctionObjArgs((PyObject *)
            &NROutFunctionDecorator_Type, function_object, NULL);
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_wrap_out_function(PyObject *self, PyObject *args,
                                            PyObject *kwds)
{
    PyObject *module = NULL;
    const char *class_name = NULL;
    const char *object_name = NULL;
    PyObject *function_object = Py_None;

    PyObject *wrapped_object = NULL;
    PyObject *parent_object = NULL;
    const char *attribute_name = NULL;

    PyObject *wrapper_object = NULL;

    PyObject *result = NULL;

    static char *kwlist[] = { "module", "class_name", "object_name",
                              "out_function", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OzzO:wrap_out_function",
                                     kwlist, &module, &class_name,
                                     &object_name, &function_object)) {
        return NULL;
    }

    if (!PyModule_Check(module) && !PyString_Check(module)) {
        PyErr_SetString(PyExc_TypeError, "module reference must be "
                        "module or string");
        return NULL;
    }

    if (!class_name && !object_name) {
        PyErr_SetString(PyExc_RuntimeError, "class or object name must be "
                        "supplied");
        return NULL;
    }

    wrapped_object = NRUtilities_LookupCallable(module, class_name,
                                                object_name, &parent_object,
                                                &attribute_name);

    if (!wrapped_object)
        return NULL;

    wrapper_object = PyObject_CallFunctionObjArgs((PyObject *)
            &NROutFunctionWrapper_Type, wrapped_object,
            function_object, NULL);

    result = NRUtilities_ReplaceWithWrapper(parent_object, attribute_name,
                                            wrapper_object);

    Py_DECREF(parent_object);
    Py_DECREF(wrapped_object);

    if (!result)
        return NULL;

    return wrapper_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_post_function(PyObject *self, PyObject *args,
                                        PyObject *kwds)
{
    PyObject *function_object = NULL;
    PyObject *run_once = NULL;

    static char *kwlist[] = { "post_function", "run_once", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O|O!:post_function",
                                     kwlist, &function_object, &PyBool_Type,
                                     &run_once)) {
        return NULL;
    }

    return PyObject_CallFunctionObjArgs((PyObject *)
            &NRPostFunctionDecorator_Type, function_object, run_once, NULL);
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_wrap_post_function(PyObject *self, PyObject *args,
                                             PyObject *kwds)
{
    PyObject *module = NULL;
    const char *class_name = NULL;
    const char *object_name = NULL;
    PyObject *function_object = NULL;
    PyObject *run_once = NULL;

    PyObject *wrapped_object = NULL;
    PyObject *parent_object = NULL;
    const char *attribute_name = NULL;

    PyObject *wrapper_object = NULL;

    PyObject *result = NULL;

    static char *kwlist[] = { "module", "class_name", "object_name",
                              "post_function", "run_once", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OzzO|O!:wrap_post_function",
                                     kwlist, &module, &class_name,
                                     &object_name, &function_object,
                                     &PyBool_Type, &run_once)) {
        return NULL;
    }

    if (!class_name && !object_name) {
        PyErr_SetString(PyExc_RuntimeError, "class or object name must be "
                        "supplied");
        return NULL;
    }

    wrapped_object = NRUtilities_LookupCallable(module, class_name,
                                                object_name, &parent_object,
                                                &attribute_name);

    if (!wrapped_object)
        return NULL;

    wrapper_object = PyObject_CallFunctionObjArgs((PyObject *)
            &NRPostFunctionWrapper_Type, wrapped_object,
            function_object, (run_once ? Py_True : Py_False), NULL);

    result = NRUtilities_ReplaceWithWrapper(parent_object, attribute_name,
                                            wrapper_object);

    Py_DECREF(parent_object);
    Py_DECREF(wrapped_object);

    if (!result)
        return NULL;

    return wrapper_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_pre_function(PyObject *self, PyObject *args,
                                       PyObject *kwds)
{
    PyObject *function_object = NULL;
    PyObject *run_once = NULL;

    static char *kwlist[] = { "pre_function", "run_once", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O|O!:pre_function",
                                     kwlist, &function_object, &PyBool_Type,
                                     &run_once)) {
        return NULL;
    }

    return PyObject_CallFunctionObjArgs((PyObject *)
            &NRPreFunctionDecorator_Type, function_object, run_once, NULL);
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_wrap_pre_function(PyObject *self, PyObject *args,
                                            PyObject *kwds)
{
    PyObject *module = NULL;
    const char *class_name = NULL;
    const char *object_name = NULL;
    PyObject *function_object = NULL;
    PyObject *run_once = NULL;

    PyObject *wrapped_object = NULL;
    PyObject *parent_object = NULL;
    const char *attribute_name = NULL;

    PyObject *wrapper_object = NULL;

    PyObject *result = NULL;

    static char *kwlist[] = { "module", "class_name", "object_name",
                              "pre_function", "run_once", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OzzO|O!:wrap_pre_function",
                                     kwlist, &module, &class_name,
                                     &object_name, &function_object,
                                     &PyBool_Type, &run_once)) {
        return NULL;
    }

    if (!PyModule_Check(module) && !PyString_Check(module)) {
        PyErr_SetString(PyExc_TypeError, "module reference must be "
                        "module or string");
        return NULL;
    }

    if (!class_name && !object_name) {
        PyErr_SetString(PyExc_RuntimeError, "class or object name must be "
                        "supplied");
        return NULL;
    }

    wrapped_object = NRUtilities_LookupCallable(module, class_name,
                                                object_name, &parent_object,
                                                &attribute_name);

    if (!wrapped_object)
        return NULL;

    wrapper_object = PyObject_CallFunctionObjArgs((PyObject *)
            &NRPreFunctionWrapper_Type, wrapped_object,
            function_object, (run_once ? Py_True : Py_False), NULL);

    result = NRUtilities_ReplaceWithWrapper(parent_object, attribute_name,
                                            wrapper_object);

    Py_DECREF(parent_object);
    Py_DECREF(wrapped_object);

    if (!result)
        return NULL;

    return wrapper_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_wrap_object(PyObject *self, PyObject *args,
                                      PyObject *kwds)
{
    PyObject *module = NULL;
    const char *class_name = NULL;
    const char *object_name = NULL;
    PyObject *factory_object = NULL;

    PyObject *wrapped_object = NULL;
    PyObject *parent_object = NULL;
    const char *attribute_name = NULL;

    PyObject *wrapper_object = NULL;

    PyObject *result = NULL;

    static char *kwlist[] = { "module", "class_name", "object_name",
                              "factory", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OzzO:wrap_object",
                                     kwlist, &module, &class_name,
                                     &object_name, &factory_object)) {
        return NULL;
    }

    if (!PyModule_Check(module) && !PyString_Check(module)) {
        PyErr_SetString(PyExc_TypeError, "module reference must be "
                        "module or string");
        return NULL;
    }

    if (!class_name && !object_name) {
        PyErr_SetString(PyExc_RuntimeError, "class or object name must be "
                        "supplied");
        return NULL;
    }

    wrapped_object = NRUtilities_LookupCallable(module, class_name,
                                                object_name, &parent_object,
                                                &attribute_name);

    if (!wrapped_object)
        return NULL;

    wrapper_object = PyObject_CallFunctionObjArgs((PyObject *)
            factory_object, wrapped_object, NULL);

    result = NRUtilities_ReplaceWithWrapper(parent_object, attribute_name,
                                            wrapper_object);

    Py_DECREF(parent_object);
    Py_DECREF(wrapped_object);

    if (!result)
        return NULL;

    return wrapper_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_register_import_hook(PyObject *self,
                                                    PyObject *args,
                                                    PyObject *kwds)
{
    PyObject *callable = NULL;
    PyObject *name = NULL;

    static char *kwlist[] = { "name", "callable", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OO:register_import_hook",
                                     kwlist, &name, &callable)) {
        return NULL;
    }

    if (!PyString_Check(name)) {
        PyErr_SetString(PyExc_TypeError, "expected string for module name");
        return NULL;
    }

    if (!PyCallable_Check(callable)) {
        PyErr_SetString(PyExc_TypeError, "expected callable");
        return NULL;
    }

    return NRImport_RegisterImportHook(name, callable);
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_import_hook(PyObject *self, PyObject *args,
                                      PyObject *kwds)
{
    PyObject *name = NULL;

    static char *kwlist[] = { "name", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:import_hook",
                                     kwlist, &name)) {
        return NULL;
    }

    if (!PyString_Check(name)) {
        PyErr_SetString(PyExc_TypeError, "expected string for module name");
        return NULL;
    }

    return PyObject_CallFunctionObjArgs((PyObject *)
            &NRImportHookDecorator_Type, name, NULL);
}

/* ------------------------------------------------------------------------- */

static PyObject *newrelic_shutdown(PyObject *self, PyObject *args)
{
    static int shutdown = 0;

    if (!shutdown) {
        shutdown = 1;

        Py_BEGIN_ALLOW_THREADS

        nr__harvest_thread_body("shutdown");

        nr__send_stop_for_each_application();
        nr__stop_communication(&(nr_per_process_globals.nrdaemon), NULL);
        nr__destroy_harvest_thread();

        /*
         * XXX Can't destroy application globals here because
         * Python objects may get destroyed later than the
         * shutdown function and they may try and access a
         * cached application object which is referencing what
         * would be deleted memory.
         */

#if 0
        nr__free_applications_global();
        nrfree (nr_per_process_globals.nrdaemon.sockpath);
        if (nr_per_process_globals.env != NULL) {
            nro__delete (nr_per_process_globals.env);
        }
#endif

        Py_END_ALLOW_THREADS
    }

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyMethodDef newrelic_methods[] = {
    { "application",        (PyCFunction)newrelic_application,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "settings",           (PyCFunction)newrelic_settings,
                            METH_NOARGS, 0 },
    { "log",                (PyCFunction)newrelic_log,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "harvest",            (PyCFunction)newrelic_harvest,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "transaction",        (PyCFunction)newrelic_transaction,
                            METH_NOARGS, 0 },
    { "callable_name",      (PyCFunction)newrelic_callable_name,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "resolve_object",     (PyCFunction)newrelic_resolve_object,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "object_context",     (PyCFunction)newrelic_object_context,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "web_transaction",    (PyCFunction)newrelic_web_transaction,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "wrap_web_transaction", (PyCFunction)newrelic_wrap_web_transaction,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "background_task",    (PyCFunction)newrelic_background_task,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "wrap_background_task", (PyCFunction)newrelic_wrap_background_task,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "database_trace",     (PyCFunction)newrelic_database_trace,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "wrap_database_trace", (PyCFunction)newrelic_wrap_database_trace,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "error_trace",        (PyCFunction)newrelic_error_trace,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "wrap_error_trace",   (PyCFunction)newrelic_wrap_error_trace,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "external_trace",     (PyCFunction)newrelic_external_trace,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "wrap_external_trace", (PyCFunction)newrelic_wrap_external_trace,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "function_trace",     (PyCFunction)newrelic_function_trace,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "wrap_function_trace", (PyCFunction)newrelic_wrap_function_trace,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "memcache_trace",     (PyCFunction)newrelic_memcache_trace,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "wrap_memcache_trace", (PyCFunction)newrelic_wrap_memcache_trace,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "name_transaction",   (PyCFunction)newrelic_name_transaction,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "wrap_name_transaction", (PyCFunction)newrelic_wrap_name_transaction,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "in_function",        (PyCFunction)newrelic_in_function,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "wrap_in_function",   (PyCFunction)newrelic_wrap_in_function,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "out_function",       (PyCFunction)newrelic_out_function,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "wrap_out_function",  (PyCFunction)newrelic_wrap_out_function,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "post_function",      (PyCFunction)newrelic_post_function,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "wrap_post_function", (PyCFunction)newrelic_wrap_post_function,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "pre_function",       (PyCFunction)newrelic_pre_function,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "wrap_pre_function",  (PyCFunction)newrelic_wrap_pre_function,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "wrap_object",        (PyCFunction)newrelic_wrap_object,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "register_import_hook", (PyCFunction)newrelic_register_import_hook,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { "import_hook",        (PyCFunction)newrelic_import_hook,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { NULL, NULL }
};

/* ------------------------------------------------------------------------- */

static PyMethodDef newrelic_method_shutdown = {
    "shutdown", newrelic_shutdown, METH_NOARGS, 0
};

PyMODINIT_FUNC
init_newrelic(void)
{
    PyObject *module;
    PyObject *atexit_module;

    PyGILState_STATE gil_state;

    module = Py_InitModule3("_newrelic", newrelic_methods, NULL);
    if (module == NULL)
        return;

    /* Initialise type objects. */

    if (PyType_Ready(&NRApplication_Type) < 0)
        return;
    if (PyType_Ready(&NRBackgroundTask_Type) < 0)
        return;
    if (PyType_Ready(&NRBackgroundTaskDecorator_Type) < 0)
        return;
    if (PyType_Ready(&NRBackgroundTaskWrapper_Type) < 0)
        return;
    if (PyType_Ready(&NRDatabaseTrace_Type) < 0)
        return;
    if (PyType_Ready(&NRDatabaseTraceDecorator_Type) < 0)
        return;
    if (PyType_Ready(&NRDatabaseTraceWrapper_Type) < 0)
        return;
    if (PyType_Ready(&NRErrorTrace_Type) < 0)
        return;
    if (PyType_Ready(&NRErrorTraceDecorator_Type) < 0)
        return;
    if (PyType_Ready(&NRErrorTraceWrapper_Type) < 0)
        return;
    if (PyType_Ready(&NRExternalTrace_Type) < 0)
        return;
    if (PyType_Ready(&NRExternalTraceDecorator_Type) < 0)
        return;
    if (PyType_Ready(&NRExternalTraceWrapper_Type) < 0)
        return;
    if (PyType_Ready(&NRFunctionTrace_Type) < 0)
        return;
    if (PyType_Ready(&NRFunctionTraceDecorator_Type) < 0)
        return;
    if (PyType_Ready(&NRFunctionTraceWrapper_Type) < 0)
        return;
    if (PyType_Ready(&NRMemcacheTrace_Type) < 0)
        return;
    if (PyType_Ready(&NRMemcacheTraceDecorator_Type) < 0)
        return;
    if (PyType_Ready(&NRMemcacheTraceWrapper_Type) < 0)
        return;
    if (PyType_Ready(&NRNameTransactionWrapper_Type) < 0)
        return;
    if (PyType_Ready(&NRNameTransactionDecorator_Type) < 0)
        return;
    if (PyType_Ready(&NRSettings_Type) < 0)
        return;
    if (PyType_Ready(&NRTracerSettings_Type) < 0)
        return;
    if (PyType_Ready(&NRErrorsSettings_Type) < 0)
        return;
    if (PyType_Ready(&NRDebugSettings_Type) < 0)
        return;
    if (PyType_Ready(&NRTransaction_Type) < 0)
        return;
    if (PyType_Ready(&NRWebTransaction_Type) < 0)
        return;
    if (PyType_Ready(&NRWebTransactionIterable_Type) < 0)
        return;
    if (PyType_Ready(&NRWebTransactionDecorator_Type) < 0)
        return;
    if (PyType_Ready(&NRWebTransactionWrapper_Type) < 0)
        return;
    if (PyType_Ready(&NRInFunctionDecorator_Type) < 0)
        return;
    if (PyType_Ready(&NRInFunctionWrapper_Type) < 0)
        return;
    if (PyType_Ready(&NROutFunctionDecorator_Type) < 0)
        return;
    if (PyType_Ready(&NROutFunctionWrapper_Type) < 0)
        return;
    if (PyType_Ready(&NRPostFunctionDecorator_Type) < 0)
        return;
    if (PyType_Ready(&NRPostFunctionWrapper_Type) < 0)
        return;
    if (PyType_Ready(&NRPreFunctionDecorator_Type) < 0)
        return;
    if (PyType_Ready(&NRPreFunctionWrapper_Type) < 0)
        return;
    if (PyType_Ready(&NRImportHookFinder_Type) < 0)
        return;
    if (PyType_Ready(&NRImportHookLoader_Type) < 0)
        return;
    if (PyType_Ready(&NRImportHookDecorator_Type) < 0)
        return;

    /* Initialise type objects. */

    Py_INCREF(&NRBackgroundTask_Type);
    PyModule_AddObject(module, "BackgroundTask",
                       (PyObject *)&NRBackgroundTask_Type);
    Py_INCREF(&NRBackgroundTaskDecorator_Type);
    PyModule_AddObject(module, "BackgroundTaskDecorator",
                       (PyObject *)&NRBackgroundTaskDecorator_Type);
    Py_INCREF(&NRBackgroundTaskWrapper_Type);
    PyModule_AddObject(module, "BackgroundTaskWrapper",
                       (PyObject *)&NRBackgroundTaskWrapper_Type);
    Py_INCREF(&NRDatabaseTrace_Type);
    PyModule_AddObject(module, "DatabaseTrace",
                       (PyObject *)&NRDatabaseTrace_Type);
    Py_INCREF(&NRDatabaseTraceDecorator_Type);
    PyModule_AddObject(module, "DatabaseTraceDecorator",
                       (PyObject *)&NRDatabaseTraceDecorator_Type);
    Py_INCREF(&NRDatabaseTraceWrapper_Type);
    PyModule_AddObject(module, "DatabaseTraceWrapper",
                       (PyObject *)&NRDatabaseTraceWrapper_Type);
    Py_INCREF(&NRErrorTrace_Type);
    PyModule_AddObject(module, "ErrorTrace",
                       (PyObject *)&NRErrorTrace_Type);
    Py_INCREF(&NRErrorTraceDecorator_Type);
    PyModule_AddObject(module, "ErrorTraceDecorator",
                       (PyObject *)&NRErrorTraceDecorator_Type);
    Py_INCREF(&NRErrorTraceWrapper_Type);
    PyModule_AddObject(module, "ErrorTraceWrapper",
                       (PyObject *)&NRErrorTraceWrapper_Type);
    Py_INCREF(&NRExternalTrace_Type);
    PyModule_AddObject(module, "ExternalTrace",
                       (PyObject *)&NRExternalTrace_Type);
    Py_INCREF(&NRExternalTraceDecorator_Type);
    PyModule_AddObject(module, "ExternalTraceDecorator",
                       (PyObject *)&NRExternalTraceDecorator_Type);
    Py_INCREF(&NRExternalTraceWrapper_Type);
    PyModule_AddObject(module, "ExternalTraceWrapper",
                       (PyObject *)&NRExternalTraceWrapper_Type);
    Py_INCREF(&NRFunctionTrace_Type);
    PyModule_AddObject(module, "FunctionTrace",
                       (PyObject *)&NRFunctionTrace_Type);
    Py_INCREF(&NRFunctionTraceDecorator_Type);
    PyModule_AddObject(module, "FunctionTraceDecorator",
                       (PyObject *)&NRFunctionTraceDecorator_Type);
    Py_INCREF(&NRFunctionTraceWrapper_Type);
    PyModule_AddObject(module, "FunctionTraceWrapper",
                       (PyObject *)&NRFunctionTraceWrapper_Type);
    Py_INCREF(&NRMemcacheTrace_Type);
    PyModule_AddObject(module, "MemcacheTrace",
                       (PyObject *)&NRMemcacheTrace_Type);
    Py_INCREF(&NRMemcacheTraceDecorator_Type);
    PyModule_AddObject(module, "MemcacheTraceDecorator",
                       (PyObject *)&NRMemcacheTraceDecorator_Type);
    Py_INCREF(&NRMemcacheTraceWrapper_Type);
    PyModule_AddObject(module, "MemcacheTraceWrapper",
                       (PyObject *)&NRMemcacheTraceWrapper_Type);
    Py_INCREF(&NRNameTransactionDecorator_Type);
    PyModule_AddObject(module, "NameTransactionDecorator",
                       (PyObject *)&NRNameTransactionDecorator_Type);
    Py_INCREF(&NRNameTransactionWrapper_Type);
    PyModule_AddObject(module, "NameTransactionWrapper",
                       (PyObject *)&NRNameTransactionWrapper_Type);
    Py_INCREF(&NRWebTransaction_Type);
    PyModule_AddObject(module, "WebTransaction",
                       (PyObject *)&NRWebTransaction_Type);
    Py_INCREF(&NRWebTransactionDecorator_Type);
    PyModule_AddObject(module, "WebTransactionDecorator",
                       (PyObject *)&NRWebTransactionDecorator_Type);
    Py_INCREF(&NRWebTransactionWrapper_Type);
    PyModule_AddObject(module, "WebTransactionWrapper",
                       (PyObject *)&NRWebTransactionWrapper_Type);
    Py_INCREF(&NRInFunctionDecorator_Type);
    PyModule_AddObject(module, "InFunctionDecorator",
                       (PyObject *)&NRInFunctionDecorator_Type);
    Py_INCREF(&NRInFunctionWrapper_Type);
    PyModule_AddObject(module, "InFunctionWrapper",
                       (PyObject *)&NRInFunctionWrapper_Type);
    Py_INCREF(&NROutFunctionDecorator_Type);
    PyModule_AddObject(module, "OutFunctionDecorator",
                       (PyObject *)&NROutFunctionDecorator_Type);
    Py_INCREF(&NROutFunctionWrapper_Type);
    PyModule_AddObject(module, "OutFunctionWrapper",
                       (PyObject *)&NROutFunctionWrapper_Type);
    Py_INCREF(&NRPostFunctionDecorator_Type);
    PyModule_AddObject(module, "PostFunctionDecorator",
                       (PyObject *)&NRPostFunctionDecorator_Type);
    Py_INCREF(&NRPostFunctionWrapper_Type);
    PyModule_AddObject(module, "PostFunctionWrapper",
                       (PyObject *)&NRPostFunctionWrapper_Type);
    Py_INCREF(&NRPreFunctionDecorator_Type);
    PyModule_AddObject(module, "PreFunctionDecorator",
                       (PyObject *)&NRPreFunctionDecorator_Type);
    Py_INCREF(&NRPreFunctionWrapper_Type);
    PyModule_AddObject(module, "PreFunctionWrapper",
                       (PyObject *)&NRPreFunctionWrapper_Type);
    Py_INCREF(&NRImportHookFinder_Type);
    PyModule_AddObject(module, "ImportHookFinder",
                       (PyObject *)&NRImportHookFinder_Type);

    /* Initialise module constants. */

    PyModule_AddObject(module, "LOG_ERROR",
                       PyInt_FromLong(LOG_ERROR));
    PyModule_AddObject(module, "LOG_INFO",
                       PyInt_FromLong(LOG_INFO));
    PyModule_AddObject(module, "LOG_WARNING",
                       PyInt_FromLong(LOG_WARNING));
    PyModule_AddObject(module, "LOG_VERBOSE",
                       PyInt_FromLong(LOG_VERBOSE));
    PyModule_AddObject(module, "LOG_DEBUG",
                       PyInt_FromLong(LOG_DEBUG));
    PyModule_AddObject(module, "LOG_VERBOSEDEBUG",
                       PyInt_FromLong(LOG_VERBOSEDEBUG));

    PyModule_AddObject(module, "RECORDSQL_OFF",
                       PyInt_FromLong(NR_TRANSACTION_TRACE_RECORDSQL_OFF));
    PyModule_AddObject(module, "RECORDSQL_RAW",
                       PyInt_FromLong(NR_TRANSACTION_TRACE_RECORDSQL_RAW));
    PyModule_AddObject(module, "RECORDSQL_OBFUSCATED",
                       PyInt_FromLong(
                       NR_TRANSACTION_TRACE_RECORDSQL_OBFUSCATED));

    /*
     * TODO Don't install signal handlers for catching back
     * trace when crash at this time as can't test it on
     * MacOS X as is Linux specific. Could be added at some
     * point but then would clash if something like mod_wsgi
     * did the same thing. Really should be left up to the
     * hosting environment to do it and not this module.
     */

    /*
     * Initialise the daemon client mutex lock. This prevents
     * the harvest thread and daemon client code working on
     * accumulated data at the same time. Note that we always
     * rely on the ability to have a background thread for
     * performing harvesting. We do not support harvesting
     * being triggered as a side effect of request based on
     * a time since last harvest was performed.
     */

    nrthread_mutex_init(&(nr_per_process_globals.nrdaemon.lock), NULL);

    /*
     * Application name initialisation. This is only a default
     * and can be overridden by configuration file or in user
     * code at point decorator or wrapper applied.
     */

    nr_per_process_globals.appname = nrstrdup("My Application");

    /*
     * Logging initialisation in daemon client code is PHP
     * specific so set reasonable defaults here instead.
     * Initially there will be no log file and set level to be
     * WARNING. Because the first time something is logged the log
     * file will be created, need to avoid doing any logging
     * during initialisation of this module. This provides
     * opportunity for user to override the log file location
     * and level immediately after they import this module.
     */

    nr_per_process_globals.logfilename = NULL;
    nr_per_process_globals.loglevel = LOG_WARNING;
    nr_per_process_globals.logfileptr = NULL;

    /*
     * Initialise the daemon client socket information for the
     * connection to the local daemon process via the UNIX
     * socket. For values where it is sensible, these will be
     * able to be overridden via the settings object. Such
     * changes will be picked up next time need to connect to
     * the local daemon as part of the harvest cycle.
     */

    nr_per_process_globals.nrdaemon.sockpath = nrstrdup("/tmp/.newrelic.sock");
    nr_per_process_globals.nrdaemon.sockfd = -1;
    nr_per_process_globals.nrdaemon.timeout = 10;
    nr_per_process_globals.nrdaemon.nonblock = 1;
    nr_per_process_globals.nrdaemon.buffer = NULL;

    /*
     * Initialise default whether request parameters are
     * captured. This is only a default and can be overridden by
     * configuration file or in user code. When enabled specific
     * request parameters can still be excluded.
     */

    nr_per_process_globals.enable_params = 1;

    /*
     * Initialise metrics table. The limit of number of metrics
     * collected per harvest file can be overriden via the
     * settings object and will apply next time harvest cycle
     * runs. Is a risk of it being changed mid cycle and so
     * limit different for different metrics tables, but not a
     * but issue.
     */

    nr_per_process_globals.metric_limit = 2000;

    nr__initialize_overflow_metric();

    /*
     * Initialise transaction, errors and sql tracing defaults.
     * Transaction tracing is on by default and can be
     * overridden via the settings object at any time and will
     * apply on the next harvest cycle.
     *
     * TODO These need to be able to be overridden on per
     * request basis via WSGI environ dictionary. The globals
     * may not need to use PHP variables if only PHP wrapper
     * refers to them. Only problem is that PHP agent isn't
     * properly thread safe and relies on fact that per request
     * variable stashed into a global.
     */

    nr_per_process_globals.errors_enabled = 1;

    nr_per_process_globals.tt_enabled = 1;
    nr_per_process_globals.tt_threshold_is_apdex_f = 1;
    nr_initialize_global_tt_threshold_from_apdex(NULL);

    nr_per_process_globals.tt_recordsql =
            NR_TRANSACTION_TRACE_RECORDSQL_OBFUSCATED;

    nr_per_process_globals.slow_sql_stacktrace = 500 * 1000;

    /*
     * XXX Following metrics settings only available as string
     * macros and not integers so cannot use them and need to
     * redefine them. The macro for node time threshold is
     * actually in seconds and not the required micro seconds.
     * Believed it is actually meant to equate to 2 milli
     * seconds.
     */

    nr_per_process_globals.metric_limit = 3000;
    nr_per_process_globals.expensive_nodes_size = 100;
    nr_per_process_globals.expensive_node_minimum = 2000;

    nr_per_process_globals.special_flags = 0;

    /* Initialise support for tracking multiple applications. */

    nr__initialize_applications_global();

    /* Initialise the global application environment. */

    nr_per_process_globals.env = nro__new(NR_OBJECT_HASH);

    newrelic_populate_environment();
    newrelic_populate_plugin_list();

    /*
     * Register shutdown method with atexit module for execution
     * on process shutdown. Because functions registered with
     * the atexit module are technically only invoked for the
     * main interpreter and not sub interpreters (except under
     * mod_wsgi), then we explicitly release the GIL and then
     * reacquire it against the main interpreter before actually
     * performing the registration. Note that under mod_python,
     * functions registered with the atexit module aren't called
     * at all as it doesn't properly shutdown the interpreter
     * when the process is being stopped. Since mod_python is
     * officially dead, use of it should be discouraged. Also be
     * aware that if both mod_python and mod_wsgi are loaded at
     * the same time into Apache, even if mod_python is not
     * actually used, mod_python controls interpreter
     * initialisation and destruction and so simply loading
     * mod_python causes any functions registered with atexit
     * module under mod_wsgi to not be called either.
     */

    Py_BEGIN_ALLOW_THREADS

    gil_state = PyGILState_Ensure();

    atexit_module = PyImport_ImportModule("atexit");

    if (atexit_module) {
        PyObject *module_dict = NULL;
        PyObject *register_function = NULL;

        module_dict = PyModule_GetDict(atexit_module);
        register_function = PyDict_GetItemString(module_dict, "register");

        if (register_function) {
            PyObject *callback_function = NULL;
            PyObject *args = NULL;
            PyObject *result = NULL;

            Py_INCREF(register_function);

            callback_function = PyCFunction_New(&newrelic_method_shutdown,
                                                NULL);

            args = PyTuple_Pack(1, callback_function);
            result = PyObject_Call(register_function, args, NULL);

            Py_DECREF(callback_function);
            Py_DECREF(args);
            Py_DECREF(register_function);

            Py_XDECREF(result);
        }

        Py_DECREF(atexit_module);
    }

    PyGILState_Release(gil_state);

    Py_END_ALLOW_THREADS

    /* Initialise samplers. */

    nr__initialize_samplers();
}

/* ------------------------------------------------------------------------- */

/*
 * vim: set cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
