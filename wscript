APPNAME="simple-rpc"
VERSION="0.2"

def options(opt):
    opt.load("compiler_cxx")

def configure(conf):
    conf.load("compiler_cxx")
    conf.load("python")
    conf.env.USES = ""

    try:
        conf.check_python_headers()
        conf.env.USES += " PYTHON"
    except conf.errors.ConfigurationError as e:
        Logs.pprint("RED", "Python extension will not be built")

    _enable_pic(conf)
    _enable_cxx11(conf)
    _enable_debug(conf)
    _extra_warnings(conf)

    if os.getenv("RPC_STATISTICS") in ["true", "1"]:
        conf.env.append_value("CXXFLAGS", "-DRPC_STATISTICS")
        Logs.pprint("PINK", "RPC statistics enabled")

    conf.env.LIB_PTHREAD = 'pthread'
    conf.env.USES += " PTHREAD"
    conf.find_program('protoc', var='PROTOC', mandatory=False)
    if conf.env.PROTOC != []:
        Logs.pprint("PINK", "Google protocol buffer support enabled")
        conf.env.LIB_PROTOBUF = 'protobuf'
        conf.env.USES += " PROTOBUF"

def build(bld):
    _depend("pylib/simplerpcgen/rpcgen.py", "pylib/simplerpcgen/rpcgen.g", "pylib/yapps/main.py pylib/simplerpcgen/rpcgen.g")
    _depend("rlog/log_service.h", "rlog/log_service.rpc", "bin/rpcgen rlog/log_service.rpc")
    _depend("test/benchmark_service.h test/benchmark_service.py", "test/benchmark_service.rpc", "bin/rpcgen --cpp --python test/benchmark_service.rpc")
    _depend("test/test_service.h test/test_service.py", "test/test_service.rpc", "bin/rpcgen --cpp --python test/test_service.rpc")
    _depend("test/floodtest_service.h test/floodtest_service.py", "test/floodtest_service.rpc", "bin/rpcgen --cpp --python test/floodtest_service.rpc")

    bld.stlib(source=bld.path.ant_glob("base/*.cc"), target="base", includes=". base", use="PTHREAD")
    bld.stlib(source=bld.path.ant_glob("rpc/*.cc"), target="simplerpc", includes=". rpc", use=bld.env.USES)
    bld.stlib(
        source="rlog/rlog.cc",
        target="rlog",
        includes=". rlog rpc",
        use="simplerpc base %s" % bld.env.USES)

    if "PYTHON" in bld.env.USES:
        bld.shlib(
            features="pyext",
            source=bld.path.ant_glob("pylib/simplerpc/*.cc"),
            target="_pyrpc",
            includes=". rpc",
            use="simplerpc base %s" % bld.env.USES)
    else:
        Logs.pprint("RED", "Python extension will not be built")

    def _prog(source, target, includes=".", use="simplerpc base %s" % bld.env.USES):
        bld.program(source=source, target=target, includes=includes, use=use)

    _prog("test/rpcbench.cc test/benchmark_service.cc", "rpcbench")
    _prog("test/floodtest.cc test/test_service.cc", "floodtest", includes=". rlog", use=bld.env.USES + " rlog")
    _prog(bld.path.ant_glob("rlog/*.cc", excl="rlog/rlog.cc"), "rlogserver")

    test_src = bld.path.ant_glob("test/test*.cc") + bld.path.ant_glob("rlog/*.cc", excl="rlog/log_server.cc") + ["test/benchmark_service.cc"]
    if bld.env.PROTOC != []:
        _depend("test/person.pb.cc test/person.pb.h", "test/person.proto", "%s --cpp_out=test -Itest test/person.proto" % bld.env.PROTOC)
        test_src += bld.path.ant_glob("test/*.pb.cc") + bld.path.ant_glob("test/protobuf-test*.cc")
    _prog(test_src, "unittest", use="rlog %s" % bld.env.USES)

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

def _extra_warnings(conf):
    warning_flags = "-Wextra -pedantic -Wformat=2 -Wno-unused-parameter -Wshadow -Wwrite-strings -Wredundant-decls -Wmissing-include-dirs -Wno-format-nonliteral"
    if sys.platform == "darwin":
        warning_flags += " -Wno-gnu -Wstrict-prototypes -Wold-style-definition -Wnested-externs"
    conf.env.append_value("CXXFLAGS", warning_flags.split())

def _run_cmd(cmd):
    Logs.pprint('PINK', cmd)
    os.system(cmd)

def _properly_split(args):
    if args == None:
        return []
    else:
        return args.split()

def _depend(target, source, action):
    target = _properly_split(target)
    source = _properly_split(source)
    for s in source:
        if not os.path.exists(s):
            Logs.pprint('RED', "'%s' not found!" % s)
            exit(1)
    for t in target:
        if not os.path.exists(t):
            _run_cmd(action)
            return
    if not target or min([os.stat(t).st_mtime for t in target]) < max([os.stat(s).st_mtime for s in source]):
        _run_cmd(action)
