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

import sys

import pytest
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.common.package_version_utils import get_package_version
from newrelic.packages import six

SKLEARN_VERSION = get_package_version("sklearn")

SKLEARN_BELOW_v1_0 = SKLEARN_VERSION < "1.0"
SKLEARN_v1_0_TO_v1_1 = SKLEARN_VERSION >= "1.0" and SKLEARN_VERSION < "1.1"
SKLEARN_v1_1_AND_ABOVE = SKLEARN_VERSION >= "1.1"


def test_model_methods_wrapped_in_function_trace(ensemble_model_name, run_ensemble_model):
    expected_scoped_metrics = {
        "AdaBoostClassifier": [
            ("Function/MLModel/Sklearn/Named/AdaBoostClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/AdaBoostClassifier.predict", 2),
            ("Function/MLModel/Sklearn/Named/AdaBoostClassifier.predict_log_proba", 1),
            ("Function/MLModel/Sklearn/Named/AdaBoostClassifier.predict_proba", 2),
            ("Function/MLModel/Sklearn/Named/AdaBoostClassifier.score", 1),
        ],
        "AdaBoostRegressor": [
            ("Function/MLModel/Sklearn/Named/AdaBoostRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/AdaBoostRegressor.predict", 2),
            ("Function/MLModel/Sklearn/Named/AdaBoostRegressor.score", 1),
        ],
        "BaggingClassifier": [
            ("Function/MLModel/Sklearn/Named/BaggingClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/BaggingClassifier.predict", 2),
            ("Function/MLModel/Sklearn/Named/BaggingClassifier.score", 1),
            ("Function/MLModel/Sklearn/Named/BaggingClassifier.predict_log_proba", 1),
            ("Function/MLModel/Sklearn/Named/BaggingClassifier.predict_proba", 3),
        ],
        "BaggingRegressor": [
            ("Function/MLModel/Sklearn/Named/BaggingRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/BaggingRegressor.predict", 2),
            ("Function/MLModel/Sklearn/Named/BaggingRegressor.score", 1),
        ],
        "ExtraTreesClassifier": [
            ("Function/MLModel/Sklearn/Named/ExtraTreesClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/ExtraTreesClassifier.predict", 2),
            ("Function/MLModel/Sklearn/Named/ExtraTreesClassifier.score", 1),
            ("Function/MLModel/Sklearn/Named/ExtraTreesClassifier.predict_log_proba", 1),
            ("Function/MLModel/Sklearn/Named/ExtraTreesClassifier.predict_proba", 4),
        ],
        "ExtraTreesRegressor": [
            ("Function/MLModel/Sklearn/Named/ExtraTreesRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/ExtraTreesRegressor.predict", 2),
            ("Function/MLModel/Sklearn/Named/ExtraTreesRegressor.score", 1),
        ],
        "GradientBoostingClassifier": [
            ("Function/MLModel/Sklearn/Named/GradientBoostingClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/GradientBoostingClassifier.predict", 2),
            ("Function/MLModel/Sklearn/Named/GradientBoostingClassifier.score", 1),
            ("Function/MLModel/Sklearn/Named/GradientBoostingClassifier.predict_log_proba", 1),
            ("Function/MLModel/Sklearn/Named/GradientBoostingClassifier.predict_proba", 2),
        ],
        "GradientBoostingRegressor": [
            ("Function/MLModel/Sklearn/Named/GradientBoostingRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/GradientBoostingRegressor.predict", 2),
            ("Function/MLModel/Sklearn/Named/GradientBoostingRegressor.score", 1),
        ],
        "IsolationForest": [
            ("Function/MLModel/Sklearn/Named/IsolationForest.fit", 1),
            ("Function/MLModel/Sklearn/Named/IsolationForest.predict", 1),
        ],
        "RandomForestClassifier": [
            ("Function/MLModel/Sklearn/Named/RandomForestClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/RandomForestClassifier.predict", 2),
            ("Function/MLModel/Sklearn/Named/RandomForestClassifier.score", 1),
            ("Function/MLModel/Sklearn/Named/RandomForestClassifier.predict_log_proba", 1),
            ("Function/MLModel/Sklearn/Named/RandomForestClassifier.predict_proba", 4),
        ],
        "RandomForestRegressor": [
            ("Function/MLModel/Sklearn/Named/RandomForestRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/RandomForestRegressor.predict", 2),
            ("Function/MLModel/Sklearn/Named/RandomForestRegressor.score", 1),
        ],
        "VotingClassifier": [
            ("Function/MLModel/Sklearn/Named/VotingClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/VotingClassifier.predict", 2),
            ("Function/MLModel/Sklearn/Named/VotingClassifier.score", 1),
            ("Function/MLModel/Sklearn/Named/VotingClassifier.transform", 1),
        ],
    }

    if SKLEARN_v1_0_TO_v1_1:
        expected_scoped_metrics["HistGradientBoostingClassifier"] = [
            ("Function/MLModel/Sklearn/Named/HistGradientBoostingClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/HistGradientBoostingClassifier.predict", 2),
            ("Function/MLModel/Sklearn/Named/HistGradientBoostingClassifier.score", 1),
            ("Function/MLModel/Sklearn/Named/HistGradientBoostingClassifier.predict_proba", 3),
        ]
        expected_scoped_metrics["HistGradientBoostingRegressor"] = [
            ("Function/MLModel/Sklearn/Named/HistGradientBoostingRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/HistGradientBoostingRegressor.predict", 2),
            ("Function/MLModel/Sklearn/Named/HistGradientBoostingRegressor.score", 1),
        ]
        expected_scoped_metrics["StackingClassifier"] = [
            ("Function/MLModel/Sklearn/Named/StackingClassifier.fit", 1),
        ]
        expected_scoped_metrics["StackingRegressor"] = [
            ("Function/MLModel/Sklearn/Named/StackingRegressor.fit", 1),
        ]
        expected_scoped_metrics["VotingRegressor"] = [
            ("Function/MLModel/Sklearn/Named/VotingRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/VotingRegressor.predict", 2),
            ("Function/MLModel/Sklearn/Named/VotingRegressor.score", 1),
            ("Function/MLModel/Sklearn/Named/VotingRegressor.transform", 1),
        ]
    elif SKLEARN_v1_1_AND_ABOVE:
        if sys.version_info[:2] > (3, 7):
            expected_scoped_metrics["VotingClassifier"].append(
                ("Function/MLModel/Sklearn/Named/VotingClassifier.predict_proba", 3)
            )
        expected_scoped_metrics["StackingClassifier"] = [
            ("Function/MLModel/Sklearn/Named/StackingClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/StackingClassifier.predict", 2),
            ("Function/MLModel/Sklearn/Named/StackingClassifier.score", 1),
            ("Function/MLModel/Sklearn/Named/StackingClassifier.predict_proba", 1),
            ("Function/MLModel/Sklearn/Named/StackingClassifier.transform", 4),
        ]
        expected_scoped_metrics["StackingRegressor"] = [
            ("Function/MLModel/Sklearn/Named/StackingRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/StackingRegressor.predict", 2),
            ("Function/MLModel/Sklearn/Named/StackingRegressor.score", 1),
        ]
        expected_scoped_metrics["VotingRegressor"] = [
            ("Function/MLModel/Sklearn/Named/VotingRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/VotingRegressor.predict", 2),
            ("Function/MLModel/Sklearn/Named/VotingRegressor.score", 1),
            ("Function/MLModel/Sklearn/Named/VotingRegressor.transform", 1),
        ]
        expected_scoped_metrics["HistGradientBoostingClassifier"] = [
            ("Function/MLModel/Sklearn/Named/HistGradientBoostingClassifier.fit", 1),
            ("Function/MLModel/Sklearn/Named/HistGradientBoostingClassifier.predict", 2),
            ("Function/MLModel/Sklearn/Named/HistGradientBoostingClassifier.score", 1),
            ("Function/MLModel/Sklearn/Named/HistGradientBoostingClassifier.predict_proba", 3),
        ]
        expected_scoped_metrics["HistGradientBoostingRegressor"] = [
            ("Function/MLModel/Sklearn/Named/HistGradientBoostingRegressor.fit", 1),
            ("Function/MLModel/Sklearn/Named/HistGradientBoostingRegressor.predict", 2),
            ("Function/MLModel/Sklearn/Named/HistGradientBoostingRegressor.score", 1),
        ]

    expected_transaction_name = "test_ensemble_models:_test"
    if six.PY3:
        expected_transaction_name = "test_ensemble_models:test_model_methods_wrapped_in_function_trace.<locals>._test"

    @validate_transaction_metrics(
        expected_transaction_name,
        scoped_metrics=expected_scoped_metrics[ensemble_model_name],
        rollup_metrics=expected_scoped_metrics[ensemble_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_ensemble_model()

    _test()


class_params = [
    "AdaBoostClassifier",
    "AdaBoostRegressor",
    "BaggingClassifier",
    "BaggingRegressor",
    "ExtraTreesClassifier",
    "ExtraTreesRegressor",
    "GradientBoostingClassifier",
    "GradientBoostingRegressor",
    "IsolationForest",
    "RandomForestClassifier",
    "RandomForestRegressor",
]
if SKLEARN_v1_0_TO_v1_1 or SKLEARN_v1_1_AND_ABOVE:
    class_params.extend(
        (
            "HistGradientBoostingClassifier",
            "HistGradientBoostingRegressor",
            "StackingClassifier",
            "StackingRegressor",
            "VotingClassifier",
            "VotingRegressor",
        )
    )


@pytest.fixture(params=class_params)
def ensemble_model_name(request):
    return request.param


@pytest.fixture
def run_ensemble_model(ensemble_model_name):
    def _run():
        import sklearn.ensemble
        from sklearn.datasets import load_iris
        from sklearn.model_selection import train_test_split

        # This works better with StackingClassifier and StackingRegressor models
        X, y = load_iris(return_X_y=True)
        x_train, x_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=0)

        if ensemble_model_name == "StackingClassifier":
            clf = getattr(sklearn.ensemble, ensemble_model_name)(
                estimators=[("rf", RandomForestClassifier())], final_estimator=RandomForestClassifier()
            )
        elif ensemble_model_name == "VotingClassifier":
            # Voting=soft is needed to also be able to test for "predict_proba"
            # However, predict_proba is not supported in versions less than v1.1
            if SKLEARN_BELOW_v1_0 or SKLEARN_v1_0_TO_v1_1:
                voting_flag = "hard"
            else:
                voting_flag = "soft"
            clf = getattr(sklearn.ensemble, ensemble_model_name)(
                estimators=[("rf", RandomForestClassifier())], voting=voting_flag
            )
        elif ensemble_model_name == "StackingRegressor":
            clf = getattr(sklearn.ensemble, ensemble_model_name)(
                estimators=[("rf", RandomForestRegressor())], final_estimator=RandomForestRegressor()
            )
        elif ensemble_model_name == "VotingRegressor":
            clf = getattr(sklearn.ensemble, ensemble_model_name)([("rf", RandomForestRegressor())])
        else:
            clf = getattr(sklearn.ensemble, ensemble_model_name)(random_state=0)

        model = clf.fit(x_train, y_train)
        model.predict(x_test)

        if hasattr(model, "score"):
            model.score(x_test, y_test)
        if hasattr(model, "predict_log_proba"):
            model.predict_log_proba(x_test)
        if hasattr(model, "predict_proba"):
            model.predict_proba(x_test)
        if hasattr(model, "transform"):
            model.transform(x_test)

        return model

    return _run
