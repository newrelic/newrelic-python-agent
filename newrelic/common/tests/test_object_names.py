import datetime
import inspect
import pytest
import unittest

import newrelic.packages.six as six
from newrelic.packages.six.moves import builtins

from newrelic.common.object_names import (callable_name,
        expand_builtin_exception_name)

if six.PY3:
    try:
        # python 3.4 +
        from importlib import reload
    except ImportError:
        # python 3.0 - 3.3
        from imp import reload
import newrelic.common.tests._test_object_names as _test_object_names

class TestCallableName(unittest.TestCase):

    def setUp(self):
        reload(_test_object_names)

    def test_function_name(self):
        self.assertEqual(
                callable_name(_test_object_names._function1),
                _test_object_names._module_fqdn('_function1'))

    def test_function_partial(self):
        self.assertEqual(
                callable_name(_test_object_names._partial_function1),
                _test_object_names._module_fqdn('_function_a'))

    def test_old_class_type(self):
        self.assertEqual(
                callable_name(_test_object_names._class1),
                _test_object_names._module_fqdn('_class1'))

    def test_old_class_instance(self):
        self.assertEqual(
                callable_name(_test_object_names._class1()),
                _test_object_names._module_fqdn('_class1'))

    def test_old_class_type_instancemethod(self):
        self.assertEqual(
                callable_name(_test_object_names._class1._function1),
                _test_object_names._module_fqdn('_class1._function1'))

    def test_old_class_instance_instancemethod(self):
        self.assertEqual(
                callable_name(_test_object_names._class1()._function1),
                _test_object_names._module_fqdn('_class1._function1'))

    def test_old_class_type_classmethod(self):
        self.assertEqual(
                callable_name(_test_object_names._class1._function2),
                _test_object_names._module_fqdn('_class1._function2'))

    def test_old_class_instance_classmethod(self):
        self.assertEqual(
                callable_name(_test_object_names._class1()._function2),
                _test_object_names._module_fqdn('_class1._function2'))

    def test_old_class_type_staticmethod(self):
        if six.PY3:
            self.assertEqual(
                    callable_name(_test_object_names._class1._function3),
                    _test_object_names._module_fqdn('_class1._function3'))
        else:
            # Cannot work out class name for Python 2.
            self.assertEqual(
                    callable_name(_test_object_names._class1._function3),
                    _test_object_names._module_fqdn('_function3'))

    def test_old_class_instance_staticmethod(self):
        if six.PY3:
            self.assertEqual(
                    callable_name(_test_object_names._class1._function3),
                    _test_object_names._module_fqdn('_class1._function3'))
        else:
            # Cannot work out class name for Python 2.
            self.assertEqual(
                    callable_name(_test_object_names._class1._function3),
                    _test_object_names._module_fqdn('_function3'))

    def test_new_class_type(self):
        self.assertEqual(
                callable_name(_test_object_names._class2),
                _test_object_names._module_fqdn('_class2'))

    def test_new_class_instance(self):
        self.assertEqual(
                callable_name(_test_object_names._class2()),
                _test_object_names._module_fqdn('_class2'))

    def test_new_class_type_instancemethod(self):
        self.assertEqual(
                callable_name(_test_object_names._class2._function1),
                _test_object_names._module_fqdn('_class2._function1'))

    def test_new_class_instance_instancemethod(self):
        self.assertEqual(
                callable_name(_test_object_names._class2()._function1),
                _test_object_names._module_fqdn('_class2._function1'))

    def test_new_class_type_classmethod(self):
        self.assertEqual(
                callable_name(_test_object_names._class2._function2),
                _test_object_names._module_fqdn('_class2._function2'))

    def test_new_class_instance_classmethod(self):
        self.assertEqual(
                callable_name(_test_object_names._class2()._function2),
                _test_object_names._module_fqdn('_class2._function2'))

    def test_new_class_type_staticmethod(self):
        if six.PY3:
            self.assertEqual(
                    callable_name(_test_object_names._class2._function3),
                    _test_object_names._module_fqdn('_class2._function3'))
        else:
            # Cannot work out class name for Python 2.
            self.assertEqual(
                    callable_name(_test_object_names._class2._function3),
                    _test_object_names._module_fqdn('_function3'))

    def test_new_class_instance_staticmethod(self):
        if six.PY3:
            self.assertEqual(
                    callable_name(_test_object_names._class2._function3),
                    _test_object_names._module_fqdn('_class2._function3'))
        else:
            # Cannot work out class name for Python 2.
            self.assertEqual(
                    callable_name(_test_object_names._class2._function3),
                    _test_object_names._module_fqdn('_function3'))

    def test_generated_class_type(self):
        self.assertEqual(
                callable_name(_test_object_names._class3),
                _test_object_names._module_fqdn('_class3'))

    def test_generated_class_instance(self):
        self.assertEqual(
                callable_name(_test_object_names._class3(1)),
                _test_object_names._module_fqdn('_class3'))

    def test_generated_class_type_instancemethod(self):
        # Cannot work out module name of method bound class for
        # Python 3. Make consistent between 2 and use Python 3.
        self.assertEqual(
                callable_name(_test_object_names._class3._asdict),
                _test_object_names._module_fqdn('_class3._asdict', '<namedtuple__class3>'))

    def test_generated_class_instance_instancemethod(self):
        if six.PY3:
            self.assertEqual(
                    callable_name(_test_object_names._class3(1)._asdict),
                    _test_object_names._module_fqdn('_class3._asdict', '<namedtuple__class3>'))
        else:
            self.assertEqual(
                    callable_name(_test_object_names._class3(1)._asdict),
                    _test_object_names._module_fqdn('_class3._asdict'))

    def test_generated_class_type_staticmethod(self):
        if six.PY3:
            self.assertEqual(
                    callable_name(_test_object_names._class3._make),
                    _test_object_names._module_fqdn('_class3._make', '<namedtuple__class3>'))
        else:
            self.assertEqual(
                    callable_name(_test_object_names._class3._make),
                    _test_object_names._module_fqdn('_class3._make'))

    def test_generated_class_instance_staticmethod(self):
        if six.PY3:
            self.assertEqual(
                    callable_name(_test_object_names._class3(1)._make),
                    _test_object_names._module_fqdn('_class3._make', '<namedtuple__class3>'))
        else:
            self.assertEqual(
                    callable_name(_test_object_names._class3(1)._make),
                    _test_object_names._module_fqdn('_class3._make'))

    def test_function_name_wraps_decorator(self):
        self.assertEqual(
                callable_name(_test_object_names._function2),
                _test_object_names._module_fqdn('_function2'))

    def test_function_name_desc_decorator(self):
        self.assertEqual(
                callable_name(_test_object_names._function3),
                _test_object_names._module_fqdn('_function3'))

    def test_new_class_type_instancemethod_wraps_decorator(self):
        self.assertEqual(
                callable_name(_test_object_names._class4._function1),
                _test_object_names._module_fqdn('_class4._function1'))

    def test_new_class_instance_instancemethod_wraps_decorator(self):
        self.assertEqual(
                callable_name(_test_object_names._class4()._function1),
                _test_object_names._module_fqdn('_class4._function1'))

    def test_new_class_type_instancemethod_desc_decorator(self):
        if six.PY3:
            self.assertEqual(
                    callable_name(_test_object_names._class4._function2),
                    _test_object_names._module_fqdn('_class4._function2'))
        else:
            # Cannot work out class name for Python 2.
            self.assertEqual(
                    callable_name(_test_object_names._class4._function2),
                    _test_object_names._module_fqdn('_function2'))

    def test_new_class_instance_instancemethod_desc_decorator(self):
        if six.PY3:
            self.assertEqual(
                    callable_name(_test_object_names._class4()._function2),
                    _test_object_names._module_fqdn('_class4._function2'))
        else:
            # Cannot work out class name for Python 2.
            self.assertEqual(
                    callable_name(_test_object_names._class4()._function2),
                    _test_object_names._module_fqdn('_function2'))

    def test_builtin_function_name(self):
        self.assertEqual(
                callable_name(globals),
                _test_object_names._module_fqdn('globals', builtins.__name__))

    def test_builtin_class_type(self):
        self.assertEqual(
                callable_name(list),
                _test_object_names._module_fqdn('list', builtins.__name__))

    def test_builtin_class_instance(self):
        self.assertEqual(
                callable_name(list()),
                _test_object_names._module_fqdn('list', builtins.__name__))

    def test_builtin_class_type_methoddescriptor(self):
        self.assertEqual(
                callable_name(list.pop),
                _test_object_names._module_fqdn('list.pop', builtins.__name__))

    def test_builtin_class_instance_methoddescriptor(self):
        self.assertEqual(
                callable_name(list().pop),
                _test_object_names._module_fqdn('list.pop', builtins.__name__))

    def test_builtin_class_type_slotwrapper(self):
        self.assertEqual(
                callable_name(int.__add__),
                _test_object_names._module_fqdn('int.__add__', builtins.__name__))

    def test_builtin_class_instance_slotwrapper(self):
        self.assertEqual(
                callable_name(int().__add__),
                _test_object_names._module_fqdn('int.__add__', builtins.__name__))

    def test_nested_class_type(self):
        if six.PY3:
            self.assertEqual(
                    callable_name(_test_object_names._class5._class6),
                    _test_object_names._module_fqdn('_class5._class6'))
        else:
            # Cannot work out nested contexts for Python 2.
            self.assertEqual(
                    callable_name(_test_object_names._class5._class6),
                    _test_object_names._module_fqdn('_class6'))

    def test_nested_class_instance(self):
        if six.PY3:
            self.assertEqual(
                    callable_name(_test_object_names._class5._class6()),
                    _test_object_names._module_fqdn('_class5._class6'))
        else:
            # Cannot work out nested contexts for Python 2.
            self.assertEqual(
                    callable_name(_test_object_names._class5._class6()),
                    _test_object_names._module_fqdn('_class6'))

    def test_nested_class_type_instancemethod(self):
        if six.PY3:
            self.assertEqual(
                    callable_name(_test_object_names._class5._class6._function1),
                    _test_object_names._module_fqdn('_class5._class6._function1'))
        else:
            # Cannot work out nested contexts for Python 2.
            self.assertEqual(
                    callable_name(_test_object_names._class5._class6._function1),
                    _test_object_names._module_fqdn('_class6._function1'))

    def test_nested_class_instance_instancemethod(self):
        if six.PY3:
            self.assertEqual(
                    callable_name(_test_object_names._class5._class6()._function1),
                    _test_object_names._module_fqdn('_class5._class6._function1'))
        else:
            # Cannot work out nested contexts for Python 2.
            self.assertEqual(
                    callable_name(_test_object_names._class5._class6()._function1),
                    _test_object_names._module_fqdn('_class6._function1'))

    def test_extension_class_type(self):
        self.assertEqual(
                callable_name(datetime.date),
                _test_object_names._module_fqdn('date', 'datetime'))

    def test_extension_method_via_class(self):
        self.assertEqual(
                callable_name(datetime.date.strftime),
                _test_object_names._module_fqdn('date.strftime', 'datetime'))

    def test_extension_method_via_instance(self):
        self.assertEqual(
                callable_name(datetime.date(200, 1, 1).strftime),
                _test_object_names._module_fqdn('date.strftime', 'datetime'))

    @pytest.mark.skipif(six.PY3,
            reason='Yet to be able to work out name of subclass')
    def test_subclass_old_class_type_instancemethod(self):
        self.assertEqual(
                callable_name(_test_object_names._class7._function1),
                _test_object_names._module_fqdn('_class7._function1'))

    def test_subclass_old_class_instance_instancemethod(self):
        self.assertEqual(
                callable_name(_test_object_names._class7()._function1),
                _test_object_names._module_fqdn('_class7._function1'))

    def test_subclass_old_class_type_classmethod(self):
        self.assertEqual(
                callable_name(_test_object_names._class7._function2),
                _test_object_names._module_fqdn('_class7._function2'))

    def test_subclass_old_class_instance_classmethod(self):
        self.assertEqual(
                callable_name(_test_object_names._class7()._function2),
                _test_object_names._module_fqdn('_class7._function2'))

    @pytest.mark.skipif(six.PY3,
            reason='Yet to be able to work out name of subclass')
    def test_subclass_old_class_type_staticmethod(self):
        if six.PY3:
            self.assertEqual(
                    callable_name(_test_object_names._class7._function3),
                    _test_object_names._module_fqdn('_class7._function3'))
        else:
            # Cannot work out class name for Python 2.
            self.assertEqual(
                    callable_name(_test_object_names._class7._function3),
                    _test_object_names._module_fqdn('_function3'))

    @pytest.mark.skipif(six.PY3,
            reason='Yet to be able to work out name of subclass')
    def test_subclass_old_class_instance_staticmethod(self):
        if six.PY3:
            self.assertEqual(
                    callable_name(_test_object_names._class7()._function3),
                    _test_object_names._module_fqdn('_class7._function3'))
        else:
            # Cannot work out class name for Python 2.
            self.assertEqual(
                    callable_name(_test_object_names._class7()._function3),
                    _test_object_names._module_fqdn('_function3'))

    def test_subclass_old_class_non_inherited_method(self):
        self.assertEqual(
                callable_name(_test_object_names._class7()._function4),
                _test_object_names._module_fqdn('_class7._function4'))

    @pytest.mark.skipif(six.PY3,
            reason='Yet to be able to work out name of subclass')
    def test_subclass_old_class_wrapped_type_instancemethod(self):
        self.assertEqual(
                callable_name(_test_object_names._class7._function5),
                _test_object_names._module_fqdn('_class7._function5'))

    def test_subclass_old_class_wrapped_instance_instancemethod(self):
        self.assertEqual(
                callable_name(_test_object_names._class7()._function5),
                _test_object_names._module_fqdn('_class7._function5'))

    @pytest.mark.skipif(six.PY3,
            reason='Yet to be able to work out name of subclass')
    def test_subclass_new_class_type_instancemethod(self):
        self.assertEqual(
                callable_name(_test_object_names._class8._function1),
                _test_object_names._module_fqdn('_class8._function1'))

    def test_subclass_new_class_instance_instancemethod(self):
        self.assertEqual(
                callable_name(_test_object_names._class8()._function1),
                _test_object_names._module_fqdn('_class8._function1'))

    def test_subclass_new_class_type_classmethod(self):
        self.assertEqual(
                callable_name(_test_object_names._class8._function2),
                _test_object_names._module_fqdn('_class8._function2'))

    def test_subclass_new_class_instance_classmethod(self):
        self.assertEqual(
                callable_name(_test_object_names._class8()._function2),
                _test_object_names._module_fqdn('_class8._function2'))

    @pytest.mark.skipif(six.PY3,
            reason='Yet to be able to work out name of subclass')
    def test_subclass_new_class_type_staticmethod(self):
        if six.PY3:
            self.assertEqual(
                    callable_name(_test_object_names._class8._function3),
                    _test_object_names._module_fqdn('_class8._function3'))
        else:
            # Cannot work out class name for Python 2.
            self.assertEqual(
                    callable_name(_test_object_names._class8._function3),
                    _test_object_names._module_fqdn('_function3'))

    @pytest.mark.skipif(six.PY3,
            reason='Yet to be able to work out name of subclass')
    def test_subclass_new_class_instance_staticmethod(self):
        if six.PY3:
            self.assertEqual(
                    callable_name(_test_object_names._class8()._function3),
                    _test_object_names._module_fqdn('_class8._function3'))
        else:
            # Cannot work out class name for Python 2.
            self.assertEqual(
                    callable_name(_test_object_names._class8()._function3),
                    _test_object_names._module_fqdn('_function3'))

    def test_subclass_new_class_non_inherited_method(self):
        self.assertEqual(
                callable_name(_test_object_names._class8()._function4),
                _test_object_names._module_fqdn('_class8._function4'))

    @pytest.mark.skipif(six.PY3,
            reason='Yet to be able to work out name of subclass')
    def test_subclass_new_class_wrapped_type_instancemethod(self):
        self.assertEqual(
                callable_name(_test_object_names._class8._function5),
                _test_object_names._module_fqdn('_class8._function5'))

    def test_subclass_new_class_wrapped_instance_instancemethod(self):
        self.assertEqual(
                callable_name(_test_object_names._class8()._function5),
                _test_object_names._module_fqdn('_class8._function5'))

    def test_subclass_new_class_wrapped_bound_method(self):
        decorator = _test_object_names._decorator3
        bound_method = _test_object_names._class8()._function1
        test_object = decorator(bound_method)
        self.assertEqual(
                callable_name(test_object),
                _test_object_names._module_fqdn('_class8._function1'))

    @pytest.mark.skipif(six.PY3,
            reason='Yet to be able to work out name of subclass')
    def test_subclass_new_class_type_instancemethod_wraps_decorator(self):
        self.assertEqual(
                callable_name(_test_object_names._class11._function1),
                _test_object_names._module_fqdn('_class11._function1'))

    def test_subclass_new_class_instance_instancemethod_wraps_decorator(self):
        self.assertEqual(
                callable_name(_test_object_names._class11()._function1),
                _test_object_names._module_fqdn('_class11._function1'))

    @pytest.mark.skipif(six.PY3,
            reason='Yet to be able to work out name of subclass')
    def test_subclass_new_class_type_instancemethod_desc_decorator(self):
        if six.PY3:
            self.assertEqual(
                    callable_name(_test_object_names._class11._function2),
                    _test_object_names._module_fqdn('_class11._function2'))
        else:
            # Cannot work out class name for Python 2.
            self.assertEqual(
                    callable_name(_test_object_names._class11._function2),
                    _test_object_names._module_fqdn('_function2'))

    @pytest.mark.skipif(six.PY3,
            reason='Yet to be able to work out name of subclass')
    def test_subclass_new_class_instance_instancemethod_desc_decorator(self):
        if six.PY3:
            self.assertEqual(
                    callable_name(_test_object_names._class11()._function2),
                    _test_object_names._module_fqdn('_class11._function2'))
        else:
            # Cannot work out class name for Python 2.
            self.assertEqual(
                    callable_name(_test_object_names._class11()._function2),
                    _test_object_names._module_fqdn('_function2'))

class TestCallableNameCaching(unittest.TestCase):

    def setUp(self):
        reload(_test_object_names)

        if six.PY3:
            self.method = _test_object_names._class9()._function1
            self.method_as_function = _test_object_names._class9._function1
        else:
            self.bound_method = _test_object_names._class9()._function1
            self.method = _test_object_names._class9._function1

        self.function = _test_object_names._function4
        self.wrapper = _test_object_names._decorator3
        self.bound_wrapped = _test_object_names._class9()._function2

        assert inspect.ismethod(self.method)
        assert inspect.isfunction(self.function)
        assert hasattr(self.bound_wrapped, '_nr_parent')

        self.cached_callable_name = ':'.join(_test_object_names._cached_value)

    @pytest.mark.skipif(not six.PY3, reason='This is a python 3 only test')
    def test_py3_method_as_function_uses_cache(self):
        self.assertEqual(
                callable_name(self.method_as_function),
                self.cached_callable_name)

    @pytest.mark.skipif(six.PY3, reason='This is a python 2 only test')
    def test_py2_bound_method_uses_cache(self):
        self.assertEqual(
                callable_name(self.bound_method),
                self.cached_callable_name)

    @pytest.mark.skipif(not six.PY3, reason='This is a python 3 only test')
    def test_py3_methods_do_not_use_cache(self):
        self.assertNotEqual(
                callable_name(self.method),
                self.cached_callable_name)

    @pytest.mark.skipif(six.PY3, reason='This is a python 2 only test')
    def test_py2_methods_use_cache(self):
        self.assertEqual(
                callable_name(self.method),
                self.cached_callable_name)

    def test_functions_use_cache(self):
        self.assertEqual(
                callable_name(self.function),
                self.cached_callable_name)

    def test_wrapped_bound_methods_use_parent_cache(self):
        # whether this is py2 or py3, always use the cache since the parent
        # object will never be a method
        self.assertEqual(
                callable_name(self.bound_wrapped),
                self.cached_callable_name)

    @pytest.mark.skipif(not six.PY3, reason='This is a python 3 only test')
    def test_py3_wrapped_methods_do_not_use_source_cache(self):
        method = self.wrapper(self.method)
        self.assertNotEqual(
                callable_name(method),
                self.cached_callable_name)

    @pytest.mark.skipif(six.PY3, reason='This is a python 2 only test')
    def test_py2_wrapped_methods_use_source_cache(self):
        method = self.wrapper(self.method)
        self.assertEqual(
                callable_name(method),
                self.cached_callable_name)

    def test_wrapped_functions_use_source_cache(self):
        function = self.wrapper(self.function)
        self.assertEqual(
                callable_name(function),
                self.cached_callable_name)

class TestExpandBuiltinExceptionName(unittest.TestCase):

    def test_builtin_exception(self):
        result = expand_builtin_exception_name('KeyError')
        if six.PY3:
            self.assertEqual(result, 'builtins:KeyError')
        elif six.PY2:
            self.assertEqual(result, 'exceptions:KeyError')
        else:
            self.assertEqual(result, 'KeyError')

    def test_base_exception(self):
        result = expand_builtin_exception_name('BaseException')
        if six.PY3:
            self.assertEqual(result, 'builtins:BaseException')
        elif six.PY2:
            self.assertEqual(result, 'exceptions:BaseException')
        else:
            self.assertEqual(result, 'BaseException')

    def test_warning(self):
        result = expand_builtin_exception_name('UnicodeWarning')
        if six.PY3:
            self.assertEqual(result, 'builtins:UnicodeWarning')
        elif six.PY2:
            self.assertEqual(result, 'exceptions:UnicodeWarning')
        else:
            self.assertEqual(result, 'UnicodeWarning')

    def test_py3_exception_only(self):
        result = expand_builtin_exception_name('BrokenPipeError')
        if six.PY3:
            self.assertEqual(result, 'builtins:BrokenPipeError')
        else:
            self.assertEqual(result, 'BrokenPipeError')

    def test_not_builtin(self):
        result = expand_builtin_exception_name('Foo')
        self.assertEqual(result, 'Foo')

    def test_builtin_not_exception(self):
        result = expand_builtin_exception_name('sum')
        self.assertEqual(result, 'sum')

    def test_not_builtin_with_colon(self):
        result = expand_builtin_exception_name('MyModule:KeyError')
        self.assertEqual(result, 'MyModule:KeyError')

if __name__ == '__main__':
    unittest.main()
