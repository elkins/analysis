
import os
from PyQt5 import QtCore, QtGui, QtWidgets
import pandas as pd
import numpy
import re
from ccpn.ui.gui.widgets.PulldownListsForObjects import PeakListPulldown, ChemicalShiftListPulldown, ChainPulldown
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.ListWidget import ListWidgetPair
from ccpn.ui.gui.widgets.CheckBox import CheckBox
import json

from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.lib.GuiPath import PathEdit
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.FileDialog import OtherFileDialog
from ccpn.ui.gui.widgets import ButtonList
from ccpn.ui.gui.widgets.HLine import LabeledHLine
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.util.Path import aPath
from ccpn.core.DataTable import TableFrame
from ccpn.util.traits.CcpNmrTraits import Path

class MMCif_DataSelectorImporter(CcpnDialogMainWidget):
    """
    Basic setup principals of GUI based macros
    """
    FIXEDWIDTH = True
    FIXEDHEIGHT = False

    _GREY = '#888888'

    title = 'MMCif_DataSelectorImporter'

    def __init__(self, parent=None, mainWindow=None, title=title,  **kwds):

        super().__init__(parent, setLayout=True, windowTitle=title,
                         size=(500, 500), minimumSize=None, **kwds)

        if mainWindow:
            self.mainWindow = mainWindow
            self.application = mainWindow.application
            self.current = self.application.current
            self.project = mainWindow.project
            self.stateJsonPath = os.path.join(self.project.path,"state","MMCif_DataSelector.json")

        else:
            self.mainWindow = None
            self.application = None
            self.current = None
            self.project = None
            self.stateJsonPath = ""

        self._createWidgets()

        # enable the buttons

        self.setOkButton(callback=self._okCallback, tipText ='Okay', text='OK', enabled=True)
        self.setCloseButton(callback=self.reject, tipText='Close')
        self.setDefaultButton(CcpnDialogMainWidget.CLOSEBUTTON)

    def save_to_json(self, data, file_path):
        """
        Save a dictionary to a JSON file.

        Parameters:
        - data: The dictionary to be saved.
        - file_path: The path to the JSON file.
        """
        with open(file_path, 'w') as json_file:
            json.dump(data, json_file, indent=2)
        json_file.close()

    def load_from_json(self, file_path):
        """
        Load a dictionary from a JSON file.

        Parameters:
        - file_path: The path to the JSON file.

        Returns:
        - A dictionary containing the data from the JSON file.
        If the file doesn't exist, returns an empty dictionary.
        """
        if os.path.exists(file_path):
            with open(file_path, 'r') as json_file:
                print(file_path, json_file)
                data = json.load(json_file)
            return data
        else:
            # If the file doesn't exist, return an empty dictionary
            return {}

    def _getPathFromDialog(self):
        """Select a new path from using a dialog
        """
        _path = self.project.application.dataPath
        dialog = FileDialog(parent=self.mainWindow, directory=str(_path))
        dialog._show()

        if (path := dialog.selectedFile()) is not None:
            self.pathData.setText(str(path))
            self._loadRunData()

    def _createWidgets(self):
        """Make the widgets
        """

        row = 0


        pathFrame = Frame(parent=self.mainWidget, setLayout=True, grid=(row, 0), gridSpan=(1, 5))
        self.pathLabel = Label(pathFrame, text="Path to MMCif/PDBx File", grid=(row, 0), hAlign='left')
        self.pathData = PathEdit(pathFrame, grid=(row, 1), gridSpan=(1, 1), vAlign='t')
        self.pathData.setMinimumWidth(400)

        self.pathDataButton = Button(pathFrame, grid=(row, 2), callback=self._getPathFromDialog,
                                     icon='icons/directory', hPolicy='fixed')

        if os.path.exists(self.stateJsonPath):
            loaded_data = self.load_from_json(self.stateJsonPath)

            try:
                self.pathData.set(loaded_data['pathToMMCif'])
            except:
                print('No previous data')

        row += 1
        self.useChainInfo = ChainPulldown(parent=self.mainWidget,grid = (row,0))

        row += 1
        ssFrame = Frame(parent=self.mainWidget, setLayout=True, grid=(row, 0), gridSpan=(1, 5))

        self.SSLabel = Label(parent=ssFrame,
                             text="Import Secondary Structure Data",
                             grid=(0, 0), hAlign='left')

        self.SecStructCheck = CheckBox(parent=ssFrame,
                                       checked = True, grid = (0,1))

        row += 1
        self.listWidgetPair = ListWidgetPair(self.mainWidget, grid=(row, 0), gridSpan=(1, 2))


    def _okCallback(self):
        """Clicked 'OK':
        """
        print(self.listWidgetPair.rightList.getTexts())
        loopNames = self.listWidgetPair.rightList.getTexts()
        pathToMMCif = self.pathData.get()
        chain = self.useChainInfo.getSelectedObject()
        chainInfo = True

        data_to_save = {'pathToMMCif': pathToMMCif}
        # Save data to JSON file
        self.save_to_json(data_to_save, self.stateJsonPath)

        if ("_struct_conf"  in loopNames) or ("_struct_sheet_range" in loopNames) or self.SecStructCheck.isChecked():

            _struct_confDict = {}
            if chainInfo:
                for residue in chain.residues:
                    _struct_confDict[int(residue.sequenceCode)] = {}
                    _struct_confDict[int(residue.sequenceCode)]['sequenceCode']  = residue.sequenceCode
                    _struct_confDict[int(residue.sequenceCode)]['residueType']  = residue.residueType
                    _struct_confDict[int(residue.sequenceCode)]['residuePID'] = residue.pid
                    _struct_confDict[int(residue.sequenceCode)]['conf_type_id'] = "COIL"

            # user wants secondary structure data
            try:
                dfHelix = self.getLoopData(pathToMMCif, "_struct_conf")
            except:
                dfHelix = None

            try:
                dfSheet = self.getLoopData(pathToMMCif, "_struct_sheet_range")
            except:
                dfSheet = None

            print("type dfHelix", type(dfHelix), "type dfSheet", type(dfSheet))


            if dfHelix is not None:
                # Iterate over rows in the DataFrame
                print("dfHelix\n",dfHelix.tail())
                for index, row in dfHelix.iterrows():
                    # Get the relevant values from the row
                    conf_type_id = row['conf_type_id']
                    startTLC = row['beg_label_comp_id']
                    startID = row['beg_label_seq_id']
                    endTLC = row['end_label_comp_id']
                    endID = row['end_label_seq_id']
                    print(conf_type_id, startID, endID)
                    # Iterate over the range between startID and endID
                    for id in range(int(startID), int(endID) + 1):
                        # Set dictionary values for each 'id'
                        try:
                            _struct_confDict[id]['conf_type_id'] = conf_type_id
                        except:
                            print("Not found error. Likely mismatch between Chain and mmcif sequence")

            if dfSheet is not None:
                # Iterate over rows in the DataFrame
                for index, row in dfSheet.iterrows():
                    # Get the relevant values from the row
                    conf_type_id = 'STRN' # set sheet info to PDB type for Beta Strand
                    startTLC = row['beg_label_comp_id']
                    startID = row['beg_label_seq_id']
                    endTLC = row['end_label_comp_id']
                    endID = row['end_label_seq_id']

                    # Iterate over the range between startID and endID
                    for id in range(int(startID), int(endID) + 1):
                        # Set dictionary values for each 'id'
                        try:
                            _struct_confDict[id]['conf_type_id'] = conf_type_id
                        except:
                            print("Not found error. Likely mismatch between Chain and mmcif sequence")


            # Convert the nested dictionary to a Pandas DataFrame
            df1 = pd.DataFrame.from_dict(_struct_confDict, orient='index')

            # reset the index to have a separate column for the index values
            df1.reset_index(inplace=True)
            df1.rename(columns={'index': 'id'}, inplace=True)

            self.project.newDataTable(name="SecondaryStructure", data=df1, comment='Secondary Structure Data from MMCIF')


        for loopName in loopNames:
            if loopName == '_atom_site':
                from ccpn.util.StructureData import EnsembleData, averageStructure
                ensemble = EnsembleData.from_mmcif(str(pathToMMCif))
                se = self.newStructureEnsemble(name="EnsembleData", data=ensemble)

            else:
                df = self.getLoopData(pathToMMCif, loopName)
                print(df.head())

                self.project.newDataTable(name=loopName, data=df, comment='MMCif Data '+loopName)



        #if not self.project:
        #    raise RuntimeError('Project is not defined')



    def _getPathFromDialog(self):

        _currentPath = self.pathData.get()
        if len(_currentPath) > 0:
            _directory = aPath(_currentPath).parent.asString()
        else:
            _directory = self.project.application.dataPath.asString()

        dialog = OtherFileDialog(parent=self.mainWindow, _useDirectoryOnly=False, directory=_directory)
        dialog._show()
        if (path := dialog.selectedFile()) is not None:
            self.pathData.setText(str(path))
        self._updateCallback()

    def _updateCallback(self):
        pathToMMCif = self.pathData.get()
        loopNames = self.getLoopNames(pathToMMCif)
        print(loopNames)
        for x in loopNames: self.listWidgetPair.leftList.addItem(x)


    def getLoopData(self, filename, loopName) -> pd.DataFrame:
        """
        Create a Pandas DataFrame from an mmCIF file and a specified loop.
        """
        columns = []
        atomData = []
        loop_ = False
        _atom_siteLoop = False
        with open(filename) as f:
            for l in f:
                l = l.strip()
                if len(l) == 0:
                    continue  # Ignore blank lines
                if l.startswith('#'):
                    loop_ = False
                    _atom_siteLoop = False
                    continue
                if l.startswith('loop_'):
                    loop_ = True
                    _atom_siteLoop = False
                    continue
                if loop_ and l.startswith(loopName+'.'):
                    _atom_siteLoop = True
                    columns.append(l.replace(loopName+'.', "").strip())
                if _atom_siteLoop and l.startswith('#'):
                    loop_ = False
                    _atom_siteLoop = False
                if _atom_siteLoop and not l.startswith(loopName+'.'):
                    split_data = re.findall(r"'[^']*'|\S+", l)
                    split_data = [item.strip("'") for item in split_data]
                    atomData.append(split_data)

        df = pd.DataFrame(atomData, columns=columns)
        # df = df.infer_objects()  # This method returns the DataFrame with inferred data types
        df['idx'] = numpy.arange(1, df.shape[0] + 1)  # Create an 'idx' column
        df.set_index('idx', inplace=True)  # Set 'idx' as the index

        return df

    def getLoopNames(self, filename):
        print(filename)
        loopNames = []
        loop_ = False
        with open(filename) as f:
            for l in f:
                l = l.strip()
                if len(l) == 0:
                    continue  # Ignore blank lines
                if l.startswith('#'):
                    loop_ = False
                    continue
                if l.startswith('loop_'):
                    loop_ = True
                    continue
                if (loop_ == True) and (l.startswith('_')):
                    loopNames.append(l.split('.')[0])

        return list(set(loopNames))

if __name__ == '__main__':

    popup = MMCif_DataSelectorImporter(mainWindow=mainWindow)
    popup.show()
    popup.raise_()

