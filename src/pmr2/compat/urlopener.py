import urlparse

from cellml.api.pmr2.urlopener import DefaultURLOpener

class LocalOpener(DefaultURLOpener):
    """
    Opener for local files.
    """

    def loadURL(self, location, headers=None):
        p = urlparse.urlparse(location)
        if not p.scheme == "":
            # assuming http/https
            return super(LocalOpener, self).loadURL(location, headers=headers)
        # should raise exception if file not found.
        with open(location) as fd:
            return fd.read()

    def validateProtocol(self, location):
        # assuming absolute paths are valid absolute local filesystem
        # paths.
        return location.startswith('/') or \
            super(LocalOpener, self).validateProtocol(location)
