import json
from collections import ChainMap, OrderedDict
from ccpn.util.Logging import getLogger

class PPTxDataHandler:
    """
    Abstract handler for managing data with dynamic attributes via **kwargs.
    Provides utility methods for accessing, validating, and manipulating data for the PPTx template Mapper.
    """

    def __init__(self, **kwargs):
        self._data = kwargs

    def setData(self, **kwargs):
        """Set or update data using keyword arguments."""
        self._data.update(kwargs)

    def getData(self, key=None, default=None):
        """
        Retrieve data for a given key or return the entire data dictionary.
        :param key: Key to retrieve specific data.
        :param default: Default value if key is not found.
        :return: Value associated with the key or entire data dictionary.
        """
        if key is None:
            return self._data
        if key not in self._data:
            getLogger().warn(f'PPTx Data does not have the key "{key}". Returning default value.')
        return self._data.get(key, default)

    def hasData(self, key):
        """
        Check if a specific key exists in the data.
        :param key: Key to check.
        :return: True if key exists, False otherwise.
        """
        return key in self._data

    def removeData(self, key):
        """
        Remove data associated with a specific key.
        :param key: Key to remove.
        """
        if key in self._data:
            del self._data[key]

    def updateData(self, **kwargs):
        """
        Update existing data entries with new values.
        """
        self._data.update(kwargs)

    def clearData(self):
        """
        Clear all stored data.
        """
        self._data.clear()

    def validateData(self, validation_rules):
        """
        Stud. Validate the current data.
        """
        pass

    def getAttr(self, attr: str, default=None):
        """
        Retrieve a specific attribute of the class, returning a default value if it doesn't exist.
        Logs a warning if the attribute is missing.

        :param attr: Name of the attribute to retrieve.
        :param default: Value to return if the attribute does not exist.
        :return: The attribute's value if it exists, otherwise the default value.
        """
        if not hasattr(self, attr):
            getLogger().warn(f'Object {self} does not have attribute "{attr}". Returning default value.')
        return getattr(self, attr, default)

    def __repr__(self):
        return f'< PPTxDataHandler - ID: {id(self)} >'