#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, AutoToolsBuildEnvironment, tools, MSBuild
import os
import shutil


class LZ4Conan(ConanFile):
    name = "lz4"
    version = "1.8.3"
    description = "Extremely Fast Compression algorithm"
    license = "BSD 2-Clause, BSD 3-Clause"
    url = "https://github.com/bincrafters/conan-lz4"
    author = "Bincrafters <bincrafters@gmail.com>"
    exports = ["LICENSE.md"]
    source_subfolder = "source_subfolder"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = "shared=False", "fPIC=True"

    def configure(self):
        del self.settings.compiler.libcxx

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    @property
    def _is_mingw_windows(self):
        return self.settings.os == "Windows" and self.settings.compiler == "gcc" and os.name == "nt"

    def build_requirements(self):
        if self._is_mingw_windows:
            self.build_requires("msys2_installer/latest@bincrafters/stable")

    def source(self):
        archive_name = "{0}-{1}".format(self.name, self.version)
        source_url = "https://github.com/lz4/lz4"
        tools.get("{0}/archive/v{1}.tar.gz".format(source_url, self.version))
        os.rename(archive_name, self.source_subfolder)

    def build_make(self):
        prefix = self.package_folder
        prefix = tools.unix_path(prefix) if self.settings.os == "Windows" else prefix
        with tools.chdir(self.source_subfolder):
            env_build = AutoToolsBuildEnvironment(self)
            if self.options.shared:
                args = ["BUILD_SHARED=yes", "BUILD_STATIC=no"]
            else:
                args = ["BUILD_SHARED=no", "BUILD_STATIC=yes"]
            env_build.make(args=args)
            env_build.make(args=["PREFIX=%s" % prefix, "install"])

            if self.settings.os == 'Macos' and self.options.shared:
                lib_dir = os.path.join(prefix, 'lib')
                old = '/usr/local/lib/liblz4.1.dylib'
                new = 'liblz4.1.dylib'
                for lib in os.listdir(lib_dir):
                    if lib.endswith('.dylib'):
                        self.run('install_name_tool -change %s %s %s' % (old, new, os.path.join(lib_dir, lib)))

    def build_vs(self):
        shutil.copy(os.path.join(self.source_subfolder, "lib", "lz4.h"),
                    os.path.join(self.source_subfolder, "visual", "VS2010", "liblz4-dll", "lz4.h"))
        # Unable to load plug-in localespc.dll
        for project in ["lz4", "liblz4", "liblz4-dll"]:
            project_name = os.path.join(self.source_subfolder, "visual", "VS2010", project, "%s.vcxproj" % project)
            tools.replace_in_file(project_name, "<RunCodeAnalysis>true</RunCodeAnalysis>", "")
            tools.replace_in_file(project_name, "<TreatWarningAsError>true</TreatWarningAsError>", "")
        with tools.chdir(os.path.join(self.source_subfolder, 'visual', 'VS2010')):
            target = 'liblz4-dll' if self.options.shared else 'liblz4'

            msbuild = MSBuild(self)
            msbuild.build(project_file="lz4.sln", targets=[target], platforms={'x86': 'Win32'})

    def build(self):
        if self.settings.compiler == "Visual Studio":
            self.build_vs()
        else:
            self.build_make()

    def package(self):
        self.copy(pattern="LICENSE", dst="license", src=self.source_subfolder)
        if self.settings.compiler == "Visual Studio":
            include_dir = os.path.join(self.source_subfolder, 'lib')
            self.copy(pattern="lz4*.h", dst="include", src=include_dir, keep_path=False)
            arch = 'Win32' if self.settings.arch == 'x86' else 'x64'
            bin_dir = os.path.join(self.source_subfolder, 'visual', 'VS2010', 'bin', '%s_%s' %
                                   (arch, self.settings.build_type))
            self.copy("*.dll", dst='bin', src=bin_dir, keep_path=False)
            self.copy("*.lib", dst='lib', src=bin_dir, keep_path=False)
        if self.settings.os == "Windows" and self.settings.compiler == "gcc":
            # MinGW doesn't support install, so copy files manually
            self.copy(pattern="*.h", src=os.path.join(self.source_subfolder, "lib"), dst="include")
            self.copy(pattern="*.a", src=os.path.join(self.source_subfolder, "lib"), dst="lib", keep_path=False)
            self.copy(pattern="*.dll", src=os.path.join(self.source_subfolder, "lib"), dst="bin", keep_path=False)
            self.copy(pattern="*.lib", src=os.path.join(self.source_subfolder, "lib"), dst="lib", keep_path=False)
            if self.options.shared:
                with tools.chdir(os.path.join(self.package_folder, "bin")):
                    shutil.move("liblz4.so.%s.dll" % self.version, "liblz4.dll")
            else:
                with tools.chdir(os.path.join(self.package_folder, "lib")):
                    shutil.move("liblz4.a", "liblz4.lib")

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
