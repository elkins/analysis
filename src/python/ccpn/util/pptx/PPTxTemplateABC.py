import abc
import importlib
import importlib.util
from abc import ABC
import sys
from ccpn.framework.Application import getProject, getApplication, getCurrent
from ccpn.util.Path import aPath, joinPath
from ccpn.util.pptx.PPTxTemplateSettings import PPTxTemplateSettingsHandler
from ccpn.util.pptx.PPTxWriter import *

TEMPLATE_DIR_NAME = 'pptx_templates'

class PPTxTemplateMapperABC(ABC):

    templateMapperName = 'PresentationTemplateABC' # the name that will appear in the GUI selections
    templateEntryOrder = -1 # the order in which will appear in the GUI selections
    templateResourcesFileName = '' # the template file name .pptx . The file must be in one of the resources' directory. See getAbsoluteResourcesTemplatePath
    templateSettingsFileName = '' # the path for the Settings File, .json. The file must be in one of the resources' directory. See getAbsoluteResourcesTemplatePath
    slideMapping = {}

    def __init__(self, *args, **kwargs):
        self.project = getProject()
        self.application = getApplication()
        self.current = getCurrent()
        self._data = None
        self.settingsHandler = PPTxTemplateSettingsHandler(self.getAbsoluteResourcesTemplateSettingsPath())

    @property
    def data(self):
        return self._data

    def setData(self, **kwargs):
        self._data = {**kwargs}

    @property
    def settingsData(self):
        return self.settingsHandler.data

    # @abc.abstractmethod
    def buildLayouts(self, writer):
        """
        Builds the slides based on the template mapping definitions
        """

        isValidTemplate, templateErrors = writer._validateTemplate() # move this method from writer to this class.
        if not isValidTemplate and writer._placeholderErrorPolicy == 'raise':
            raise RuntimeError(f'Detected errors while building a new Presentation from Template \n{writer._formatDefaultDict(templateErrors)}')
        else:
            for slideLayoutName in self.slideMapping:
                layoutFuncName = self.slideMapping[slideLayoutName].get(LAYOUT_GETTER, '')
                layoutFunc = getattr(self, layoutFuncName)
                if layoutFunc is not None:
                    layoutFunc(writer, slideLayoutName)

    def getAbsoluteResourcesTemplatePath(self):
        """The templates  should live in the resources' folder. The default template is in distribution folder.
         However, users can override it in their local resources folders, either at project level or .ccpn/
        Searching hierarchy levels: 1) project, 2) internal .ccpn, 3) distribution
        """
        return self._getAbsoluteResourcesFilePath(self.templateResourcesFileName)

    def getAbsoluteResourcesTemplateSettingsPath(self):
        """The default configuration settings  is in distribution folder.
         However, users can override it in their local resources folders, either at project level or .ccpn/
        Searching hierarchy levels: 1) project, 2) internal .ccpn, 3) distribution
        """
        return self._getAbsoluteResourcesFilePath(self.templateSettingsFileName)

    @staticmethod
    def _getAbsoluteResourcesFilePath(fileName):
        """_internal. Get the absolute file path for a resources file associated with the template
        Searching hierarchy levels:
        1) Search the template first in the project resources directory if it exists.
        2) Search in the internal user resources path.
        3) Search the default template in the main distribution resources directory.
        """
        from ccpn.framework.PathsAndUrls import ccpnResourcesPath, userCcpnResourcesPath, CCPN_RESOURCES_DIRECTORY

        searchPaths = []

        # 1) Project resources path
        if (project := getProject()) is not None:
            projectResourcesPath = project.projectPath / CCPN_RESOURCES_DIRECTORY / TEMPLATE_DIR_NAME
            searchPaths.append(projectResourcesPath)

        # 2) Internal user resources path
        internalResourcesDirPath = userCcpnResourcesPath / TEMPLATE_DIR_NAME
        searchPaths.append(internalResourcesDirPath)

        # 3) Default resources path
        defaultResourcesDirPath = ccpnResourcesPath / TEMPLATE_DIR_NAME
        searchPaths.append(defaultResourcesDirPath)

        # Check each path in the hierarchy and return accordingly
        for directory in searchPaths:
            absTemplateFilePath = directory / fileName
            if absTemplateFilePath.exists():
                return absTemplateFilePath

        # Raise error if the template is not found
        raise FileNotFoundError( f"File '{fileName}' not found in any of the resources directories." )

    @staticmethod
    def formatNestedDictToText(data, indentLevel=0):
        """
        Converts a nested dictionary into a readable indented string.
        :param data: The nested dictionary.
        :param indentLevel: The current level of indentation.
        :return: A formatted string.
        """
        formattedText = ""
        indent = "  " * indentLevel  # Two spaces per level
        for key, value in data.items():
            if isinstance(value, dict):
                formattedText += f"{indent}{key}:\n"
                formattedText += PPTxTemplateMapperABC.formatNestedDictToText(value, indentLevel + 1)
            else:
                formattedText += f"{indent}{key}: {value}\n"
        return formattedText


def loadPPTxTemplateMapperObjects(filePath):
    """
    Dynamically loads all PPTxTemplateMapperABC subclasses from a  given .py filePath
    :param filePath: The full path to the .py file.
    :return: List of objects that are subclasses of the PPTxTemplateMapperABC.
    """
    # Extract module name from file path
    moduleName = aPath(filePath).basename
    parentClass = PPTxTemplateMapperABC
    # Check if the module is already imported
    if moduleName in sys.modules:
        module = sys.modules[moduleName]
    else:
        # If the module is not already imported, load it dynamically
        spec = importlib.util.spec_from_file_location(moduleName, filePath)
        module = importlib.util.module_from_spec(spec)
        sys.modules[moduleName] = module
        spec.loader.exec_module(module)

    # Find all classes in the module that are subclasses of the parentClass
    subclassObjects = [
        getattr(module, name)
        for name in dir(module)
        if isinstance(getattr(module, name), type) and issubclass(getattr(module, name), parentClass) and getattr(module, name) is not parentClass
        ]

    return subclassObjects
