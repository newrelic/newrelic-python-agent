from newrelic.api.function_trace import wrap_function_trace


def instrument_sklearn(module):
    if module.__name__ == 'sklearn.base':
        if hasattr(module.ClusterMixin, "fit_predict"):
            wrap_function_trace(module, "ClusterMixin.fit_predict")

    if module.__name__ == 'sklearn.calibration':
        if hasattr(module.CalibratedClassifierCV, "predict"):
            wrap_function_trace(module, "CalibratedClassifierCV.predict")
        if hasattr(module.CalibratedClassifierCV, "predict_proba"):
            wrap_function_trace(module, "CalibratedClassifierCV.predict_proba")
        if hasattr(module.CalibrationDisplay, "from_predictions"):
            wrap_function_trace(module, "CalibrationDisplay.from_predictions")

    if module.__name__ == 'sklearn.cluster':
        if hasattr(module.AffinityPropagation, "fit_predict"):
            wrap_function_trace(module, "AffinityPropagation.fit_predict")
        if hasattr(module.AffinityPropagation, "predict"):
            wrap_function_trace(module, "AffinityPropagation.predict")
        if hasattr(module.AgglomerativeClustering, "fit_predict"):
            wrap_function_trace(module, "AgglomerativeClustering.fit_predict")
        if hasattr(module.Birch, "fit_predict"):
            wrap_function_trace(module, "Birch.fit_predict")
        if hasattr(module.Birch, "predict"):
            wrap_function_trace(module, "Birch.predict")
        if hasattr(module.BisectingKMeans, "fit_predict"):
            wrap_function_trace(module, "BisectingKMeans.fit_predict")
        if hasattr(module.BisectingKMeans, "predict"):
            wrap_function_trace(module, "BisectingKMeans.predict")
        if hasattr(module.DBSCAN, "fit_predict"):
            wrap_function_trace(module, "DBSCAN.fit_predict")
        if hasattr(module.FeatureAgglomeration, "fit_predict"):
            wrap_function_trace(module, "FeatureAgglomeration.fit_predict")
        if hasattr(module.KMeans, "fit_predict"):
            wrap_function_trace(module, "KMeans.fit_predict")
        if hasattr(module.KMeans, "predict"):
            wrap_function_trace(module, "KMeans.predict")
        if hasattr(module.MeanShift, "fit_predict"):
            wrap_function_trace(module, "MeanShift.fit_predict")
        if hasattr(module.MeanShift, "predict"):
            wrap_function_trace(module, "MeanShift.predict")
        if hasattr(module.MiniBatchKMeans, "fit_predict"):
            wrap_function_trace(module, "MiniBatchKMeans.fit_predict")
        if hasattr(module.MiniBatchKMeans, "predict"):
            wrap_function_trace(module, "MiniBatchKMeans.predict")
        if hasattr(module.OPTICS, "fit_predict"):
            wrap_function_trace(module, "OPTICS.fit_predict")
        if hasattr(module.SpectralClustering, "fit_predict"):
            wrap_function_trace(module, "SpectralClustering.fit_predict")

    if module.__name__ == 'sklearn.compose':
        if hasattr(module.TransformedTargetRegressor, "predict"):
            wrap_function_trace(module, "TransformedTargetRegressor.predict")

    if module.__name__ == 'sklearn.covariance':
        if hasattr(module.EllipticEnvelope, "fit_predict"):
            wrap_function_trace(module, "EllipticEnvelope.fit_predict")
        if hasattr(module.EllipticEnvelope, "predict"):
            wrap_function_trace(module, "EllipticEnvelope.predict")

    if module.__name__ == 'sklearn.cross_decomposition':
        if hasattr(module.CCA, "predict"):
            wrap_function_trace(module, "CCA.predict")
        if hasattr(module.PLSCanonical, "predict"):
            wrap_function_trace(module, "PLSCanonical.predict")
        if hasattr(module.PLSRegression, "predict"):
            wrap_function_trace(module, "PLSRegression.predict")

    if module.__name__ == 'sklearn.discriminant_analysis':
        if hasattr(module.LinearDiscriminantAnalysis, "predict"):
            wrap_function_trace(module, "LinearDiscriminantAnalysis.predict")
        if hasattr(module.LinearDiscriminantAnalysis, "predict_log_proba"):
            wrap_function_trace(module, "LinearDiscriminantAnalysis.predict_log_proba")
        if hasattr(module.LinearDiscriminantAnalysis, "predict_proba"):
            wrap_function_trace(module, "LinearDiscriminantAnalysis.predict_proba")
        if hasattr(module.QuadraticDiscriminantAnalysis, "predict"):
            wrap_function_trace(module, "QuadraticDiscriminantAnalysis.predict")
        if hasattr(module.QuadraticDiscriminantAnalysis, "predict_log_proba"):
            wrap_function_trace(module, "QuadraticDiscriminantAnalysis.predict_log_proba")
        if hasattr(module.QuadraticDiscriminantAnalysis, "predict_proba"):
            wrap_function_trace(module, "QuadraticDiscriminantAnalysis.predict_proba")

    if module.__name__ == 'sklearn.dummy':
        if hasattr(module.DummyClassifier, "predict"):
            wrap_function_trace(module, "DummyClassifier.predict")
        if hasattr(module.DummyClassifier, "predict_log_proba"):
            wrap_function_trace(module, "DummyClassifier.predict_log_proba")
        if hasattr(module.DummyClassifier, "predict_proba"):
            wrap_function_trace(module, "DummyClassifier.predict_proba")
        if hasattr(module.DummyRegressor, "predict"):
            wrap_function_trace(module, "DummyRegressor.predict")

    if module.__name__ == 'sklearn.ensemble':
        if hasattr(module.AdaBoostClassifier, "predict"):
            wrap_function_trace(module, "AdaBoostClassifier.predict")
        if hasattr(module.AdaBoostClassifier, "predict_log_proba"):
            wrap_function_trace(module, "AdaBoostClassifier.predict_log_proba")
        if hasattr(module.AdaBoostClassifier, "predict_proba"):
            wrap_function_trace(module, "AdaBoostClassifier.predict_proba")
        if hasattr(module.AdaBoostClassifier, "staged_predict"):
            wrap_function_trace(module, "AdaBoostClassifier.staged_predict")
        if hasattr(module.AdaBoostClassifier, "staged_predict_proba"):
            wrap_function_trace(module, "AdaBoostClassifier.staged_predict_proba")
        if hasattr(module.AdaBoostRegressor, "predict"):
            wrap_function_trace(module, "AdaBoostRegressor.predict")
        if hasattr(module.AdaBoostRegressor, "staged_predict"):
            wrap_function_trace(module, "AdaBoostRegressor.staged_predict")
        if hasattr(module.BaggingClassifier, "predict"):
            wrap_function_trace(module, "BaggingClassifier.predict")
        if hasattr(module.BaggingClassifier, "predict_log_proba"):
            wrap_function_trace(module, "BaggingClassifier.predict_log_proba")
        if hasattr(module.BaggingClassifier, "predict_proba"):
            wrap_function_trace(module, "BaggingClassifier.predict_proba")
        if hasattr(module.BaggingRegressor, "predict"):
            wrap_function_trace(module, "BaggingRegressor.predict")
        if hasattr(module.ExtraTreesClassifier, "predict"):
            wrap_function_trace(module, "ExtraTreesClassifier.predict")
        if hasattr(module.ExtraTreesClassifier, "predict_log_proba"):
            wrap_function_trace(module, "ExtraTreesClassifier.predict_log_proba")
        if hasattr(module.ExtraTreesClassifier, "predict_proba"):
            wrap_function_trace(module, "ExtraTreesClassifier.predict_proba")
        if hasattr(module.ExtraTreesRegressor, "predict"):
            wrap_function_trace(module, "ExtraTreesRegressor.predict")
        if hasattr(module.GradientBoostingClassifier, "predict"):
            wrap_function_trace(module, "GradientBoostingClassifier.predict")
        if hasattr(module.GradientBoostingClassifier, "predict_log_proba"):
            wrap_function_trace(module, "GradientBoostingClassifier.predict_log_proba")
        if hasattr(module.GradientBoostingClassifier, "predict_proba"):
            wrap_function_trace(module, "GradientBoostingClassifier.predict_proba")
        if hasattr(module.GradientBoostingClassifier, "staged_predict"):
            wrap_function_trace(module, "GradientBoostingClassifier.staged_predict")
        if hasattr(module.GradientBoostingClassifier, "staged_predict_proba"):
            wrap_function_trace(module, "GradientBoostingClassifier.staged_predict_proba")
        if hasattr(module.GradientBoostingRegressor, "predict"):
            wrap_function_trace(module, "GradientBoostingRegressor.predict")
        if hasattr(module.GradientBoostingRegressor, "staged_predict"):
            wrap_function_trace(module, "GradientBoostingRegressor.staged_predict")
        if hasattr(module.HistGradientBoostingClassifier, "predict"):
            wrap_function_trace(module, "HistGradientBoostingClassifier.predict")
        if hasattr(module.HistGradientBoostingClassifier, "predict_proba"):
            wrap_function_trace(module, "HistGradientBoostingClassifier.predict_proba")
        if hasattr(module.HistGradientBoostingClassifier, "staged_predict"):
            wrap_function_trace(module, "HistGradientBoostingClassifier.staged_predict")
        if hasattr(module.HistGradientBoostingClassifier, "staged_predict_proba"):
            wrap_function_trace(module, "HistGradientBoostingClassifier.staged_predict_proba")
        if hasattr(module.HistGradientBoostingRegressor, "predict"):
            wrap_function_trace(module, "HistGradientBoostingRegressor.predict")
        if hasattr(module.HistGradientBoostingRegressor, "staged_predict"):
            wrap_function_trace(module, "HistGradientBoostingRegressor.staged_predict")
        if hasattr(module.IsolationForest, "fit_predict"):
            wrap_function_trace(module, "IsolationForest.fit_predict")
        if hasattr(module.IsolationForest, "predict"):
            wrap_function_trace(module, "IsolationForest.predict")
        if hasattr(module.RandomForestClassifier, "predict"):
            wrap_function_trace(module, "RandomForestClassifier.predict")
        if hasattr(module.RandomForestClassifier, "predict_log_proba"):
            wrap_function_trace(module, "RandomForestClassifier.predict_log_proba")
        if hasattr(module.RandomForestClassifier, "predict_proba"):
            wrap_function_trace(module, "RandomForestClassifier.predict_proba")
        if hasattr(module.RandomForestRegressor, "predict"):
            wrap_function_trace(module, "RandomForestRegressor.predict")
        if hasattr(module.StackingClassifier, "predict"):
            wrap_function_trace(module, "StackingClassifier.predict")
        if hasattr(module.StackingClassifier, "predict_proba"):
            wrap_function_trace(module, "StackingClassifier.predict_proba")
        if hasattr(module.StackingRegressor, "predict"):
            wrap_function_trace(module, "StackingRegressor.predict")
        if hasattr(module.VotingClassifier, "predict"):
            wrap_function_trace(module, "VotingClassifier.predict")
        if hasattr(module.VotingClassifier, "predict_proba"):
            wrap_function_trace(module, "VotingClassifier.predict_proba")
        if hasattr(module.VotingRegressor, "predict"):
            wrap_function_trace(module, "VotingRegressor.predict")

    if module.__name__ == 'sklearn.feature_selection':
        if hasattr(module.RFE, "predict"):
            wrap_function_trace(module, "RFE.predict")
        if hasattr(module.RFE, "predict_log_proba"):
            wrap_function_trace(module, "RFE.predict_log_proba")
        if hasattr(module.RFE, "predict_proba"):
            wrap_function_trace(module, "RFE.predict_proba")
        if hasattr(module.RFECV, "predict"):
            wrap_function_trace(module, "RFECV.predict")
        if hasattr(module.RFECV, "predict_log_proba"):
            wrap_function_trace(module, "RFECV.predict_log_proba")
        if hasattr(module.RFECV, "predict_proba"):
            wrap_function_trace(module, "RFECV.predict_proba")

    if module.__name__ == 'sklearn.gaussian_process':
        if hasattr(module.GaussianProcessClassifier, "predict"):
            wrap_function_trace(module, "GaussianProcessClassifier.predict")
        if hasattr(module.GaussianProcessClassifier, "predict_proba"):
            wrap_function_trace(module, "GaussianProcessClassifier.predict_proba")
        if hasattr(module.GaussianProcessRegressor, "predict"):
            wrap_function_trace(module, "GaussianProcessRegressor.predict")
    if module.__name__ == 'sklearn.isotonic':
        if hasattr(module.IsotonicRegression, "predict"):
            wrap_function_trace(module, "IsotonicRegression.predict")

    if module.__name__ == 'sklearn.kernel_ridge':
        if hasattr(module.KernelRidge, "predict"):
            wrap_function_trace(module, "KernelRidge.predict")

    if module.__name__ == 'sklearn.linear_model':
        if hasattr(module.ARDRegression, "predict"):
            wrap_function_trace(module, "ARDRegression.predict")
        if hasattr(module.BayesianRidge, "predict"):
            wrap_function_trace(module, "BayesianRidge.predict")
        if hasattr(module.ElasticNet, "predict"):
            wrap_function_trace(module, "ElasticNet.predict")
        if hasattr(module.ElasticNetCV, "predict"):
            wrap_function_trace(module, "ElasticNetCV.predict")
        if hasattr(module.GammaRegressor, "predict"):
            wrap_function_trace(module, "GammaRegressor.predict")
        if hasattr(module.HuberRegressor, "predict"):
            wrap_function_trace(module, "HuberRegressor.predict")
        if hasattr(module.Lars, "predict"):
            wrap_function_trace(module, "Lars.predict")
        if hasattr(module.LarsCV, "predict"):
            wrap_function_trace(module, "LarsCV.predict")
        if hasattr(module.Lasso, "predict"):
            wrap_function_trace(module, "Lasso.predict")
        if hasattr(module.LassoCV, "predict"):
            wrap_function_trace(module, "LassoCV.predict")
        if hasattr(module.LassoLars, "predict"):
            wrap_function_trace(module, "LassoLars.predict")
        if hasattr(module.LassoLarsCV, "predict"):
            wrap_function_trace(module, "LassoLarsCV.predict")
        if hasattr(module.LassoLarsIC, "predict"):
            wrap_function_trace(module, "LassoLarsIC.predict")
        if hasattr(module.LinearRegression, "predict"):
            wrap_function_trace(module, "LinearRegression.predict")
        if hasattr(module.LogisticRegression, "predict"):
            wrap_function_trace(module, "LogisticRegression.predict")
        if hasattr(module.LogisticRegression, "predict_log_proba"):
            wrap_function_trace(module, "LogisticRegression.predict_log_proba")
        if hasattr(module.LogisticRegression, "predict_proba"):
            wrap_function_trace(module, "LogisticRegression.predict_proba")
        if hasattr(module.LogisticRegressionCV, "predict"):
            wrap_function_trace(module, "LogisticRegressionCV.predict")
        if hasattr(module.LogisticRegressionCV, "predict_log_proba"):
            wrap_function_trace(module, "LogisticRegressionCV.predict_log_proba")
        if hasattr(module.LogisticRegressionCV, "predict_proba"):
            wrap_function_trace(module, "LogisticRegressionCV.predict_proba")
        if hasattr(module.MultiTaskElasticNet, "predict"):
            wrap_function_trace(module, "MultiTaskElasticNet.predict")
        if hasattr(module.MultiTaskElasticNetCV, "predict"):
            wrap_function_trace(module, "MultiTaskElasticNetCV.predict")
        if hasattr(module.MultiTaskLasso, "predict"):
            wrap_function_trace(module, "MultiTaskLasso.predict")
        if hasattr(module.MultiTaskLassoCV, "predict"):
            wrap_function_trace(module, "MultiTaskLassoCV.predict")
        if hasattr(module.OrthogonalMatchingPursuit, "predict"):
            wrap_function_trace(module, "OrthogonalMatchingPursuit.predict")
        if hasattr(module.OrthogonalMatchingPursuitCV, "predict"):
            wrap_function_trace(module, "OrthogonalMatchingPursuitCV.predict")
        if hasattr(module.PassiveAggressiveClassifier, "predict"):
            wrap_function_trace(module, "PassiveAggressiveClassifier.predict")
        if hasattr(module.Perceptron, "predict"):
            wrap_function_trace(module, "Perceptron.predict")
        if hasattr(module.PoissonRegressor, "predict"):
            wrap_function_trace(module, "PoissonRegressor.predict")
        if hasattr(module.QuantileRegressor, "predict"):
            wrap_function_trace(module, "QuantileRegressor.predict")
        if hasattr(module.RANSACRegressor, "predict"):
            wrap_function_trace(module, "RANSACRegressor.predict")
        if hasattr(module.Ridge, "predict"):
            wrap_function_trace(module, "Ridge.predict")
        if hasattr(module.RidgeClassifier, "predict"):
            wrap_function_trace(module, "RidgeClassifier.predict")
        if hasattr(module.RidgeClassifierCV, "predict"):
            wrap_function_trace(module, "RidgeClassifierCV.predict")
        if hasattr(module.RidgeCV, "predict"):
            wrap_function_trace(module, "RidgeCV.predict")
        if hasattr(module.SGDClassifier, "predict"):
            wrap_function_trace(module, "SGDClassifier.predict")
        if hasattr(module.SGDClassifier, "predict_log_proba"):
            wrap_function_trace(module, "SGDClassifier.predict_log_proba")
        if hasattr(module.SGDClassifier, "predict_proba"):
            wrap_function_trace(module, "SGDClassifier.predict_proba")
        if hasattr(module.SGDOneClassSVM, "fit_predict"):
            wrap_function_trace(module, "SGDOneClassSVM.fit_predict")
        if hasattr(module.SGDOneClassSVM, "predict"):
            wrap_function_trace(module, "SGDOneClassSVM.predict")
        if hasattr(module.SGDRegressor, "predict"):
            wrap_function_trace(module, "SGDRegressor.predict")
        if hasattr(module.TheilSenRegressor, "predict"):
            wrap_function_trace(module, "TheilSenRegressor.predict")
        if hasattr(module.TweedieRegressor, "predict"):
            wrap_function_trace(module, "TweedieRegressor.predict")

    if module.__name__ == 'sklearn.metrics':
        if hasattr(module.ConfusionMatrixDisplay, "from_predictions"):
            wrap_function_trace(module, "ConfusionMatrixDisplay.from_predictions")
        if hasattr(module.DetCurveDisplay, "from_predictions"):
            wrap_function_trace(module, "DetCurveDisplay.from_predictions")
        if hasattr(module.PrecisionRecallDisplay, "from_predictions"):
            wrap_function_trace(module, "PrecisionRecallDisplay.from_predictions")
        if hasattr(module.RocCurveDisplay, "from_predictions"):
            wrap_function_trace(module, "RocCurveDisplay.from_predictions")

    if module.__name__ == 'sklearn.mixture':
        if hasattr(module.BayesianGaussianMixture, "fit_predict"):
            wrap_function_trace(module, "BayesianGaussianMixture.fit_predict")
        if hasattr(module.BayesianGaussianMixture, "predict"):
            wrap_function_trace(module, "BayesianGaussianMixture.predict")
        if hasattr(module.BayesianGaussianMixture, "predict_proba"):
            wrap_function_trace(module, "BayesianGaussianMixture.predict_proba")
        if hasattr(module.GaussianMixture, "fit_predict"):
            wrap_function_trace(module, "GaussianMixture.fit_predict")
        if hasattr(module.GaussianMixture, "predict"):
            wrap_function_trace(module, "GaussianMixture.predict")
        if hasattr(module.GaussianMixture, "predict_proba"):
            wrap_function_trace(module, "GaussianMixture.predict_proba")

    # TODO! sklearn.model_selection.cross_val_predict

    if module.__name__ == 'sklearn.model_selection':
        if hasattr(module.GridSearchCV, "predict"):
            wrap_function_trace(module, "GridSearchCV.predict")
        if hasattr(module.GridSearchCV, "predict_log_proba"):
            wrap_function_trace(module, "GridSearchCV.predict_log_proba")
        if hasattr(module.GridSearchCV, "predict_proba"):
            wrap_function_trace(module, "GridSearchCV.predict_proba")

        # TODO! "ImportError: HalvingGridSearchCV is experimental and the API might change without any
        # deprecation cycle. To use it, you need to explicitly import enable_halving_search_cv:"

        # if hasattr(module.HalvingGridSearchCV, "predict"):
        #     wrap_function_trace(module, "HalvingGridSearchCV.predict")
        # if hasattr(module.HalvingGridSearchCV, "predict_log_proba"):
        #     wrap_function_trace(module,
        #                                                                                  "HalvingGridSearchCV.predict_log_proba")
        # if hasattr(module.HalvingGridSearchCV, "predict_proba"):
        #     wrap_function_trace(module,
        #                                                                              "HalvingGridSearchCV.predict_proba")
        # if hasattr(module.HalvingRandomSearchCV, "predict"):
        #     wrap_function_trace(module,
        #                                                                          "HalvingRandomSearchCV.predict")
        # if hasattr(module.HalvingRandomSearchCV, "predict_log_proba"):
        #     wrap_function_trace(module,
        #                                                                                    "HalvingRandomSearchCV.predict_log_proba")
        # if hasattr(module.HalvingRandomSearchCV, "predict_proba"):
        #     wrap_function_trace(module,
        #                                                                                "HalvingRandomSearchCV.predict_proba")
        if hasattr(module.RandomizedSearchCV, "predict"):
            wrap_function_trace(module, "RandomizedSearchCV.predict")
        if hasattr(module.RandomizedSearchCV, "predict_log_proba"):
            wrap_function_trace(module, "RandomizedSearchCV.predict_log_proba")
        if hasattr(module.RandomizedSearchCV, "predict_proba"):
            wrap_function_trace(module, "RandomizedSearchCV.predict_proba")

    if module.__name__ == 'sklearn.multiclass':
        if hasattr(module.OneVsOneClassifier, "predict"):
            wrap_function_trace(module, "OneVsOneClassifier.predict")
        if hasattr(module.OneVsRestClassifier, "predict"):
            wrap_function_trace(module, "OneVsRestClassifier.predict")
        if hasattr(module.OneVsRestClassifier, "predict_proba"):
            wrap_function_trace(module, "OneVsRestClassifier.predict_proba")
        if hasattr(module.OutputCodeClassifier, "predict"):
            wrap_function_trace(module, "OutputCodeClassifier.predict")

    if module.__name__ == 'sklearn.multioutput':
        if hasattr(module.ClassifierChain, "predict"):
            wrap_function_trace(module, "ClassifierChain.predict")
        if hasattr(module.ClassifierChain, "predict_proba"):
            wrap_function_trace(module, "ClassifierChain.predict_proba")
        if hasattr(module.MultiOutputClassifier, "predict"):
            wrap_function_trace(module, "MultiOutputClassifier.predict")
        if hasattr(module.MultiOutputClassifier, "predict_proba"):
            wrap_function_trace(module, "MultiOutputClassifier.predict_proba")
        if hasattr(module.MultiOutputRegressor, "predict"):
            wrap_function_trace(module, "MultiOutputRegressor.predict")
        if hasattr(module.RegressorChain, "predict"):
            wrap_function_trace(module, "RegressorChain.predict")

    if module.__name__ == 'sklearn.naive_bayes':
        if hasattr(module.BernoulliNB, "predict"):
            wrap_function_trace(module, "BernoulliNB.predict")
        if hasattr(module.BernoulliNB, "predict_log_proba"):
            wrap_function_trace(module, "BernoulliNB.predict_log_proba")
        if hasattr(module.BernoulliNB, "predict_proba"):
            wrap_function_trace(module, "BernoulliNB.predict_proba")
        if hasattr(module.CategoricalNB, "predict"):
            wrap_function_trace(module, "CategoricalNB.predict")
        if hasattr(module.CategoricalNB, "predict_log_proba"):
            wrap_function_trace(module, "CategoricalNB.predict_log_proba")
        if hasattr(module.CategoricalNB, "predict_proba"):
            wrap_function_trace(module, "CategoricalNB.predict_proba")
        if hasattr(module.ComplementNB, "predict"):
            wrap_function_trace(module, "ComplementNB.predict")
        if hasattr(module.ComplementNB, "predict_log_proba"):
            wrap_function_trace(module, "ComplementNB.predict_log_proba")
        if hasattr(module.ComplementNB, "predict_proba"):
            wrap_function_trace(module, "ComplementNB.predict_proba")
        if hasattr(module.GaussianNB, "predict"):
            wrap_function_trace(module, "GaussianNB.predict")
        if hasattr(module.GaussianNB, "predict_log_proba"):
            wrap_function_trace(module, "GaussianNB.predict_log_proba")
        if hasattr(module.GaussianNB, "predict_proba"):
            wrap_function_trace(module, "GaussianNB.predict_proba")
        if hasattr(module.MultinomialNB, "predict"):
            wrap_function_trace(module, "MultinomialNB.predict")
        if hasattr(module.MultinomialNB, "predict_log_proba"):
            wrap_function_trace(module, "MultinomialNB.predict_log_proba")
        if hasattr(module.MultinomialNB, "predict_proba"):
            wrap_function_trace(module, "MultinomialNB.predict_proba")

    if module.__name__ == 'sklearn.neighbors':
        if hasattr(module.KNeighborsClassifier, "predict"):
            wrap_function_trace(module, "KNeighborsClassifier.predict")
        if hasattr(module.KNeighborsClassifier, "predict_proba"):
            wrap_function_trace(module, "KNeighborsClassifier.predict_proba")
        if hasattr(module.KNeighborsRegressor, "predict"):
            wrap_function_trace(module, "KNeighborsRegressor.predict")
        if hasattr(module.LocalOutlierFactor, "fit_predict"):
            wrap_function_trace(module, "LocalOutlierFactor.fit_predict")
        if hasattr(module.LocalOutlierFactor, "predict"):
            wrap_function_trace(module, "LocalOutlierFactor.predict")
        if hasattr(module.NearestCentroid, "predict"):
            wrap_function_trace(module, "NearestCentroid.predict")
        if hasattr(module.RadiusNeighborsClassifier, "predict"):
            wrap_function_trace(module, "RadiusNeighborsClassifier.predict")
        if hasattr(module.RadiusNeighborsClassifier, "predict_proba"):
            wrap_function_trace(module, "RadiusNeighborsClassifier.predict_proba")
        if hasattr(module.RadiusNeighborsRegressor, "predict"):
            wrap_function_trace(module, "RadiusNeighborsRegressor.predict")

    if module.__name__ == 'sklearn.neural_network':
        if hasattr(module.MLPClassifier, "predict"):
            wrap_function_trace(module, "MLPClassifier.predict")
        if hasattr(module.MLPClassifier, "predict_log_proba"):
            wrap_function_trace(module, "MLPClassifier.predict_log_proba")
        if hasattr(module.MLPClassifier, "predict_proba"):
            wrap_function_trace(module, "MLPClassifier.predict_proba")
        if hasattr(module.MLPRegressor, "predict"):
            wrap_function_trace(module, "MLPRegressor.predict")

    if module.__name__ == 'sklearn.pipeline':
        if hasattr(module.Pipeline, "fit_predict"):
            wrap_function_trace(module, "Pipeline.fit_predict")
        if hasattr(module.Pipeline, "predict"):
            wrap_function_trace(module, "Pipeline.predict")
        if hasattr(module.Pipeline, "predict_log_proba"):
            wrap_function_trace(module, "Pipeline.predict_log_proba")
        if hasattr(module.Pipeline, "predict_proba"):
            wrap_function_trace(module, "Pipeline.predict_proba")

    if module.__name__ == 'sklearn.semi_supervised':
        if hasattr(module.LabelPropagation, "predict"):
            wrap_function_trace(module, "LabelPropagation.predict")
        if hasattr(module.LabelPropagation, "predict_proba"):
            wrap_function_trace(module, "LabelPropagation.predict_proba")
        if hasattr(module.LabelSpreading, "predict"):
            wrap_function_trace(module, "LabelSpreading.predict")
        if hasattr(module.LabelSpreading, "predict_proba"):
            wrap_function_trace(module, "LabelSpreading.predict_proba")
        if hasattr(module.SelfTrainingClassifier, "predict"):
            wrap_function_trace(module, "SelfTrainingClassifier.predict")
        if hasattr(module.SelfTrainingClassifier, "predict_log_proba"):
            wrap_function_trace(module, "SelfTrainingClassifier.predict_log_proba")
        if hasattr(module.SelfTrainingClassifier, "predict_proba"):
            wrap_function_trace(module, "SelfTrainingClassifier.predict_proba")
    if module.__name__ == 'sklearn.svm':
        if hasattr(module.LinearSVC, "predict"):
            wrap_function_trace(module, "LinearSVC.predict")
        if hasattr(module.LinearSVR, "predict"):
            wrap_function_trace(module, "LinearSVR.predict")
        if hasattr(module.NuSVC, "predict"):
            wrap_function_trace(module, "NuSVC.predict")
        if hasattr(module.NuSVC, "predict_log_proba"):
            wrap_function_trace(module, "NuSVC.predict_log_proba")
        if hasattr(module.NuSVC, "predict_proba"):
            wrap_function_trace(module, "NuSVC.predict_proba")
        if hasattr(module.NuSVR, "predict"):
            wrap_function_trace(module, "NuSVR.predict")
        if hasattr(module.OneClassSVM, "fit_predict"):
            wrap_function_trace(module, "OneClassSVM.fit_predict")
        if hasattr(module.OneClassSVM, "predict"):
            wrap_function_trace(module, "OneClassSVM.predict")
        if hasattr(module.SVC, "predict"):
            wrap_function_trace(module, "SVC.predict")
        if hasattr(module.SVC, "predict_log_proba"):
            wrap_function_trace(module, "SVC.predict_log_proba")
        if hasattr(module.SVC, "predict_proba"):
            wrap_function_trace(module, "SVC.predict_proba")
        if hasattr(module.SVR, "predict"):
            wrap_function_trace(module, "SVR.predict")

    if module.__name__ == 'sklearn.tree':
        if hasattr(module.DecisionTreeClassifier, "predict"):
            wrap_function_trace(module, "DecisionTreeClassifier.predict")
        if hasattr(module.DecisionTreeClassifier, "predict_log_proba"):
            wrap_function_trace(module, "DecisionTreeClassifier.predict_log_proba")
        if hasattr(module.DecisionTreeClassifier, "predict_proba"):
            wrap_function_trace(module, "DecisionTreeClassifier.predict_proba")
        if hasattr(module.DecisionTreeRegressor, "predict"):
            wrap_function_trace(module, "DecisionTreeRegressor.predict")
        if hasattr(module.ExtraTreeClassifier, "predict"):
            wrap_function_trace(module, "ExtraTreeClassifier.predict")
        if hasattr(module.ExtraTreeClassifier, "predict_log_proba"):
            wrap_function_trace(module, "ExtraTreeClassifier.predict_log_proba")
        if hasattr(module.ExtraTreeClassifier, "predict_proba"):
            wrap_function_trace(module, "ExtraTreeClassifier.predict_proba")
        if hasattr(module.ExtraTreeRegressor, "predict"):
            wrap_function_trace(module, "ExtraTreeRegressor.predict")
