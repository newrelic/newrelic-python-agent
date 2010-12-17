/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include <Python.h>

#include "py_application.h"
#include "py_background_task.h"
#include "py_database_trace.h"
#include "py_external_trace.h"
#include "py_function_trace.h"
#include "py_global_settings.h"
#include "py_memcache_trace.h"
#include "py_web_transaction.h"

#include "globals.h"
#include "logging.h"

#include "generic_object_funcs.h"

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

    nr_generic_object__add_string_to_hash(nr_per_process_globals.env,
                                          "Python Program Name",
                                          Py_GetProgramName());
    nr_generic_object__add_string_to_hash(nr_per_process_globals.env,
                                          "Python Home", Py_GetPythonHome());

    nr_generic_object__add_string_to_hash(nr_per_process_globals.env,
                                          "Python Program Full Path",
                                          Py_GetProgramFullPath());
    nr_generic_object__add_string_to_hash(nr_per_process_globals.env,
                                          "Python Prefix", Py_GetPrefix());
    nr_generic_object__add_string_to_hash(nr_per_process_globals.env,
                                          "Python Exec Prefix",
                                          Py_GetPrefix());
    nr_generic_object__add_string_to_hash(nr_per_process_globals.env,
                                          "Python Version", Py_GetVersion());
    nr_generic_object__add_string_to_hash(nr_per_process_globals.env,
                                          "Python Platform", Py_GetPlatform());
    nr_generic_object__add_string_to_hash(nr_per_process_globals.env,
                                          "Python Copyright",
                                          Py_GetCopyright());
    nr_generic_object__add_string_to_hash(nr_per_process_globals.env,
                                          "Python Compiler",
                                          Py_GetCompiler());
    nr_generic_object__add_string_to_hash(nr_per_process_globals.env,
                                          "Python Build Info",
                                          Py_GetBuildInfo());
    
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
            PyObject *result = NULL;

            Py_INCREF(object);

            args = Py_BuildValue("(s)", "CONFIG_ARGS");
            result = PyEval_CallObject(object, args);

            if (result && result != Py_None) {
                nr_generic_object__add_string_to_hash(
                        nr_per_process_globals.env, "Python Config Args",
                        PyString_AsString(result));
            }
            else
                PyErr_Clear();

            Py_XDECREF(result);

            Py_DECREF(args);
            Py_DECREF(object);
        }
    }
    else
      PyErr_Clear();
}

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
    nr_generic_object* plugins;

    plugins = nr_generic_object__allocate(NR_OBJECT_ARRAY);
    plugins = nr_generic_object__add_object_to_hash(nr_per_process_globals.env,
                                                    "Plugin List", plugins);

    for (i = 0; PyImport_Inittab[i].name != NULL; i++) {
        if (!PyImport_Inittab[i].name)
            break;

        nr_generic_object__add_string_to_array(plugins,
                                               PyImport_Inittab[i].name) ;
    }
}

static PyObject *newrelic_Application(PyObject *self, PyObject *args)
{
    NRApplicationObject *rv;
    const char *name = NULL;
    const char *framework = NULL;

    if (!PyArg_ParseTuple(args, "s|s:Application", &name, &framework))
        return NULL;

    rv = NRApplication_New(name, framework);
    if (rv == NULL)
        return NULL;

    return (PyObject *)rv;
}

static PyObject *newrelic_GlobalSettings(PyObject *self, PyObject *args)
{
    NRGlobalSettingsObject *rv;

    rv = NRGlobalSettings_New();
    if (rv == NULL)
        return NULL;

    return (PyObject *)rv;
}

static PyMethodDef newrelic_methods[] = {
    { "Application", newrelic_Application, METH_VARARGS, 0 },
    { "GlobalSettings", newrelic_GlobalSettings, METH_NOARGS, 0 },
    { NULL, NULL }
};

PyMODINIT_FUNC
init_newrelic(void)
{
    PyObject *module;
    PyObject *settings;

    module = Py_InitModule3("_newrelic", newrelic_methods, NULL);
    if (module == NULL)
        return;

    /* Initialise type objects. */

    if (PyType_Ready(&NRApplication_Type) < 0)
        return;
    if (PyType_Ready(&NRBackgroundTask_Type) < 0)
        return;
    if (PyType_Ready(&NRDatabaseTrace_Type) < 0)
        return;
    if (PyType_Ready(&NRExternalTrace_Type) < 0)
        return;
    if (PyType_Ready(&NRFunctionTrace_Type) < 0)
        return;
    if (PyType_Ready(&NRMemcacheTrace_Type) < 0)
        return;
    if (PyType_Ready(&NRGlobalSettings_Type) < 0)
        return;
    if (PyType_Ready(&NRWebTransaction_Type) < 0)
        return;

    /* Initialise module constants. */

    PyModule_AddObject(module, "LOG_ERROR", PyInt_FromLong(LOG_ERROR));
    PyModule_AddObject(module, "LOG_INFO", PyInt_FromLong(LOG_INFO));
    PyModule_AddObject(module, "LOG_WARNING", PyInt_FromLong(LOG_WARNING));
    PyModule_AddObject(module, "LOG_VERBOSE", PyInt_FromLong(LOG_VERBOSE));
    PyModule_AddObject(module, "LOG_DEBUG", PyInt_FromLong(LOG_DEBUG));
    PyModule_AddObject(module, "LOG_VERBOSEDEBUG", PyInt_FromLong(LOG_VERBOSEDEBUG));

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

    pthread_mutex_init(&(nr_per_process_globals.daemon.lock),NULL);

    /*
     * Logging initialisation in daemon client code is PHP
     * specific so set reasonable defaults here instead.
     * Initially there will be no log file and set level to be
     * INFO. Because the first time something is logged the log
     * file will be created, need to avoid doing any logging
     * during initialisation of this module. This provides
     * opportunity for user to override the log file location
     * and level immediately after they import this module.
     */

    nr_per_process_globals.logfilename = NULL;
    nr_per_process_globals.loglevel = LOG_INFO;
    nr_per_process_globals.logfileptr = NULL;

    /*
     * Initialise the daemon client socket information for the
     * connection to the local daemon process via the UNIX
     * socket. For values where it is sensible, these will be
     * able to be overridden via the settings object. Such
     * changes will be picked up next time need to connect to
     * the local daemon as part of the harvest cycle.
     */

    nr_per_process_globals.daemon.sockpath = nrstrdup("/tmp/.newrelic.sock");
    nr_per_process_globals.daemon.sockfd = -1;
    nr_per_process_globals.daemon.timeout = 10;
    nr_per_process_globals.daemon.nonblock = 1;
    nr_per_process_globals.daemon.buffer = NULL;

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
     * Initialise transaction tracing defaults. Transaction
     * tracing is on by default and can be overridden via the
     * settings object at any time and will apply on the
     * next harvest cycle.
     */

    nr_per_process_globals.tt_enabled = 1;

    /* Initialise support for tracking multiple applications. */

    nr__initialize_applications_global();

    /* Initialise the global application environment. */

    nr_per_process_globals.env = nr_generic_object__allocate(NR_OBJECT_HASH);

    newrelic_populate_environment();
    newrelic_populate_plugin_list();
}

/* ------------------------------------------------------------------------- */
