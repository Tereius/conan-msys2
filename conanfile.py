from conans import ConanFile, tools
from conans.errors import ConanInvalidConfiguration
import os
import shutil


class MSYS2Conan(ConanFile):
    name = "msys2"
    description = "MSYS2 is a software distro and building platform for Windows"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "http://www.msys2.org"
    license = "MSYS license"
    topics = ("conan", "msys", "unix", "subsystem")
    version = "20200517"
    build_requires = "7z_installer/1.0@conan/stable"
    short_paths = True
    options = {"exclude_files": "ANY",  # Comma separated list of file patterns to exclude from the package
               "packages": "ANY",  # Comma separated
               "additional_packages": "ANY"}    # Comma separated
    default_options = {"exclude_files": "*/link.exe",
                       "packages": "base-devel,binutils,gcc",
                       "additional_packages": None}
    settings = "os_build", "arch_build"

    def configure(self):
        if self.settings.os_build != "Windows":
            raise ConanInvalidConfiguration("Only Windows supported")

    def source(self):
        # build tools have to download files in build method when the
        # source files downloaded will be different based on architecture or OS
        pass

    def _download(self, url):
        from six.moves.urllib.parse import urlparse
        filename = os.path.basename(urlparse(url[0]).path)
        tools.download(url=url, filename=filename)
        return filename

    @property
    def _msys_dir(self):
        return "msys64" if self.settings.arch_build == "x86_64" else "msys32"

    def build(self):
        arch = 0 if self.settings.arch_build == "x86" else 1  # index in the sources list
        url = ""
        if self.settings.arch_build == "x86":
            url = "http://repo.msys2.org/distrib/i686/msys2-base-i686-%s.tar.xz" % self.version
        elif self.settings.arch_build == "x86_64":
            url = "https://sourceforge.net/projects/msys2/files/Base/i686/msys2-base-i686-%s.tar.xz" % self.version
        filename = self._download(url)
        self.run("7z.exe x {0}".format(filename))
        os.unlink(filename)

        packages = []
        if self.options.packages:
            packages.extend(str(self.options.packages).split(","))
        if self.options.additional_packages:
            packages.extend(str(self.options.additional_packages).split(","))

        with tools.chdir(os.path.join(self._msys_dir, "usr", "bin")):
            for package in packages:
                self.run('bash -l -c "pacman -S %s --noconfirm"' % package)

        # create /tmp dir in order to avoid
        # bash.exe: warning: could not find /tmp, please create!
        tmp_dir = os.path.join(self._msys_dir, 'tmp')
        if not os.path.isdir(tmp_dir):
            os.makedirs(tmp_dir)
        tmp_name = os.path.join(tmp_dir, 'dummy')
        with open(tmp_name, 'a'):
            os.utime(tmp_name, None)

        # Prepend the PKG_CONFIG_PATH environment variable with an eventual PKG_CONFIG_PATH environment variable
        tools.replace_in_file(os.path.join(self._msys_dir, "etc", "profile"),
                              'PKG_CONFIG_PATH="', 'PKG_CONFIG_PATH="$PKG_CONFIG_PATH:')

    def package(self):
        excludes = None
        if self.options.exclude_files:
            excludes = tuple(str(self.options.exclude_files).split(","))
        self.copy("*", dst="bin", src=self._msys_dir, excludes=excludes)
        shutil.copytree(os.path.join(self.package_folder, "bin", "usr", "share", "licenses"),
                        os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        msys_root = os.path.join(self.package_folder, "bin")
        msys_bin = os.path.join(msys_root, "usr", "bin")

        self.output.info("Creating MSYS_ROOT env var : %s" % msys_root)
        self.env_info.MSYS_ROOT = msys_root

        self.output.info("Creating MSYS_BIN env var : %s" % msys_bin)
        self.env_info.MSYS_BIN = msys_bin

        self.output.info("Appending PATH env var with : " + msys_bin)
        self.env_info.path.append(msys_bin)

