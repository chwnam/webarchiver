from __future__ import absolute_import
import atexit
import io
import operator
import os
import tempfile
import time
import unittest
import tarfile
import zipfile

from threading import Thread

# noinspection PyUnresolvedReferences
from six.moves import SimpleHTTPServer
# noinspection PyUnresolvedReferences
from six.moves.SimpleHTTPServer import SimpleHTTPRequestHandler
# noinspection PyUnresolvedReferences
from six.moves.socketserver import TCPServer
# noinspection PyUnresolvedReferences
from six.moves.urllib.parse import urlparse

import python_web_archiver
import python_web_archiver.connectors as connectors

RESOURCE_PATH = os.path.join(os.path.dirname(__file__), 'resources')

TEST_SERVER_ADDRESS = ('127.0.0.1', 8895)


def unlink_file(path):
    """
    remove file if exists
    """
    if os.path.exists(path):
        os.unlink(path)


def factory_connector():
    """
    get default RequestsConnector.
    test_cookie.cookie files are created, but it will be removed as soon as the program exits.
    """
    cookie_file = Path(os.path.dirname(__file__)).child('test_cookie.cookie')
    extra_headers = {'user-agents': connectors.UserAgents.chrome()}
    connector = connectors.RequestsConnector(cookie_file, extra_headers)
    atexit.register(unlink_file, cookie_file)
    return connector


def get_http_test_server_thread():
    """
    get local http server: root path is 'archiver.resources'.
    please noted: you should call stop() before finishing
    """
    class SimpleTestServerThread(Thread):
        daemon = True
        current_path = os.getcwd()
        httpd = None

        def run(self):
            os.chdir(RESOURCE_PATH)
            self.httpd = TCPServer(TEST_SERVER_ADDRESS, SimpleHTTPRequestHandler)
            self.httpd.serve_forever()

    def server_cleanup(thread):
        print('server_cleanup() called!', thread)
        if thread.is_alive():
            thread.httpd.shutdown()
            thread.join()
            thread.join()
            print('is it alive?: %s' % thread.is_alive())
            # while not thread.is_alive():
            #     print('waiting for completed...')
            #     time.sleep(2)
            print('thread joined!')

    t = SimpleTestServerThread()
    atexit.register(server_cleanup, t)
    print('get_http_test_server_thread() called')
    return t


server_thread = get_http_test_server_thread()


class TestArchiver(unittest.TestCase):

    def setUp(self):
        print('setUp')
        self.test_path = os.path.dirname(__file__)
        self.server = server_thread
        if not self.server.is_alive():
            print('try to run the server!')
            self.server.start()

    def tearDown(self):
        print('tearDown')

    def test_url_download(self):
        """
        test archiver.url_download()
        """
        # test URL: google logo image
        test_url = 'http://%s:%s/test_images/google.png' % (TEST_SERVER_ADDRESS[0], TEST_SERVER_ADDRESS[1])

        # the URL content already downloaded
        file_path = os.path.join(RESOURCE_PATH, 'test_images', 'google.png')

        # run the function
        file_buffer = io.BytesIO()
        python_web_archiver.url_download(test_url, file_buffer)

        # check the content is true
        with open(file_path, 'rb') as f:
            real_content = f.read()
        self.assertEqual(file_buffer.getvalue(), real_content)

        file_buffer.close()

    def test_zip_recursive(self):
        """
        test archiver.zip_recursive()
        """
        archive_path = tempfile.NamedTemporaryFile()
        test_path = self.test_path

        # target_path must exist
        self.assertTrue(os.path.exists(test_path))

        # testing
        python_web_archiver.zip_recursive(archive_path, test_path)

        # archived our directory
        archive_root = os.path.dirname(self.test_path)
        with zipfile.ZipFile(archive_path) as zf:
            zipped_files_sizes = [
                (os.path.join(archive_root, item.filename), item.file_size)
                for item in zf.infolist()
                ]
        zipped_files_sizes.sort(key=operator.itemgetter(0))

        # collect real directory information
        correct_files_sizes = []
        for dirpath, dirnames, filenames in os.walk(test_path):
            for entry in filenames:
                filename = os.path.join(dirpath, entry)
                filesize = os.stat(filename).st_size
                correct_files_sizes.append((filename, filesize))
        correct_files_sizes.sort(key=operator.itemgetter(0))

        # check the zip file is correct
        self.assertEqual(zipped_files_sizes, correct_files_sizes)

        archive_path.close()

    def test_archive_remote_urls(self):

        test_server = 'http://{}:{}'.format(TEST_SERVER_ADDRESS[0], TEST_SERVER_ADDRESS[1])

        download_path = tempfile.gettempdir()
        title = 'test_images'
        urls = [
            test_server + '/test_images/google.png',
            test_server + '/test_images/twitter.png',
            test_server + '/test_images/facebook.png',
        ]

        comparison_list = [
            os.path.join(title, '%02d%s' % (i + 1, os.path.splitext(x)[1]))
            for i, x in enumerate(urls)
            ]

        # test as .tar.gz
        python_web_archiver.archive_remote_urls(
            download_path=download_path,
            title=title,
            urls=urls,
            archiver='.tar.gz',
            cleanup=True
        )

        archived = os.path.join(download_path, title + '.tar.gz')
        self.assertTrue(os.path.exists(archived))

        # check the content
        with tarfile.open(archived) as tar:
            archived_files = sorted(tar.getnames())
            self.assertListEqual(
                archived_files,
                [title] + comparison_list  # tar has directories
            )

        # test as .zip
        python_web_archiver.archive_remote_urls(
            download_path=download_path,
            title=title,
            urls=urls,
            archiver='.zip',
            cleanup=True
        )

        archived = os.path.join(download_path, title + '.zip')
        self.assertTrue(os.path.exists(archived))

        # check the content
        with zipfile.ZipFile(archived) as zip:
            archived_files = sorted(zip.namelist())
            self.assertListEqual(
                archived_files,
                comparison_list
            )

    def test_simple_http_server(self):
        pass
        #     server = get_http_test_server_thread()
        #     print('hello!')
        #     server.join(5)

    def test_get_safe_name(self):
        result = python_web_archiver.get_safe_name('i_/am-:un|safe? maybe,...')
        self.assertEqual('i_am-unsafe maybe,...', result)
