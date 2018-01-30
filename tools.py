""" Utility functions and classes.
"""
import json
import os
import string
import logging
import random
import concurrent.futures
import requests

SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
TIME_UNITS = [
    ['second', 'minute', 'hour', 'day', 'week', 'month', 'year'],
    ['s', 'm', 'h', 'd', 'w', 'm', 'y'],
]
TIME_INTERVALS = [1, 60, 3600, 86400, 604800, 2419200, 29030400, 2**62]
TIME_UNIT_COUNT = 7
BLOCK_SIZE = 8192
MIN_DIV_SIZE = 100*(2**20)
MAX_THREAD = 8
CHARS = string.ascii_lowercase + string.digits

def random_string(size=12):
    """Creates a random string of lowercase alphabets and numbers

    Keyword Arguments:
        size {int} -- Length of the string (default: {12})
    """
    return ''.join(random.choice(CHARS) for _ in range(size))

def random_useragent():
    """Returns a random user agent string.

    Returns:
        str -- A user agent string.
    """
    with open('ua.json', 'r') as file:
        agents = json.load(file)
        return random.choice(agents)


def readable_filesize(size):
    """Returns a human readable file size, with reasonable units.

    Arguments:
        size {int} -- Size of file, in bytes.

    Returns:
        str -- Human readable file size with units.
    """
    unit_index = 0
    while size >= 1000:
        unit_index += 1
        size /= 1024.0
    if unit_index == 0:
        return "%.0f%s" % (size, SIZE_UNITS[unit_index])
    else:
        return "%.1f%s" % (size, SIZE_UNITS[unit_index])


def time_string(seconds, short=False):
    """Generates a time string

    Arguments:
        seconds {int} -- Time in seconds.

    Keyword Arguments:
        short {boolean} -- Abbreviates the units if this is true. (default: {False})

    Returns:
        str -- The generated time string.
    """
    time_data = []
    last_nonzero_index = 0
    for i in range(TIME_UNIT_COUNT):
        now = int((seconds % TIME_INTERVALS[i+1]) / TIME_INTERVALS[i])
        time_data.append(now)
        if now != 0:
            last_nonzero_index = i
    ret_string = ''
    for i in reversed(range(last_nonzero_index+1)):
        unit_string = TIME_UNITS[1 if short else 0][i]
        if time_data[i] > 1:
            unit_string += 's'
        ret_string += '%d %s ' % (time_data[i], unit_string)
    return ret_string


def progress_bar(progress, length=20, file_size=None, show_percentage=False):
    """Returns a console progress bar string

    Arguments:
        progress {float} -- Progress, a float between 0 and 1.

    Keyword Arguments:
        length {str} -- Length of the progress bar. (default: {20})
        show_percentage {boolean} -- Show progress percentage. (default: {False})

    Returns:
        str -- Progress bar.
    """
    count = int(progress*length)
    progress_str = '[' + '#'*count + '-'*(length-count) + ']'
    if file_size:
        progress_str += ' %s' % readable_filesize(file_size)
    if show_percentage:
        progress_str += ' %.1f%%' % (progress*100)
    return progress_str


def divide_range(filesize, min_size=MIN_DIV_SIZE, max_threads=MAX_THREAD):
    """Divides the filesize range to the number of threads

    Arguments:
        filesize {int} -- Size of the file in bytes.

    Keyword Arguments:
        min_size {int} -- Minimum size of range. (default: {MIN_DIV_SIZE})
        max_threads {int} -- Maximum number of threads. (default: {MAX_THREAD})

    Returns:
        list -- List of tuples of range.
    """
    thread_count = max(1, min(max_threads, int(filesize/min_size)))
    div_size = int(filesize / thread_count)
    ret = []
    start, end = 0, div_size
    for _ in range(thread_count):
        if end >= filesize:
            end = filesize - 1
        ret.append((start, end))
        start = end + 1
        end = start + div_size
    return ret

def check_httpfile_info(url, timeout=15):
    """Check if the server accepts range requests, and get content length.

    Arguments:
        url {str} -- Url of file to check.

    Keyword Arguments:
        timeout {int} -- Timeout of request (default: {15})

    Returns:
        bool -- Whether the server accepts range requests.
        int -- Content length.
    """
    req = requests.head(url, headers={
        'User-Agent': random_useragent(),
        'Range': 'bytes=0-7'
    }, timeout=timeout)
    print(req.headers)
    # Check if server accepts range and properly returns data
    accept_range = 'Accept-Ranges' in req.headers or req.headers['Content-Length'] == '8'
    if 'Content-Range' in req.headers:
        content_length = int(req.headers['Content-Range'].split('/')[-1])
    else:
        content_length = int(req.headers['Content-Length'])
    return accept_range, content_length

def merge_files(dest):
    """Merge files with the given name

    Arguments:
        dest {str} -- File
    """
    filename = os.path.basename(dest)
    files = []
    for file in os.listdir():
        if not os.path.isfile(file):
            continue
        filename_cmp = os.path.basename(file)
        if len(filename_cmp) < 15:
            continue
        if filename_cmp[:-15] == filename:
            files.append(file)
    files = sorted(files)
    with open(dest, 'wb') as newfile:
        for file in files:
            with open(file, 'rb') as dfile:
                data = dfile.read(BLOCK_SIZE)
                while data:
                    newfile.write(data)
                    data = dfile.read(BLOCK_SIZE)
            os.remove(file)

class BasicLogger(object):
    """A basic logger class, same as logging module.
    """
    def info(self, text):
        """Log a info string.

        Arguments:
            text {str} -- Text to log
        """
        print(text)
    def warning(self, text):
        """Log a warning string.

        Arguments:
            text {str} -- Text to log
        """
        logging.warning(text)
    def error(self, text):
        """Log a error string.

        Arguments:
            text {str} -- Text to log
        """
        logging.error(text)

class PoolManager(object):
    """Pool Manager using concurrent.futures.ThreadPoolExecutor.
    """
    def __init__(self):
        self.worker = concurrent.futures.ThreadPoolExecutor()
        self.works = []
    def add_pool(self, func, *args, **kwargs):
        """Add a work to the pool

        Arguments:
            func {function} -- Function to execute
        """
        work = self.worker.submit(func, *args, **kwargs)
        self.works.append(work)
    def iscomplete(self):
        """Check if all work added is complete.

        Returns:
            bool -- Whether the works are completed.
        """
        for work in self.works:
            if work.running():
                return False
        return True
    def wait_all(self):
        """Wait for all tasks to end.

        Returns:
            list -- list of values returned from tasks.
        """
        ret = [work.result() for work in self.works]
        self.works = []
        return ret