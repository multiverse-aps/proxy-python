from __future__ import absolute_import

try:
    from queue import Queue
except ImportError:
    from Queue import Queue  # NOQA

try:
    import urlparse as _urlparse
except ImportError:
    from urllib import parse as _urlparse  # NOQA

try:
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import HTTPError  # NOQA
