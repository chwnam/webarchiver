from __future__ import absolute_import
import atexit
import io
import operator
import os
import tempfile
import unittest
import tarfile
import time
import zipfile

from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.expected_conditions import presence_of_element_located

from threading import Thread
# noinspection PyUnresolvedReferences
from six.moves import SimpleHTTPServer
# noinspection PyUnresolvedReferences
from six.moves.SimpleHTTPServer import SimpleHTTPRequestHandler
# noinspection PyUnresolvedReferences
from six.moves.socketserver import TCPServer
# noinspection PyUnresolvedReferences
from six.moves.urllib.parse import urlparse, parse_qsl
# noinspection PyUnresolvedReferences
from six.moves.BaseHTTPServer import BaseHTTPRequestHandler

import webarchiver
import webarchiver.connectors as connectors


RESOURCE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')

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
    cookie_file = os.path.join(os.path.dirname(__file__), 'test_cookie.cookie')
    extra_headers = {'user-agent': connectors.UserAgents.chrome()}
    connector = connectors.RequestsConnector(cookie_file, extra_headers)
    atexit.register(unlink_file, cookie_file)
    return connector


def get_http_test_server_thread(handler_class):
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
            TCPServer.allow_reuse_address = True
            # SimpleHTTPRequestHandler
            self.httpd = TCPServer(TEST_SERVER_ADDRESS, handler_class)
            self.httpd.serve_forever()

        def server_cleanup(self):
            if self.is_alive():
                self.httpd.shutdown()
                self.httpd.server_close()
                self.join()

    return SimpleTestServerThread()


class TestArchiver(unittest.TestCase):
    server = None

    @classmethod
    def setUpClass(cls):
        cls.test_path = os.path.dirname(os.path.abspath(__file__))
        cls.server = get_http_test_server_thread(SimpleHTTPRequestHandler)
        if not cls.server.is_alive():
            cls.server.start()

    @classmethod
    def tearDownClass(cls):
        if cls.server.is_alive():
            cls.server.server_cleanup()

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
        webarchiver.url_download(test_url, file_buffer)

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
        webarchiver.zip_recursive(archive_path, test_path)

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
        webarchiver.archive_remote_urls(
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
        webarchiver.archive_remote_urls(
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

    def test_get_safe_name(self):
        result = webarchiver.get_safe_name('i_/am-:un|safe? maybe,...')
        self.assertEqual('i_am-unsafe maybe,...', result)


class TestConnectorMixin(unittest.TestCase):
    """
    Testing connectors.ConnectorMixin
    """

    test_cases = [
        # 0: kwargs
        # 1: expected

        # 0th
        (
            {
                'url':    'http://google.com/',
                'params': None,
            },
            'http://google.com/'
        ),

        (
            {
                'url':    'http://google.com/?q=green+tea',
                'params': {
                    'refer': 'changwoo.pe.kr',
                    'param': 'https',
                    'token': 'test_value'
                },
            },
            'http://google.com/?q=green+tea&refer=changwoo.pe.kr&param=https&token=test_value'
        ),
    ]

    def test_create_cet_url(self):
        """
        tests connectors.ConnectorMixin.create_get_url()
        :return:
        """
        for kwargs, expected in self.test_cases:
            return_value = connectors.ConnectorMixin.create_get_url(**kwargs)

            actual_query = parse_qsl(urlparse(return_value).query)
            expected_query = parse_qsl(urlparse(expected).query)

            actual_query.sort(key=operator.itemgetter(0))
            expected_query.sort(key=operator.itemgetter(0))

            self.assertListEqual(actual_query, expected_query)


class TestConnectorsUserAgents(unittest.TestCase):
    """
    Testing connector's user agent
    """
    server = None

    @classmethod
    def setUpClass(cls):
        class UserAgentEchoHandler(BaseHTTPRequestHandler):
            """
            A dumb handler just to check headers
            """
            user_agent = ''  # stores last user agent accessed to path '/'

            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(self.headers['user-agent'])
                if self.path == '/':
                    self.__class__.user_agent = self.headers['user-agent']
                return

        cls.server = get_http_test_server_thread(UserAgentEchoHandler)
        if not cls.server.is_alive():
            cls.server.start()

    @classmethod
    def tearDownClass(cls):
        if cls.server.is_alive():
            cls.server.server_cleanup()

    def test_requests_connector(self):
        """
        Test RequestsConnector properly accepts our User-Agent header request.
        """
        cookie_file = os.path.join(os.path.dirname(__file__), 'test_cookie.cookie')
        extra_headers = {'user-agent': connectors.UserAgents.chrome()}
        connector = connectors.RequestsConnector(cookie_file, 0, extra_headers)

        connector.get('http://%s:%s' % (TEST_SERVER_ADDRESS[0], TEST_SERVER_ADDRESS[1]))
        actual_agent = self.server.httpd.RequestHandlerClass.user_agent
        expected_agent = connectors.UserAgents.chrome()

        self.assertEqual(actual_agent, expected_agent)

    def test_phantomjs_connector(self):
        """
        Test PhantomJSConnector accepts our User-agent header order properly
        """
        caps = dict(DesiredCapabilities.PHANTOMJS)
        caps['phantomjs.page.settings.userAgent'] = connectors.UserAgents.firefox()

        connector = connectors.PhantomJSConnector(
            desired_capabilities=caps,
            service_log_path=os.devnull,
        )

        connector.get('http://%s:%s' % (TEST_SERVER_ADDRESS[0], TEST_SERVER_ADDRESS[1]))
        actual_agent = self.server.httpd.RequestHandlerClass.user_agent
        expected_agent = caps['phantomjs.page.settings.userAgent']

        self.assertEqual(actual_agent, expected_agent)

        connector.disconnect()


class TestRequestsConnectorCookie(unittest.TestCase):
    """
    Test RequestConnector's cookie settings.
    """
    pass


class TestPhantomjsFactoryMixinWaits(unittest.TestCase):
    """
    Test connectors.phantomjs_factory_mixin_waits
    """
    def test(self):
        waits = connectors.phantomjs_factory_mixin_waits(
            wait=10,
            wait_method='presence_of_element_located',
            by='CSS_SELECTOR',
            expr='div.content'
        )

        self.assertTrue('wait' in waits)
        self.assertEqual(waits['wait'], 10)

        self.assertTrue('until_condition' in waits)
        self.assertTrue(isinstance(waits['until_condition'], presence_of_element_located))
        self.assertEqual(waits['until_condition'].locator[0], 'css selector')
        self.assertEqual(waits['until_condition'].locator[1], 'div.content')
