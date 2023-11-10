from ccpn.util import Path
from ccpn.framework.PathsAndUrls import userPreferencesDirectory
import os
from ccpn.util.Logging import getLogger

def loadPipeSysModules(paths):
    """
    dynamic pipe importer. Called upon initialisation of the program for loading the registered ccpn Pipes.
    Path = path of the top dir containing the pipes files.
    Users pipes are loaded only when opening a Gui Pipeline.
    """
    import pkgutil as _pkgutil
    import traceback
    from ccpn.util.Logging import getLogger
    import sys
    from ccpn import core # keeps this . It prevents circular imports [started after refactorings]

    modules = []
    name = None

    for loader, name, isPpkg in _pkgutil.walk_packages(paths):
        if name:
            try:
                found = loader.find_module(name)
                if found:
                    if sys.modules.get(name): # already loaded.
                        continue
                    else:
                        module = found.load_module(name)
                        modules.append(module)
            except Exception as err:
                traceback.print_tb(err.__traceback__)
                getLogger().warning('Error Loading Pipe %s. %s' % (name, str(err)))
    return modules


def _fetchUserPipesPath(application=None):
    """
    get the userPipesPath from preferences if defined, otherwise it creates a dir in the .ccpn dir
    """

    defaultDirName = 'pipes'
    preferencesPipesTag = 'userPipesPath'
    if application:
        preferences = application.preferences
        if preferencesPipesTag in preferences.general:
            savedPath = preferences.general.userPipesPath
            if os.path.exists(savedPath):
                return savedPath
            else:
                path = Path.fetchDir(userPreferencesDirectory, defaultDirName)
                return path
    else:
        path = Path.fetchDir(userPreferencesDirectory, defaultDirName)
        return path


def _fetchDemoPipe():
    """
    copy template pipes from pipeline dir to a user dir

    """
    from ccpn.framework.PathsAndUrls import pipeTemplates
    from shutil import copyfile
    destDir = _fetchUserPipesPath()
    if os.path.exists(pipeTemplates):
        for templateFile in  os.listdir(pipeTemplates):
            src = os.path.join(pipeTemplates, templateFile)
            dstFile = os.path.join(destDir, templateFile)
            if not os.path.isfile(dstFile):
                try:
                    copyfile(src, dstFile)
                except Exception as err:
                    getLogger().warning(f"Fetching User's pipes. Cannot copy the file {src} to {dstFile}. Exit with error: {err}")

