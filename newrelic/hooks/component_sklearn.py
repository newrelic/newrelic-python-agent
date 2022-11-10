# Copyright 2010 New Relic, Inc.",
# ",
# Licensed under the Apache License, Version 2.0 (the "License");",
# you may not use this file except in compliance with the License.",
# You may obtain a copy of the License at",
# ",
#      http://www.apache.org/licenses/LICENSE-2.0",
# ",
# Unless required by applicable law or agreed to in writing, software",
# distributed under the License is distributed on an "AS IS" BASIS,",
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.",
# See the License for the specific language governing permissions and",
# limitations under the License.",
import sys

from newrelic.api.function_trace import FunctionTraceWrapper
from newrelic.common.object_wrapper import wrap_function_wrapper

MODEL_PATHS = [
    "sklearn.calibration.CalibratedClassifierCV",
    "sklearn.calibration.CalibrationDisplay",
    "sklearn.cluster._affinity_propagation.AffinityPropagation",
    "sklearn.cluster._agglomerative.AgglomerativeClustering",
    "sklearn.cluster._agglomerative.FeatureAgglomeration",
    "sklearn.cluster._bicluster.BaseSpectral",
    "sklearn.cluster._bicluster.SpectralCoclustering",
    "sklearn.cluster._bicluster.SpectralBiclustering",
    "sklearn.cluster._birch.Birch",
    "sklearn.cluster._bisect_k_means.BisectingKMeans",
    "sklearn.cluster._dbscan.DBSCAN",
    "sklearn.cluster._feature_agglomeration.AgglomerationTransform",
    "sklearn.cluster._kmeans.KMeans",
    "sklearn.cluster._kmeans.MiniBatchKMeans",
    "sklearn.cluster._mean_shift.MeanShift",
    "sklearn.cluster._optics.OPTICS",
    "sklearn.cluster._spectral.SpectralClustering",
    "sklearn.compose._column_transformer.ColumnTransformer",
    "sklearn.covariance._elliptic_envelope.EllipticEnvelope",
    "sklearn.covariance._empirical_covariance.EmpiricalCovariance",
    "sklearn.covariance._graph_lasso.BaseGraphicalLasso",
    "sklearn.covariance._graph_lasso.GraphicalLasso",
    "sklearn.covariance._graph_lasso.GraphicalLassoCV",
    "sklearn.covariance._robust_covariance.MinCovDet",
    "sklearn.covariance._shrunk_covariance.ShrunkCovariance",
    "sklearn.covariance._shrunk_covariance.LedoitWolf",
    "sklearn.covariance._shrunk_covariance.OAS",
    "sklearn.cross_decomposition._pls.PLSRegression",
    "sklearn.cross_decomposition._pls.PLSCanonical",
    "sklearn.cross_decomposition._pls.CCA",
    "sklearn.cross_decomposition._pls.PLSSVD",
    "sklearn.datasets._openml.OpenMLError",
    "sklearn.decomposition._dict_learning.SparseCoder",
    "sklearn.decomposition._dict_learning.DictionaryLearning",
    "sklearn.decomposition._dict_learning.MiniBatchDictionaryLearning",
    "sklearn.decomposition._factor_analysis.FactorAnalysis",
    "sklearn.decomposition._fastica.FastICA",
    "sklearn.decomposition._incremental_pca.IncrementalPCA",
    "sklearn.decomposition._kernel_pca.KernelPCA",
    "sklearn.decomposition._lda.LatentDirichletAllocation",
    "sklearn.decomposition._nmf.NMF",
    "sklearn.decomposition._nmf.MiniBatchNMF",
    "sklearn.decomposition._pca.PCA",
    "sklearn.decomposition._sparse_pca.SparsePCA",
    "sklearn.decomposition._sparse_pca.MiniBatchSparsePCA",
    "sklearn.decomposition._truncated_svd.TruncatedSVD",
    "sklearn.discriminant_analysis.LinearDiscriminantAnalysis",
    "sklearn.discriminant_analysis.QuadraticDiscriminantAnalysis",
    "sklearn.dummy.DummyClassifier",
    "sklearn.dummy.DummyRegressor",
    "sklearn.ensemble._bagging.BaseBagging",
    "sklearn.ensemble._bagging.BaggingClassifier",
    "sklearn.ensemble._bagging.BaggingRegressor",
    "sklearn.ensemble._base.BaseEnsemble",
    "sklearn.ensemble._forest.BaseForest",
    "sklearn.ensemble._forest.ForestClassifier",
    "sklearn.ensemble._forest.ForestRegressor",
    "sklearn.ensemble._forest.RandomForestClassifier",
    "sklearn.ensemble._forest.RandomForestRegressor",
    "sklearn.ensemble._forest.ExtraTreesClassifier",
    "sklearn.ensemble._forest.ExtraTreesRegressor",
    "sklearn.ensemble._forest.RandomTreesEmbedding",
    "sklearn.ensemble._gb.VerboseReporter:",
    "sklearn.ensemble._gb.BaseGradientBoosting",
    "sklearn.ensemble._gb.GradientBoostingClassifier",
    "sklearn.ensemble._gb.GradientBoostingRegressor",
    "sklearn.ensemble._gb_losses.LossFunction",
    "sklearn.ensemble._gb_losses.RegressionLossFunction",
    "sklearn.ensemble._gb_losses.LeastSquaresError",
    "sklearn.ensemble._gb_losses.LeastAbsoluteError",
    "sklearn.ensemble._gb_losses.HuberLossFunction",
    "sklearn.ensemble._gb_losses.QuantileLossFunction",
    "sklearn.ensemble._gb_losses.ClassificationLossFunction",
    "sklearn.ensemble._gb_losses.BinomialDeviance",
    "sklearn.ensemble._gb_losses.MultinomialDeviance",
    "sklearn.ensemble._gb_losses.ExponentialLoss",
    "sklearn.ensemble._iforest.IsolationForest",
    "sklearn.ensemble._stacking.StackingClassifier",
    "sklearn.ensemble._stacking.StackingRegressor",
    "sklearn.ensemble._voting.VotingClassifier",
    "sklearn.ensemble._voting.VotingRegressor",
    "sklearn.ensemble._weight_boosting.BaseWeightBoosting",
    "sklearn.ensemble._weight_boosting.AdaBoostClassifier",
    "sklearn.ensemble._weight_boosting.AdaBoostRegressor",
    "sklearn.gaussian_process._gpc.GaussianProcessClassifier",
    "sklearn.gaussian_process._gpr.GaussianProcessRegressor",
    "sklearn.gaussian_process.kernels.Hyperparameter",
    "sklearn.gaussian_process.kernels.Kernel",
    "sklearn.gaussian_process.kernels.CompoundKernel",
    "sklearn.gaussian_process.kernels.KernelOperator",
    "sklearn.gaussian_process.kernels.Sum",
    "sklearn.gaussian_process.kernels.Product",
    "sklearn.gaussian_process.kernels.Exponentiation",
    "sklearn.gaussian_process.kernels.ConstantKernel",
    "sklearn.gaussian_process.kernels.WhiteKernel",
    "sklearn.gaussian_process.kernels.RBF",
    "sklearn.gaussian_process.kernels.Matern",
    "sklearn.gaussian_process.kernels.RationalQuadratic",
    "sklearn.gaussian_process.kernels.ExpSineSquared",
    "sklearn.gaussian_process.kernels.DotProduct",
    "sklearn.gaussian_process.kernels.PairwiseKernel",
    "sklearn.impute._base.SimpleImputer",
    "sklearn.impute._base.MissingIndicator",
    "sklearn.impute._iterative.IterativeImputer",
    "sklearn.impute._knn.KNNImputer",
    "sklearn.isotonic.IsotonicRegression",
    "sklearn.kernel_approximation.PolynomialCountSketch",
    "sklearn.kernel_approximation.RBFSampler",
    "sklearn.kernel_approximation.SkewedChi2Sampler",
    "sklearn.kernel_approximation.AdditiveChi2Sampler",
    "sklearn.kernel_approximation.Nystroem",
    "sklearn.kernel_ridge.KernelRidge",
    "sklearn.linear_model._base.LinearModel",
    "sklearn.linear_model._base.LinearClassifierMixin",
    "sklearn.linear_model._base.SparseCoefMixin:",
    "sklearn.linear_model._base.LinearRegression",
    "sklearn.linear_model._bayes.BayesianRidge",
    "sklearn.linear_model._bayes.ARDRegression",
    "sklearn.linear_model._coordinate_descent.ElasticNet",
    "sklearn.linear_model._coordinate_descent.Lasso",
    "sklearn.linear_model._coordinate_descent.LinearModelCV",
    "sklearn.linear_model._coordinate_descent.LassoCV",
    "sklearn.linear_model._coordinate_descent.ElasticNetCV",
    "sklearn.linear_model._coordinate_descent.MultiTaskElasticNet",
    "sklearn.linear_model._coordinate_descent.MultiTaskLasso",
    "sklearn.linear_model._coordinate_descent.MultiTaskElasticNetCV",
    "sklearn.linear_model._coordinate_descent.MultiTaskLassoCV",
    "sklearn.linear_model._glm.glm.PoissonRegressor",
    "sklearn.linear_model._glm.glm.GammaRegressor",
    "sklearn.linear_model._glm.glm.TweedieRegressor",
    "sklearn.linear_model._huber.HuberRegressor",
    "sklearn.linear_model._least_angle.Lars",
    "sklearn.linear_model._least_angle.LassoLars",
    "sklearn.linear_model._least_angle.LarsCV",
    "sklearn.linear_model._least_angle.LassoLarsCV",
    "sklearn.linear_model._least_angle.LassoLarsIC",
    "sklearn.linear_model._linear_loss.LinearModelLoss",
    "sklearn.linear_model._logistic.LogisticRegression",
    "sklearn.linear_model._logistic.LogisticRegressionCV",
    "sklearn.linear_model._omp.OrthogonalMatchingPursuit",
    "sklearn.linear_model._omp.OrthogonalMatchingPursuitCV",
    "sklearn.linear_model._passive_aggressive.PassiveAggressiveClassifier",
    "sklearn.linear_model._passive_aggressive.PassiveAggressiveRegressor",
    "sklearn.linear_model._perceptron.Perceptron",
    "sklearn.linear_model._quantile.QuantileRegressor",
    "sklearn.linear_model._ransac.RANSACRegressor",
    "sklearn.linear_model._ridge.Ridge",
    "sklearn.linear_model._ridge.RidgeClassifier",
    "sklearn.linear_model._ridge.RidgeCV",
    "sklearn.linear_model._ridge.RidgeClassifierCV",
    "sklearn.linear_model._stochastic_gradient.BaseSGD",
    "sklearn.linear_model._stochastic_gradient.BaseSGDClassifier",
    "sklearn.linear_model._stochastic_gradient.SGDClassifier",
    "sklearn.manifold._isomap.Isomap",
    "sklearn.manifold._locally_linear.LocallyLinearEmbedding",
    "sklearn.manifold._mds.MDS",
    "sklearn.manifold._spectral_embedding.SpectralEmbedding",
    "sklearn.manifold._t_sne.TSNE",
    "sklearn.mixture._base.BaseMixture",
    "sklearn.mixture._bayesian_mixture.BayesianGaussianMixture",
    "sklearn.mixture._gaussian_mixture.GaussianMixture",
    "sklearn.mixture.tests.test_gaussian_mixture.RandomData:",
    "sklearn.model_selection._search.ParameterGrid:",
    "sklearn.model_selection._search.ParameterSampler:",
    "sklearn.model_selection._search.BaseSearchCV",
    "sklearn.model_selection._search.GridSearchCV",
    "sklearn.model_selection._search.RandomizedSearchCV",
    "sklearn.model_selection._search_successive_halving.BaseSuccessiveHalving",
    "sklearn.model_selection._search_successive_halving.HalvingGridSearchCV",
    "sklearn.model_selection._search_successive_halving.HalvingRandomSearchCV",
    "sklearn.model_selection._split.BaseCrossValidator",
    "sklearn.model_selection._split.LeaveOneOut",
    "sklearn.model_selection._split.LeavePOut",
    "sklearn.model_selection._split.KFold",
    "sklearn.model_selection._split.GroupKFold",
    "sklearn.model_selection._split.StratifiedKFold",
    "sklearn.model_selection._split.StratifiedGroupKFold",
    "sklearn.model_selection._split.TimeSeriesSplit",
    "sklearn.model_selection._split.LeaveOneGroupOut",
    "sklearn.model_selection._split.LeavePGroupsOut",
    "sklearn.model_selection._split.RepeatedKFold",
    "sklearn.model_selection._split.RepeatedStratifiedKFold",
    "sklearn.model_selection._split.BaseShuffleSplit",
    "sklearn.model_selection._split.ShuffleSplit",
    "sklearn.model_selection._split.GroupShuffleSplit",
    "sklearn.model_selection._split.StratifiedShuffleSplit",
    "sklearn.model_selection._split.PredefinedSplit",
    "sklearn.multiclass.OneVsRestClassifier",
    "sklearn.multiclass.OneVsOneClassifier",
    "sklearn.multiclass.OutputCodeClassifier",
    "sklearn.multioutput.MultiOutputRegressor",
    "sklearn.multioutput.MultiOutputClassifier",
    "sklearn.multioutput.ClassifierChain",
    "sklearn.multioutput.RegressorChain",
    "sklearn.naive_bayes.GaussianNB",
    "sklearn.naive_bayes.MultinomialNB",
    "sklearn.naive_bayes.ComplementNB",
    "sklearn.naive_bayes.BernoulliNB",
    "sklearn.naive_bayes.CategoricalNB",
    "sklearn.neighbors._base.NeighborsBase",
    "sklearn.neighbors._classification.KNeighborsClassifier",
    "sklearn.neighbors._classification.RadiusNeighborsClassifier",
    "sklearn.neighbors._distance_metric.DistanceMetric",
    "sklearn.neighbors._graph.KNeighborsTransformer",
    "sklearn.neighbors._graph.RadiusNeighborsTransformer",
    "sklearn.neighbors._kde.KernelDensity",
    "sklearn.neighbors._lof.LocalOutlierFactor",
    "sklearn.neighbors._nca.NeighborhoodComponentsAnalysis",
    "sklearn.neighbors._nearest_centroid.NearestCentroid",
    "sklearn.neighbors._regression.KNeighborsRegressor",
    "sklearn.neighbors._regression.RadiusNeighborsRegressor",
    "sklearn.neighbors._unsupervised.NearestNeighbors",
    "sklearn.neural_network._multilayer_perceptron.BaseMultilayerPerceptron",
    "sklearn.neural_network._multilayer_perceptron.MLPClassifier",
    "sklearn.neural_network._multilayer_perceptron.MLPRegressor",
    "sklearn.neural_network._rbm.BernoulliRBM",
    "sklearn.preprocessing._data.MinMaxScaler",
    "sklearn.preprocessing._data.StandardScaler",
    "sklearn.preprocessing._data.MaxAbsScaler",
    "sklearn.preprocessing._data.RobustScaler",
    "sklearn.preprocessing._data.Normalizer",
    "sklearn.preprocessing._data.Binarizer",
    "sklearn.preprocessing._data.KernelCenterer",
    "sklearn.preprocessing._data.QuantileTransformer",
    "sklearn.preprocessing._data.PowerTransformer",
    "sklearn.preprocessing._discretization.KBinsDiscretizer",
    "sklearn.preprocessing._encoders.OneHotEncoder",
    "sklearn.preprocessing._encoders.OrdinalEncoder",
    "sklearn.preprocessing._function_transformer.FunctionTransformer",
    "sklearn.preprocessing._label.LabelEncoder",
    "sklearn.preprocessing._label.LabelBinarizer",
    "sklearn.preprocessing._label.MultiLabelBinarizer",
    "sklearn.preprocessing._polynomial.PolynomialFeatures",
    "sklearn.preprocessing._polynomial.SplineTransformer",
    "sklearn.random_projection.BaseRandomProjection",
    "sklearn.random_projection.GaussianRandomProjection",
    "sklearn.random_projection.SparseRandomProjection",
    "sklearn.semi_supervised._label_propagation.BaseLabelPropagation",
    "sklearn.semi_supervised._label_propagation.LabelPropagation",
    "sklearn.semi_supervised._label_propagation.LabelSpreading",
    "sklearn.semi_supervised._self_training.SelfTrainingClassifier",
    "sklearn.svm._base.BaseLibSVM",
    "sklearn.svm._base.BaseSVC",
    "sklearn.svm._classes.LinearSVC",
    "sklearn.svm._classes.LinearSVR",
    "sklearn.svm._classes.SVC",
    "sklearn.svm._classes.NuSVC",
    "sklearn.svm._classes.SVR",
    "sklearn.svm._classes.NuSVR",
    "sklearn.svm._classes.OneClassSVM",
]


def _nr_wrap_model_class(wrapped, instance, args, kwargs):
    name = "%s.%s" % (wrapped.__class__.__name__, wrapped.__name__)
    return FunctionTraceWrapper(wrapped, name=name, group="MLModel/Sklearn/Named")(*args, **kwargs)


def _nr_instrument_model(module, model, model_path):
    if "ExtraTreeRegressor" in model_path:
        breakpoint()
    if hasattr(model, "predict"):
        wrap_function_wrapper(module, "%s.predict" % model_path, _nr_wrap_model_class_method)
    else:
        print("Model " + model_path + " has no method predict")
    if hasattr(model, "fit"):
        wrap_function_wrapper(module, "%s.fit" % model_path, _nr_wrap_model_class_method)
    else:
        print("Model " + model_path + " has no method fit")
    if hasattr(model, "predict_log_proba"):
        wrap_function_wrapper(module, "%s.predict_log_proba" % model_path, _nr_wrap_model_class_method)
    else:
        print("Model " + model_path + " has no method predict_log_proba")
    if hasattr(model, "predict_proba"):
        wrap_function_wrapper(module, "%s.predict_proba" % model_path, _nr_wrap_model_class_method)
    else:
        print("Model " + model_path + " has no method predict_proba")
    if hasattr(model, "transform"):
        wrap_function_wrapper(module, "%s.transform" % model_path, _nr_wrap_model_class_method)
    else:
        print("Model " + model_path + " has no method transform")
    if hasattr(model, "score"):
        wrap_function_wrapper(module, "%s.score" % model_path, _nr_wrap_model_class_method)
    else:
        print("Model " + model_path + " has no method score")


def instrument_sklearn_tree_models(module):
    model_classes = [
        "BaseDecisionTree",
        "DecisionTreeClassifier",
        "DecisionTreeRegressor",
        "ExtraTreeClassifier",
        "ExtraTreeRegressor",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.tree._classes.%s" % model_path)


def instrument_sklearn_base_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_calibration_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_cluster_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_compose_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_covariance_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_cross_decomposition_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_discriminant_analysis_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_dummy_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_ensemble_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_feature_selection_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_gaussian_process_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_isotonic_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_kernel_ridge_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_linear_model_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_metrics_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_mixture_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_model_selection_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_multiclass_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_multioutput_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_naive_bayes_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_neighbors_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_neural_network_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_pipeline_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_semi_supervised_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)


def instrument_sklearn_svm_models(module):
    model_classes = [
        "ClusterMixin",
        "Pipeline",
        "FeatureUnion",
    ]
    for model_path in model_classes:
        _nr_instrument_model(module, model, "sklearn.base.%s" % model_path)
