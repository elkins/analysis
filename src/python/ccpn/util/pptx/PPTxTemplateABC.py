import importlib
from abc import ABC
from ccpn.framework.Application import getProject, getApplication, getMainWindow, getCurrent
from ccpn.util.Path import aPath


class PPTxTemplateMapperABC(ABC):

    templateName = 'PresentationTemplateABC' # the name that will appear in the GUI selections
    templateEntryOrder = -1 # the order in which will appear in the GUI selections
    templateRelativePath = '' # the relative path from this file where the template is located
    slideMapping = {}

    def __init__(self, *args, **kwargs):
        self.project = getProject()
        self.application = getApplication()
        self.mainWindow = getMainWindow()
        self.current = getCurrent()
        self._data = None

    @property
    def data(self):
        return self._data

    def setData(self, **kwargs):
        self._data = {**kwargs}

    def getAbsoluteTemplatePath(self):
        # Get the module where the current class (or subclass) is defined
        moduleName = self.__class__.__module__
        module = importlib.import_module(moduleName)
        # Retrieve the file path of  the subclassed module
        thisFile = aPath(module.__file__)
        workingDir = aPath(thisFile.parent)
        absPath = workingDir / self.templateRelativePath
        return absPath

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
