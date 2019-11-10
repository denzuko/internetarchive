#!/usr/bin/env python

import os
import sys
import errno

from internetarchive import search_items, download, upload, get_item

from fuse import FUSE, FuseOSError, Operations
from Passthrough import Passthrough

class iafs(Passthrough):
    def __init__(self, root, fallbackPath):
        self.root = root
        self.fallbackPath = fallbackPath
        
    # Helpers
    # =======
    def _full_path(self, partial, useFallBack=False):
        if partial.startswith("/"):
            partial = partial[1:]
        # Find out the real path. If has been requesetd for a fallback path,
        # use it
        path = primaryPath = os.path.join(
            self.fallbackPath if useFallBack else self.root, partial)
        # If the pah does not exists and we haven't been asked for the fallback path
        # try to look on the fallback filessytem
        if not os.path.exists(primaryPath) and not useFallBack:
            path = fallbackPath = os.path.join(self.fallbackPath, partial)
            # If the path does not exists neither in the fallback filesysem
            # it's likely to be a write operation, so use the primary
            # filesystem... unless the path to get the file exists in the
            # fallbackFS!
            if not os.path.exists(fallbackPath):
                ## Write opperation?
                ## Upload to the archive
                               
                ## TOOD: Upload...
                
                primaryDir = os.path.dirname(primaryPath)
                fallbackDir = os.path.dirname(fallbackPath)
                if os.path.exists(primaryDir) or not os.path.exists(fallbackDir):
                    path = primaryPath
        return path
      
    # read metadata
    def getattr(self, path, fh=None):
        full_path = self._full_path(path)
        st = get_item(full_path)
        return {
            'st_atime': st['created'],
            'st_ctime': st['created'],
            'st_mtime': st['updated'],
            'st_size': st['item_size'],
            'st_gid': 0,
            'st_uid': 0
        }
    
    def readdir(self, path, fh):
        dirents = ['.', '..']
        full_path = self._full_path(path)

        # search IA.. (ls ./nasa => ?query=nasa)
        for r in search_items(full_path)iter_as_items():
            yield r

def main(mountpoint, root, fallbackPath):
    FUSE(dfs(root, fallbackPath), mountpoint, nothreads=True,
         foreground=True, **{'allow_other': True})

if __name__ == '__main__':
    mountpoint = sys.argv[3]
    root = sys.argv[1]
    fallbackPath = sys.argv[2]
    main(mountpoint, root, fallbackPath)
