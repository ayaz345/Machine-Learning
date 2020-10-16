from configs import LEVEL_MAP, Level, LEVEL_Stable_Thresholds_MAP
from db.QueryBuilder import get_level_refactorings, get_level_stable
from db.DBConnector import execute_query
from utils.log import log


class LowLevelRefactoring:
    _name = ""
    _level = Level.NONE
    _commitThreshold = -1

    def __init__(self, name, level, commitThreshold):
        self._name = name
        self._level = level
        self._commitThreshold = commitThreshold

    def get_refactored_instances(self, dataset: str = ""):
        """
        Get all refactoring instances for this refactoring, e.g. for refactoring "Extract Method".

        Parameter:
            dataset (str) (optional): filter the refactoring instances for this dataset. If no dataset is specified, no filter is applied.
        """
        return execute_query(get_level_refactorings(int(self._level), self._name, dataset))

    def get_non_refactored_instances(self, dataset: str = ""):
        """
        Get all non-refactored (stable) instances of the same level of the refactoring, e.g. Level 2 for refactoring "Extract Method".

        Parameter:
            dataset (str) (optional): filter the non-refactored for this dataset. If no dataset is specified, no filter is applied.
        """
        return execute_query(get_level_stable(int(self._level), self._commitThreshold, dataset))

    def level(self) -> str:
        """
        Get the level of the refactoring type, e.g. Level.Field for "Push Down Attribute"
        """
        return str(self._level)

    def name(self) -> str:
        """
        Get the name of the refactoring type, e.g. "Push Down Attribute"
        """
        return self._name

    def commit_threshold(self) -> int:
        """
        Get the stable commit threshold for this run, e.g. 15
        """
        return self._commitThreshold


def build_refactorings(selected_level: Level):
    """
    Build LowLevelRefactoring for all refactoring types for the given level.

    Parameter:
        selected_level (Level): all level to select the refactoring types for, e.g. [Level.Class, Level.Method]
    """
    all_refactorings = []
    for level in selected_level:
        for refactoring in LEVEL_MAP[level]:
            for commitThreshold in LEVEL_Stable_Thresholds_MAP[level]:
                all_refactorings += [LowLevelRefactoring(refactoring, level, commitThreshold)]
    log(f"Built refactoring objects for {str(len(all_refactorings))} refactoring types.")

    return all_refactorings
