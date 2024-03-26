from datetime import datetime, timedelta

from datasets import AERTrial
import scipy.io
import numpy as np

ASCERTAIN_ECG_SAMPLE_RATE = 256
ASCERTAIN_ECG_N_CHANNELS = 2


class AscertainTrial(AERTrial):
    def __init__(self, participant_id, movie_id):
        super().__init__(participant_id, movie_id)
        self._ecg_signal_duration = None

    def load_ground_truth(self):
        return 0

    def get_signal_metadata(self, signal_type):
        if signal_type == 'ECG':
            return {
                'signal_type': signal_type,
                'sample_rate': ASCERTAIN_ECG_SAMPLE_RATE,
                'n_channels': ASCERTAIN_ECG_N_CHANNELS,
                'duration': self._ecg_signal_duration,
            }

    def load_signal_data(self, signal_type):
        signal_data_file = self._signal_data_files[signal_type]
        matfile = scipy.io.loadmat(signal_data_file)

        if signal_type == 'ECG':
            data = self._load_ecg_signal_data(matfile)
            self._ecg_signal_duration = data.shape[1] / ASCERTAIN_ECG_SAMPLE_RATE
            return data
        elif signal_type == 'GSR':
            return self._load_gsr_signal_data(matfile)
        elif signal_type == 'EEG':
            return self._load_eeg_signal_data(matfile)
        else:
            raise ValueError('_load_signal_data not implemented for signal type {}'.format(signal_type))

    @staticmethod
    def _load_eeg_signal_data(signal_data_file):
        return []

    @staticmethod
    def _load_ecg_signal_data(signal_data_file):
        start_time_arr = signal_data_file['timeECG'][0]
        start_time = datetime(
            int(start_time_arr[0]),
            int(start_time_arr[1]),
            int(start_time_arr[2]),
            int(start_time_arr[3]),
            int(start_time_arr[4]),
            int(start_time_arr[5]),
            int(1000 * (start_time_arr[5] % 1))
        )

        def convert_to_epoch(_timestamp, _start_time):
            return (_start_time + timedelta(milliseconds=_timestamp)).timestamp()

        timeconverter = np.vectorize(lambda _ts: convert_to_epoch(_ts, start_time))

        ecg_data = signal_data_file['Data_ECG']
        left_arm_idx = 1 if (len(ecg_data[0]) < 6) else 4
        right_arm_idx = 2 if (len(ecg_data[0]) < 6) else 5

        ecg = ecg_data[:, [0, left_arm_idx, right_arm_idx]]
        ts = np.apply_along_axis(
            func1d=timeconverter,
            axis=0,
            arr=ecg[:, 0])
        ts = ts.reshape(-1, 1)

        result = np.append(ts, ecg[:, [1, 2]], axis=1)
        return result.transpose()

    @staticmethod
    def _load_gsr_signal_data(signal_data_file):
        return []
