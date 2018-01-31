""" Class for downloading multiple files.
"""
import tools
import Downloader
import json

MAX_THREADS = 4

class BatchDownloader(object):
    """Batch downloader class.
    """
    def __init__(self, max_threads=MAX_THREADS, logger=None):
        self.thread_pool = tools.PoolManager(max_workers=max_threads)
        self.working = False
        self.logger = logger or tools.BasicLogger()

    def download_list(self, urls, directory):
        if directory[-1] != '/':
            directory = '%s/' % directory
        self.directory = directory
        if self.working:
            self.logger.error('Downloader is busy.')
            return
        self.working = True
        for url in urls:
            self.thread_pool.add_pool(self.single_download, url)

    def single_download(self, url: str):
        Downloader.Downloader().download(url, self.directory, None, True)

if __name__ == '__main__':
    with open('json.json', 'r') as ff:
        urls = json.load(ff)
        BatchDownloader().download_list(urls, './Downloads')