import fuse # for fuse_python_api
from fuse import Fuse

import argparse
import errno
import os
import stat
import sys
import syslog

#fuse.fuse_python_api = (0, 2)

class TimeMachineFS(Fuse):
    """
    A FUSE interface to interface with a time machine backup.
    """
    def __init__(self, *args, **kwargs):
        Fuse.__init__(self, *args, **kwargs)
        # keep track of open file descriptors so we can close them
        # later.
        # path => (flags => fd)
        #
        # By the docs, each (path, flags) combination will get one open
        # and one release.
        self.fds = {}

        if "hfs_path" not in kwargs:
            self.parser.error("hfs_path option required, not found")

        # Base directory -- points to a mounted HFS+ filesystem 
        self.hfs_path = kwargs['hfs_path']

        if "hostname" not in kwargs:
            self.parser_error("hd option required, not found")

        # Name of the host that we're recovering.
        self.hostname = kwargs["hostname"]

        # XXX: Should have an internal error routine that handles this
        # sorts of messages -- it's not a parser problem.
        if not self.check_options(): parser.error("invalid options")
        return

    def check_options(self):
        """
        I check to make sure that the self.hfs_path attribute points to
        a mounted filesystem that looks like a time machine
        implementation, and that the self.hostname exists.
        """
        # check that self.hfs_path exists...
        try:
            dirents = os.listdir(self.hfs_path)
        except OSError: # doesn't exist, not a directory, etc
            return False

        # ...and that it contains the private directory that we're
        # looking for.
        self.private_dir = None
        for de in dirents:
            if de.startswith(".HFS+ Private Directory Data"):
                self.private_dir = os.path.join(self.hfs_path, de)
                break

        if self.private_dir is None:
            return False

        # Now check that self.hostname is an actual hostname in the mountpoint and
        # has a Latest dir to restore
        path_to_hd = os.path.join(self.hfs_path, "Backups.backupdb", self.hostname, "Latest")
        try:
            os.stat(path_to_hd)
        except OSError:
            return False

        self.basedir = path_to_hd

        return True

    def error(self, msg):
        """
        I print an error and then exit.
        """
        print >>os.stderr, msg
        sys.exit(1)

    # FUSE API methods
    def getattr(self, path):
        """
        Return stats for path by translating it to a real path and then
        running stat on it normally.
        """
        syslog.syslog("handling getattr on %s" % path)
        return self.run_operation_on_real_path(path, os.stat)

    def getdir(self, path):
        """
        return: [[('file1', 0), ('file2', 0), ... ]]
        """
        syslog.syslog("handling getdir on %s" % path)
        entries = self.run_operation_on_real_path(path, os.listdir)
        syslog.syslog("got entries %s for %s" % (entries, path))
        if entries is not None:
            # per docs, the listdir call doesn't append the '.' or '..'
            # entries, so we have to add them ourselves.
            entries.append(".")
            entries.append("..")
        syslog.syslog("returning %s" % entries)
        return map(lambda x: (x, 0), entries)

    def statfs ( self ):
        syslog.syslog('handling statfs')
        return self.run_operation_on_real_path(path, os.statvfs)

    def open (self, path, flags):
        # Ignore flags; we're read-only, and we return an error if they
        # try to write to us.
        syslog.syslog("opening fd for %s" % path)
        fd = self.run_operation_on_real_path(path, lambda realpath: os.open(realpath, os.O_RDONLY))
        if fd is None:
            return 1

        self.fds.setdefault(path, {})[flags] = fd
        return 0

    def read ( self, path, length, offset ):
        syslog.syslog("reading data from %s" % path)
        f = self.run_operation_on_real_path(path, lambda realpath: open(realpath, "rb"))
        f.seek(offset)
        data = f.read(length)
        f.close()
        return data

    def readlink ( self, path ):
        syslog.syslog("reading link at %s" % path)
        return self.run_operation_on_real_path(path, os.readlink)

    def release(self, path, flags):
        syslog.syslog("releasing %s" % path)
        fd = self.fds[path][flags]
        os.close(fd)
        del(self.fds[path][flags])

    # The following operations aren't supported.
    def rename ( self, oldPath, newPath ):
        syslog.syslog("rename")
        return -errno.ENOSYS

    def rmdir ( self, path ):
        syslog.syslog("rmdir")
        return -errno.ENOSYS

    def mythread(self):
        syslog.syslog("mythread")
        return -errno.ENOSYS

    def chmod (self, path, mode):
        syslog.syslog("chmod")
        return -errno.ENOSYS

    def chown(self, path, uid, gid):
        syslog.syslog("chown")
        return -errno.ENOSYS

    def fsync(self, path, isFsyncFile):
        syslog.syslog("fsync")
        return -errno.ENOSYS

    def link(self, targetPath, linkPath):
        syslog.syslog("link")
        return -errno.ENOSYS

    def mkdir ( self, path, mode ):
        syslog.syslog("mkdir")
        return -errno.ENOSYS

    def mknod ( self, path, mode, dev ):
        syslog.syslog("mknod")
        return -errno.ENOSYS

    def symlink ( self, targetPath, linkPath ):
        syslog.syslog("symlink")
        return -errno.ENOSYS

    def truncate ( self, path, size ):
        syslog.syslog("truncate")
        return -errno.ENOSYS

    def unlink ( self, path ):
        syslog.syslog("unlink")
        return -errno.ENOSYS

    def utime ( self, path, times ):
        syslog.syslog("utime")
        return -errno.ENOSYS

    def write ( self, path, buf, offset ):
        syslog.syslog("write")
        return -errno.ENOSYS

    # Utility methods
    def get_real_path(self, path):
        """
        I translate a conceptual path (e.g.,
        /Users/kacarstensen/Documents/foo/bar/baz into the actual path
        (which may be something like
        /mountpoint/.HFS_private_whatever/dir_5323123/), and return that
        to my caller.
        """
        # leading /s confuse os.path.join
        if path.startswith("/"):
            path = path[1:]
        comps = os.path.split(path)
        syslog.syslog
        # Check each component for validity.
        path = self.basedir
        syslog.syslog(path)
        for comp in comps:
            syslog.syslog("considering %s" % comp)
            syslog.syslog("joining %s and %s" % (path, comp))
            candidate = os.path.join(path, comp)
            syslog.syslog("translates to candidate path %s" % candidate)
            # the candidate can be a directory, in which case we keep
            # going...
            if os.path.isdir(candidate):
                syslog.syslog("is a directory")
                path = candidate
                continue
            # otherwise, it's a file, and we need to stat it to learn
            # more about it.
            st_info = os.stat(candidate)

            # if the size is greater than 0, then it's a file.
            if st_info.st_size > 0 or st_info.st_nlink < 100:
                syslog.syslog("is a file")
                path = candidate
                continue

            # otherwise, it might be a directory disguised as a file.
            syslog.syslog("is a fake file, looking up the directory")
            new_path = os.path.join(self.private_dir, "dir_%s" % st_info.st_nlink)
            syslog.syslog("checking new path %s" % new_path)
            assert os.path.isdir(new_path)
            path = new_path

        return path

    def run_operation_on_real_path(self, path, op):
        """
        I translate my path argument into an actual path, then run the
        given callback on that path. If the operation completes and
        returns something, I return that to my caller. If the operation
        raises an exception, I return None to my caller.
        """
        syslog.syslog("asked to run an operation on %s" % path)
        realpath = self.get_real_path(path)
        syslog.syslog("this translates to real path %s" % realpath)
        result = None
        try:
            result = op(realpath)
        except OSError, e:
            syslog.syslog('got error %s' % e)
            pass
        finally:
            return result

if __name__=="__main__":
    # build an argument parser. We're looking for something that
    # handles invocations of the form:
    #   $0 mountpoint --hfs_path --hd
    parser = argparse.ArgumentParser(description="translation layer for paths on an HFS+ time machine backup")

    parser.add_argument("mountpoint", action='store')
    parser.add_argument("--hfs-path", dest='hfs_path', action='store', help='path to the HFS+ time machine filesystem')
    parser.add_argument("--hostname", dest='hostname', action='store', help='name of the host you want to mount')

    args = parser.parse_args()

    fs = TimeMachineFS(args.mountpoint, hfs_path=args.hfs_path, hostname=args.hostname)
    fs.flags = 0
    fs.multithreaded = 0
    fs.debug = True
    fs.main()