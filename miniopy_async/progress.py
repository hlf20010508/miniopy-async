# -*- coding: utf-8 -*-
# Asynchronous MinIO Client SDK for Python
# (C) 2018 MinIO, Inc.
# (C) 2022 L-ING <hlf01@icloud.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module implements a progress printer while communicating with MinIO server
:copyright:
(C) 2018 by MinIO, Inc.
(C) 2022 L-ING <hlf01@icloud.com>
:license: Apache 2.0, see LICENSE for more details.
"""

import time

_BAR_SIZE = 20
_KILOBYTE = 1024
_FINISHED_BAR = "#"
_REMAINING_BAR = "-"

_UNKNOWN_SIZE = "?"
_STR_MEGABYTE = " MB"

_HOURS_OF_ELAPSED = "%d:%02d:%02d"
_MINUTES_OF_ELAPSED = "%02d:%02d"

_RATE_FORMAT = "%5.2f"
_PERCENTAGE_FORMAT = "%3d%%"
_HUMANINZED_FORMAT = "%0.2f"

_DISPLAY_FORMAT = "|%s| %s/%s %s [elapsed: %s left: %s, %s MB/sec]"

_REFRESH_CHAR = "\r"


class Progress:
    """
    Constructs a :class:`Progress` object.
    :param interval: Sets the time interval to be displayed on the screen.
    :param stdout: Sets the standard output
    :return: :class:`Progress` object
    """

    def __init__(self, object_name, total_length):
        self.object_name = object_name
        self.total_length = total_length
        self.prefix = self.object_name + ": " if self.object_name else ""

        self.interval = 1
        self.last_printed_len = 0
        self.current_size = 0

        self.initial_time = time.time()

    def update(self, size):
        """
        Update object size to be showed. This method called while uploading
        :param size: Object size to be showed. The object size should be in
                     bytes.
        """
        if not isinstance(size, int):
            raise ValueError(
                f"{type(size)} type can not be displayed. " "Please change it to Int."
            )

        displayed_time = time.time() - self.initial_time
        self.current_size += size
        self.print_status(
            current_size=self.current_size,
            total_length=self.total_length,
            displayed_time=displayed_time,
            prefix=self.prefix,
        )

    def print_status(self, current_size, total_length, displayed_time, prefix):
        formatted_str = prefix + format_string(
            current_size, total_length, displayed_time
        )
        print(
            _REFRESH_CHAR
            + formatted_str
            + " " * max(self.last_printed_len - len(formatted_str), 0)
        )
        self.last_printed_len = len(formatted_str)


def seconds_to_time(seconds):
    """
    Consistent time format to be displayed on the elapsed time in screen.
    :param seconds: seconds
    """
    minutes, seconds = divmod(int(seconds), 60)
    hours, m = divmod(minutes, 60)

    if hours:
        return _HOURS_OF_ELAPSED % (hours, m, seconds)
    else:
        return _MINUTES_OF_ELAPSED % (m, seconds)


def format_string(current_size, total_length, elapsed_time):
    """
    Consistent format to be displayed on the screen.
    :param current_size: Number of finished object size
    :param total_length: Total object size
    :param elapsed_time: number of seconds passed since start
    """

    n_to_mb = current_size / _KILOBYTE / _KILOBYTE
    elapsed_str = seconds_to_time(elapsed_time)

    rate = _RATE_FORMAT % (n_to_mb / elapsed_time) if elapsed_time else _UNKNOWN_SIZE

    frac = float(current_size) / total_length
    bar_length = int(frac * _BAR_SIZE)

    bar = _FINISHED_BAR * bar_length + _REMAINING_BAR * (_BAR_SIZE - bar_length)

    percentage = _PERCENTAGE_FORMAT % (frac * 100)

    left_str = (
        seconds_to_time(elapsed_time / current_size * (total_length - current_size))
        if current_size
        else _UNKNOWN_SIZE
    )

    humanized_total = (
        _HUMANINZED_FORMAT % (total_length / _KILOBYTE / _KILOBYTE) + _STR_MEGABYTE
    )

    humanized_n = _HUMANINZED_FORMAT % n_to_mb + _STR_MEGABYTE

    return _DISPLAY_FORMAT % (
        bar,
        humanized_n,
        humanized_total,
        percentage,
        elapsed_str,
        left_str,
        rate,
    )
