import json
from collections import ChainMap, OrderedDict


class PPTxTemplateSettingsHandler:
    def __init__(self, jsonFilePath, defaults=None):
        """
        Initialize the settings handler with a JSON file and optional defaults.
        :param jsonFilePath: Path to the JSON file to load.
        :param defaults: A dictionary of default values to use if keys are missing.
        """
        self.jsonFilePath = jsonFilePath
        self.data = self._loadJson(jsonFilePath)
        self.chainMap = ChainMap(self.data, defaults or {})

    def _loadJson(self, jsonFilePath):
        """Load JSON data from a file."""
        with open(jsonFilePath, 'r') as file:
            return json.load(file)

    def _parseKeyPath(self, keyPath):
        """Convert keyPath to a list if it's a string."""
        return keyPath if isinstance(keyPath, list) else [keyPath]

    def getValue(self, keyPath, default=None):
        """
        Get the value for a key path from the ChainMap.
        :param keyPath: A string for a top-level key or a list for a nested path.
        :param default: Default value if the key path is not found.
        """
        keyPath = self._parseKeyPath(keyPath)
        value = self.chainMap
        for key in keyPath:
            if isinstance(value, ChainMap):
                value = value.maps[0]
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def setValue(self, keyPath, value):
        """
        Set the value for a key path in the primary data layer.
        :param keyPath: A string for a top-level key or a list for a nested path.
        :param value: The value to set.
        """
        keyPath = self._parseKeyPath(keyPath)
        current = self.chainMap.maps[0]
        for key in keyPath[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[keyPath[-1]] = value

    def saveToFile(self):
        """Write the current primary data layer back to the JSON file."""
        ordered_data = OrderedDict(self.chainMap.maps[0])  # Convert to OrderedDict
        with open(self.jsonFilePath, 'w') as file:
            json.dump(self.chainMap.maps[0], file, indent=4)



