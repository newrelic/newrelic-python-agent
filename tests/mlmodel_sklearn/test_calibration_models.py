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

import pytest
from sklearn import __version__  # noqa: needed for get_package_version
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


def test_model_methods_wrapped_in_function_trace(calibration_model_name, run_calibration_model):
    expected_scoped_metrics = {
        "CalibratedClassifierCV": [
            ("Function/MLModel/Sklearn/Named/CalibratedClassifierCV.fit", 1),
            ("Function/MLModel/Sklearn/Named/CalibratedClassifierCV.predict", 2),
            ("Function/MLModel/Sklearn/Named/CalibratedClassifierCV.predict_proba", 2),
        ],
        # "CalibrationDisplay": [
        #     ("Function/MLModel/Sklearn/Named/CalibrationDisplay.from_predictions", 2),
        # ],
    }

    # if SKLEARN_v1_0_TO_v1_1:
    #     expected_scoped_metrics["HistGradientBoostingClassifier"] = [
    #         ("Function/MLModel/Sklearn/Named/HistGradientBoostingClassifier.fit", 1),
    #         ("Function/MLModel/Sklearn/Named/HistGradientBoostingClassifier.predict", 2),
    #         ("Function/MLModel/Sklearn/Named/HistGradientBoostingClassifier.score", 1),
    #         ("Function/MLModel/Sklearn/Named/HistGradientBoostingClassifier.predict_proba", 3),
    #     ]
    # elif SKLEARN_v1_1_AND_ABOVE:
    #     if sys.version_info[:2] > (3, 7):
    #         expected_scoped_metrics["VotingClassifier"].append(
    #             ("Function/MLModel/Sklearn/Named/VotingClassifier.predict_proba", 3)
    #         )
    #     expected_scoped_metrics["StackingClassifier"] = [
    #         ("Function/MLModel/Sklearn/Named/StackingClassifier.fit", 1),
    #         ("Function/MLModel/Sklearn/Named/StackingClassifier.predict", 2),
    #         ("Function/MLModel/Sklearn/Named/StackingClassifier.score", 1),
    #         ("Function/MLModel/Sklearn/Named/StackingClassifier.predict_proba", 1),
    #         ("Function/MLModel/Sklearn/Named/StackingClassifier.transform", 4),
    #     ]

    expected_transaction_name = "test_calibration_models:_test"
    if six.PY3:
        expected_transaction_name = (
            "test_calibration_models:test_model_methods_wrapped_in_function_trace.<locals>._test"
        )

    @validate_transaction_metrics(
        expected_transaction_name,
        scoped_metrics=expected_scoped_metrics[calibration_model_name],
        rollup_metrics=expected_scoped_metrics[calibration_model_name],
        background_task=True,
    )
    @background_task()
    def _test():
        run_calibration_model()

    _test()


# class_params = [
#     "AdaBoostClassifier",
#     "AdaBoostRegressor",
#     "BaggingClassifier",
#     "BaggingRegressor",
#     "ExtraTreesClassifier",
#     "ExtraTreesRegressor",
#     "GradientBoostingClassifier",
#     "GradientBoostingRegressor",
#     "IsolationForest",
#     "RandomForestClassifier",
#     "RandomForestRegressor",
# ]
# if SKLEARN_v1_0_TO_v1_1 or SKLEARN_v1_1_AND_ABOVE:
#     class_params.extend(
#         (
#             "HistGradientBoostingClassifier",
#             "HistGradientBoostingRegressor",
#             "StackingClassifier",
#             "StackingRegressor",
#             "VotingClassifier",
#             "VotingRegressor",
#         )
#     )


@pytest.fixture(params=["CalibratedClassifierCV"])
def calibration_model_name(request):
    return request.param


@pytest.fixture
def run_calibration_model(calibration_model_name):
    def _run():
        from sklearn import calibration as calibration
        from sklearn.datasets import load_iris
        from sklearn.model_selection import train_test_split

        # This works better with StackingClassifier and StackingRegressor models
        X, y = load_iris(return_X_y=True)
        x_train, x_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=0)

        # if calibration_model_name == "StackingClassifier":
        #     clf = getattr(sklearn.calibration, calibration_model_name)(
        #         estimators=[("rf", RandomForestClassifier())], final_estimator=RandomForestClassifier()
        #     )
        # elif calibration_model_name == "VotingClassifier":
        #     # Voting=soft is needed to also be able to test for "predict_proba"
        #     # However, predict_proba is not supported in versions less than v1.1
        #     if SKLEARN_BELOW_v1_0 or SKLEARN_v1_0_TO_v1_1:
        #         voting_flag = "hard"
        #     else:
        #         voting_flag = "soft"
        #     clf = getattr(sklearn.calibration, calibration_model_name)(
        #         estimators=[("rf", RandomForestClassifier())], voting=voting_flag
        #     )
        # elif calibration_model_name == "StackingRegressor":
        #     clf = getattr(sklearn.calibration, calibration_model_name)(
        #         estimators=[("rf", RandomForestRegressor())], final_estimator=RandomForestRegressor()
        #     )
        # elif calibration_model_name == "VotingRegressor":
        #     clf = getattr(sklearn.calibration, calibration_model_name)([("rf", RandomForestRegressor())])
        # else:
        # clf = getattr(calibration, calibration_model_name)(random_state=0)
        clf = getattr(calibration, calibration_model_name)()

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
