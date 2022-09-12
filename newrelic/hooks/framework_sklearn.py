from newrelic.api.function_trace import FunctionTrace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper


def _wrap_sklearn_method_wrapper(module, function):
    name = "%s.%s" % (module.__name__, function)

    def _nr_wrapper_sklearn_method_(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        with FunctionTrace(name=name) as function_trace:
            output = wrapped(*args, **kwargs)

        function_trace.add_custom_attribute("input", args[0])
        function_trace.add_custom_attribute("output", output)

        return output

    wrap_function_wrapper(module, function, _nr_wrapper_sklearn_method_)


def instrument_sklearn(module):
    if module.__name__ == 'sklearn.base':
        if hasattr(module.ClusterMixin, "fit_predict"):
            _wrap_sklearn_method_wrapper(module, "ClusterMixin.fit_predict")

    if module.__name__ == 'sklearn.calibration':
        if hasattr(module.CalibratedClassifierCV, "predict"):
            _wrap_sklearn_method_wrapper(module, "CalibratedClassifierCV.predict")
        if hasattr(module.CalibratedClassifierCV, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "CalibratedClassifierCV.predict_proba")
        if hasattr(module.CalibrationDisplay, "from_predictions"):
            _wrap_sklearn_method_wrapper(module, "CalibrationDisplay.from_predictions")

    if module.__name__ == 'sklearn.cluster':
        if hasattr(module.AffinityPropagation, "fit_predict"):
            _wrap_sklearn_method_wrapper(module, "AffinityPropagation.fit_predict")
        if hasattr(module.AffinityPropagation, "predict"):
            _wrap_sklearn_method_wrapper(module, "AffinityPropagation.predict")
        if hasattr(module.AgglomerativeClustering, "fit_predict"):
            _wrap_sklearn_method_wrapper(module, "AgglomerativeClustering.fit_predict")
        if hasattr(module.Birch, "fit_predict"):
            _wrap_sklearn_method_wrapper(module, "Birch.fit_predict")
        if hasattr(module.Birch, "predict"):
            _wrap_sklearn_method_wrapper(module, "Birch.predict")
        if hasattr(module.BisectingKMeans, "fit_predict"):
            _wrap_sklearn_method_wrapper(module, "BisectingKMeans.fit_predict")
        if hasattr(module.BisectingKMeans, "predict"):
            _wrap_sklearn_method_wrapper(module, "BisectingKMeans.predict")
        if hasattr(module.DBSCAN, "fit_predict"):
            _wrap_sklearn_method_wrapper(module, "DBSCAN.fit_predict")
        if hasattr(module.FeatureAgglomeration, "fit_predict"):
            _wrap_sklearn_method_wrapper(module, "FeatureAgglomeration.fit_predict")
        if hasattr(module.KMeans, "fit_predict"):
            _wrap_sklearn_method_wrapper(module, "KMeans.fit_predict")
        if hasattr(module.KMeans, "predict"):
            _wrap_sklearn_method_wrapper(module, "KMeans.predict")
        if hasattr(module.MeanShift, "fit_predict"):
            _wrap_sklearn_method_wrapper(module, "MeanShift.fit_predict")
        if hasattr(module.MeanShift, "predict"):
            _wrap_sklearn_method_wrapper(module, "MeanShift.predict")
        if hasattr(module.MiniBatchKMeans, "fit_predict"):
            _wrap_sklearn_method_wrapper(module, "MiniBatchKMeans.fit_predict")
        if hasattr(module.MiniBatchKMeans, "predict"):
            _wrap_sklearn_method_wrapper(module, "MiniBatchKMeans.predict")
        if hasattr(module.OPTICS, "fit_predict"):
            _wrap_sklearn_method_wrapper(module, "OPTICS.fit_predict")
        if hasattr(module.SpectralClustering, "fit_predict"):
            _wrap_sklearn_method_wrapper(module, "SpectralClustering.fit_predict")

    if module.__name__ == 'sklearn.compose':
        if hasattr(module.TransformedTargetRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "TransformedTargetRegressor.predict")

    if module.__name__ == 'sklearn.covariance':
        if hasattr(module.EllipticEnvelope, "fit_predict"):
            _wrap_sklearn_method_wrapper(module, "EllipticEnvelope.fit_predict")
        if hasattr(module.EllipticEnvelope, "predict"):
            _wrap_sklearn_method_wrapper(module, "EllipticEnvelope.predict")

    if module.__name__ == 'sklearn.cross_decomposition':
        if hasattr(module.CCA, "predict"):
            _wrap_sklearn_method_wrapper(module, "CCA.predict")
        if hasattr(module.PLSCanonical, "predict"):
            _wrap_sklearn_method_wrapper(module, "PLSCanonical.predict")
        if hasattr(module.PLSRegression, "predict"):
            _wrap_sklearn_method_wrapper(module, "PLSRegression.predict")

    if module.__name__ == 'sklearn.discriminant_analysis':
        if hasattr(module.LinearDiscriminantAnalysis, "predict"):
            _wrap_sklearn_method_wrapper(module, "LinearDiscriminantAnalysis.predict")
        if hasattr(module.LinearDiscriminantAnalysis, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "LinearDiscriminantAnalysis.predict_log_proba")
        if hasattr(module.LinearDiscriminantAnalysis, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "LinearDiscriminantAnalysis.predict_proba")
        if hasattr(module.QuadraticDiscriminantAnalysis, "predict"):
            _wrap_sklearn_method_wrapper(module, "QuadraticDiscriminantAnalysis.predict")
        if hasattr(module.QuadraticDiscriminantAnalysis, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "QuadraticDiscriminantAnalysis.predict_log_proba")
        if hasattr(module.QuadraticDiscriminantAnalysis, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "QuadraticDiscriminantAnalysis.predict_proba")

    if module.__name__ == 'sklearn.dummy':
        if hasattr(module.DummyClassifier, "predict"):
            _wrap_sklearn_method_wrapper(module, "DummyClassifier.predict")
        if hasattr(module.DummyClassifier, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "DummyClassifier.predict_log_proba")
        if hasattr(module.DummyClassifier, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "DummyClassifier.predict_proba")
        if hasattr(module.DummyRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "DummyRegressor.predict")

    if module.__name__ == 'sklearn.ensemble':
        if hasattr(module.AdaBoostClassifier, "predict"):
            _wrap_sklearn_method_wrapper(module, "AdaBoostClassifier.predict")
        if hasattr(module.AdaBoostClassifier, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "AdaBoostClassifier.predict_log_proba")
        if hasattr(module.AdaBoostClassifier, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "AdaBoostClassifier.predict_proba")
        if hasattr(module.AdaBoostClassifier, "staged_predict"):
            _wrap_sklearn_method_wrapper(module, "AdaBoostClassifier.staged_predict")
        if hasattr(module.AdaBoostClassifier, "staged_predict_proba"):
            _wrap_sklearn_method_wrapper(module, "AdaBoostClassifier.staged_predict_proba")
        if hasattr(module.AdaBoostRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "AdaBoostRegressor.predict")
        if hasattr(module.AdaBoostRegressor, "staged_predict"):
            _wrap_sklearn_method_wrapper(module, "AdaBoostRegressor.staged_predict")
        if hasattr(module.BaggingClassifier, "predict"):
            _wrap_sklearn_method_wrapper(module, "BaggingClassifier.predict")
        if hasattr(module.BaggingClassifier, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "BaggingClassifier.predict_log_proba")
        if hasattr(module.BaggingClassifier, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "BaggingClassifier.predict_proba")
        if hasattr(module.BaggingRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "BaggingRegressor.predict")
        if hasattr(module.ExtraTreesClassifier, "predict"):
            _wrap_sklearn_method_wrapper(module, "ExtraTreesClassifier.predict")
        if hasattr(module.ExtraTreesClassifier, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "ExtraTreesClassifier.predict_log_proba")
        if hasattr(module.ExtraTreesClassifier, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "ExtraTreesClassifier.predict_proba")
        if hasattr(module.ExtraTreesRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "ExtraTreesRegressor.predict")
        if hasattr(module.GradientBoostingClassifier, "predict"):
            _wrap_sklearn_method_wrapper(module, "GradientBoostingClassifier.predict")
        if hasattr(module.GradientBoostingClassifier, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "GradientBoostingClassifier.predict_log_proba")
        if hasattr(module.GradientBoostingClassifier, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "GradientBoostingClassifier.predict_proba")
        if hasattr(module.GradientBoostingClassifier, "staged_predict"):
            _wrap_sklearn_method_wrapper(module, "GradientBoostingClassifier.staged_predict")
        if hasattr(module.GradientBoostingClassifier, "staged_predict_proba"):
            _wrap_sklearn_method_wrapper(module, "GradientBoostingClassifier.staged_predict_proba")
        if hasattr(module.GradientBoostingRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "GradientBoostingRegressor.predict")
        if hasattr(module.GradientBoostingRegressor, "staged_predict"):
            _wrap_sklearn_method_wrapper(module, "GradientBoostingRegressor.staged_predict")
        if hasattr(module.HistGradientBoostingClassifier, "predict"):
            _wrap_sklearn_method_wrapper(module, "HistGradientBoostingClassifier.predict")
        if hasattr(module.HistGradientBoostingClassifier, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "HistGradientBoostingClassifier.predict_proba")
        if hasattr(module.HistGradientBoostingClassifier, "staged_predict"):
            _wrap_sklearn_method_wrapper(module, "HistGradientBoostingClassifier.staged_predict")
        if hasattr(module.HistGradientBoostingClassifier, "staged_predict_proba"):
            _wrap_sklearn_method_wrapper(module, "HistGradientBoostingClassifier.staged_predict_proba")
        if hasattr(module.HistGradientBoostingRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "HistGradientBoostingRegressor.predict")
        if hasattr(module.HistGradientBoostingRegressor, "staged_predict"):
            _wrap_sklearn_method_wrapper(module, "HistGradientBoostingRegressor.staged_predict")
        if hasattr(module.IsolationForest, "fit_predict"):
            _wrap_sklearn_method_wrapper(module, "IsolationForest.fit_predict")
        if hasattr(module.IsolationForest, "predict"):
            _wrap_sklearn_method_wrapper(module, "IsolationForest.predict")
        if hasattr(module.RandomForestClassifier, "predict"):
            _wrap_sklearn_method_wrapper(module, "RandomForestClassifier.predict")
        if hasattr(module.RandomForestClassifier, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "RandomForestClassifier.predict_log_proba")
        if hasattr(module.RandomForestClassifier, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "RandomForestClassifier.predict_proba")
        if hasattr(module.RandomForestRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "RandomForestRegressor.predict")
        if hasattr(module.StackingClassifier, "predict"):
            _wrap_sklearn_method_wrapper(module, "StackingClassifier.predict")
        if hasattr(module.StackingClassifier, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "StackingClassifier.predict_proba")
        if hasattr(module.StackingRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "StackingRegressor.predict")
        if hasattr(module.VotingClassifier, "predict"):
            _wrap_sklearn_method_wrapper(module, "VotingClassifier.predict")
        if hasattr(module.VotingClassifier, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "VotingClassifier.predict_proba")
        if hasattr(module.VotingRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "VotingRegressor.predict")

    if module.__name__ == 'sklearn.feature_selection':
        if hasattr(module.RFE, "predict"):
            _wrap_sklearn_method_wrapper(module, "RFE.predict")
        if hasattr(module.RFE, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "RFE.predict_log_proba")
        if hasattr(module.RFE, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "RFE.predict_proba")
        if hasattr(module.RFECV, "predict"):
            _wrap_sklearn_method_wrapper(module, "RFECV.predict")
        if hasattr(module.RFECV, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "RFECV.predict_log_proba")
        if hasattr(module.RFECV, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "RFECV.predict_proba")

    if module.__name__ == 'sklearn.gaussian_process':
        if hasattr(module.GaussianProcessClassifier, "predict"):
            _wrap_sklearn_method_wrapper(module, "GaussianProcessClassifier.predict")
        if hasattr(module.GaussianProcessClassifier, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "GaussianProcessClassifier.predict_proba")
        if hasattr(module.GaussianProcessRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "GaussianProcessRegressor.predict")
    if module.__name__ == 'sklearn.isotonic':
        if hasattr(module.IsotonicRegression, "predict"):
            _wrap_sklearn_method_wrapper(module, "IsotonicRegression.predict")

    if module.__name__ == 'sklearn.kernel_ridge':
        if hasattr(module.KernelRidge, "predict"):
            _wrap_sklearn_method_wrapper(module, "KernelRidge.predict")

    if module.__name__ == 'sklearn.linear_model':
        if hasattr(module.ARDRegression, "predict"):
            _wrap_sklearn_method_wrapper(module, "ARDRegression.predict")
        if hasattr(module.BayesianRidge, "predict"):
            _wrap_sklearn_method_wrapper(module, "BayesianRidge.predict")
        if hasattr(module.ElasticNet, "predict"):
            _wrap_sklearn_method_wrapper(module, "ElasticNet.predict")
        if hasattr(module.ElasticNetCV, "predict"):
            _wrap_sklearn_method_wrapper(module, "ElasticNetCV.predict")
        if hasattr(module.GammaRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "GammaRegressor.predict")
        if hasattr(module.HuberRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "HuberRegressor.predict")
        if hasattr(module.Lars, "predict"):
            _wrap_sklearn_method_wrapper(module, "Lars.predict")
        if hasattr(module.LarsCV, "predict"):
            _wrap_sklearn_method_wrapper(module, "LarsCV.predict")
        if hasattr(module.Lasso, "predict"):
            _wrap_sklearn_method_wrapper(module, "Lasso.predict")
        if hasattr(module.LassoCV, "predict"):
            _wrap_sklearn_method_wrapper(module, "LassoCV.predict")
        if hasattr(module.LassoLars, "predict"):
            _wrap_sklearn_method_wrapper(module, "LassoLars.predict")
        if hasattr(module.LassoLarsCV, "predict"):
            _wrap_sklearn_method_wrapper(module, "LassoLarsCV.predict")
        if hasattr(module.LassoLarsIC, "predict"):
            _wrap_sklearn_method_wrapper(module, "LassoLarsIC.predict")
        if hasattr(module.LinearRegression, "predict"):
            _wrap_sklearn_method_wrapper(module, "LinearRegression.predict")
        if hasattr(module.LogisticRegression, "predict"):
            _wrap_sklearn_method_wrapper(module, "LogisticRegression.predict")
        if hasattr(module.LogisticRegression, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "LogisticRegression.predict_log_proba")
        if hasattr(module.LogisticRegression, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "LogisticRegression.predict_proba")
        if hasattr(module.LogisticRegressionCV, "predict"):
            _wrap_sklearn_method_wrapper(module, "LogisticRegressionCV.predict")
        if hasattr(module.LogisticRegressionCV, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "LogisticRegressionCV.predict_log_proba")
        if hasattr(module.LogisticRegressionCV, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "LogisticRegressionCV.predict_proba")
        if hasattr(module.MultiTaskElasticNet, "predict"):
            _wrap_sklearn_method_wrapper(module, "MultiTaskElasticNet.predict")
        if hasattr(module.MultiTaskElasticNetCV, "predict"):
            _wrap_sklearn_method_wrapper(module, "MultiTaskElasticNetCV.predict")
        if hasattr(module.MultiTaskLasso, "predict"):
            _wrap_sklearn_method_wrapper(module, "MultiTaskLasso.predict")
        if hasattr(module.MultiTaskLassoCV, "predict"):
            _wrap_sklearn_method_wrapper(module, "MultiTaskLassoCV.predict")
        if hasattr(module.OrthogonalMatchingPursuit, "predict"):
            _wrap_sklearn_method_wrapper(module, "OrthogonalMatchingPursuit.predict")
        if hasattr(module.OrthogonalMatchingPursuitCV, "predict"):
            _wrap_sklearn_method_wrapper(module, "OrthogonalMatchingPursuitCV.predict")
        if hasattr(module.PassiveAggressiveClassifier, "predict"):
            _wrap_sklearn_method_wrapper(module, "PassiveAggressiveClassifier.predict")
        if hasattr(module.Perceptron, "predict"):
            _wrap_sklearn_method_wrapper(module, "Perceptron.predict")
        if hasattr(module.PoissonRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "PoissonRegressor.predict")
        if hasattr(module.QuantileRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "QuantileRegressor.predict")
        if hasattr(module.RANSACRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "RANSACRegressor.predict")
        if hasattr(module.Ridge, "predict"):
            _wrap_sklearn_method_wrapper(module, "Ridge.predict")
        if hasattr(module.RidgeClassifier, "predict"):
            _wrap_sklearn_method_wrapper(module, "RidgeClassifier.predict")
        if hasattr(module.RidgeClassifierCV, "predict"):
            _wrap_sklearn_method_wrapper(module, "RidgeClassifierCV.predict")
        if hasattr(module.RidgeCV, "predict"):
            _wrap_sklearn_method_wrapper(module, "RidgeCV.predict")
        if hasattr(module.SGDClassifier, "predict"):
            _wrap_sklearn_method_wrapper(module, "SGDClassifier.predict")
        if hasattr(module.SGDClassifier, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "SGDClassifier.predict_log_proba")
        if hasattr(module.SGDClassifier, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "SGDClassifier.predict_proba")
        if hasattr(module.SGDOneClassSVM, "fit_predict"):
            _wrap_sklearn_method_wrapper(module, "SGDOneClassSVM.fit_predict")
        if hasattr(module.SGDOneClassSVM, "predict"):
            _wrap_sklearn_method_wrapper(module, "SGDOneClassSVM.predict")
        if hasattr(module.SGDRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "SGDRegressor.predict")
        if hasattr(module.TheilSenRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "TheilSenRegressor.predict")
        if hasattr(module.TweedieRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "TweedieRegressor.predict")

    if module.__name__ == 'sklearn.metrics':
        if hasattr(module.ConfusionMatrixDisplay, "from_predictions"):
            _wrap_sklearn_method_wrapper(module, "ConfusionMatrixDisplay.from_predictions")
        if hasattr(module.DetCurveDisplay, "from_predictions"):
            _wrap_sklearn_method_wrapper(module, "DetCurveDisplay.from_predictions")
        if hasattr(module.PrecisionRecallDisplay, "from_predictions"):
            _wrap_sklearn_method_wrapper(module, "PrecisionRecallDisplay.from_predictions")
        if hasattr(module.RocCurveDisplay, "from_predictions"):
            _wrap_sklearn_method_wrapper(module, "RocCurveDisplay.from_predictions")

    if module.__name__ == 'sklearn.mixture':
        if hasattr(module.BayesianGaussianMixture, "fit_predict"):
            _wrap_sklearn_method_wrapper(module, "BayesianGaussianMixture.fit_predict")
        if hasattr(module.BayesianGaussianMixture, "predict"):
            _wrap_sklearn_method_wrapper(module, "BayesianGaussianMixture.predict")
        if hasattr(module.BayesianGaussianMixture, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "BayesianGaussianMixture.predict_proba")
        if hasattr(module.GaussianMixture, "fit_predict"):
            _wrap_sklearn_method_wrapper(module, "GaussianMixture.fit_predict")
        if hasattr(module.GaussianMixture, "predict"):
            _wrap_sklearn_method_wrapper(module, "GaussianMixture.predict")
        if hasattr(module.GaussianMixture, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "GaussianMixture.predict_proba")

    # TODO! sklearn.model_selection.cross_val_predict

    if module.__name__ == 'sklearn.model_selection':
        if hasattr(module.GridSearchCV, "predict"):
            _wrap_sklearn_method_wrapper(module, "GridSearchCV.predict")
        if hasattr(module.GridSearchCV, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "GridSearchCV.predict_log_proba")
        if hasattr(module.GridSearchCV, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "GridSearchCV.predict_proba")

        # TODO! "ImportError: HalvingGridSearchCV is experimental and the API might change without any
        # deprecation cycle. To use it, you need to explicitly import enable_halving_search_cv:"

        # if hasattr(module.HalvingGridSearchCV, "predict"):
        #     _wrap_sklearn_method_wrapper(module, "HalvingGridSearchCV.predict")
        # if hasattr(module.HalvingGridSearchCV, "predict_log_proba"):
        #     _wrap_sklearn_method_wrapper(module,
        #                                                                                  "HalvingGridSearchCV.predict_log_proba")
        # if hasattr(module.HalvingGridSearchCV, "predict_proba"):
        #     _wrap_sklearn_method_wrapper(module,
        #                                                                              "HalvingGridSearchCV.predict_proba")
        # if hasattr(module.HalvingRandomSearchCV, "predict"):
        #     _wrap_sklearn_method_wrapper(module,
        #                                                                          "HalvingRandomSearchCV.predict")
        # if hasattr(module.HalvingRandomSearchCV, "predict_log_proba"):
        #     _wrap_sklearn_method_wrapper(module,
        #                                                                                    "HalvingRandomSearchCV.predict_log_proba")
        # if hasattr(module.HalvingRandomSearchCV, "predict_proba"):
        #     _wrap_sklearn_method_wrapper(module,
        #                                                                                "HalvingRandomSearchCV.predict_proba")
        if hasattr(module.RandomizedSearchCV, "predict"):
            _wrap_sklearn_method_wrapper(module, "RandomizedSearchCV.predict")
        if hasattr(module.RandomizedSearchCV, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "RandomizedSearchCV.predict_log_proba")
        if hasattr(module.RandomizedSearchCV, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "RandomizedSearchCV.predict_proba")

    if module.__name__ == 'sklearn.multiclass':
        if hasattr(module.OneVsOneClassifier, "predict"):
            _wrap_sklearn_method_wrapper(module, "OneVsOneClassifier.predict")
        if hasattr(module.OneVsRestClassifier, "predict"):
            _wrap_sklearn_method_wrapper(module, "OneVsRestClassifier.predict")
        if hasattr(module.OneVsRestClassifier, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "OneVsRestClassifier.predict_proba")
        if hasattr(module.OutputCodeClassifier, "predict"):
            _wrap_sklearn_method_wrapper(module, "OutputCodeClassifier.predict")

    if module.__name__ == 'sklearn.multioutput':
        if hasattr(module.ClassifierChain, "predict"):
            _wrap_sklearn_method_wrapper(module, "ClassifierChain.predict")
        if hasattr(module.ClassifierChain, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "ClassifierChain.predict_proba")
        if hasattr(module.MultiOutputClassifier, "predict"):
            _wrap_sklearn_method_wrapper(module, "MultiOutputClassifier.predict")
        if hasattr(module.MultiOutputClassifier, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "MultiOutputClassifier.predict_proba")
        if hasattr(module.MultiOutputRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "MultiOutputRegressor.predict")
        if hasattr(module.RegressorChain, "predict"):
            _wrap_sklearn_method_wrapper(module, "RegressorChain.predict")

    if module.__name__ == 'sklearn.naive_bayes':
        if hasattr(module.BernoulliNB, "predict"):
            _wrap_sklearn_method_wrapper(module, "BernoulliNB.predict")
        if hasattr(module.BernoulliNB, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "BernoulliNB.predict_log_proba")
        if hasattr(module.BernoulliNB, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "BernoulliNB.predict_proba")
        if hasattr(module.CategoricalNB, "predict"):
            _wrap_sklearn_method_wrapper(module, "CategoricalNB.predict")
        if hasattr(module.CategoricalNB, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "CategoricalNB.predict_log_proba")
        if hasattr(module.CategoricalNB, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "CategoricalNB.predict_proba")
        if hasattr(module.ComplementNB, "predict"):
            _wrap_sklearn_method_wrapper(module, "ComplementNB.predict")
        if hasattr(module.ComplementNB, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "ComplementNB.predict_log_proba")
        if hasattr(module.ComplementNB, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "ComplementNB.predict_proba")
        if hasattr(module.GaussianNB, "predict"):
            _wrap_sklearn_method_wrapper(module, "GaussianNB.predict")
        if hasattr(module.GaussianNB, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "GaussianNB.predict_log_proba")
        if hasattr(module.GaussianNB, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "GaussianNB.predict_proba")
        if hasattr(module.MultinomialNB, "predict"):
            _wrap_sklearn_method_wrapper(module, "MultinomialNB.predict")
        if hasattr(module.MultinomialNB, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "MultinomialNB.predict_log_proba")
        if hasattr(module.MultinomialNB, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "MultinomialNB.predict_proba")

    if module.__name__ == 'sklearn.neighbors':
        if hasattr(module.KNeighborsClassifier, "predict"):
            _wrap_sklearn_method_wrapper(module, "KNeighborsClassifier.predict")
        if hasattr(module.KNeighborsClassifier, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "KNeighborsClassifier.predict_proba")
        if hasattr(module.KNeighborsRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "KNeighborsRegressor.predict")
        if hasattr(module.LocalOutlierFactor, "fit_predict"):
            _wrap_sklearn_method_wrapper(module, "LocalOutlierFactor.fit_predict")
        if hasattr(module.LocalOutlierFactor, "predict"):
            _wrap_sklearn_method_wrapper(module, "LocalOutlierFactor.predict")
        if hasattr(module.NearestCentroid, "predict"):
            _wrap_sklearn_method_wrapper(module, "NearestCentroid.predict")
        if hasattr(module.RadiusNeighborsClassifier, "predict"):
            _wrap_sklearn_method_wrapper(module, "RadiusNeighborsClassifier.predict")
        if hasattr(module.RadiusNeighborsClassifier, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "RadiusNeighborsClassifier.predict_proba")
        if hasattr(module.RadiusNeighborsRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "RadiusNeighborsRegressor.predict")

    if module.__name__ == 'sklearn.neural_network':
        if hasattr(module.MLPClassifier, "predict"):
            _wrap_sklearn_method_wrapper(module, "MLPClassifier.predict")
        if hasattr(module.MLPClassifier, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "MLPClassifier.predict_log_proba")
        if hasattr(module.MLPClassifier, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "MLPClassifier.predict_proba")
        if hasattr(module.MLPRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "MLPRegressor.predict")

    if module.__name__ == 'sklearn.pipeline':
        if hasattr(module.Pipeline, "fit_predict"):
            _wrap_sklearn_method_wrapper(module, "Pipeline.fit_predict")
        if hasattr(module.Pipeline, "predict"):
            _wrap_sklearn_method_wrapper(module, "Pipeline.predict")
        if hasattr(module.Pipeline, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "Pipeline.predict_log_proba")
        if hasattr(module.Pipeline, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "Pipeline.predict_proba")

    if module.__name__ == 'sklearn.semi_supervised':
        if hasattr(module.LabelPropagation, "predict"):
            _wrap_sklearn_method_wrapper(module, "LabelPropagation.predict")
        if hasattr(module.LabelPropagation, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "LabelPropagation.predict_proba")
        if hasattr(module.LabelSpreading, "predict"):
            _wrap_sklearn_method_wrapper(module, "LabelSpreading.predict")
        if hasattr(module.LabelSpreading, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "LabelSpreading.predict_proba")
        if hasattr(module.SelfTrainingClassifier, "predict"):
            _wrap_sklearn_method_wrapper(module, "SelfTrainingClassifier.predict")
        if hasattr(module.SelfTrainingClassifier, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "SelfTrainingClassifier.predict_log_proba")
        if hasattr(module.SelfTrainingClassifier, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "SelfTrainingClassifier.predict_proba")
    if module.__name__ == 'sklearn.svm':
        if hasattr(module.LinearSVC, "predict"):
            _wrap_sklearn_method_wrapper(module, "LinearSVC.predict")
        if hasattr(module.LinearSVR, "predict"):
            _wrap_sklearn_method_wrapper(module, "LinearSVR.predict")
        if hasattr(module.NuSVC, "predict"):
            _wrap_sklearn_method_wrapper(module, "NuSVC.predict")
        if hasattr(module.NuSVC, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "NuSVC.predict_log_proba")
        if hasattr(module.NuSVC, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "NuSVC.predict_proba")
        if hasattr(module.NuSVR, "predict"):
            _wrap_sklearn_method_wrapper(module, "NuSVR.predict")
        if hasattr(module.OneClassSVM, "fit_predict"):
            _wrap_sklearn_method_wrapper(module, "OneClassSVM.fit_predict")
        if hasattr(module.OneClassSVM, "predict"):
            _wrap_sklearn_method_wrapper(module, "OneClassSVM.predict")
        if hasattr(module.SVC, "predict"):
            _wrap_sklearn_method_wrapper(module, "SVC.predict")
        if hasattr(module.SVC, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "SVC.predict_log_proba")
        if hasattr(module.SVC, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "SVC.predict_proba")
        if hasattr(module.SVR, "predict"):
            _wrap_sklearn_method_wrapper(module, "SVR.predict")

    if module.__name__ == 'sklearn.tree':
        if hasattr(module.DecisionTreeClassifier, "predict"):
            _wrap_sklearn_method_wrapper(module, "DecisionTreeClassifier.predict")
        if hasattr(module.DecisionTreeClassifier, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "DecisionTreeClassifier.predict_log_proba")
        if hasattr(module.DecisionTreeClassifier, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "DecisionTreeClassifier.predict_proba")
        if hasattr(module.DecisionTreeRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "DecisionTreeRegressor.predict")
        if hasattr(module.ExtraTreeClassifier, "predict"):
            _wrap_sklearn_method_wrapper(module, "ExtraTreeClassifier.predict")
        if hasattr(module.ExtraTreeClassifier, "predict_log_proba"):
            _wrap_sklearn_method_wrapper(module, "ExtraTreeClassifier.predict_log_proba")
        if hasattr(module.ExtraTreeClassifier, "predict_proba"):
            _wrap_sklearn_method_wrapper(module, "ExtraTreeClassifier.predict_proba")
        if hasattr(module.ExtraTreeRegressor, "predict"):
            _wrap_sklearn_method_wrapper(module, "ExtraTreeRegressor.predict")
