
import random
import os
from os import path
from django.utils.lru_cache import lru_cache


__all__ = ['get_random_file', 'get_random_image', 'get_cached_files']


IMAGE_EXTENSIONS = ("jpg", "png", "gif", "jpeg", "bmp", "tiff", "pnga")


@lru_cache(100)
def collect_files(folders, extensions=None):
    _images = []
    for folder in folders:
        for root, dirs, files in os.walk(folder):
            for f in files:
                _, ext = path.splitext(f)
                ext = ext.strip(".").lower()
                if extensions is None or ext in extensions:
                    filename = path.join(root, f)
                    _images.append(filename)
    return _images


def get_cached_files(folders, extensions):
    if not isinstance(folders, (tuple, list)):
        folders = (folders, )
    if extensions is not None:
        extensions = tuple(extensions)
    return collect_files(tuple(folders), extensions)


def get_random_file(folders, extensions=None):
    return random.choice(get_cached_files(folders, extensions))


def get_random_image(folders):
    return get_random_file(folders, IMAGE_EXTENSIONS)

