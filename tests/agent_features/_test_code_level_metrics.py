# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import functools

def exercise_function():
    return


class ExerciseClass():
    def exercise_method(self):
        return

    @staticmethod
    def exercise_static_method():
        return

    @classmethod
    def exercise_class_method(cls):
        return


class ExerciseClassCallable():
    def __call__(self):
        return

CLASS_INSTANCE = ExerciseClass()
CLASS_INSTANCE_CALLABLE = ExerciseClassCallable()

exercise_lambda = lambda: None
exercise_partial = functools.partial(exercise_function)
