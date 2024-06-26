#  Copyright (c) 2024. Affects AI LLC
#
#  Licensed under the Creative Common CC BY-NC-SA 4.0 International License (the "License");
#  you may not use this file except in compliance with the License. The full text of the License is
#  provided in the included LICENSE file. If this file is not available, you may obtain a copy of the
#  License at
#
#       https://creativecommons.org/licenses/by-nc-sa/4.0/deed.en
#
#  Unless required by applicable law or agreed to in writing, software distributed under the License
#  is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
#  express or implied. See the License for the specific language governing permissions and limitations
#  under the License.


import abc
from pathlib import Path

import numpy as np

from aardt import config


class AERDataset(metaclass=abc.ABCMeta):
    """
    AERDataset is the base class for all dataset implementations in AARDT. All AERDatasets expose the following
    properties:
    - trials: a list of all AERTrials associated with this dataset
    - signals: a list of signals loaded in this dataset instance (a proper subset of the available signals within this
    dataset)
    - participant_ids: a list of participant identifiers in the dataset. Participant IDs are offset by the value of
     participant_offset
    - media_ids: a list of identifiers for the media file used as emotional stimulus in the dataset. Media IDs are
    offset by the value of media_file_offset
    - participant_offset: a constant value that is added to all participants identifiers in the dataset. This is useful
    when you will be using trials from several different AERDatasets.
    - media_file_offset: a constant value that is added to all media file identifiers in the dataset. This is useful
    when you will be using trials from several different AERDatasets
    - signal_preprocessors: a mapping of signal_type to SignalPreprocessor chain, used to automate signal preprocessing
    when signals are loaded from the AERTrial instances under this dataset.

    AERDataset also encapsulates business logic that is reusable by its subclasses, including:
    - preload signal checking: calls to `preload` are first checked to see if all signals have already been preloaded by
     a previous invocation. If a preload is necessary, then the subclass' _preload_dataset method will be called,
     otherwise no action is taken.
    - get_trial_splits: used to generate training, validation and test splits based on participant identifiers.
    """
    def __init__(self, signals=None, participant_offset=0, mediafile_offset=0):
        if signals is None:
            signals = []
        self._signals = signals
        self._signal_preprocessors = {}
        self._participant_offset = participant_offset
        self._media_file_offset = mediafile_offset
        self._participant_ids = set()
        self._media_ids = set()
        self._all_trials = []

    def preload(self):
        """
        Checks to see if a preload is necessary, and calls the subclass' _preload_dataset method as needed. AERDataset
        pre-loading is used to perform data transformations to optimize loading and processing when iterating over
        trials in the dataset. This is subclass-specific, and the details of how the preload works are encapsulated in
        the abstract _preload_dataset method.

        The status of the preload is saved in this dataset's working directory, specified by `self.get_working_Dir()`,
        in a file named `.preload.npy`. The file contains the list of all signals that have been preloaded for this
        AERDataset already.

        If this file does not exist, or if this AERDataset instance includes a signal type that is not already listed
        in the preload status file, then `self._preload_dataset()` is called. When this method returns, the preload
        status file is created or updated to include the new set of preloaded signal types.

        If this file exists and all signal types in this AERDataset are also listed in the preload status file, then no
        action is taken.

        :return:
        """
        preload_file = self.get_working_dir() / Path('.preload.npy')
        if preload_file.exists():
            preloaded_signals = set(np.load(preload_file))

            # If self.signals is a subset of the signals that have already been preloaded
            # then we don't have to preload anything.
            if set(self.signals).issubset(preloaded_signals):
                return

        self._preload_dataset()
        np.save(preload_file, self.signals)

    @abc.abstractmethod
    def _preload_dataset(self):
        """
        Abstract method invoked by self.preload() to perform the implementation-specific optimizations. See subclasses
        for more information about each AERDataset type's preload.

        :return:
        """
        pass

    @abc.abstractmethod
    def load_trials(self):
        """
        Loads the AERTrials from the preloaded dataset into memory. This method should load all relevant trials from
        the dataset. To avoid memory utilization issues, it is strongly recommended to defer loading signal data into
        the AERTrial until that AERTrial's load_signal_data method is called.

        See subclasses for dataset-specific details.
        :return:
        """
        pass

    def get_working_dir(self):
        """
        Returns the working path for this AERDataset instance, given by:
           aardt.config['working_dir'] / self.__class__.__name__ /

        For example, consider an AERDataset subclass named MyTestDataset:
            class MyTestDataset(AERDataset):
               pass

        The working directory is a subfolder of aardt.config['working_dir'] named "MyTestDataset/"

        This AERDataset working directory is where the preload status file is saved, and is also where any output
        generated by the _preload_dataset method should be stored.

        :return:
        """
        path = Path(config['working_dir']) / Path(self.__class__.__name__)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def signals(self):
        """
        Returns the set of signal types that are loaded by this AERDataset instance. This is a proper subset of the
        signal types available within this AERDataset. For example, DREAMER includes both 'EEG' and 'ECG' signal data,
        but this instance may only use 'ECG', 'EEG', or both.
        :return:
        """
        return self._signals

    @property
    def trials(self):
        """
        Returns a collection of all AERTrial instances loaded by this AERDataset. Order is not defined nor guaranteed.

        :return:
        """
        return self._all_trials

    def get_trial_splits(self, splits=None):
        """
        Returns the trials associated with this dataset, grouped into len(splits) splits. Splits are generated by
        participant-id. `splits` must be a list of relative sizes of each split, and np.sum(splits) must be 1.0. If
        `splits` is None, then [1.0] is assumed returning all trials.

        If splits=[0.7, 0.3] then the return value is a list with two elements, where the first element is a list
        containing trials from 70% of the participants in this dataset, and the second is a list containing trials from
        the remaining 30%. You may specify as many splits as needed, so for example, use `splits=[.70,.15,.15] to
        generate 70% training, 15% validation and 15% test splits.

        :param splits:
        :return: a list of trials if splits=None or [1], otherwise a list of N lists of trials, where N is the number
        of splits requested, and each list contains trials from the percent of participants specified by the split
        """
        if splits is None:
            splits = [1]

        if abs(1.0 - np.sum(splits)) > 1e-4:
            raise ValueError("Splits must sum to be 1.0")

        # If we only have 1 split then just return the list of all_trials, not a list of lists.
        if len(splits) == 1:
            return self._all_trials

        # Convert the percentages into participant counts
        splits = (np.array(splits) * len(self.participant_ids)).astype(dtype=np.int32)
        if sum(splits) != len(self.participant_ids):
            splits[0] += len(self.participant_ids) - sum(splits)

        # Split the participant ids randomly into len(splits) groups
        all_ids = set(self.participant_ids)
        participant_splits = []
        for i in range(len(splits)):
            participant_splits.append(
                list(np.random.choice(list(all_ids), splits[i], False))
            )
            all_ids = all_ids - set([x for xs in participant_splits for x in xs])

        # Obtain the groups of trials corresponding to each group of participant ids
        trial_splits = []
        for participant_split in participant_splits:
            trial_splits.append([trial for trial in self.trials if trial.participant_id in participant_split])

        return trial_splits

    @property
    def media_ids(self):
        """
        Returns the collection of all media identifiers associated with this AERDataset instance. The values returned
        have already been offset by self.media_file_offset. So for example, a media identifier from this AERDataset
        instance:
          N = self.media_ids[0]

        corresponds to the media id (N - self.media_file_offset) in the underlying dataset.

        :return:
        """
        return self._media_ids

    @property
    def participant_ids(self):
        """
        Returns the collection of all participant identifiers associated with this AERDataset instance. The values
        returned have already been offset by self.participant_offset. So for example, a media identifier from this
        AERDataset instance:
          N = self.participant_ids[0]

        corresponds to the participant id (N - self.participant_offset) in the underlying dataset.

        :return:
        """
        return self._participant_ids

    @property
    def media_file_offset(self):
        """
        The constant value added to all media identifiers within the underlying dataset. This is useful for when you
        want to mix AERTrials from multiple AERDataset instances.

        For example, if aerDataset1 uses media_file_offset=0, and has media identifiers 1 through 50, then you
        might instantiate aerDataset2 using participant_offset=50. Then, media identifier 1 within the second
        dataset will be loaded as media_id=51 instead, avoiding any conflict at runtime.

        :return:
        """
        return self._media_file_offset

    @property
    def participant_offset(self):
        """
        The constant value added to all participant identifiers within the underlying dataset. This is useful for when
        you want to mix AERTrials from multiple AERDataset instances.

        For example, if aerDataset1 uses participant_offset=0, and has participant identifiers 1 through 50, then you
        might instantiate aerDataset2 using participant_offset=50. Then, participant identifier 1 within the second
        dataset will be loaded as participant_id=51 instead, avoiding any conflict at runtime.

        :return:
        """
        return self._participant_offset

    @property
    def signal_preprocessors(self):
        return self._signal_preprocessors
