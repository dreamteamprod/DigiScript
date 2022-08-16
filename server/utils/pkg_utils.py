from pkgutil import iter_modules
import sys
from setuptools import find_packages


def find_modules(path, prefix=None):
    modules = set()
    for pkg in find_packages(path):
        modules.add(pkg)
        pkgpath = path + '/' + pkg.replace('.', '/')
        if sys.version_info.major == 3 and sys.version_info.minor < 6:
            for _, name, ispkg in iter_modules([pkgpath]):
                if not ispkg:
                    modules.add(pkg + '.' + name)
        else:
            for info in iter_modules([pkgpath]):
                if not info.ispkg:
                    modules.add(pkg + '.' + info.name)

    if not prefix:
        return modules
    return [x for x in modules if x.startswith(prefix)]


def find_end_modules(path, prefix=None):
    modules = find_modules(path, prefix)
    end_modules = []
    for module in modules:
        if not any(x for x in modules if x != module and x.startswith(module)):
            end_modules.append(module)
    return end_modules
