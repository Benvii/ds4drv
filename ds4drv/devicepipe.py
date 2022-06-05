import os
import threading
from typing import NoReturn

from ds4drv.device import DS4Device

DEVICES_PIPE = "/tmp/ds4drv-device.pipe"
DEVICES_LAST_ADDR = "/tmp/ds4drv-device.lastaddr"


class DevicePipe:

    def __init__(self, device_pipe_path: str = DEVICES_PIPE, last_mac_addr_file_path: str = DEVICES_LAST_ADDR):
        """
        :param device_pipe_path: Pipe where all new mac address will be written
        :param last_mac_addr_file_path: File were we keep the last one, useful when an app want it and wasn't listening
                                        to the pipe when the last device was added.
        """
        self.device_pipe_path = device_pipe_path
        self.last_mac_addr_file_path = last_mac_addr_file_path

        self.fifo = None # Until someone read on it
        self.datas_to_write = [] # Accumulate lines to write, as fifo is block until someone read on it

    def __enter__(self):
        try:
            if os.path.exists(self.device_pipe_path):
                os.unlink(self.device_pipe_path)
            os.mkfifo(self.device_pipe_path)
        except:
            pass

        t = threading.Thread(target=self.open_pipe_blocking_until_reader)
        t.start()
        return self

    def open_pipe_blocking_until_reader(self):
        self.fifo = open(self.device_pipe_path, "w", encoding='utf-8')
        print('Someone listen')
        self._write_data_waiting()

    def _write_data_waiting(self) -> NoReturn:
        """
        Writes data that were stuck due to blocking fifo.
        """
        for data_to_write in self.datas_to_write:
            self._write_to_fifo(data_to_write)
        self.datas_to_write = []

    def _write_to_fifo(self, data) -> NoReturn:
        """
        Write data to fifo
        :param data:
        :return:
        """
        self.fifo.write(data + "\n")
        self.fifo.flush()

    def append(self, device: DS4Device) -> NoReturn:
        """
        Notify a new device in the pipe.
        :param device: The added device.
        """
        data_to_write = device.device_addr

        if self.fifo is None:
            self.datas_to_write.append(data_to_write)
        else:
            self._write_to_fifo(data_to_write)

        with open(self.last_mac_addr_file_path, 'w', encoding='utf-8') as last_file:
            last_file.write(device.device_addr)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.fifo:
            try:
                self.fifo.close()
            except:
                pass
