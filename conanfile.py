#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, AutoToolsBuildEnvironment, tools
import os


class LZ4Conan(ConanFile):
    name = "lz4"
    version = "1.8.0"
    description = "Extremely Fast Compression algorithm"
    license = "BSD 2-Clause, BSD 3-Clause"
    url = "https://github.com/bincrafters/conan-lz4"
    exports = ["LICENSE.md"]
    source_subfolder = "source_subfolder"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = "shared=False"

    def configure(self):
        del self.settings.compiler.libcxx

    def source(self):
        archive_name = "{0}-{1}".format(self.name, self.version)
        source_url = "https://github.com/lz4/lz4"
        tools.get("{0}/archive/v{1}.tar.gz".format(source_url, self.version))
        os.rename(archive_name, self.source_subfolder)

    def build_make(self):
        install_dir = os.path.abspath('lz4-install')
        with tools.chdir(self.source_subfolder):
            env_build = AutoToolsBuildEnvironment(self)
            with tools.environment_append(env_build.vars):
                self.run("make")
                self.run("make DESTDIR=%s install" % install_dir)

                if self.settings.os == 'Macos' and self.options.shared:
                    lib_dir = os.path.join(install_dir, 'usr', 'local', 'lib')
                    old = '/usr/local/lib/liblz4.1.dylib'
                    new = 'liblz4.1.dylib'
                    for lib in os.listdir(lib_dir):
                        if lib.endswith('.dylib'):
                            self.run('install_name_tool -change %s %s %s' % (old, new, os.path.join(lib_dir, lib)))

    def build_vs(self):
        with tools.chdir(os.path.join(self.source_subfolder, 'visual', 'VS2010')):
            target = 'liblz4-dll' if self.options.shared else 'liblz4'

            if self.settings.compiler.runtime == 'MD':
                runtime = 'MultiThreadedDLL'
            elif self.settings.compiler.runtime == 'MDd':
                runtime = 'MultiThreadedDebugDLL'
            elif self.settings.compiler.runtime == 'MT':
                runtime = 'MultiThreaded'
            elif self.settings.compiler.runtime == 'MTd':
                runtime = 'MultiThreadedDebug'

            proj_path = os.path.join(target, '%s.vcxproj' % target)
            tools.replace_in_file(
                proj_path, 
                search='</ClCompile>',
                replace='<RuntimeLibrary>%s</RuntimeLibrary></ClCompile>' % runtime)

            sln_path = os.path.join(os.getcwd(), 'lz4.sln')
            command = tools.msvc_build_command(self.settings, sln_path, targets=[target])
            if self.settings.arch == 'x86':
                command = command.replace('/p:Platform="x86"', '/p:Platform="Win32"')
            self.run(command)
         
    def build(self):
        if self.settings.os == "Windows":
            self.build_vs()
        else:
            self.build_make()

    def package(self):
        self.copy(pattern="LICENSE", dst="license", src=self.source_subfolder)
        if self.settings.os == "Windows":
            include_dir = os.path.join(self.source_subfolder, 'lib')
            self.copy(pattern="lz4*.h", dst="include", src=include_dir, keep_path=False)
            arch = 'Win32' if self.settings.arch == 'x86' else 'x64'
            bin_dir = os.path.join(self.source_subfolder, 'visual', 'VS2010', 'bin', '%s_%s' %
                                   (arch, self.settings.build_type))
            if self.options.shared:
                self.copy("*.dll", dst='bin', src=bin_dir, keep_path=False)
            self.copy("*.lib", dst='lib', src=bin_dir, keep_path=False)
        else:
            include_dir = os.path.join('lz4-install', 'usr', 'local', 'include')
            lib_dir = os.path.join('lz4-install', 'usr', 'local', 'lib')
            self.copy(pattern="*.h", dst="include", src=include_dir, keep_path=False)
            if str(self.settings.os) in ['Macos', 'iOS', 'watchOS', 'tvOS']:
                if self.options.shared:
                    self.copy("*.dylib", dst='lib', src=lib_dir, keep_path=False)
                else:
                    self.copy("*.a", dst='lib', src=lib_dir, keep_path=False)
            elif str(self.settings.os) in ['Linux', 'Android']:
                if self.options.shared:
                    self.copy("*.so*", dst='lib', src=lib_dir, keep_path=False)
                else:
                    self.copy("*.a", dst='lib', src=lib_dir, keep_path=False)
            
    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
