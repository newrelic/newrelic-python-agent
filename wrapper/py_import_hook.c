/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_import_hook.h"

/* ------------------------------------------------------------------------- */

static PyObject *NRImportFinder_new(PyTypeObject *type, PyObject *args,
                                    PyObject *kwds)
{
    NRImportFinderObject *self;

    self = (NRImportFinderObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->skip = PyDict_New();

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static void NRImportFinder_dealloc(NRImportFinderObject *self)
{
    Py_XDECREF(self->skip);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRImportFinder_find_module(
        NRImportFinderObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *fullname = NULL;
    PyObject *path = Py_None;

    PyObject *registry = NULL;
    PyObject *module = NULL;

    static char *kwlist[] = { "fullname", "path", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O!|O:find_module",
                                     kwlist, &PyString_Type, &fullname,
                                     &path)) {
        return NULL;
    }

    registry = NRImport_GetImportHooks();

    if (!registry)
        return NULL;

    if (PyDict_Contains(registry, fullname) <= 0) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    if (PyDict_Contains(self->skip, fullname) != 0) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    PyDict_SetItem(self->skip, fullname, Py_True);

    module = PyImport_ImportModule(PyString_AsString(fullname));

    if (!module) {
        PyErr_Clear();
        return NULL;
    }

    PyDict_DelItem(self->skip, fullname);

    return PyObject_CallFunctionObjArgs(
            (PyObject *)&NRImportLoader_Type, NULL);
}

/* ------------------------------------------------------------------------- */

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

static PyMethodDef NRImportFinder_methods[] = {
    { "find_module",        (PyCFunction)NRImportFinder_find_module,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { NULL, NULL }
};

PyTypeObject NRImportFinder_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.ImportFinder", /*tp_name*/
    sizeof(NRImportFinderObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRImportFinder_dealloc, /*tp_dealloc*/
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
    NRImportFinder_methods, /*tp_methods*/
    0,                      /*tp_members*/
    0,                      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    0,                      /*tp_init*/
    0,                      /*tp_alloc*/
    NRImportFinder_new,      /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRImportLoader_new(PyTypeObject *type, PyObject *args,
                                    PyObject *kwds)
{
    NRImportLoaderObject *self;

    self = (NRImportLoaderObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static void NRImportLoader_dealloc(NRImportLoaderObject *self)
{
    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRImportLoader_load_module(
        NRImportLoaderObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *fullname = NULL;
    PyObject *modules = NULL;
    PyObject *module = NULL;
    PyObject *result = NULL;

    static char *kwlist[] = { "fullname", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:find_module",
                                     kwlist, &fullname)) {
        return NULL;
    }

    modules = PyImport_GetModuleDict();

    module = PyDict_GetItem(modules, fullname);

    if (!module)
        return NULL;

    result = NRImport_NotifyHooks(fullname, module);

    if (!result) {
        Py_DECREF(module);
        return NULL;
    }

    Py_DECREF(result);

    return module;
}

/* ------------------------------------------------------------------------- */

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

static PyMethodDef NRImportLoader_methods[] = {
    { "load_module",        (PyCFunction)NRImportLoader_load_module,
                            METH_VARARGS|METH_KEYWORDS, 0 },
    { NULL, NULL }
};

PyTypeObject NRImportLoader_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.ImportLoader", /*tp_name*/
    sizeof(NRImportLoaderObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRImportLoader_dealloc, /*tp_dealloc*/
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
    NRImportLoader_methods, /*tp_methods*/
    0,                      /*tp_members*/
    0,                      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    0,                      /*tp_init*/
    0,                      /*tp_alloc*/
    NRImportLoader_new,     /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

PyObject *NRImport_GetImportHooks(void)
{
    PyObject *module = NULL;

    PyObject *dict = NULL;
    PyObject *registry = NULL;

    module = PyImport_ImportModule("newrelic");

    if (!module)
        return NULL;

    dict = PyModule_GetDict(module);

    registry = PyDict_GetItemString(dict, "import_hooks");

    if (!registry) {
        registry = PyDict_New();
        PyDict_SetItemString(dict, "import_hooks", registry);
        Py_DECREF(registry);
    }

    Py_DECREF(module);

    return registry;
}

/* ------------------------------------------------------------------------- */

PyObject* NRImport_RegisterImportHook(PyObject *callable, PyObject *name)
{
    PyObject *registry = NULL;
    PyObject *hooks = NULL;
    PyObject *modules = NULL;

    PyObject *imp_module = NULL;
    PyObject *imp_dict = NULL;
    PyObject *imp_lock = NULL;
    PyObject *imp_unlock = NULL;
    PyObject *imp_result = NULL;

    PyObject *result = NULL;

    registry = NRImport_GetImportHooks();

    if (!registry)
        return NULL;

    modules = PyImport_GetModuleDict();

    imp_module = PyImport_ImportModule("imp");

    if (!imp_module) {
        return NULL;
    }

    imp_dict = PyModule_GetDict(imp_module);

    imp_lock = PyDict_GetItemString(imp_dict, "acquire_lock");
    imp_unlock = PyDict_GetItemString(imp_dict, "release_lock");

    if (imp_lock && imp_unlock) {
        imp_result = PyObject_CallFunctionObjArgs(imp_lock, NULL);
        if (!imp_result) {
            Py_XDECREF(imp_lock);
            Py_XDECREF(imp_unlock);
            Py_XDECREF(imp_module);
            return NULL;
        }
        Py_DECREF(imp_result);
    }

    hooks = PyDict_GetItem(registry, name);

    /*
     * If no entry in registry or entry already flagged with None
     * then module may have been loaded, in which case need to
     * check and fire hook immediately.
     */

    if (hooks == NULL || hooks == Py_None) {
        PyObject *module = NULL;

        module = PyDict_GetItem(modules, name);

        if (module != NULL) {
            /*
	     * The module has already been loaded so fire hook
	     * immediately.
             */

            if (hooks == NULL)
                PyDict_SetItem(registry, name, Py_None);

            result = PyObject_CallFunctionObjArgs(callable, module, NULL);

            if (result) {
                Py_INCREF(Py_None);
                result = Py_None;
            }

            Py_XDECREF(result);
        }
        else {
            /*
	     * No hook has been registered so far so create list
	     * and add current hook.
             */

            hooks = PyList_New(0);
            PyList_Append(hooks, callable);
            PyDict_SetItem(registry, name, hooks);
            Py_DECREF(hooks);
        }
    }
    else if (PyList_Check(hooks)) {
        /*
	 * Hook has already been registered, so append current
	 * hook.
         */

        PyList_Append(hooks, callable);
    }
    else {
        PyErr_Format(PyExc_TypeError, "expected list of hooks, got '%.200s'",
                     Py_TYPE(hooks)->tp_name);
    }

    if (imp_lock && imp_unlock) {
        imp_result = PyObject_CallFunctionObjArgs(imp_unlock, NULL);
        if (!imp_result) {
            Py_XDECREF(imp_lock);
            Py_XDECREF(imp_unlock);
            Py_XDECREF(imp_module);
            Py_XDECREF(result);
            return NULL;
        }
        Py_DECREF(imp_result);
    }

    Py_XDECREF(imp_lock);
    Py_XDECREF(imp_unlock);
    Py_XDECREF(imp_module);

    return result;
}

/* ------------------------------------------------------------------------- */

PyObject *NRImport_NotifyHooks(PyObject *name, PyObject *module)
{
    PyObject *registry = NULL;
    PyObject *hooks = NULL;
    PyObject *hook = NULL;

    registry = NRImport_GetImportHooks();

    hooks = PyDict_GetItem(registry, name);

    if (!hooks && PyList_Check(hooks)) {
        PyObject *iter = NULL;

        iter = PyObject_GetIter(hooks);

        while ((hook = PyIter_Next(iter))) {
            PyObject *result = NULL;

            result = PyObject_CallFunctionObjArgs(hook, module, NULL);

            if (!result) {
                PyDict_SetItem(registry, name, Py_None);

                return NULL;
            }

            Py_XDECREF(result);
        }

        PyDict_SetItem(registry, name, Py_None);
    }

    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

/*
 * vim: et cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
