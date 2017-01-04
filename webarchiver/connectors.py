from __future__ import absolute_import

# noinspection PyUnresolvedReferences
from six.moves.urllib.parse import (
    parse_qsl,
    urlencode
)

from os.path import exists as path_exists
from signal import SIGTERM
from time import sleep

# noinspection PyUnresolvedReferences
from six.moves.http_cookiejar import (
    Cookie,
    LWPCookieJar,
    LoadError,
)

from requests import request
from requests.cookies import RequestsCookieJar

from selenium.webdriver import PhantomJS
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions


def get_ec_class():
    return expected_conditions


def get_by_class():
    return By


class ConnectorMixin(object):
    """
    Connector mixin
    """
    @staticmethod
    def create_get_url(url, params=None):
        """
        Creates a url for a GET request.
        params argument is encoded and appended to url.
        Query strings already existing in the url are also preserved.
        """
        if not url:
            return ''
        if not params:
            params = {}

        query_index = url.rfind('?')
        if query_index > -1:
            params.update(parse_qsl(url[query_index + 1:]))
            url = url[:query_index]

        return url + ('' if not params else '?' + urlencode(params))


class BaseConnector(object):
    """
    Connector base class
    """

    def __init__(self, delay=3, extra_headers=None):
        """
        Keywords
        --------
        delay: mandatory halt after each response. May be zero.
        extra_headers: dict for additional request headers
        """
        self._delay = delay
        self._extra_headers = extra_headers or {}
        self.last_content = ''

    def disconnect(self):
        pass

    def request(self, url, method='GET', params=None, data=None, headers=None):
        raise NotImplemented()

    def get(self, url, params=None, headers=None):
        return self.request(url, method='GET', params=params, headers=headers)

    def post(self, url, data=None, headers=None):
        return self.request(url, method='POST', data=data, headers=headers)

    def save_last_content(self, file_name):
        with open(file_name, 'w') as f:
            f.write(self.last_content)


class RequestsConnector(BaseConnector):
    def __init__(self, cookie_file, delay=2, extra_headers=None):
        super(RequestsConnector, self).__init__(delay, extra_headers)

        self._cookie_file = cookie_file
        self._cookie_jar = RequestsCookieJar()
        self.last_response = None

        self.load_cookie()

    def request(self, url, method='GET', params=None, data=None, headers=None):
        headers = headers or {}
        headers.update(self._extra_headers)
        self.last_response = request(
            url=url,
            method=method,
            params=params,
            data=data,
            headers=headers,
            cookies=self._cookie_jar
        )
        self.last_content = self.last_response.text
        self._cookie_jar.update(self.last_response.cookies)
        sleep(self._delay)
        return self.last_content

    def save_cookie(self, cookie_path=None, **kwargs):

        cookie_path = cookie_path or self._cookie_file
        lwp_jar = LWPCookieJar()
        for item in self._cookie_jar:
            args = dict(vars(item).items())
            args['rest'] = args['_rest']
            del args['_rest']
            lwp_jar.set_cookie(Cookie(**args))
        lwp_jar.save(cookie_path, **kwargs)

    def load_cookie(self, cookie_path=None, **kwargs):

        cookie_path = cookie_path or self._cookie_file
        if path_exists(cookie_path):
            try:
                lwp_jar = LWPCookieJar()
                lwp_jar.load(cookie_path, **kwargs)
                self._cookie_jar.update(lwp_jar)
            except LoadError:
                # TODO: log error message
                pass

    def get_cookie(self, name, default=None):
        return self._cookie_jar.get(name, default)

    def set_cookie(self, name, value, **kwargs):
        self._cookie_jar.set(name, value, **kwargs)


class PhantomJSConnector(BaseConnector):
    def __init__(
            self,
            executable_path='phantomjs',
            port=0,
            desired_capabilities=DesiredCapabilities.PHANTOMJS,
            service_args=None,
            service_log_path=None,
            wait=10,
            until_condition=None
    ):
        super(BaseConnector, self).__init__()

        self.driver = PhantomJS(
            executable_path=executable_path,
            port=port,
            desired_capabilities=desired_capabilities,
            service_args=service_args,
            service_log_path=service_log_path
        )

        self.wait = wait

        self.until_condition = until_condition

        self.driver_open = True

    def __del__(self):
        self.disconnect()

    def disconnect(self):
        if isinstance(self.driver, PhantomJS) and self.driver_open:
            self.driver.close()
            self.driver.service.process.send_signal(SIGTERM)
            self.driver.quit()
            self.driver_open = False

    def get(self, url, params=None, headers=None):
        self.driver.get(url)
        if self.wait and self.until_condition:
            WebDriverWait(self.driver, self.wait).until(self.until_condition)
        self.last_content = self.driver.page_source
        return self.last_content

    def post(self, url, data=None, headers=None):
        raise NotImplemented('')

    def save_last_content(self, file_name):
        with open(file_name, 'w') as f:
            f.write(self.driver.page_source)


def phantomjs_factory(user_agent='chrome', **kwargs):
    """
    reduce log level
     service_args=["--webdriver-loglevel=SEVERE"]

    remove logging
     service_log_path=os.path.devnull
    """
    if 'desired_capabilities' not in kwargs:
        caps = dict(DesiredCapabilities.PHANTOMJS)
        caps['phantomjs.page.settings.userAgent'] = getattr(UserAgents, user_agent, UserAgents.chrome)()
        kwargs['desired_capabilities'] = caps

    connector = PhantomJSConnector(**kwargs)
    return connector


def phantomjs_factory_mixin_waits(wait, wait_method, by, expr):
    """
    factory function to be used with phantomjs_factory.
    for example,

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'my-id'))

    code is similar to:
        mixin_waits = phantomjs_factory_mixin_waits(10, 'presence_of_element_located', 'ID', 'my-id')
        connector = phantomjs_factory(phantomjs_factory_mixin_waits())

    :param wait:              wait before throwing timeout
    :param wait_method:       method of EC as string
    :param by:                attribute of By class as string
    :param expr:              string expression to be retrieved
    :return:
    """

    ec_class = get_ec_class()
    by_class = get_by_class()

    method = getattr(ec_class, wait_method)
    by_attr = getattr(by_class, by)

    if method and by_attr:
        return {
            'wait': wait,
            'until_condition': method((by_attr, expr))
        }
    raise AttributeError('wait_method or by attribute is invalid.')


class UserAgents(object):
    """
    Sample user agent strings.
    """

    @staticmethod
    def firefox():
        return 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:50.0) Gecko/20100101 Firefox/50.0'

    @staticmethod
    def chrome():
        return 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) ' + \
               'Ubuntu Chromium/53.0.2785.143 Chrome/53.0.2785.143 Safari/537.36'

    @staticmethod
    def edge():
        return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)' + \
               'Chrome/42.0.2311.135 Safari/537.36 Edge/12.246'

    @staticmethod
    def ie11():
        return 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko'
