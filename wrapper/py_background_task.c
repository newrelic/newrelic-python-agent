/* ------------------------------------------------------------------------- */

/* (C) Copyright 2010-2011 New Relic Inc. All rights reserved. */

/* ------------------------------------------------------------------------- */

#include "py_background_task.h"

#include "py_web_transaction.h"

#include "py_utilities.h"

#include "globals.h"

#include "structmember.h"

/* ------------------------------------------------------------------------- */

static int NRBackgroundTask_init(NRTransactionObject *self, PyObject *args,
                                 PyObject *kwds)
{
    NRApplicationObject *application = NULL;
    PyObject *name = NULL;
    PyObject *scope = Py_None;

    PyObject *newargs = NULL;

    static char *kwlist[] = { "application", "name", "scope", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O!O|O:BackgroundTask",
                                     kwlist, &NRApplication_Type,
                                     &application, &name, &scope)) {
        return -1;
    }

    if (!PyString_Check(name) && !PyUnicode_Check(name)) {
        PyErr_Format(PyExc_TypeError, "expected string or Unicode for "
                     "name, found type '%s'", name->ob_type->tp_name);
        return -1;
    }

    if (!PyString_Check(scope) && !PyUnicode_Check(scope) &&
        scope != Py_None) {
        PyErr_Format(PyExc_TypeError, "expected string, Unicode or None "
                     "for scope, found type '%s'", scope->ob_type->tp_name);
        return -1;
    }

    /*
     * Validate that this method hasn't been called previously.
     */

    if (self->application) {
        PyErr_SetString(PyExc_TypeError, "transaction already initialized");
        return -1;
    }

    /*
     * Pass application object to the base class constructor.
     */

    newargs = PyTuple_Pack(1, PyTuple_GetItem(args, 0));

    if (NRTransaction_Type.tp_init((PyObject *)self, newargs, kwds) < 0) {
        Py_DECREF(newargs);
        return -1;
    }

    Py_DECREF(newargs);

    /*
     * Setup the background task specific attributes of the
     * transaction. Note that mark it as being named but do
     * not currently check that and prevent the name from
     * being overridden as the PHP code seems to do. The PHP
     * code may only do that as may only attach the name at
     * the end of the transaction and not at the start. Since
     * we do it at the start, then user can still override it.
     */

    if (self->transaction) {
        PyObject *bytes = NULL;

        bytes = NRUtilities_ConstructPath(name, scope);
        self->transaction->path_type = NR_PATH_TYPE_RAW;
        self->transaction->path = nrstrdup(PyString_AsString(bytes));
        Py_DECREF(bytes);

        self->transaction->realpath = NULL;

        self->transaction->backgroundjob = 1;
    }

    return 0;
}


/* ------------------------------------------------------------------------- */

PyTypeObject NRBackgroundTask_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.BackgroundTask", /*tp_name*/
    sizeof(NRTransactionObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    0,                      /*tp_dealloc*/
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
    0,                      /*tp_methods*/
    0,                      /*tp_members*/
    0,                      /*tp_getset*/
    &NRTransaction_Type,    /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)NRBackgroundTask_init, /*tp_init*/
    0,                      /*tp_alloc*/
    0,                      /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRBackgroundTaskWrapper_new(PyTypeObject *type, PyObject *args,
                                           PyObject *kwds)
{
    NRBackgroundTaskWrapperObject *self;

    self = (NRBackgroundTaskWrapperObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->dict = NULL;
    self->next_object = NULL;
    self->last_object = NULL;
    self->application = NULL;
    self->name = NULL;
    self->scope = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRBackgroundTaskWrapper_init(NRBackgroundTaskWrapperObject *self,
                                       PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;

    PyObject *application = Py_None;
    PyObject *name = Py_None;
    PyObject *scope = Py_None;

    PyObject *object = NULL;

    static char *kwlist[] = { "wrapped", "application", "name",
                              "scope", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O|OOO:BackgroundTaskWrapper",
                                     kwlist, &wrapped_object, &application,
                                     &name, &scope)) {
        return -1;
    }

    if (!PyString_Check(scope) && !PyUnicode_Check(scope) &&
        scope != Py_None) {
        PyErr_Format(PyExc_TypeError, "expected string, Unicode or None "
                     "for scope, found type '%s'", scope->ob_type->tp_name);
        return -1;
    }

    if (application != Py_None &&
        Py_TYPE(application) != &NRApplication_Type &&
        !PyString_Check(application) && !PyUnicode_Check(application)) {
        PyErr_Format(PyExc_TypeError, "application argument must be None, "
                     "str, unicode, or application object, found type '%s'",
                     application->ob_type->tp_name);
        return -1;
    }

    if (Py_TYPE(application) != &NRApplication_Type) {
        PyObject *func_args;

        if (application == Py_None) {
            application = PyString_FromString("Python Application");
            func_args = PyTuple_Pack(1, application);
            Py_DECREF(application);
        }
        else
            func_args = PyTuple_Pack(1, application);

        application = NRApplication_Singleton(func_args, NULL);

        Py_DECREF(func_args);
    }
    else
        Py_INCREF(application);

    Py_INCREF(wrapped_object);

    Py_XDECREF(self->dict);
    Py_XDECREF(self->next_object);
    Py_XDECREF(self->last_object);

    self->next_object = wrapped_object;
    self->last_object = NULL;
    self->dict = NULL;

    object = PyObject_GetAttrString(wrapped_object, "__newrelic__");

    if (object) {
        Py_DECREF(object);

        object = PyObject_GetAttrString(wrapped_object, "__last_object__");

        if (object)
            self->last_object = object;
        else
            PyErr_Clear();
    }
    else
        PyErr_Clear();

    if (!self->last_object) {
        Py_INCREF(wrapped_object);
        self->last_object = wrapped_object;
    }

    object = PyObject_GetAttrString(self->last_object, "__dict__");

    if (object)
        self->dict = object;
    else
        PyErr_Clear();

    Py_INCREF(application);
    Py_XDECREF(self->application);
    self->application = application;

    Py_INCREF(name);
    Py_XDECREF(self->name);
    self->name = name;

    Py_INCREF(scope);
    Py_XDECREF(self->scope);
    self->scope = scope;

    Py_DECREF(application);

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRBackgroundTaskWrapper_dealloc(NRBackgroundTaskWrapperObject *self)
{
    Py_XDECREF(self->dict);

    Py_XDECREF(self->next_object);
    Py_XDECREF(self->last_object);

    Py_XDECREF(self->application);
    Py_XDECREF(self->name);
    Py_XDECREF(self->scope);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRBackgroundTaskWrapper_call(
        NRBackgroundTaskWrapperObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_result = NULL;

    PyObject *current_transaction = NULL;

    PyObject *background_task = NULL;

    PyObject *instance_method = NULL;
    PyObject *method_args = NULL;
    PyObject *method_result = NULL;

    PyObject *name = NULL;
    PyObject *scope = NULL;

    /* Calculate name to be assigned to background task. */

    if (self->name == Py_None) {
        name = NRUtilities_CallableName(self->next_object,
                                        (PyObject *)self, args, ":");
    }
    else if (PyString_Check(self->name) || PyUnicode_Check(self->name)) {
        name = self->name;
        Py_INCREF(name);
    }
    else {
        /*
         * Name if actually a callable function to provide the
         * name based on arguments supplied to wrapped function.
         */

        name = PyObject_Call(self->name, args, kwds);

        if (!name)
            return NULL;
    }

    if (self->scope == Py_None) {
        Py_INCREF(Py_None);
        scope = Py_None;
    }
    else if (PyString_Check(self->scope) || PyUnicode_Check(self->scope)) {
        Py_INCREF(self->scope);
        scope = self->scope;
    }
    else {
        /*
         * Scope if actually a callable function to provide the
         * scope based on arguments supplied to wrapped function.
         */

        scope = PyObject_Call(self->scope, args, kwds);

        if (!scope) {
            Py_DECREF(scope);
            return NULL;
        }
    }

    /*
     * Check to see if we are being called within the context
     * of a web transaction. If we are, then rather than
     * start a new transaction for a background task, we will
     * just flag the current web transaction as a background
     * task.
     */

    current_transaction = NRTransaction_CurrentTransaction();

    if (current_transaction) {
        if (Py_TYPE(current_transaction) == &NRWebTransaction_Type) {
            PyObject *method = NULL;
            PyObject *result = NULL;

            PyObject_SetAttrString(current_transaction, "background_task",
                                   Py_True);

            method = PyObject_GetAttrString(current_transaction,
                                            "name_transaction");

            if (method) {
                result = PyObject_CallFunctionObjArgs(method, name,
                                                      scope, NULL);

                if (!result)
                    PyErr_WriteUnraisable(method);
                else
                    Py_DECREF(result);

                Py_DECREF(method);
                Py_DECREF(scope);
                Py_DECREF(name);

                return PyObject_Call(self->next_object, args, kwds);
            }

            PyErr_Clear();
        }
    }

    /* Create background task context manager. */

    background_task = PyObject_CallFunctionObjArgs((PyObject *)
            &NRBackgroundTask_Type, self->application, name,
            scope, NULL);

    Py_DECREF(name);
    Py_DECREF(scope);

    /* Now call __enter__() on the context manager. */

    instance_method = PyObject_GetAttrString(background_task, "__enter__");

    method_args = PyTuple_Pack(0);
    method_result = PyObject_Call(instance_method, method_args, NULL);

    if (!method_result)
        PyErr_WriteUnraisable(instance_method);
    else
        Py_DECREF(method_result);

    Py_DECREF(method_args);
    Py_DECREF(instance_method);

    /*
     * Now call the actual wrapped function with the original
     * position and keyword arguments.
     */

    wrapped_result = PyObject_Call(self->next_object, args, kwds);

    /*
     * Now call __exit__() on the context manager. If the call
     * of the wrapped function is successful then pass all None
     * objects, else pass exception details.
     */

    instance_method = PyObject_GetAttrString(background_task, "__exit__");

    if (wrapped_result) {
        method_args = PyTuple_Pack(3, Py_None, Py_None, Py_None);
        method_result = PyObject_Call(instance_method, method_args, NULL);

        if (!method_result)
            PyErr_WriteUnraisable(instance_method);
        else
            Py_DECREF(method_result);

        Py_DECREF(method_args);
        Py_DECREF(instance_method);
    }
    else {
        PyObject *type = NULL;
        PyObject *value = NULL;
        PyObject *traceback = NULL;

        PyErr_Fetch(&type, &value, &traceback);

        if (!value) {
            value = Py_None;
            Py_INCREF(value);
        }

        if (!traceback) {
            traceback = Py_None;
            Py_INCREF(traceback);
        }

        PyErr_NormalizeException(&type, &value, &traceback);

        method_args = PyTuple_Pack(3, type, value, traceback);
        method_result = PyObject_Call(instance_method, method_args, NULL);

        if (!method_result)
            PyErr_WriteUnraisable(instance_method);
        else
            Py_DECREF(method_result);

        Py_DECREF(method_args);
        Py_DECREF(instance_method);

        PyErr_Restore(type, value, traceback);
    }

    Py_DECREF(background_task);

    return wrapped_result;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRBackgroundTaskWrapper_get_next(
        NRBackgroundTaskWrapperObject *self, void *closure)
{
    if (!self->next_object) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    Py_INCREF(self->next_object);
    return self->next_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRBackgroundTaskWrapper_get_last(
        NRBackgroundTaskWrapperObject *self, void *closure)
{
    if (!self->last_object) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    Py_INCREF(self->last_object);
    return self->last_object;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRBackgroundTaskWrapper_get_marker(
        NRBackgroundTaskWrapperObject *self, void *closure)
{
    Py_INCREF(Py_None);
    return Py_None;
}

/* ------------------------------------------------------------------------- */

static PyObject *NRBackgroundTaskWrapper_get_module(
        NRBackgroundTaskWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    return PyObject_GetAttrString(self->last_object, "__module__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRBackgroundTaskWrapper_get_name(
        NRBackgroundTaskWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    return PyObject_GetAttrString(self->last_object, "__name__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRBackgroundTaskWrapper_get_doc(
        NRBackgroundTaskWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    return PyObject_GetAttrString(self->last_object, "__doc__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRBackgroundTaskWrapper_get_dict(
        NRBackgroundTaskWrapperObject *self)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    if (self->dict) {
        Py_INCREF(self->dict);
        return self->dict;
    }

    return PyObject_GetAttrString(self->last_object, "__dict__");
}

/* ------------------------------------------------------------------------- */

static PyObject *NRBackgroundTaskWrapper_getattro(
        NRBackgroundTaskWrapperObject *self, PyObject *name)
{
    PyObject *object = NULL;

    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return NULL;
    }

    object = PyObject_GenericGetAttr((PyObject *)self, name);

    if (object)
        return object;

    PyErr_Clear();

    return PyObject_GetAttr(self->last_object, name);
}

/* ------------------------------------------------------------------------- */

static int NRBackgroundTaskWrapper_setattro(
        NRBackgroundTaskWrapperObject *self, PyObject *name, PyObject *value)
{
    if (!self->last_object) {
      PyErr_SetString(PyExc_ValueError,
              "object wrapper has not been initialised");
      return -1;
    }

    return PyObject_SetAttr(self->last_object, name, value);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRBackgroundTaskWrapper_descr_get(PyObject *function,
                                                PyObject *object,
                                                PyObject *type)
{
    if (object == Py_None)
        object = NULL;

    return PyMethod_New(function, object, type);
}

/* ------------------------------------------------------------------------- */

static PyGetSetDef NRBackgroundTaskWrapper_getset[] = {
    { "__next_object__",    (getter)NRBackgroundTaskWrapper_get_next,
                            NULL, 0 },
    { "__last_object__",    (getter)NRBackgroundTaskWrapper_get_last,
                            NULL, 0 },
    { "__newrelic__",       (getter)NRBackgroundTaskWrapper_get_marker,
                            NULL, 0 },
    { "__module__",         (getter)NRBackgroundTaskWrapper_get_module,
                            NULL, 0 },
    { "__name__",           (getter)NRBackgroundTaskWrapper_get_name,
                            NULL, 0 },
    { "__doc__",            (getter)NRBackgroundTaskWrapper_get_doc,
                            NULL, 0 },
    { "__dict__",           (getter)NRBackgroundTaskWrapper_get_dict,
                            NULL, 0 },
    { NULL },
};

PyTypeObject NRBackgroundTaskWrapper_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.BackgroundTaskWrapper", /*tp_name*/
    sizeof(NRBackgroundTaskWrapperObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRBackgroundTaskWrapper_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRBackgroundTaskWrapper_call, /*tp_call*/
    0,                      /*tp_str*/
    (getattrofunc)NRBackgroundTaskWrapper_getattro, /*tp_getattro*/
    (setattrofunc)NRBackgroundTaskWrapper_setattro, /*tp_setattro*/
    0,                      /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT,     /*tp_flags*/
    0,                      /*tp_doc*/
    0,                      /*tp_traverse*/
    0,                      /*tp_clear*/
    0,                      /*tp_richcompare*/
    0,                      /*tp_weaklistoffset*/
    0,                      /*tp_iter*/
    0,                      /*tp_iternext*/
    0,                      /*tp_methods*/
    0,                      /*tp_members*/
    NRBackgroundTaskWrapper_getset, /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    NRBackgroundTaskWrapper_descr_get, /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    offsetof(NRBackgroundTaskWrapperObject, dict), /*tp_dictoffset*/
    (initproc)NRBackgroundTaskWrapper_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRBackgroundTaskWrapper_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

static PyObject *NRBackgroundTaskDecorator_new(PyTypeObject *type,
                                              PyObject *args, PyObject *kwds)
{
    NRBackgroundTaskDecoratorObject *self;

    self = (NRBackgroundTaskDecoratorObject *)type->tp_alloc(type, 0);

    if (!self)
        return NULL;

    self->application = NULL;
    self->name = NULL;
    self->scope = NULL;

    return (PyObject *)self;
}

/* ------------------------------------------------------------------------- */

static int NRBackgroundTaskDecorator_init(
        NRBackgroundTaskDecoratorObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *application = Py_None;
    PyObject *name = Py_None;
    PyObject *scope = Py_None;

    static char *kwlist[] = { "application", "name", "scope", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds,
                                     "|OOO:BackgroundTaskDecorator",
                                     kwlist, &application, &name, &scope)) {
        return -1;
    }

    if (application != Py_None &&
        Py_TYPE(application) != &NRApplication_Type &&
        !PyString_Check(application) && !PyUnicode_Check(application)) {
        PyErr_Format(PyExc_TypeError, "application argument must be None, "
                     "str, unicode, or application object, found type '%s'",
                     application->ob_type->tp_name);
        return -1;
    }

    Py_INCREF(application);
    Py_XDECREF(self->application);
    self->application = application;

    Py_INCREF(name);
    Py_XDECREF(self->name);
    self->name = name;

    Py_INCREF(scope);
    Py_XDECREF(self->scope);
    self->scope = scope;

    return 0;
}

/* ------------------------------------------------------------------------- */

static void NRBackgroundTaskDecorator_dealloc(
        NRBackgroundTaskDecoratorObject *self)
{
    Py_XDECREF(self->application);
    Py_XDECREF(self->name);
    Py_XDECREF(self->scope);

    Py_TYPE(self)->tp_free(self);
}

/* ------------------------------------------------------------------------- */

static PyObject *NRBackgroundTaskDecorator_call(
        NRBackgroundTaskDecoratorObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *wrapped_object = NULL;

    static char *kwlist[] = { "wrapped", NULL };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:BackgroundTaskDecorator",
                                     kwlist, &wrapped_object)) {
        return NULL;
    }

    return PyObject_CallFunctionObjArgs(
            (PyObject *)&NRBackgroundTaskWrapper_Type,
            wrapped_object, self->application, self->name, self->scope, NULL);
}

/* ------------------------------------------------------------------------- */

PyTypeObject NRBackgroundTaskDecorator_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "_newrelic.BackgroundTaskDecorator", /*tp_name*/
    sizeof(NRBackgroundTaskDecoratorObject), /*tp_basicsize*/
    0,                      /*tp_itemsize*/
    /* methods */
    (destructor)NRBackgroundTaskDecorator_dealloc, /*tp_dealloc*/
    0,                      /*tp_print*/
    0,                      /*tp_getattr*/
    0,                      /*tp_setattr*/
    0,                      /*tp_compare*/
    0,                      /*tp_repr*/
    0,                      /*tp_as_number*/
    0,                      /*tp_as_sequence*/
    0,                      /*tp_as_mapping*/
    0,                      /*tp_hash*/
    (ternaryfunc)NRBackgroundTaskDecorator_call, /*tp_call*/
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
    0,                      /*tp_methods*/
    0,                      /*tp_members*/
    0,                      /*tp_getset*/
    0,                      /*tp_base*/
    0,                      /*tp_dict*/
    0,                      /*tp_descr_get*/
    0,                      /*tp_descr_set*/
    0,                      /*tp_dictoffset*/
    (initproc)NRBackgroundTaskDecorator_init, /*tp_init*/
    0,                      /*tp_alloc*/
    NRBackgroundTaskDecorator_new, /*tp_new*/
    0,                      /*tp_free*/
    0,                      /*tp_is_gc*/
};

/* ------------------------------------------------------------------------- */

/*
 * vim: set cino=>2,e0,n0,f0,{2,}0,^0,\:2,=2,p2,t2,c1,+2,(2,u2,)20,*30,g2,h2 ts=8
 */
