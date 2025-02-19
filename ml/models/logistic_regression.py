from random import uniform

from sklearn.linear_model import LogisticRegression

from configs import CORE_COUNT, SEED
from ml.models.base import SupervisedMLRefactoringModel


class LogisticRegressionRefactoringModel(SupervisedMLRefactoringModel):
    def feature_reduction(self) -> bool:
        return True

    def params_to_tune(self):
        return {
            "max_iter": [100, 500, 1000, 2000, 5000, 10000],
            "C": [uniform(0.01, 100) for _ in range(0, 5)],
        }

    def model(self, best_params=None):
        if best_params is not None:
            return LogisticRegression(
                solver='saga',
                max_iter=best_params["max_iter"],
                C=best_params["C"],
                n_jobs=CORE_COUNT,
                random_state=SEED)

        return LogisticRegression(solver='saga', random_state=SEED)
