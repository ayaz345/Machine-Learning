from collections import Counter
from typing import Iterable
import pandas as pd
from configs import SCALE_DATASET, BALANCE_DATASET, DROP_METRICS, \
    DROP_PROCESS_AND_AUTHORSHIP_METRICS, PROCESS_AND_AUTHORSHIP_METRICS,\
    DROP_FAULTY_PROCESS_AND_AUTHORSHIP_METRICS, TRAINING_SAMPLE_RATIO
from ml.preprocessing.sampling import perform_balancing, sample_reduction
from ml.preprocessing.scaling import perform_scaling, perform_fit_scaling
from ml.refactoring import LowLevelRefactoring
from utils.log import log


def retrieve_labelled_instances(
        datasets: Iterable[str],
        refactoring: LowLevelRefactoring,
        is_training_data: bool = True,
        scaler=None):
    """
    This method retrieves all the labelled instances
    for a given refactoring and dataset.
    It performs the following pipeline:
      1. Get all refactored and non refactored instances from the db.
      2. Merge them into a single dataset,
      having 1=true and 0=false, as labels.
      3. Removes possible NAs
      (the data collection process is tough;
      bad data might had make it through)
      4. Shuffles the dataset (good practice)
      5. Balances the dataset (if configured)
      6. Scales the features values (if configured)

    :param dataset: a string containing the name of the dataset to be retrieved
    :param refactoring: the refactoring object,
    containing the refactoring to be retrieved
    :param is_training_data: is this training data? If so,
    :param scaler: a predefined scaler, for this data

    :return:
        x: a dataframe with the feature values
        y: the label (1=true, a refactoring has happened,
        ƒ0=false, no refactoring has happened)
        ids: instance ids, to query the actual data from the database
        scaler: the scaler object used in the scaling process.
    """
    log(
        f"---- Retrieve labeled instances for dataset: {datasets} and the\
             refactoring {refactoring.name()}")

    # get all refactoring examples we have in our dataset
    refactored_instances = refactoring.get_refactored_instances(
        datasets)
    # load non-refactoring examples
    non_refactored_instances = refactoring.get_non_refactored_instances(
        datasets)

    log(
        f"raw number of refactoring instances:\
             {refactored_instances.shape[0]}")
    log(
        f"raw number of non-refactoring with K={refactoring.commit_threshold()}\
             instances: {non_refactored_instances.shape[0]}")

    # if there' still a row with NAs, drop it as it'll cause a failure later
    # on.
    refactored_instances = refactored_instances.dropna()
    non_refactored_instances = non_refactored_instances.dropna()

    # test if any refactorings were found for the given refactoring type
    if refactored_instances.shape[0] == 0:
        log(
            f"No refactorings found for refactoring type:\
                 {refactoring.name()}")
        return None, None, None

    if non_refactored_instances.shape[0] == 0:
        log(
            f"No non-refactorings found for threshold:\
                 {refactoring.commit_threshold()}")
        return None, None, None
    # test if any refactorings were found for the given refactoring type

    log(
        f"refactoring instances (after dropping NA)s: {refactored_instances.shape[0]}"
    )
    log(
        f"non-refactoring instances (after dropping NA)s: {non_refactored_instances.shape[0]}"
    )

    assert non_refactored_instances.shape[0] > 0, \
        "Found no non-refactoring instances for level: " + refactoring.level()

    # set the prediction variable as true and false in the datasets
    refactored_instances["prediction"] = 1
    non_refactored_instances["prediction"] = 0

    # reduce the amount training samples, if specified, also keep the
    # specified balance
    if is_training_data and \
            0 < TRAINING_SAMPLE_RATIO < 1 and\
            not BALANCE_DATASET:
        refactored_instances, non_refactored_instances = sample_reduction(
            refactored_instances, non_refactored_instances,
            TRAINING_SAMPLE_RATIO)

    refactored_instances = refactored_instances.drop_duplicates()
    non_refactored_instances = non_refactored_instances.drop_duplicates()
    log(
        f"refactoring instances (after dropping duplicates)s: {refactored_instances.shape[0]}"
    )
    log(
        f"non-refactoring instances (after dropping duplicates)s: {non_refactored_instances.shape[0]}"
    )
    # now, combine both datasets (with both TRUE and FALSE predictions)
    if non_refactored_instances.shape[1] != refactored_instances.shape[1]:
        raise ImportError("Number of columns differ from both datasets.")
    merged_dataset = pd.concat(
        [refactored_instances, non_refactored_instances])
    # do we want to try the models without some metrics, e.g. process and
    # authorship metrics?
    merged_dataset = merged_dataset.drop(DROP_METRICS, axis=1)

    # Remove all instances with a -1 value
    # in the process and authorship metrics,
    # ToDo: do this after the feature reduction to simplify the query and do
    # not drop instances which are not affected by faulty process and
    # authorship metrics, which are not in the feature set
    if DROP_FAULTY_PROCESS_AND_AUTHORSHIP_METRICS and \
            not DROP_PROCESS_AND_AUTHORSHIP_METRICS:
        log(
            f"Instance count before dropping faulty process metrics: {len(merged_dataset.index)}"
        )
        metrics = [
            metric for metric in PROCESS_AND_AUTHORSHIP_METRICS
            if metric in merged_dataset.columns.values]
        query = " and ".join(["%s != -1" % metric for metric in metrics])
        merged_dataset = merged_dataset.query(query)
        log(
            f"Instance count after dropping faulty process metrics: {len(merged_dataset.index)}"
        )

    # separate the x from the y (as required by the scikit-learn API)
    y = merged_dataset["prediction"]
    x = merged_dataset.drop("prediction", axis=1)
    # y = merged_dataset["prediction"]
    # balance the datasets, as we have way more 'non refactored examples'
    #  rather than refactoring examples
    # for now, we basically perform under sampling
    if BALANCE_DATASET:
        log("instances before balancing: {}".format(Counter(y)))
        x, y = perform_balancing(x, y)
        assert x.shape[0] == y.shape[0], "Balancing did not work,\
        x and y have different shapes."
        log("instances after balancing: {}".format(Counter(y)))

    # shuffle data after balancing it, because some of the samplers order the
    # data during balancing it

    # apply some scaling to speed up the algorithm
    if SCALE_DATASET and scaler is None:
        x, scaler = perform_fit_scaling(x)
    elif SCALE_DATASET:
        x = perform_scaling(x, scaler)

    log(f"Got {x.shape[0]} instances with {x.shape[1]}\
        features for the dataset: {datasets}\
        at threshold {refactoring.commit_threshold()}.")
    return x, y, scaler
