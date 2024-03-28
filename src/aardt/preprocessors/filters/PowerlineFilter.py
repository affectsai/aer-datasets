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
import numpy as np
from neurokit2 import signal as nk2signal

from aardt.preprocessors.SignalPreprocessor import SignalPreprocessor


class PowerlineFilter(SignalPreprocessor):
    """
    Filters out powerline noise by smoothing the signal with a moving average kernel the width of one period at the
    powerline frequency. Uses NeuroKit2 signal filtering.
    """

    def __init__(self, Fs, powerline=60, parent_preprocessor=None, child_preprocessor=None):
        """
        :param Fs: The sampling frequency
        :param powerline: the powerline frequency, defaults to 60Hz, typically either 50 or 60
        :param parent_preprocessor:
        """
        super().__init__(parent_preprocessor, child_preprocessor)
        self._sampling_frequency = Fs
        self._powerline = powerline

    def process_signal(self, signal):
        return nk2signal.signal_filter(signal, self._sampling_frequency, method='powerline', powerline=self._powerline)
