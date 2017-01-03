from os import (
    chdir,
    getcwd,
    makedirs,
    walk,
)

from os.path import (
    abspath as path_abspath,
    dirname as path_dirname,
    exists as path_exists,
    join as path_join,
    isdir as path_isdir,
    relpath as path_relpath,
    splitext as path_splitext,
)

from re import compile as re_compile
from shutil import rmtree
from tarfile import open as tarfile_open
from time import sleep
# noinspection PyUnresolvedReferences
from six.moves.urllib.parse import urlparse
from zipfile import ZipFile

from requests import get as requests_get

from .connectors import UserAgents

__author__ = 'Changwoo Nam <ep6tri@hotmail.com>'
__version__ = '1.0.0a1'


def url_download(url, download_path, **kwargs):
    """
    Stores a remote path
    :param url:           url to fetch
    :param download_path: file path or file-like objects
    :param kwargs:        any keywords for Request object
    :return:
    """
    if 'headers' not in kwargs:
        kwargs['headers'] = {}

    if 'user-agent' not in kwargs['headers']:
        kwargs['headers']['user-agent'] = UserAgents.chrome()

    content = requests_get(url, **kwargs).content
    if isinstance(download_path, str):
        with open(download_path, 'wb') as f:
            f.write(content)
    elif hasattr(download_path, 'write'):
        download_path.write(content)


def zip_recursive(archive_path, target_path):
    """
    recursive zip archiving
    :param archive_path: .zip file
    :param target_path:  directory to inflate
    """
    tp = path_abspath(target_path)
    if not path_isdir(tp) or not path_exists(tp):
        raise ValueError('target_path must be a existing directory')
    current_dir = getcwd()
    root_path = path_dirname(tp)
    chdir(root_path)
    with ZipFile(archive_path, 'w') as zf:
        for dirpath, dirnames, filenames in walk(target_path):
            rel_dir = path_relpath(dirpath, root_path)
            for entry in filenames:
                zf.write(path_join(rel_dir, entry))
    chdir(current_dir)


def archive_remote_urls(download_path, title, urls, archiver='.tar.gz', cleanup=True, each_delay=0):
    """
    Downloading remote resources and archiving them as a tar or zip file.
    :param download_path: path to store. final images will be saved in <download_path>/<title>
    :param title:         episode title. Used as directory name
    :param urls:          images a list of URLs.
    :param archiver:      can be either '.tar.gz', '.zip', or empty string to skip archiving
    :param cleanup:       remove <download_path>/<title> directory after archiving
    :param each_delay:    delay after downloading each url
    :return:
    """
    safe_title = get_safe_name(title)
    save_dir = path_join(download_path, safe_title)

    if not path_exists(save_dir):
        makedirs(save_dir)
        assert path_exists(save_dir)

    sleep_index = len(urls) - 1
    for idx, url in enumerate(urls):
        ext = path_splitext(urlparse(url).path.strip('/').split('/')[-1])[1]
        path = path_join(save_dir, '%02d%s' % (idx + 1, ext))
        url_download(url=url, download_path=path)
        assert path_exists(path)
        if idx < sleep_index:
            sleep(each_delay)

    if not archiver:
        return

    archive_path = path_join(download_path, safe_title + archiver)

    if archiver == '.tar.gz':
        current_dir = getcwd()
        chdir(download_path)
        with tarfile_open(archive_path, 'w:gz', compresslevel=1) as tar:
            tar.add(safe_title)
        chdir(current_dir)
    elif archiver == '.zip':
        zip_recursive(archive_path, save_dir)
    else:
        raise AttributeError('Unsupported archive: %s' % archiver)

    assert path_exists(archive_path)

    if cleanup:
        rmtree(save_dir)


unsafe_expr = re_compile(r'[<>:\"/|?*]')  # not good characters for directory


def get_safe_name(name):
    """
    return a safe name for a directory
    :param name:
    :return:
    """
    return unsafe_expr.sub('', name)
