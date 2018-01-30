""" Class for downloading a single file.
"""
import time
import os
import requests
import tools

BLOCK_SIZE = 8192

class Downloader(object):
    """Main downloader class
    """
    def __init__(self, logger=None):
        self.logger = logger or tools.BasicLogger()
        self.downloaded_size = 0
        self.total_size = 0
        self.status = 'ready'
        self.working = False
        self.thread_pool = tools.PoolManager()

    def download(self, url, dest):
        if self.working:
            self.logger.error('Downloader is busy.')
            return
        self.working = True

        dest = os.path.abspath(dest)
        if not os.path.exists(os.path.dirname(dest)):
            self.logger.warning('dest path does not exist')
            os.makedirs(os.path.dirname(dest), exist_ok=True)

        accepts_range, filesize = tools.check_httpfile_info(url)
        if accepts_range:
            ranges = tools.divide_range(filesize)
        else:
            ranges = tools.divide_range(filesize, max_threads=1)

        for ran in ranges:
            self.thread_pool.add_pool(self.download_thread, url, dest, ran[0], ran[1])
        # self.thread_pool.wait_all()
        prev_size = 0
        while not self.thread_pool.iscomplete():
            time.sleep(1)
            pgsb = tools.progress_bar(self.downloaded_size / filesize, 40, \
                                      self.downloaded_size, True)
            print('%s %s/s' % (pgsb, tools.readable_filesize(self.downloaded_size - prev_size)))
            prev_size = self.downloaded_size

        tools.merge_files(dest)

    def download_thread(self, url, dest, start_byte=0, end_byte=-1, headers=None, timeout=10000):
        self.logger.info('Starting download.')

        if not headers:
            headers = {}
        if 'User-Agent' not in headers:
            headers['User-Agent'] = tools.random_useragent()
        if end_byte < start_byte:
            headers['Range'] = 'bytes=%d-' % start_byte
        else:
            headers['Range'] = 'bytes=%d-%d' % (start_byte, end_byte)

        dest = os.path.abspath(dest)
        dest += '.%014d' % start_byte
        filename = os.path.basename(dest)
        self.logger.info('Downloading %s to %s' % (url, filename))

        try:
            req = requests.get(url, headers=headers, stream=True)
            size = 0
            with open(dest, 'wb') as file:
                for chunk in req.iter_content(chunk_size=BLOCK_SIZE):
                    size += len(chunk)
                    self.downloaded_size += len(chunk)
                    file.write(chunk)
            if size != (end_byte - start_byte + 1):
                self.download_thread(url, dest[:-15], \
                start_byte=start_byte+size, end_byte=end_byte, headers=headers, timeout=timeout)
        except requests.exceptions.RequestException as exc:
            self.logger.error(exc)


# TODO: Implement unit tests

if __name__ == '__main__':
    Downloader().download('http://releases.ubuntu.com/16.04.3/ubuntu-16.04.3-desktop-amd64.iso' \
                        , 'test.iso')
