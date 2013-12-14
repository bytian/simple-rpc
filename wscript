APPNAME="simple-rpc"
VERSION="0.1.1"

def options(opt):
    opt.load("compiler_cxx")

def configure(conf):
    conf.load("compiler_cxx")
    conf.load("python")
    conf.check_python_headers()
    _enable_pic(conf)
    _enable_cxx11(conf)
    _enable_debug(conf)
    conf.env.LIB_PTHREAD = 'pthread'
    conf.env.INCLUDES_BASE = os.path.join(os.getcwd(), "../base-utils")
    conf.env.LIBPATH_BASE = os.path.join(os.getcwd(), "../base-utils/build")
    conf.env.LIB_BASE = 'base'
    conf.find_program('protoc', var='PROTOC', mandatory=False)
    if conf.env.PROTOC != []:
        Logs.pprint("PINK", "Google protocol buffer support enabled")
        conf.env.LIB_PROTOBUF = 'protobuf'

def build(bld):
    _depend("pylib/simplerpc/rpcgen.py", "pylib/simplerpc/rpcgen.g", "pylib/yapps/main.py pylib/simplerpc/rpcgen.g")
    _depend("rlog/log_service.h", "rlog/log_service.rpc", "bin/rpcgen rlog/log_service.rpc")
    _depend("test/benchmark_service.h", "test/benchmark_service.rpc", "bin/rpcgen test/benchmark_service.rpc")
    _depend("test/benchmark_service.py", "test/benchmark_service.rpc", "bin/rpcgen test/benchmark_service.rpc")
    _depend("test/test_service.h", "test/test_service.rpc", "bin/rpcgen test/test_service.rpc")
    _depend("test/test_service.py", "test/test_service.rpc", "bin/rpcgen test/test_service.rpc")

    bld.stlib(source=bld.path.ant_glob("rpc/*.cc"), target="simplerpc", includes="rpc", use="BASE PTHREAD")
    bld.stlib(
        source="rlog/rlog.cc",
        target="rlog",
        includes=". rlog rpc",
        use="simplerpc BASE PTHREAD")
    bld.shlib(
        features="pyext",
        source=bld.path.ant_glob("pylib/simplerpc/*.cc"),
        target="_pyrpc",
        includes=". rpc",
        use="simplerpc BASE PTHREAD PYTHON")

    def _prog(source, target, includes=".", use="simplerpc BASE PTHREAD"):
        bld.program(source=source, target=target, includes=includes, use=use)

    _prog("test/rpcbench.cc test/benchmark_service.cc", "rpcbench")
    _prog(bld.path.ant_glob("rlog/*.cc", excl="rlog/rlog.cc"), "rlogserver", use="simplerpc BASE PTHREAD")

    test_src = bld.path.ant_glob("test/test*.cc") + bld.path.ant_glob("rlog/*.cc", excl="rlog/log_server.cc") + ["test/benchmark_service.cc"]
    test_use = "rlog BASE PTHREAD"
    if bld.env.PROTOC != []:
        _depend("test/person.pb.cc", "test/person.proto", "%s --cpp_out=test -Itest test/person.proto" % bld.env.PROTOC)
        _depend("test/person.pb.h", "test/person.proto", "%s --cpp_out=test -Itest test/person.proto" % bld.env.PROTOC)
        test_src += bld.path.ant_glob("test/*.pb.cc") + bld.path.ant_glob("test/protobuf-test*.cc")
        test_use += " PROTOBUF"
    _prog(test_src, "testharness", use=test_use)

#
# waf helper code
#

import os
import sys
from waflib import Logs

# use clang++ as default compiler (for c++11 support on mac)
if sys.platform == 'darwin' and not os.environ.has_key("CXX"):
    os.environ["CXX"] = "clang++"

def _enable_pic(conf):
    conf.env.append_value("CXXFLAGS", "-fPIC")
    conf.env.append_value("LINKFLAGS", "-fPIC")

def _enable_cxx11(conf):
    Logs.pprint("PINK", "C++11 features enabled")
    if sys.platform == "darwin":
        conf.env.append_value("CXXFLAGS", "-stdlib=libc++")
        conf.env.append_value("LINKFLAGS", "-stdlib=libc++")
    conf.env.append_value("CXXFLAGS", "-std=c++0x")

def _enable_debug(conf):
    if os.getenv("DEBUG") in ["true", "1"]:
        Logs.pprint("PINK", "Debug support enabled")
        conf.env.append_value("CXXFLAGS", "-Wall -pthread -ggdb".split())
    else:
        conf.env.append_value("CXXFLAGS", "-Wall -pthread -O3 -ggdb -fno-omit-frame-pointer -DNDEBUG".split())

def _run_cmd(cmd):
    Logs.pprint('PINK', cmd)
    os.system(cmd)

def _depend(target, source, action):
    if source != None and os.path.exists(source) == False:
        Logs.pprint('RED', "'%s' not found!" % source)
        exit(1)
    if os.path.exists(target) == False or os.stat(target).st_mtime < os.stat(source).st_mtime:
        _run_cmd(action)
