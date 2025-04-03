import os, pickle, zlib
from os import path
from math import atan2, cos, sin

from PyQt5 import QtCore, QtGui, QtWidgets, QtSvg
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager
from ccpnmr.chemBuild.gui.CompoundView import CompoundView
from ccpnmr.chemBuild.gui.AtomDragWidget import AtomDragWidget
from functools import partial
from memops.qtgui.CheckButton import CheckButton
from memops.qtgui.Button import Button
from memops.qtgui.CategoryMenu import CategoryMenu
from memops.qtgui.Label import Label
from memops.qtgui.WebBrowser import WebBrowser
from memops.qtgui.FileSelect import DirectoryDialog, selectDirectory, FileType
from memops.qtgui.Menu import Menu
from memops.qtgui.PulldownList import PulldownList
from memops.qtgui.InputDialog import askString
from memops.qtgui.Table import ObjectTable, Column
from memops.qtgui.Tree import FileSystemTreePanel
from memops.qtgui.MessageDialog import showYesNo, showError
from memops.qtgui.ChemCompExportFileName import ChemCompExportDialog, NAME, CCPCODE, MOLTYPE
from ccpnmr.chemBuild.general.Constants import LINK, LINKS, ELEMENTS, CCPN_MOLTYPES
from ccpnmr.chemBuild.general.Constants import PROPERTIES_ATOM, PROPERTIES_MULTI, PROPERTIES_LINKS
from ccpnmr.chemBuild.general.Constants import MIMETYPE_ELEMENT, ELEMENT_DATA, ELEMENT_DEFAULT
from ccpnmr.chemBuild.general.Constants import MIMETYPE_COMPOUND, PI, ELEMENT_FONT, CHIRAL_FONT, CHARGE_FONT
from ccpnmr.chemBuild.general.Constants import PERIODIC_TABLE, PERIODIC_TABLE_COLORS

from ccpnmr.chemBuild.model.Compound import Compound, loadCompoundPickle
from ccpnmr.chemBuild.model.Variant import Variant
from ccpnmr.chemBuild.model.VarAtom import VarAtom
from ccpnmr.chemBuild.model.Atom import Atom
from ccpnmr.chemBuild.model.Bond import Bond, BOND_STEREO_DICT

from ccpnmr.chemBuild.exchange.Ccpn import makeChemComp, importChemComp, convertCcpnProject
from ccpnmr.chemBuild.exchange.Mol2 import makeMol2, importMol2
from ccpnmr.chemBuild.exchange.MolFile import makeMolFileV2000, importMolFileV2000
from ccpnmr.chemBuild.exchange.Pdb  import makePdb,  importPdb
from ccpnmr.chemBuild.exchange.Smiles import importSmiles
from ccpnmr.chemBuild.exchange.MMCIF  import importMmCif

# from ccpnmr.chemBuild.exchange.Inchi import makeInchi, importInchi

Qt = QtCore.Qt
Qkeys = QtGui.QKeySequence
QAction = QtWidgets.QAction
# Qconnect = QtCore.QObject.connect

CHEM_GROUP_DIR = path.join(path.dirname(path.dirname(__file__)), 'chemGroups')
ICON_DIR =  path.join(path.dirname(path.dirname(__file__)), 'icons')
EXPANDING = QtWidgets.QSizePolicy.Expanding
PREFERRED = QtWidgets.QSizePolicy.Preferred
MINIMUM = QtWidgets.QSizePolicy.Minimum
DefaultCcpCode = 'Ccp'
DOCS_PAGE='https://www.ccpn.ac.uk/api-documentation/v3/html/'

ABOUT_TEXT = """
CcpNmr ChemBuild version 1.0

CcpNmr ChemBuild is a tool to create chemical compound descriptions.

Copyright Tim Stevens and Magnus Lundborg, University of Cambridge 2010-2012
"""


class ChemBuildMain(QtWidgets.QMainWindow):

  def __init__(self, parent=None, fileName=None):
  
    QtWidgets.QMainWindow.__init__(self, parent)
    
    self.chemGroupDir = CHEM_GROUP_DIR
    self.userDir = None
    self.userLibrary = None
    self.compound = None
    self.variant = None
    
    self.cache = None
    self.history = []
    self.compoundFileName = None

    # Main menu
    
    menuBar = self.menuBar() # QtWidgets.QMenuBar()
    fileMenu = Menu(menuBar, '&File')
    editMenu = Menu(menuBar, '&Edit')
    viewMenu = Menu(menuBar, '&View')
    importMenu = Menu(menuBar, '&Import')
    exportMenu = Menu(menuBar, 'E&xport')
    helpMenu = Menu(menuBar, '&Help')
    
    # Menu items
    
    fileMenu.addItem('&New Compound', self.newCompound)
    fileMenu.addItem('&Load Compound',self.loadCompound)
    fileMenu.addItem('&Save Compound', self.saveCompound)
    fileMenu.addItem('Save Compound &As...', self.saveAs)
    fileMenu.addItem('Select &User Library', self.selectUserLibrary)
    fileMenu.addSeparator()
    fileMenu.addItem('&Quit Program', self.close)
    
    #importMenu.addItem(impCcpnProjAction)
    importMenu.addItem('CCPN ChemComp XML file', self.importChemComp)
    importMenu.addItem('MDL Molfile (v2000)', self.importMolFileV2000)
    importMenu.addItem('Mol2 (SYBYL2) file', self.importMol2)
    importMenu.addItem('PDB file', self.importPdb)
    importMenu.addItem('CIF file', self.importMmCif)

    # importMenu.addItem('InChI file', self.importInchi)
    
    exportMenu.addItem('CCPN ChemComp XML file', self.exportChemComp)
    exportMenu.addItem('MDL Molfile (v2000)', self.exportMolfile)
    exportMenu.addItem('Mol2 (SYBYL2) file', self.exportMol2)
    exportMenu.addItem('PDB file', self.exportPdb)
    # exportMenu.addItem('InChI file', self.exportInchi)
    
    formats = QtGui.QImageReader.supportedImageFormats()

    imageMenu = Menu(exportMenu, '&Image')
    imageMenu.addItem('SVG', self.exportSvg)
    imageMenu.addItem('PDF', self.exportPdf)
    if [format for format in formats if format.toLower() in (b'jpg', b'jpeg')]:
      imageMenu.addItem('JPEG pixmap', self.exportJpg)
    if [format for format in formats if format.toLower() == b'png']:
      imageMenu.addItem('PNG pixmap', self.exportPng)
    
    editMenu.addItem('Paste atoms', self.pasteAtoms)
    editMenu.addItem('Copy selected atoms', self.copyAtoms)
    editMenu.addItem('Cut selected atoms', self.cutAtoms)
    editMenu.addItem('Undo last edit', self.undo)
    editMenu.addSeparator()
    editMenu.addItem('Automatic chirality', self.toggleAutoChirality, checked=True)    
    editMenu.addSeparator()
    editMenu.addItem('Add hydrogens', self.addHydrogens)
    editMenu.addItem('Delete atoms', self.deleteAtoms)
    editMenu.addItem('Remove bonds', self.deleteBonds)
    editMenu.addItem('Auto bond', self.autoBond)
    editMenu.addItem('Auto name all atoms', self.autoNameAtoms)
    editMenu.addSeparator()
    editMenu.addItem('Flip horizontally', self.mirrorLr)
    editMenu.addItem('Flip vertically', self.mirrorUd)
    editMenu.addItem('Auto-arrange', self.minimise)
    ###editMenu.addItem('Snap to Grid', self.snapToGrid)
    
    viewMenu.addItem('Atom names', self.toggleAtomNames, checked=True)
    viewMenu.addItem('Charge symbols', self.toggleChargeSymbols, checked=True)
    viewMenu.addItem('Chirality labels', self.toggleChiralityLabels, checked=True)
    self.toggleGroupsAction =  viewMenu.addItem('NMR atom groups', self.toggleGroups, checked=True)
    viewMenu.addItem('Compound stats', self.toggleAtomStats, checked=False)
    viewMenu.addItem('Skeletal formula', self.toggleSkeletalFormula, checked=False)
    viewMenu.addSeparator()
    viewMenu.addItem('Zoom In', self.zoomIn)
    viewMenu.addItem('Zoom Out', self.zoomOut)
    viewMenu.addItem('Reset Zoom', self.zoomReset)

    helpMenu.addItem('Online documentation', self.showDoc)
    helpMenu.addItem('About ChemBuild', self.about)
   
    
    # QActions
    # File
    newAction = QAction(self.getIcon('new.png'), '&New Compound', self,
                        shortcut=Qkeys.New, triggered=self.newCompound)
    loadAction = QAction(self.getIcon('open.png'), '&Load Compound ', self,
                        shortcut=Qkeys.Open, triggered=self.loadCompound)
    saveAction = QAction(self.getIcon('save.png'), '&Save Compound', self,
                         shortcut=Qkeys.Save, triggered=self.saveCompound)
    saveAsAction = QAction('Save Compound As...', self, shortcut=Qkeys.SaveAs,
                           triggered=self.saveAs)
    quitAction = QAction('&Quit Program', self, shortcut=Qkeys.Quit,
                         triggered=self.close)
    #aboutAction = QAction('&About ChemBuild', self,
    #                      triggered=self.about)

    # Edit
    undoAction = QAction(self.getIcon('edit-undo.png'), 'Undo Last Edit', self,
                         shortcut=Qkeys.Undo, triggered=self.undo)
    copyAction = QAction(self.getIcon('edit-copy.png'), 'Copy Selected Atoms', self,
                         shortcut=Qkeys.Copy, triggered=self.copyAtoms)
    cutAction = QAction(self.getIcon('edit-cut.png'), 'Cut Selected Atoms', self,
                        shortcut=Qkeys.Cut, triggered=self.cutAtoms)
    pasteAction = QAction(self.getIcon('edit-paste.png'), 'Paste Atoms', self,
                          shortcut=Qkeys.Paste, triggered=self.pasteAtoms)
    hydrogenAction = QAction(self.getIcon('add-hydrogen.png'),
                            'Add Hydrogens', self, triggered=self.addHydrogens)
    deleteAction = QAction(self.getIcon('delete-atom.png'),
                           'Delete Atoms', self, triggered=self.deleteAtoms)
    delBondAction = QAction(self.getIcon('delete-bond.png'),
                            'Remove Bonds', self, triggered=self.deleteBonds)
    rotLeftAction = QAction(self.getIcon('object-rotate-left.png'),
                             'Rotate anticlockwise', self, triggered=self.rotateLeft)
    rotRightAction = QAction(self.getIcon('object-rotate-right.png'),
                             'Rotate clockwise', self, triggered=self.rotateRight)
    mirrorLrAction = QAction(self.getIcon('flip-horizontal.png'),
                             'Flip horizontally', self, triggered=self.mirrorLr)
    mirrorUdAction = QAction(self.getIcon('flip-vertical.png'),
                             'Flip vertically', self, triggered=self.mirrorUd)
    autoBondAction = QAction(self.getIcon('auto-bond.png'),
                             'Auto Bond', self, triggered=self.autoBond)
    minimiseAction = QAction(self.getIcon('auto-arrange.png'),
                             'Auto-arrange', self, triggered=self.minimise)
    
    # View
    
    zoomInAction = QAction(self.getIcon('zoom-in.png'),
                           'Zoom In', self, triggered=self.zoomIn)
                           
    zoomOutAction = QAction(self.getIcon('zoom-out.png'),
                            'Zoom Out', self, triggered=self.zoomOut)
                            
    zoomResetAction = QAction(self.getIcon('zoom-original.png'),
                              'Reset Zoom', self, triggered=self.zoomReset)
    
    
    
    # Toolbars
    self.fileToolbar = self.addToolBar("File Toolbar")
    self.fileToolbar.setObjectName('fileToolbar') # for state save

    self.editToolbar = self.addToolBar("Edit Toolbar")
    self.editToolbar.setObjectName('editToolbar') # for state save
    
    self.viewToolbar = self.addToolBar("View Toolbar")
    self.viewToolbar.setObjectName('viewToolbar') # for state save
    self.viewToolbar.addAction(zoomInAction)
    self.viewToolbar.addAction(zoomResetAction)
    self.viewToolbar.addAction(zoomOutAction)
    self.viewToolbar.setIconSize(QtCore.QSize(32,32))
   
    self.addToolBarBreak()

    self.fileToolbar.addAction(newAction)
    self.fileToolbar.addAction(loadAction)
    self.fileToolbar.addAction(saveAction)
    
    for action in (copyAction, cutAction, pasteAction, undoAction,
                   hydrogenAction, deleteAction, delBondAction,
                   rotLeftAction, rotRightAction,  mirrorLrAction,
                   mirrorUdAction, minimiseAction, autoBondAction):
      self.editToolbar.addAction(action)
    
    
    menuButton = QtWidgets.QPushButton(self.viewToolbar, icon=self.getIcon('display-prefs.png'))
    menuButton.setIconSize(QtCore.QSize(32,32))
    menuButton.setMenu(viewMenu)
    menuButton.setToolTip('Compound display options')
    self.viewToolbar.addWidget(menuButton)
    
    self.varMenu = CategoryMenu(self.viewToolbar, icon=self.getIcon('variants.png'),
                                callback=self.selectVar,
                                tipText='Change the current protonation, seteochemistry and link version')
    self.varMenu.setIconSize(QtCore.QSize(32,32))
    self.viewToolbar.addWidget(self.varMenu)
     
    # Shortcuts
    
    # Extra compared to standard actions
    QtWidgets.QShortcut(Qkeys("Del"), self, self.deleteAtoms)
    QtWidgets.QShortcut(Qkeys("Ctrl+Del"), self, self.deleteBonds)
    QtWidgets.QShortcut(Qkeys("Ctrl+A"), self, self.selectAll)
        
    for elem in ('C','N','H','O','P','S','I','F','B'):
      QtWidgets.QShortcut(Qkeys(elem), self, lambda e=elem:self.addAtom(e))

    # Status
    statusBar = self.statusBar()
    statusBar.showMessage("Welcome")
    
    # Widgets & layout
   
    self.splitter = QtWidgets.QSplitter(self)
    self.splitter.setObjectName('Splitter')
    self.setCentralWidget(self.splitter)

    # Left panels
    toolbox = QtWidgets.QToolBox(self)
    toolbox.setMinimumWidth(220)
    self.splitter.addWidget(toolbox)
    
    frame =  QtWidgets.QWidget(toolbox)
    toolbox.addItem(frame, self.getIcon('atom-build.png'), 'Build Atoms')
    layout = QtWidgets.QVBoxLayout(frame)
    
    box = QtWidgets.QGroupBox("Elements",  frame)
    box.setSizePolicy(MINIMUM, MINIMUM)
    grid = QtWidgets.QGridLayout(box)
    grid.setSpacing(2)
    grid.setContentsMargins(2,2,2,2)
    layout.addWidget(box)

    elemCats = list(ELEMENTS.keys())
    elemCats.sort()
    
    i = 0
    for elemCat in elemCats:
      for elem in ELEMENTS[elemCat]:
        color = ELEMENT_DATA.get(elem,  ELEMENT_DEFAULT)[1]
        elemWidget = AtomDragWidget(box, elem, MIMETYPE_ELEMENT,
                                bgColor=color, data=elem,
                                callback=self.addAtom)
        grid.addWidget(elemWidget, i // 7, i % 7)
        i += 1
    
    # Smiles button
    self.smiles = ''
    box = QtWidgets.QWidget(frame)
    
    Button(box, 'Add SMILES string', callback=self.addSmiles,
           tipText='Add the above SMILES string fragment to the current compound')
    # Button(box, 'Add InChI string', callback=self.addInchi,
    #        tipText='Add the above InChI string fragment to the current compound')

    layout.addWidget(box)
        
    # Tree panel
    compoundTree = self.tree = CompoundTree(frame, self)
    compoundTree.setObjectName('compoundTree')
    compoundTree.headerItem().setText(0, "Compound Library")
    compoundTree.setMinimumSize(150, 200)
    compoundTree.setSizePolicy(MINIMUM, EXPANDING)
    
    self.setupTree(compoundTree)
    layout.addWidget(compoundTree)


    frame =  QtWidgets.QWidget(toolbox)
    toolbox.addItem(frame, self.getIcon('periodic-table.png'), 'Periodic Table')

    grid = QtWidgets.QGridLayout(frame)
    grid.setSpacing(2)
    grid.setContentsMargins(2,2,2,2)

    for row, group in enumerate(PERIODIC_TABLE):
      for col, elem in enumerate(group):
        if elem is None:
          continue
        
        color = ELEMENT_DATA.get(elem,  ELEMENT_DEFAULT)[1]
        elemWidget = AtomDragWidget(box, elem, MIMETYPE_ELEMENT,
                                bgColor=color, data=elem,
                                callback=self.addAtom)
        grid.addWidget(elemWidget, row, col)
        
    # File Tree panel
    fileTypes = [FileType('All files', ['*.*']),
                 FileType('ChemBuild', ['*.pickle',]),
                 FileType('CCPN XML', ['*.xml']),
                 FileType('MDL Molfile', ['*.mol']),
                 FileType('SYBL2 Mol2', ['*.mol2']),
                 FileType('PDB', ['*.pdb']),
                ]
    fileTree = FileSystemTreePanel(None, fileTypes=fileTypes, callback=self.importCompoundFile)
    toolbox.addItem(fileTree, self.getIcon('file-system.png'), 'Browse Files')

    # Main panel
    compoundView = CompoundView(self)
    compoundView.setSizePolicy(EXPANDING, PREFERRED)
    self.compoundView = compoundView  
    self.splitter.addWidget(compoundView)

    
    # Properties panel

    toolbox = QtWidgets.QToolBox(self)
    toolbox.setMinimumWidth(100)
    self.splitter.addWidget(toolbox)
    
    frame = QtWidgets.QWidget(toolbox)
    toolbox.addItem(frame, self.getIcon('atom-property.png'), 'Atom Properties')

    # Simple Properties
    row = 0
    for i, (cat, properties) in enumerate(PROPERTIES_ATOM+PROPERTIES_MULTI+PROPERTIES_LINKS):
      label = Label(parent=frame, text=cat + ':', grid=(row, 0), gridSpan=(1,2))
      row += 1

      col = 0   
      for name, propText, icon, propType in properties:
        # button = Button(frame, '', lambda x=propType: self.addProperty(x), self.getIcon(icon),
        button=Button(frame, name, partial(self.addProperty, propType), self.getIcon(icon),
               tipText=propText, grid=(row,col))
        button.setStyleSheet("QPushButton { text-align: left; }")
        button.setMaximumWidth(160)
        button.setIconSize(QtCore.QSize(28,28))

        col += 1
        
        if col == 2:
          row += 1
          col = 0

      row += 1
    
    # # Advanced Properties
    #
    # label = Label(frame, 'Residue Links:', grid=(row, 0), gridSpan=(1,3))
    # row += 1
    #
    # col = 0
    # for linkText, linkType, icon,  in LINKS:
    #   button = Button(frame, linkText, partial(self.addLink, linkType), self.getIcon(icon),
    #                   tipText=linkText, grid=(row,col))
    #   button.setIconSize(QtCore.QSize(28,28))
    #   button.setStyleSheet("QPushButton { text-align: left; }")
    #   button.setMinimumWidth(buttonMinWidth)
    #   col += 1
    #
    # row += 1

    # for i, (cat, properties) in enumerate(PROPERTIES_MULTI):
    #   label = Label(frame, ' ' + cat + ':', grid=(row, 1), gridSpan=(1,3))
    #   print(cat, i, row, 'hgfd')
    #   row += 1
    #
    #   col = 0
    #   for propText, icon, propType in properties:
    #     # button = Button(frame, '', lambda x=propType: self.addProperty(x), self.getIcon(icon),
    #     text = propText.split('(')[0]
    #     button = Button(frame, text, partial(self.addProperty, propType), self.getIcon(icon),
    #                     tipText=propText, grid=(row,col))
    #     button.setIconSize(QtCore.QSize(28,28))
    #     button.setStyleSheet("QPushButton { text-align: left; }")
    #     button.setMinimumWidth(buttonMinWidth)
    #     col += 1
    #
    #   row += 1
    #
    # frame.layout().setRowStretch(row, 1)
    frame.layout().setColumnStretch(0, 2)
    frame.layout().setColumnStretch(1, 2)
    frame.layout().setColumnStretch(2, 2)

    # Var panel
    
    frame = QtWidgets.QWidget(toolbox)
    toolbox.addItem(frame, self.getIcon('variants.png'), 'Compound Variants')
    
    self.defaultVarCheckBox = CheckButton(frame, 'Current is a default form',
                                          callback=self.toggleDefaultVar, grid=(0,0))
    self.delVarButton = Button(frame, 'Delete variant', callback=self.deleteVar,
                               tipText='Removes the current variant form from the compound definition',
                               grid=(1,0))

    columns = [
      Column('ID', self.getId,
             tipText='Unique identifier for the variant'),
      Column('Name', self.getVarName,
             tipText='The variant name'),
    Column('Type', self.getType,
           tipText='Type of the chemical component'),
      Column('One Letter Code', self.getOneLetterCode,
             tipText='One-letter code for the amino acid (if applicable)'),
      Column('Three Letter Code', self.getThreeLetterCode,
             tipText='Three-letter code for the amino acid or residue'),
      Column('Polymer', self.getColPoly,
             tipText='Relative position in biopolymer chain'),
      Column('Protons', self.getColProton,
             tipText='Protonation state of variant'),
      Column('Default?', self.getColDefault, setEditValue=self.setColDefault,
             tipText='Whether the variant is a default form (for its biopolymer linking)'),
      Column('Links', self.getColLink,
             tipText='Other residue links in the variant'),
      Column('Stereo', self.getColStereo,
             tipText='Stereochemistry that distinguishes variants')
      ]

    self.varTable = ObjectTable(frame, columns, [], callback=self.selectVar, grid=(2,0))
    

    frame.layout().setRowStretch(2,2)
 
 
    # Compound info
    
    frame = QtWidgets.QWidget(toolbox)
    toolbox.addItem(frame, self.getIcon('info.png'), 'Compound Info')
    alignment = Qt.AlignTop | Qt.AlignLeft
    
    layout = QtWidgets.QVBoxLayout(frame)
    layout.setSpacing(2)
    layout.setContentsMargins(2,2,2,2)
    frame.setLayout(layout)
    
    label = QtWidgets.QLabel(frame)
    label.setText("Name:")
    label.setAlignment(alignment)
    layout.addWidget(label)
    
    self.compNameEdit = box = QtWidgets.QLineEdit(self)
    box.textChanged.connect(self.changeCompName)
    layout.addWidget(box)
    
    label = QtWidgets.QLabel(frame)
    label.setText("Ccp Code:")
    label.setAlignment(alignment)
    layout.addWidget(label)
    
    self.ccpCodeEdit = box = QtWidgets.QLineEdit(frame)
    box.textChanged.connect(self.changeCcpCode)
    layout.addWidget(box)
    
    label = QtWidgets.QLabel(frame)
    label.setText("Molecule Type:")
    label.setAlignment(alignment)
    layout.addWidget(label)
    
    self.ccpMolTypeComboBox = box = PulldownList(frame, CCPN_MOLTYPES,
                                                 callback=self.changeMolType)
    layout.addWidget(box)
    
    label = QtWidgets.QLabel(frame)
    label.setText("Details:")
    label.setAlignment(alignment)
    layout.addWidget(label)
    layout.setStretch(7,2)
    
    self.detailsEdit = box = QtWidgets.QTextEdit(frame)
    box.textChanged.connect(self.changeDetails)
    layout.addWidget(box)

    # Console

    frame = QtWidgets.QWidget(toolbox)
    toolbox.addItem(frame, self.getIcon('ipython.png'), 'IPython Console')
    alignment = Qt.AlignTop | Qt.AlignLeft

    layout = QtWidgets.QVBoxLayout(frame)
    layout.setSpacing(2)
    layout.setContentsMargins(2, 2, 2, 2)
    frame.setLayout(layout)

    label = QtWidgets.QLabel(frame)
    label.setText("Commands:")
    label.setAlignment(alignment)
    layout.addWidget(label)

    # start the kernel
    self.namespace = {

                      'mainWindow': self,
                      'getCompound': self._getCompound,
                      }

    km = QtInProcessKernelManager()
    km.start_kernel()
    km.kernel.gui = 'qt4'

    self.ipythonWidget = RichJupyterWidget(self, gui_completion='plain')

    self.ipythonWidget.kernel_manager = km
    km.kernel.shell.push(self.namespace)
    self._startChannels()
    layout.addWidget(self.ipythonWidget)

    
    self.splitter.setCollapsible(1, False)
    self.splitter.setStretchFactor(0, 0)
    self.splitter.setStretchFactor(1, 2)
    self.splitter.setStretchFactor(2, 1)
    self.splitter.setSizes([200, self.width()-440, 240])

    self.setMinimumSize(800,600)
    self.setSizePolicy(EXPANDING, EXPANDING)
    self.setUnifiedTitleAndToolBarOnMac(True)

    # Settings
    self.readSettings()
    
    if self.userDir:
      fileTree.openDir(self.userDir)
    
    # compound = None
    #
    # if fileName:
    #   compound = self.readSaveFile(fileName)
    #
    # elif self.compoundFileName:
    #   compound = self.readSaveFile(self.compoundFileName)
    #
    # if not compound:
    self.compoundFileName = None
    self.setCompound( Compound('Unnamed') )

  def _getCompound(self):
    return self.compound

  def _startChannels(self):
    self.ipythonWidget.kernel_client = self.ipythonWidget.kernel_manager.client()
    self.ipythonWidget.kernel_client.start_channels()

  def _stopChannels(self):
    self.ipythonWidget.kernel_client.stop_channels()
    self.ipythonWidget.kernel_client = None

  def getIcon(self, fileName):
  
    filePath = path.join(ICON_DIR, fileName)
    
    return QtGui.QIcon(filePath)
      
  def getColPoly(self, obj):
    
    return obj.polyLink

  def getColProton(self, obj):
    
    return obj.descriptor[0]
  
  def getColDefault(self, obj):
  
    return obj in obj.compound.defaultVars

  def setColDefault(self, obj, bool):
  
    obj.setDefault(bool)

  def getColLink(self, obj):
  
    return obj.descriptor[1]
  
  def getColStereo(self, obj):
  
    return obj.descriptor[2]

  def getId(self, obj):
    return obj._id

  def getType(self, obj):
    return obj._type

  def getFormula(self, obj):
    return obj._formula

  def getOneLetterCode(self, obj):
    return obj._one_letter_code

  def getThreeLetterCode(self, obj):
    return obj._three_letter_code

  def getPdbxProcessingSite(self, obj):
    return obj._pdbx_processing_site

  def getVarName(self, obj):
    return obj._name

  def addSmiles(self):
  
    prompt = 'Enter SMILES string to add:'
    smilesString = askString('User input', prompt, initialValue=self.smiles, parent=self)
    
    if smilesString:
      self.addToHistory()
      self.smiles = smilesString
      compound = importSmiles(smilesString)
      variant = list(compound.variants)[0]
      
      x, y = self.getAddPoint()
            
      variant.snapAtomsToGrid(ignoreHydrogens=False)
        
      self.compound.copyVarAtoms(variant.varAtoms, (x,y))
      self.compoundView.centerView()
      self.autoNameAtoms()
      self.updateAll()

  # def addInchi(self):
  #
  #   prompt = 'Enter InChI string to add:'
  #   inchiString = askString('User input', prompt, parent=self)
  #
  #   if inchiString:
  #     self.addToHistory()
  #     inchiString = ''.join(inchiString.split())
  #     # Discard non-InChI data
  #     inchiString = inchiString.split('AuxInfo')[0]
  #     # Auto chirality must be disabled until the atoms are properly placed otherwise the chirality will be erased.
  #     autoChirality = self.compoundView.autoChirality
  #     self.compoundView.autoChirality = False
  #     compound = importInchi(inchiString) # Hydrogens are also added when loading InChI
  #     if compound == None:
  #       return
  #     #self.setCompound(compound, replace = False)
  #     self.compoundView.autoChirality = autoChirality
  #
  #     variant = list(compound.variants)[0]
  #
  #     x, y = self.getAddPoint()
  #
  #     variant.snapAtomsToGrid(ignoreHydrogens=False)
  #
  #     self.compound.copyVarAtoms(variant.varAtoms, (x,y))
  #     self.compoundView.centerView()
  #     self.updateAll()
  
  def showDoc(self):

    try:
      WebBrowser(self).open(DOCS_PAGE)
    except Exception:
      print('Cannot open web-page')

  def addToHistory(self):
    
    if self.compound:
      data = pickle.dumps((self.compound, self.variant.polyLink, self.variant.descriptor), -1)
      self.history.append(zlib.compress(data, 1))
 
      if len(self.history) > 10:
        self.history = self.history[-10:]
    
  def undo(self):
  

    if self.history:
      data = self.history.pop()
      self.compound, link, desc = pickle.loads(zlib.decompress(data))
       
      if self.compound.variants:
        for var in self.compound.variants:
          if (link == var.polyLink) and (desc == var.descriptor):
            variant = var
            break
        
        else:
          variant = var
        
      else:
        variant = None
      
      self.variant = variant
      self.compoundView.setVariant(variant)
      self.updateVars()
      self.updateCompDetails()
      
  def selectUserLibrary(self):

    dirDialog = DirectoryDialog(self, caption='Select directory containing user compound library',
                                directory=self.userDir, doSave=False,
                                showDetails=False, showFiles=True)
    dirPath = dirDialog.getDirectory()
    
    if dirPath and path.exists(dirPath) and path.isdir(dirPath):
      self.userLibrary = dirPath
      self.setupTree(self.tree)
      
    elif not dirPath:
      self.userLibrary = None
      self.setupTree(self.tree)
         
  def exportJpg(self):
  
    if self.compound:
      fType = 'JPEG (*.jpg *.jpr *.jpeg)'
      dialog = QtWidgets.QFileDialog
      filePath, filtr = dialog.getSaveFileName(self,filter=fType)
      # filePath = dialog.getSaveFileName(self,filter=fType)
    
      if filePath:
        widget = self.compoundView
        pixmap = widget.grab( widget.rect())
        if not pixmap.save(filePath, 'JPEG'):
          showError('Save', "Save failed (unknown reason)", self)
  
  def exportPng(self):
  
    if self.compound:
      fType = 'PNG (*.png)'
      dialog = QtWidgets.QFileDialog
      filePath, filtr = dialog.getSaveFileName(self,filter=fType)
      # filePath = dialog.getSaveFileName(self,filter=fType)
    
      if filePath:
        widget = self.compoundView
        pixmap = QtGui.QPixmap.grabWidget(widget, widget.rect())
        if not pixmap.save(filePath, 'PNG'):
          showError('Save', "Save failed (unknown reason)", self)
  
  def exportSvg(self):
    
    if self.compound:
      printer = QtSvg.QSvgGenerator()
      
      scene = self.compoundView.scene
      
      w = scene.width()
      h = scene.height()
      paperWidth = 200
      paperHeight = paperWidth * h / w
      resolution = printer.resolution() / 25.4 # Convert the resolution to dpmm
      printer.setSize(QtCore.QSize(paperWidth*resolution, paperHeight*resolution))
      
      fType = 'SVG (*.svg)'
      dialog = QtWidgets.QFileDialog
      filePath, filtr = dialog.getSaveFileName(self,filter=fType)
      # filePath = dialog.getSaveFileName(self,filter=fType)
      
      if filePath:
        printer.setFileName(filePath)
        svgPainter = QtGui.QPainter(printer)
        oldBackground = self.compoundView.backgroundColor
        self.compoundView.backgroundColor = Qt.white
        items = list(scene.items())
        cache = [None] * len(items)
        for i, item in enumerate(items):
          cache[i] = item.cacheMode()
          item.setCacheMode(item.NoCache)
        scene.render(svgPainter)
        svgPainter.end()
        self.compoundView.backgroundColor = oldBackground
        for i in range(len(items)):
          items[i].setCacheMode(cache[i])
        
        
  def exportPdf(self):
    
    if self.compound:
      printer = QtGui.QPrinter()
      printer.setOutputFormat(QtGui.QPrinter.PdfFormat)
      printer.setPaperSize(QtGui.QPrinter.A4)
      oldRes = printer.resolution()
      newRes = 600.0
      fRes = oldRes/newRes
      printer.setResolution(newRes)
      
      
      fType = 'PDF (*.pdf)'
      dialog = QtWidgets.QFileDialog
      filePath, filtr = dialog.getSaveFileName(self,filter=fType)
      # filePath = dialog.getSaveFileName(self,filter=fType)
      
      if filePath:
        printer.setOutputFileName(filePath)
        pdfPainter = QtGui.QPainter(printer)
        oldElementFontSize = ELEMENT_FONT.pointSize()
        oldChiralFontSize = CHIRAL_FONT.pointSize()
        oldChargeFontSize = CHARGE_FONT.pointSize()
        ELEMENT_FONT.setPointSizeF(oldElementFontSize * fRes)
        CHIRAL_FONT.setPointSizeF(oldChiralFontSize * fRes)
        CHARGE_FONT.setPointSizeF(oldChargeFontSize * fRes)
        oldBackground = self.compoundView.backgroundColor
        self.compoundView.backgroundColor = Qt.white
        scene = self.compoundView.scene
        items = list(scene.items())
        cache = [None] * len(items)
        for i, item in enumerate(items):
          cache[i] = item.cacheMode()
          item.setCacheMode(item.NoCache)
        scene.render(pdfPainter)
        pdfPainter.end()
        ELEMENT_FONT.setPointSizeF(oldElementFontSize)
        CHIRAL_FONT.setPointSizeF(oldChiralFontSize)
        CHARGE_FONT.setPointSizeF(oldChargeFontSize)
        self.compoundView.backgroundColor = oldBackground
        for i in range(len(items)):
          items[i].setCacheMode(cache[i])
  
  def importCompoundFile(self, filePath, haveModKey):
    
    if path.isdir(filePath):
      return
    
    if not haveModKey:
      if not self.askSave('Importing compound: '):
        return
    
    if filePath.endswith('.pickle'):
      tryFuncs = [self.loadCompound, self.importMol2,
                  self.importMolFileV2000, self.importPdb,
                  self.importChemComp]
    elif filePath.endswith('.cif'):
      tryFuncs = [self.importMmCif]

    elif filePath.endswith('.mol2'):
      tryFuncs = [self.importMol2, self.importMolFileV2000, 
                  self.importPdb, self.importChemComp,
                  self.loadCompound]
    elif filePath.endswith('.pdb'):           
      tryFuncs = [self.importPdb, self.importMolFileV2000,
                  self.importMol2,self.importChemComp,
                  self.loadCompound]
    elif filePath.endswith('.xml'):           
      tryFuncs = [self.importChemComp, self.importPdb, 
                  self.importMolFileV2000, self.importMol2,
                  self.loadCompound]
                  
      try:
        from memops.api.Implementation import MemopsRoot
        pass
 
      except ImportError:
        tryFuncs.remove(self.importChemComp)
        
    else:  # filePath.endswith('.mol'):           
      tryFuncs = [self.importMolFileV2000, self.importMol2,
                  self.importPdb, self.importChemComp,
                  self.loadCompound]
                  
    
    msg = 'Chemical file format not understood.'
    
    for func in tryFuncs:
      # try:
        compound = func(filePath, not haveModKey)
        
        if compound and not compound.atoms:
          QtWidgets.QMessageBox.warning(self, "Load Failed", msg)
        
        else:
          self.statusBar().showMessage("Loaded %s" % filePath)
          var = self.variant
          isolated = [va for va in var.varAtoms if (va.freeValences and not va.neighbours)]
          if isolated and (len(var.varAtoms) > 1):
            msg = 'Imported file has isolated, unbound atoms. '
            msg += 'Attempt to automatically add bonds?'
            
            if showYesNo('Query', msg, self):
              n = self.compoundView.autoBond()
              while n:
                n = self.compoundView.autoBond()
        
        break

        # print(f'Error parsing file in function {func}. {err}')
        # continue
        
    else:
      QtWidgets.QMessageBox.warning(self, "Load Failed", msg)
            
                
  def importChemComp(self, filePath=None, replace=True):
    
    if not self._checkCcpnInstallation():
      return
  
    from memops.api.Implementation import MemopsRoot

    if not filePath:
      if not self.askSave('Importing compound: '):
        return
      
      fType = 'XML (*.xml)'
      dialog = QtWidgets.QFileDialog
      msg = 'Select CCPN ChemComp XML file'
      filePath, filtr = dialog.getOpenFileName(self, msg, directory=self.userDir, filter=fType)
      # filePath = dialog.getOpenFileName(self, msg, directory=self.userDir, filter=fType)
 
    if filePath:
      dirName, fileName = path.split(filePath)
      self.userDir = dirName
      rootProject = MemopsRoot(name='TempProj')
      chemComp =  rootProject.importData(filePath)
      compound = importChemComp(chemComp)
      
      variant = list(compound.variants)[0]
      
      xVals = set([va.coords[0] for va in variant.varAtoms])
      
      if len(xVals) == 1:
        variant.snapAtomsToGrid(ignoreHydrogens=False)
      
      self.setCompound(compound, replace)
      try:
        self.minimise()
      except Exception as err:
        print('Warning. Could not minimise compound. Try with the manual Auto-arrange button from the main menu.')
      return compound
  
  def importMol2(self, filePath=None, replace=True):
    

    if not filePath:
      if not self.askSave('Importing compound: '):
        return

      fType = 'MOL2 (*.mol2)'
      dialog = QtWidgets.QFileDialog
      msg = 'Select Mol2 file'
      filePath, filtr = dialog.getOpenFileName(self, msg, ddirectoryir=self.userDir, filter=fType)
      # filePath = dialog.getOpenFileName(self, msg, directory=self.userDir, filter=fType)
 
    if filePath:
      dirName, fileName = path.split(filePath)
      self.userDir = dirName
      compound = importMol2(filePath)
      self.setCompound(compound, replace)
      
      return compound

  def importPdb(self, filePath=None, replace=True):

    if not filePath:

      if not self.askSave('Importing compound: '):
        return

      fType = 'PDB (*.pdb)'
      dialog = QtWidgets.QFileDialog
      msg = 'Select PDB file'
      filePath, filtr = dialog.getOpenFileName(self, msg, directory=self.userDir, filter=fType)
      # filePath = dialog.getOpenFileName(self, msg, directory=self.userDir, filter=fType)
 
    if filePath:
      
      dirName, fileName = path.split(filePath)
      self.userDir = dirName
      compound = importPdb(filePath)
      self.setCompound(compound, replace)
      
      return compound

  def importMmCif(self, filePath=None, replace=True):
    if not filePath:
      if not self.askSave('Importing compound: '):
        return

      fType = 'MMCIF (*.cif)'
      dialog = QtWidgets.QFileDialog
      msg = 'Select MMCIF file'
      filePath, filtr = dialog.getOpenFileName(self, msg, directory=self.userDir, filter=fType)

    if filePath:
      dirName, fileName = path.split(filePath)
      self.userDir = dirName
      compound = importMmCif(filePath)
      self.setCompound(compound, replace)
      self.minimise()
      return compound

  # def importInchi(self, filePath=None, replace=True):
  #
  #   if not filePath:
  #
  #     if not self.askSave('Importing compound: '):
  #       return
  #
  #     fType = 'InChI (*.inchi)'
  #     dialog = QtWidgets.QFileDialog
  #     msg = 'Select or enter InChi file name'
  #     filePath, filtr = dialog.getOpenFileName(self, msg, directory=self.userDir, filter=fType)
  #     # filePath = dialog.getOpenFileName(self, msg, directory=self.userDir, filter=fType)
  #
  #   if filePath:
  #
  #     dirName, fileName = path.split(filePath)
  #     self.userDir = dirName
  #     fileObj = open(filePath, 'r')
  #     inchi = fileObj.read()
  #     inchi = ''.join(inchi.split())
  #     # Discard non-InChI data
  #     inchi = inchi.split('AuxInfo')[0]
  #     fileObj.close()
  #
  #
  #     # Auto chirality must be disabled until the atoms are properly placed otherwise the chirality will be erased.
  #     autoChirality = self.compoundView.autoChirality
  #     self.compoundView.autoChirality = False
  #     compound = importInchi(inchi) # Hydrogens are also added when loading InChI
  #     self.setCompound(compound, replace)
  #     self.compoundView.autoChirality = autoChirality
  #
  #     variant = list(compound.variants)[0]
  #
  #     variant.snapAtomsToGrid(ignoreHydrogens=False)
  #     self.updateAll()
  #
  #     return compound
      
  def importMolFileV2000(self, filePath=None, replace=True):
 
    if not filePath:

      if not self.askSave('Importing compound: '):
        return

      fType = 'Molfile (*.mol)'
      dialog = QtWidgets.QFileDialog
      msg = 'Select Molfile file'
      filePath, filtr = dialog.getOpenFileName(self, msg, directory=self.userDir, filter=fType)
      # filePath = dialog.getOpenFileName(self, msg, directory=self.userDir, filter=fType)
 
    if filePath:
      dirName, fileName = path.split(filePath)
      self.userDir = dirName
      compound = importMolFileV2000(filePath)
      self.setCompound(compound, replace)
      
      return compound
        
  def exportMol2(self):
    
    if self.variant:
      lines = makeMol2(self.variant)
      
      if lines:
        fType = 'MOL2 (*.mol2)'
        dialog = QtWidgets.QFileDialog
        msg = 'Select or enter Mol2 file name'
        filePath, filtr = dialog.getSaveFileName(self, msg, directory=self.userDir, filter=fType)
        # filePath = dialog.getSaveFileName(self,msg, directory=self.userDir, filter=fType)
    
        if filePath:
          dirName, fileName = path.split(filePath)
          self.userDir = dirName
          fileObj = open(filePath, 'w')
          fileObj.write(lines)
          fileObj.close()
        
  def exportMolfile(self):
    
    if self.variant:
      lines = makeMolFileV2000(self.variant)
      
      if lines:
        fType = 'Molfile (*.mol)'
        dialog = QtWidgets.QFileDialog
        msg = 'Select or enter Molfile name'
        filePath, filtr = dialog.getSaveFileName(self, msg, directory=self.userDir, filter=fType)
        # filePath = dialog.getSaveFileName(self,msg, directory=self.userDir, filter=fType)
    
        if filePath:
          dirName, fileName = path.split(filePath)
          self.userDir = dirName
          fileObj = open(filePath, 'w')
          fileObj.write(lines)
          fileObj.close()
          
  def exportPdb(self):
    
    if self.variant:
      code,  ok = QtWidgets.QInputDialog.getText(self, 'Query', 'PDB Three-letter Residue Code')
      
      if not ok:
        return
      
      if len(code) != 3:
        msg = 'Residue code must be exactly three characters'
        QtWidgets.QMessageBox.warning(self, "Abort", msg)
        return
      
      lines = makePdb(self.variant,  code)
      if lines:
        fType = 'PDB (*.pdb)'
        dialog = QtWidgets.QFileDialog
        msg = 'Select or enter PDB file name'
        #filePath, filtr = dialog.getSaveFileName(self,msg, dir=self.userDir, filter=fType)
        filePath = dialog.getSaveFileName(self,msg, directory=self.userDir, filter=fType)
    
        if len(filePath)>1:
          dirName, fileName = filePath[0], filePath[1]
          self.userDir = dirName
          fileObj = open(self.userDir, 'w')
          fileObj.write(lines)
          fileObj.close()
          
  # def exportInchi(self):
  #
  #   if self.variant:
  #     inchi = makeInchi(self.variant)
  #
  #     if inchi:
  #       fType = 'InChI (*.inchi)'
  #       dialog = QtWidgets.QFileDialog
  #       msg = 'Select or enter Inchi file name'
  #       filePath, filtr = dialog.getSaveFileName(self, msg, directory=self.userDir, filter=fType)
  #       # filePath = dialog.getSaveFileName(self,msg, directory=self.userDir, filter=fType)
  #
  #       if filePath:
  #         dirName, fileName = path.split(filePath)
  #         self.userDir = dirName
  #         fileObj = open(filePath, 'w')
  #         fileObj.write(inchi)
  #         fileObj.close()
  #     else:
  #       showError('Save', "Conversion to inchi failed (unknown reason)", self)

  def exportChemComp(self):
    
    if not self._checkCcpnInstallation():
      return
  
    from memops.api.Implementation import MemopsRoot
    from memops.format.xml import XmlIO
    from memops.format.xml import Util
    from memops.general.Io import getCcpFileString

    if self.compound:
      name = str(self.compound.name).strip()
      ccpCode = str(self.compound.ccpCode).strip()
      molType = str(self.compound.ccpMolType).strip()
      disabledMolTypes = []
      if len(self.compound.atoms)==0:
        QtWidgets.QMessageBox.warning(self, "Abort", 'Compound has no atoms')
        return

      polyLinks = set([var.polyLink for var in self.compound.variants])
      check = set(['start', 'middle', 'end'])
      if not (check & polyLinks):
        disabledMolTypes = ('protein', 'DNA', 'RNA')

      self._setDefaultCcpCode()

      data = {NAME: name, CCPCODE:ccpCode, MOLTYPE:molType}
      dialog = ChemCompExportDialog(data=data, disabledMolTypes=disabledMolTypes)
      if dialog.exec_():
        fileName = dialog.getFileName()
        guid = dialog.getName()
      else:
        return

      dirDialog = DirectoryDialog(self, caption='Select output directory ',
                                  directory=self.userDir, doSave=False,
                                  showDetails=False, showFiles=True)
      dirPath = dirDialog.getDirectory()

      if dirPath and path.exists(dirPath) and path.isdir(dirPath):
        self.userDir = dirPath

        chemComp = makeChemComp(self.compound, ccpCode, molType)
        chemComp.__dict__['guid'] = guid
        print('chemComp',chemComp.createdBy)

        streamPath = os.path.join(dirPath, fileName)
        try:

          stream = open(streamPath, 'w')
          try:
            XmlIO.saveToStream(stream, chemComp)
          finally:
            stream.close()
        except Exception as e:
          print('Error in creating ChemComp file. %s' %e)
          QtWidgets.QMessageBox.warning(self, "Error", 'File not exported')


        #XmlIO.save(dirPath, chemComp)
        msg = 'CCPN ChemComp XML file saved as "%s"' % fileName
        QtWidgets.QMessageBox.information(self, "Done", msg)

  def _checkCcpnInstallation(self):
    
    try:
      from memops.api.Implementation import MemopsRoot
      from memops.general.Io import loadProject

    except ImportError:
      msg = 'Cannot import CCPN libraries:\n'
      msg += 'CCPN is not installed or the CCPN installation directory is '
      msg += 'not mentioned in your system\'s PYTHONPATH environment variable.\n'
      msg += 'Please select CCPN installation directory.'
      QtWidgets.QMessageBox.warning(self, "Abort", msg)
 
      import sys
 
      dirPath = selectDirectory(self, 'Locate CCPN installation')
 
      if not dirPath:
        return False
 
      root, last = path.split(dirPath)
      if last != 'python':
        dirPath = path.join(dirPath, 'python')
 
      sys.path.append(dirPath)
      
      try:
        from memops.api.Implementation import MemopsRoot
        from memops.general.Io import loadProject
 
      except ImportError:
        msg = 'Cannot import CCPN libraries from %s' % dirPath
        QtWidgets.QMessageBox.warning(self, "Abort", msg)
        return False
      
      finally:
        msg = 'CCPN libraries located. To avoid further queries please set'
        msg += 'your PYTHONPATH environment variable (e.g. in shell startup script) to:\n%s' % dirPath
        QtWidgets.QMessageBox.information(self, "Success", msg)
        
      
    return True    
        
  # def importCcpnProj(self):
  #
  #   if not self._checkCcpnInstallation():
  #     return
  #
  #   dirsOnly = QtWidgets.QFileDialog.ShowDirsOnly
  #   dirDialog = QtWidgets.QFileDialog.getExistingDirectory
  #   msg = 'Select CCPN project folder'
  #   projectDirectory = dirDialog(self, msg, options=dirsOnly)
  #
  #   rootProject = loadProject(str(projectDirectory))
  #
  #   convertCcpnProject(rootProject)
    
    
    
  def setCompound(self, compound, replace=True):
  
    if compound is not self.compound:
      self.addToHistory()
      
      if replace or not self.compound:
        self.compound = compound
        variants = list(compound.variants)
        if variants:
          for variant2 in variants:
            if (variant2.polyLink == 'none') and (variant2.descriptor == 'neutral'):
              variant = variant2
              break
 
          else:
            for variant2 in variants:
              if variant2.polyLink == 'none':
                variant = variant2
                break
 
            else:
              variant = variants[0]
 
        else:
          variant =  Variant(compound)
 
        self.variant = variant
        self.compoundView.setVariant(variant)
        self.updateVars()
        self.updateCompDetails()
      
      else:
        variant = list(compound.variants)[0]
        x, y = self.getAddPoint()
        
        self.compound.copyVarAtoms(variant.varAtoms, (x,y))
        self.compoundView.centerView()
        self.updateAll()

  
  def updateVars(self):

    isDefault = False
    tableList = []
    
    if self.compound:
      if self.variant in self.compound.defaultVars:
        isDefault = True

      for var in self.compound.variants:
        poly = var.polyLink
        proton, link, stereo = var.descriptor
    
        tableList.append((poly, proton, link, stereo, var))
        
      # tableList.sort()
      tableList = [x[4] for x in tableList]
      
      
      if set(tableList) != set(self.varTable.objects):
        self.varTable.setObjects(tableList)
      else:
        self.varTable.viewport().update()
      
      texts = []
      cats = []
      for var in tableList:
        name, cat = self._getVarNameAndCategory(var)
        cats.append(cat)
        texts.append(name)
      
      if (len(texts) < 5) or (len(cats)  < 2):
        cats = None
      
      if self.variant in tableList:
        index = tableList.index(self.variant)
      else:
        index = 0
      
      self.varMenu.setData(texts, tableList, cats, index)
      
    self.defaultVarCheckBox.set(isDefault)
  
  def _getVarNameAndCategory(self, var):
  
     poly = var.polyLink       
     proton, link, stereo = var.descriptor
     
     items = [poly, proton]
     
     if link != 'none':
       items.append('links:%s' % link)
     
     if stereo == 'default':
       cat = poly
     else:
       cat = '%s:%s' % (poly,stereo)
       items.append('stereo:%s' % stereo)
     
     return '; '.join(items), cat
    
  
  def selectVar(self, variant, row=None, col=None):
    # Called by table selection and category menu
    
    if self.compound and (variant is not self.variant):
      if not variant:
        variant = self.variant
      else:
        self.variant = variant
      self.compoundView.setVariant(variant)
      self.defaultVarCheckBox.set(self.variant in self.compound.defaultVars)
      
      if row is None:
        self.varTable.setCurrentObject(variant)
      else:
        self.varMenu.select(variant)
  
  def deleteVar(self):
    
    if not self.variant:
      return
    
    name, cat = self._getVarNameAndCategory(self.variant)
    msg = 'Really delete compound variant "%s"?' % name
    variants = set(self.compound.variants)
    
    if len(variants) == 1:
      msg += ' (This will clear the compound entirely)'
    
    if showYesNo('Confirm', msg, parent=self):
      self.addToHistory()
      
      var = self.variant
      variants.remove(var)
 
      var.delete()
      
      if variants:
        self.selectVar(variants.pop())
      else:
        self.setCompound( Compound('Unnamed') )
      
      self.updateVars()

  def _getUniqueID(self):
    # Get a unique Id because Ccpnmr API cannot load two Molecules with identical Ccp code (in the same project)!
    import uuid
    _id = uuid.uuid4()
    shortID = str(_id).split('-')[0]  # _id[0] has 8 char; _id[1][2][3] have 4 chars; _id[4] has 12 chars
    return str(shortID)

  def _setDefaultCcpCode(self):
    if self.compound:
      if not self.compound.ccpCode:
        self.compound.ccpCode = self._getUniqueID()
        self.ccpCodeEdit.setText(self.compound.ccpCode)

  def updateCompDetails(self):
    
    if self.compound:
      name = self.compound.name
      ccpCode = self.compound.ccpCode or self._getUniqueID()
      molType = self.compound.ccpMolType or 'other'
      details = self.compound.details or ''
    else:
      name = ''
      ccpCode = ''
      molType = 'other'
      details = ''
    
    index = CCPN_MOLTYPES.index(molType)
    self.ccpMolTypeComboBox.setCurrentIndex(index)
    self.ccpCodeEdit.setText(ccpCode)
    self.detailsEdit.setText(details)
    self.compNameEdit.setText(name)

  def changeMolType(self, text):
    
    if self.compound:
      self.compound.ccpMolType = text or 'other'
    
  def changeCcpCode(self, text):
   
    if self.compound:
      self.compound.ccpCode = text

  def changeDetails(self):

    if self.compound:
      text = self.detailsEdit.toPlainText()
      self.compound.details = text
      
  def changeCompName(self, text):
    
    if self.compound:
      self.compound.name = text
      self.updateAll()
  
  def updateAll(self):
    
    self.compoundView.updateAll()
  
  def toggleAutoChirality(self, action):
    
    state = action
     
    if self.compound:
      self.compoundView.autoChirality = state
      if state:
        self.compoundView.autoSetChirality()
      self.updateAll()
    
  def toggleDefaultVar(self,  state):
    
    state = bool(state)
    
    if self.variant:
      self.variant.setDefault(state)
      self.updateVars()
    
  def toggleAtomNames(self, action):
    
    state = action
     
    if self.compound:
      self.compoundView.nameAtoms = state
      self.updateAll()
    
  def toggleAtomStats(self, action):
    
    state = action
     
    if self.compound:
      self.compoundView.showStats = state
      self.updateAll()
      
  def toggleSkeletalFormula(self, action):
    
    state = action
    
    if self.compound:
      self.compoundView.showSkeletalFormula = state
      self.compoundView.snapToGrid = state
      if state:
        centroidBefore = self.variant.getCentroid()
        self.variant.snapAtomsToGrid(ignoreHydrogens=False)
        centroidAfter = self.variant.getCentroid()
        diffX = centroidAfter[0]-centroidBefore[0]
        diffY = centroidAfter[1]-centroidBefore[1]
        for atom in self.variant.varAtoms:
          atom.setCoords(atom.coords[0]-diffX, atom.coords[1]-diffY, atom.coords[2])

      self.updateAll()
    
  def toggleChargeSymbols(self, action):
    
    state = action
     
    if self.compound:
      self.compoundView.showChargeSymbols = state
      self.updateAll()
      
  def toggleChiralityLabels(self, action):
    
    state = action
    
    if self.compound:
      self.compoundView.showChiralities = state
      self.updateAll()

  def toggleGroups(self, action):
    
    state = action
    
    if self.compound:
      self.compoundView.showGroups = state
      self.updateAll()

  def atomGroupsOn(self):
     
    if self.compound:
      self.toggleGroupsAction.setChecked(True)
      self.compoundView.showGroups = True
      self.updateAll()
 
  def newCompound(self):
  
    if self.askSave('Creating new compound: '):
      self.statusBar().showMessage("New Compound")

      self.compoundFileName = None
      self.setCompound( Compound('Unnamed') )


  def readSaveFile(self, fileName, replace=True):
  
    if fileName:
      msg = None
      
      if not os.path.exists(fileName):
        msg = 'Compound file "%s" does not exist' % fileName
      
      elif not os.path.isfile(fileName):
        msg = 'Location "%s" is not a regular file' % fileName
      
      elif os.stat(fileName).st_size == 0:
        msg = 'File "%s" is of zero size'% fileName
        
      elif not os.access(fileName, os.R_OK):
        msg = 'File "%s" is not readable'% fileName

      try:
        compound = loadCompoundPickle(fileName)
      except IOError:
        msg = 'Compound file "%s" could not be read.' % fileName
      except AttributeError:
        msg = 'Compound file "%s" appears to be corrupt. ' % fileName
      
      if msg:	
        QtWidgets.QMessageBox.warning(self, "Compound load failed", msg)
        return 
       
      self.statusBar().showMessage('Read Compound file %s' % fileName)
      self.setCompound(compound, replace)
      
      if replace:
        self.compoundFileName = fileName
        compound.isModified = False
      
      return compound

  def writeSaveFile(self, fileName):
  
    if fileName and self.compound:
      fileName = self.compound.save(fileName)
    
      self.writeSettings()
      self.statusBar().showMessage('Saved Compound to %s' % fileName)
      self.compoundFileName = fileName
      return True
    
    else:
      return False

  def saveCompound(self):
    
    if not self.compound:
      msg = 'Cannot save; no active compound'
      QtWidgets.QMessageBox.warning(self, "Abort", msg)
      return False
    
    if self.compoundFileName:
      return self.writeSaveFile(self.compoundFileName)
          
    else:
      return self.saveAs()
      
 
  def saveAs(self):

    if not self.compound:
      msg = 'Cannot save; no active compound'
      QtWidgets.QMessageBox.warning(self, "Abort", msg)
      return False
    
    fType = 'ChemBuild (*.pickle)'

    dialog = QtWidgets.QFileDialog
    filePath, filtr = dialog.getSaveFileName(self, directory=self.userDir, filter=fType)
    # filePath = dialog.getSaveFileName(self, directory=self.userDir, filter=fType)

    if filePath:
      dirName, fileName = path.split(filePath)
      self.userDir = dirName

      return self.writeSaveFile(filePath)
      
    else:
      return False

  def askSave(self, msg='', discardMsg='Discard without saving'):
  
    if self.compound and self.compound.atoms and self.compound.isModified:
      msg2 = 'Save or discard current compound?'
      dialog = QtWidgets.QMessageBox(self)
      dialog.setWindowTitle("Confirm")
      dialog.setText(msg)
      dialog.setInformativeText(msg2)
      dialog.setIcon(QtWidgets.QMessageBox.Question)
      dialog.setStandardButtons( QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel)
      dialog.setDefaultButton(QtWidgets.QMessageBox.Save)
      
      button = dialog.button(QtWidgets.QMessageBox.Discard)
      button.setText(discardMsg)
      
      answ = dialog.exec_()
      
      if answ == QtWidgets.QMessageBox.Save:
        return self.saveCompound() # Abort on failure
        
      elif answ == QtWidgets.QMessageBox.Cancel:
        return False # Abort
      
      else:
        return True # Discard current
    
    else:
      return True # Nothing to discard
      
  def about(self):
    
    QtWidgets.QMessageBox.about(self, "CcpNmr ChemBuild", ABOUT_TEXT)

  def loadCompound(self, filePath=None, replace=True):
    
    if not filePath:
      if not self.askSave('Loading different compound: '):
        return
      
      fType = 'ChemBuild (*.pickle)'
      dialog = QtWidgets.QFileDialog
      filePath, filtr = dialog.getOpenFileName(self, directory=self.userDir, filter=fType)
      # filePath = dialog.getOpenFileName(self, directory=self.userDir, filter=fType)

    if filePath:
      dirName, fileName = path.split(filePath)
      self.userDir = dirName
      compound = self.readSaveFile(filePath, replace)
      self.statusBar().showMessage("Load compound from %s" % filePath )
    
    else:
      compound = None
      self.statusBar().showMessage("Load compound cancelled")
   
    return compound

  def zoomIn(self):
    
    self.zoom(1.5)    
  
  def zoomOut(self):
    
    self.zoom(0.75)    
  
  def zoomReset(self):
   
    self.compoundView.resetZoom()     

  def zoom(self, fac):

    newLevel = self.compoundView.zoomLevel * fac
    if 0.5 < newLevel < 5.0:
      self.compoundView.zoomLevel = newLevel
      self.compoundView.scale(fac, fac)
    
  def getAddPoint(self):
    
    compoundView = self.compoundView
    globalPos = QtGui.QCursor.pos()
    pos = compoundView.mapFromGlobal(globalPos)
    widget = compoundView.childAt(pos)

    if widget:
      x = pos.x()
      y = pos.y()
      
    else:
      x = compoundView.width()/2.0 
      y = compoundView.height()/2.0 
    
    point = compoundView.mapToScene(x, y)
    
    return point.x(), point.y()

  def addAtom(self, element):
   
    if self.compound:
      self.addToHistory()
      
      varAtoms = self.getSelectedAtoms()
      
      if len(varAtoms) == 1:
        varAtomB = varAtoms[0]
        freeValences = []
        
        for angle in varAtomB.freeValences:
          angle = angle % (2*PI)
          
          if angle > PI:
            angle -= 2*PI
          freeValences.append(angle)
          
        if freeValences:
          if varAtomB.bonds:
            n = float(len(freeValences))
            c = sum([cos(a) for a in freeValences])/n
            s = sum([sin(a) for a in freeValences])/n
            mean = atan2(s, c)
            diffs = [(abs(a-mean), a-PI/2.0, a) for a in freeValences]
            diffs.sort()
            angle = diffs[0][2]
          
          else:
             angle = PI/2.0
          
          if element == 'H':
            bondLen = 33.0
          else:
            bondLen = 50.0  
             
          x0, y0, z0 = varAtomB.coords
          x = x0 + bondLen * sin(angle)
          y = y0 + bondLen * cos(angle)
          atom = Atom(self.compound, element, None)
          VarAtom(None, atom, coords=(x, y, 0.0))
          varAtom = self.variant.atomDict[atom]
          Bond((varAtom, varAtomB), autoVar=True)
          
        else:
          x, y = self.getAddPoint()
          atom = Atom(self.compound, element, None)
          varAtom = VarAtom(None, atom, coords=(x, y, 0.0))
        
      else:
        varAtomB = None
        x, y = self.getAddPoint()
        atom = Atom(self.compound, element, None)
        varAtom = VarAtom(None, atom, coords=(x, y, 0.0))
  
      self.updateVars()
      self.updateAll()

      for view in list(self.compoundView.selectedViews):
        view.deselect()
      
      if (atom.element == 'H') and varAtomB:
        varAtom = varAtomB
      else:
        varAtom = self.variant.atomDict[atom]
      
      view = self.compoundView.atomViews[varAtom]
      view.select()
       
      self.statusBar().showMessage("Added %s atom" % element)

      
  def addLink(self, name):

    atoms = self.getSelectedAtoms()
    
    if not atoms:
      msg = 'No atoms selected: select atoms to replace with a link'
      QtWidgets.QMessageBox.warning(self, "Failure", msg)
      return
   
    if self.variant:
      atom = self.compoundView.addLink(name, atoms)
      
      if atom:
        self.statusBar().showMessage("Added %s link" % name)
 
      
  def addProperty(self, code):
    
    varAtoms = self.getSelectedAtoms()
    
    if not varAtoms:
      msg = 'No atoms selected'
      QtWidgets.QMessageBox.warning(self, "Failure", msg)
      return
      
    if self.compound:
      self.addToHistory()
      if code == 'chiral-r':
        for atom in varAtoms:
          atom.setChirality('R')
 
      elif code == 'chiral-s':
        for atom in varAtoms:
          atom.setChirality('S')

      elif code == 'chiral-rs':
        for atom in varAtoms:
          atom.setChirality('RS')

      elif code == 'chiral-a':
        for atom in varAtoms:
          atom.setChirality('a')

      elif code == 'chiral-b':
        for atom in varAtoms:
          atom.setChirality('b')

      elif code == 'chiral-n':
        for atom in varAtoms:
          atom.setChirality(None)
 
      elif code == '+':
        for atom in varAtoms:
          charge = max(0, atom.charge) + 1
          atom.setCharge(charge)    
 
      elif code == '-':
        for atom in varAtoms:
          charge = min(0, atom.charge) - 1
          atom.setCharge(charge)
 
      elif code == 'st':
        self.toggleStereoCentres(varAtoms)

      elif code == 'st+':
        self.moveAtomsForward(varAtoms)

      elif code == 'st-':
        self.moveAtomsBackward(varAtoms)

      elif code == '0':
        for atom in varAtoms:
          atom.setCharge(0)
 
      elif code == 'v+':
        atoms = [a.atom for a in varAtoms]
        for atom in atoms:
          atom.setBaseValences(min(8, atom.baseValences+1)) 
 
      elif code == 'v-':
        atoms = [a.atom for a in varAtoms]
        for atom in atoms:
          atom.setBaseValences(max(0, atom.baseValences-1)) 
 
      elif code == 'bond-aromatic':
        atoms = set([va.atom for va in varAtoms])
        aromatic = set([va.atom for va in varAtoms if va.isAromatic()])
        nonAromatic = atoms - aromatic
        
        if aromatic:
          self.compound.unsetAromatic(aromatic)
        
        if nonAromatic:
          self.compound.setAromatic(nonAromatic)

      elif code == 'bond-dative':

        bonds = set()
        varAtoms = set([va for va in varAtoms if  va.element not in ('H', LINK)])
        
        for va in varAtoms:          
          for bond in va.bonds:
            if len(bond.varAtoms & varAtoms) == 2:
              bonds.add(bond)
          
        for bond in bonds:
          vaA, vaB = bond.varAtoms
          if bond.bondType == 'dative':
            if bond.direction is vaB:
              bond.setBondType('single')
            else:
              bond.direction = vaB
          else:
            bond.setBondType('dative')
            
            if vaA.element in 'CNPOSFClI':
               bond.direction = vaB
            elif vaB.element in 'CNPOSFClI':
               bond.direction = vaA
              
        
      elif code == 'p':
        atoms = [a.atom for a in varAtoms]
        self.atomGroupsOn()
        self.compound.setAtomsProchiral(atoms)
 
      elif code == 'e':
        atoms = [a.atom for a in varAtoms]
        self.atomGroupsOn()
        self.compound.setAtomsEquivalent(atoms)

      elif code == 'u':
        atoms = [a.atom for a in varAtoms]
        self.atomGroupsOn()
        self.compound.unsetAtomsProchiral(atoms)
        self.compound.unsetAtomsEquivalent(atoms)

      elif code == 'xv':
        removed = set()
        for atom in varAtoms:
          if (atom.element in ('H','O',LINK)):
            atom.atom.setVariable(True)
            removed.add(atom)
        
        if removed:
          varAtom = removed.pop()    
          if varAtom in self.variant.varAtoms:
            for var in self.compound.variants:
              if varAtom not in var.varAtoms:
                self.compoundView.setVariant(var)
                break

      elif code == 'xf':
        for atom in varAtoms:
          if atom.element == 'H':
            if atom.isLabile:
              atom.setLabile(False)
              atom.atom.setVariable(False)
           
            else:
              atom.setLabile(True)

      else:
        for atom in varAtoms:
          atom.chirality = None
          atom.charge = 0
          atom.setLabile(False)

        self.compound.unsetAtomsEquivalent(varAtoms)
        self.compound.unsetAtomsProchiral(varAtoms)


      self.updateAll()
  
  def readSettings(self):
    
    
    settings = QtCore.QSettings()
    state = settings.value("state", None)
    geometry = settings.value("geometry", None)
    splitter = settings.value("splitter", None)
    prevFile = settings.value("prevFile", None)
    fileDialogState = settings.value("fileDialogState", None)
    userDir = settings.value("userDir", None)
    userLibrary = settings.value("userLibrary", None)
      
    if state:
      self.restoreState(state)
    
    if geometry:
      self.restoreGeometry(geometry)

    if splitter:
      self.splitter.restoreState(splitter)

    if prevFile:
      prevFile = str(prevFile)
      if path.exists(prevFile) and path.isfile(prevFile):
        self.compoundFileName = prevFile

    if userDir:
      userDir = str(userDir)
      if path.exists(userDir) and path.isdir(userDir):
        self.userDir = userDir

    if userLibrary:
      userLibrary = str(userLibrary)
      if path.exists(userLibrary) and path.isdir(userLibrary):
        self.userLibrary = userLibrary

    # Could check for access

  def writeSettings(self):
    
    settings = QtCore.QSettings()
    settings.setValue("geometry", self.saveGeometry())
    settings.setValue("state2", self.saveState())
    settings.setValue("splitter", self.splitter.saveState())
    settings.setValue("prevFile", self.compoundFileName)
    settings.setValue("userDir", self.userDir)
    settings.setValue("userLibrary", self.userLibrary)
        
  def closeEvent(self, event): # Overwrite
    
    answer = self.askSave('Closing program: ', 'Close without saving')
    
    if answer:
      self.writeSettings()
      event.accept()
    
    else:
      event.ignore()
      
  def addHydrogens(self):
  
    variant = self.variant
    
    if variant:
      atoms = self.getSelectedAtoms()
      if not atoms:
        atoms = list(variant.varAtoms)
    
      hydrogens = self.compoundView.addHydrogens(atoms)
      n = len(hydrogens)
      
      self.autoNameHydrogens(hydrogens)
      
      if n == 1:
        msg = "Added 1 hydrogen atom"
      else:
        msg = "Added %d hydrogen atoms" % n
      
      self.statusBar().showMessage(msg)
  
  def getSelectedAtomViews(self):
  
    compound = self.compound
    
    if compound:
      return self.compoundView.selectedViews
    
    return

  def getSelectedAtoms(self):
  
    compound = self.compound
    
    if compound:
      return [v.atom for v in self.compoundView.selectedViews]
    
    return
      
  def deleteAtoms(self):  
    
    n = self.compoundView.deleteSelectedAtoms()
    
    if n:
      if n == 1:
        msg = "Deleted selected atom"
      else:
        msg = "Deleted %d selected atoms" % n
 
      self.statusBar().showMessage(msg)
  
  def deleteBonds(self):
  
    nBonds = self.compoundView.deleteBonds()
    
    if nBonds:
      if nBonds == 1:
        msg = "Deleted selected bond"
      else:
        msg = "Deleted %d selected bonds" % nBonds

      self.statusBar().showMessage(msg)


  def rotateLeft(self):
    
    if self.compound:
      self.compoundView.rotateLeft()
    
  def rotateRight(self):
    
    if self.compound:
      self.compoundView.rotateRight()
  
  def mirror(self, direction='hv'):
  
    if self.compound:
      selected = self.getSelectedAtoms()
      moveAll = False
      
      if len(selected) < 2:
        selected = self.variant.varAtoms
        moveAll = True
      
      if not selected:
        return

      cx, cy = self.compoundView.centroidAtoms(selected)
      
      if moveAll:
        for atom in self.compound.atoms:
          for varAtom in atom.varAtoms:
            x1, y1, z1 = varAtom.coords
            dx = x1-cx
            dy = y1-cy
 
            if 'h' in direction:
              varAtom.coords = (cx-dx, y1, z1)
 
            if 'v' in direction:
              varAtom.coords = (x1, cy-dy, z1)
         
        for atom in self.compound.atoms:
          for varAtom in atom.varAtoms:
            varAtom.updateValences()   
         
      else:
        for atom in selected:
          x1, y1, z1 = atom.coords
          dx = x1-cx
          dy = y1-cy
 
          if 'h' in direction:
            atom.setCoords(cx-dx, y1, z1)
 
          if 'v' in direction:
            atom.setCoords(x1, cy-dy, z1)
        
        for atom in selected:
          atom.updateValences()   
      
      self.updateAll()
              
  def mirrorLr(self):
        
    self.mirror('h')
  
  def mirrorUd(self):
  
    self.mirror('v')
  
  def setupTree(self, tree):
  
    # more recursion
    
    tree.clear()
    
    fileExt = '.pickle'
    fileExtLen = len(fileExt)
 
    chemGroupDir = self.chemGroupDir
    if not chemGroupDir:
      return
    
    isdir = path.isdir
    join = path.join
    dirNames = [(join(chemGroupDir, x), x, self.tree) for x in os.listdir(chemGroupDir)]
    
    dirNames = [x for x in dirNames if isdir(x[0]) and not x[1].startswith('.')]
    dirNames.sort()
    
    if self.userLibrary:
      dirNames.append((self.userLibrary, 'User Library', self.tree))
    
    while dirNames:
      
      dirPath, dirName, parent = dirNames.pop(0)
      
      letters = []
      for char in dirName:
        if char == char.upper():
          letters.append(' ')
        
        letters.append(char)
      
      letters[0] = letters[0].upper()
      
      contents = os.listdir(dirPath)
      contents.sort()
      
      fileNames = [f for f in contents if f.endswith(fileExt)] 
      
      dirNamesB = [(join(dirPath, x), x) for x in contents]
      dirNamesB = [x for x in dirNamesB if isdir(x[0]) and not x[1].startswith('.')]
      dirNamesB.sort()
      
      if not (fileNames or dirNamesB):
        continue
      
      category = QtWidgets.QTreeWidgetItem(parent)
      category.setText(0, ''.join(letters))
      category.setData(0, 1, None)
      
      dirNamesB = [(a,b, category) for a,b in dirNamesB]
      dirNames = dirNamesB + dirNames
      
      for fileName in fileNames:
        filePath = join(dirPath,fileName)
      
        name = fileName[:-fileExtLen]
        item = QtWidgets.QTreeWidgetItem(category)
        item.setText(0, name)
        #item.setIcon(0, Icon('icons/list-add.png'))
        item.setData(0, 32, filePath)
      
  
  def addCompound(self, compoundB):
  
    compound = self.compound
    variant = self.variant
    
    if compound and compoundB:
      self.addToHistory()
    
      globalPos = QtGui.QCursor.pos()
      widget = self.childAt(self.mapFromGlobal(globalPos))
      selectAtoms = []

      if widget is self.compoundView:
        pos = self.compoundView.mapFromGlobal(globalPos)
        x = pos.x() - 25
        y = pos.y() - 25
      else:
        x, y = self.getAddPoint()
      
      selectAtoms = compound.copyCompound(compoundB, (x,y), refVar=variant)
 
      self.compoundView.centerView()
      self.updateAll()
      self.updateVars()
      
      for view in list(self.compoundView.selectedViews):
        view.deselect()

      viewDict = self.compoundView.atomViews
      for atom in selectAtoms:
        viewDict[atom].select()
      
      if len(selectAtoms) == 1:
        msg = "Added 1 atom"
      else:
        msg = "Added %d atoms" % len(selectAtoms)

      self.statusBar().showMessage(msg)

  def copyAtoms(self):
  
    atoms = self.getSelectedAtoms()
    if atoms:
      self.cache = Variant(Compound('Atom Selection'), atoms)
      
      if len(atoms) == 1:
        msg = "Copied 1 atom"
      else:
        msg = "Copied %d atoms" % len(atoms)

      self.statusBar().showMessage(msg)
  
  def cutAtoms(self):
    
    atoms = self.getSelectedAtoms()
    if atoms:
      self.addToHistory()
      self.cache = Variant(Compound('Atom Selection'), atoms)
      
      for view in list(self.getSelectedAtomViews()):
        view.delete()
      
      if len(atoms) == 1:
        msg = "Cut 1 atom"
      else:
        msg = "Cut %d atoms" % len(atoms)

      self.statusBar().showMessage(msg)
      self.updateAll()
  
  def pasteAtoms(self):
    
    compound = self.compound
    if compound and self.cache:
      self.addToHistory()
      globalPos = QtGui.QCursor.pos()
      widget = self.childAt(self.mapFromGlobal(globalPos))

      if widget is self.compoundView:
        pos = self.compoundView.mapFromGlobal(globalPos)
        x = pos.x() - 25
        y = pos.y() - 25
      else:
        x, y = self.getAddPoint()
 
      atoms = self.cache.varAtoms
      compound.copyVarAtoms(atoms, (x,y))
      
      if len(atoms) == 1:
        msg = "Pasted 1 atom"
      else:
        msg = "Pasted %d atoms" % len(atoms)

      self.statusBar().showMessage(msg)
      self.updateAll()
      self.updateVars()
      
  def selectAll(self):

    for atomView in list(self.compoundView.atomViews.values()):
      atomView.select()
  
  def autoBond(self):
     
    n = self.compoundView.autoBond()
    msg = "Made %d bonds" % n

    self.statusBar().showMessage(msg)
  
  def moveAtomsForward(self, varAtoms):
    
    self.moveStereoAtom(varAtoms, True)
    
  def moveAtomsBackward(self, varAtoms):
    
    self.moveStereoAtom(varAtoms, False)
  
  def moveStereoAtom(self, varAtoms, moveForward=True):

    if varAtoms:
      self.addToHistory()
      
      allCentres = []
      stereoCentres = []
      unsetCentres = []
      
      if len(varAtoms) == 1:
        scope = varAtoms[0].neighbours
        
      elif len(varAtoms) == 2:
        if varAtoms[0] in varAtoms[1].neighbours:
          scope = set(varAtoms)
        else:
          scope = set(varAtoms[0].neighbours) & set(varAtoms[1].neighbours)
      
      else:
        scope = set(self.variant.varAtoms) - set(varAtoms)
      
      used = set()
      for varAtom in varAtoms:
        for varAtom2 in varAtom.neighbours:
          if varAtom2 not in scope:
            continue
          
          if 3 < len(varAtom2.neighbours) < 8:
            allCentres.append(varAtom2)
            used.add(varAtom)  
            
            if varAtom2.stereo:
              stereoCentres.append(varAtom2)
            else:
              unsetCentres.append(varAtom2)
              
              
      if not allCentres:
        msg = 'Selected atom(s) must be next to a stereo centre'
        QtWidgets.QMessageBox.warning(self, "Failure", msg)
        return
      
      if stereoCentres:
        if unsetCentres:
          for centre in stereoCentres:
            if moveForward:
              if centre.stereo[3] not in used:
                break
            
            elif centre.stereo[1] not in used:
              break
          
          else:    
            index = allCentres.index(stereoCentres[-1])
            n = len(allCentres)
            while allCentres[index] in stereoCentres:
              index = (index + 1) % n
 
            centre = allCentres[index]
        
        else:
          centre = stereoCentres[0]
        
      else:
        centre = unsetCentres[0] 
      
      if centre in unsetCentres:
        self.toggleStereoCentres([centre,])
        
        # Put the group with lowest priority to be moved in the other direction (if no stereochemistry was set before).
        if not moveForward:          
          stereo = centre.stereo
          temp = stereo[3]
          stereo[3] = stereo[1]
          stereo[1] = temp
        if stereoCentres:
          self.toggleStereoCentres([stereoCentres[-1],])
      
      isFlip = centre in stereoCentres
        
      for varAtom in varAtoms:
        if varAtom not in centre.neighbours:
          continue
        
        stereo = list(centre.stereo)
        nStereo = len(stereo)
        indexA = stereo.index(varAtom)
        upDownA = BOND_STEREO_DICT[nStereo][indexA]
        
        if moveForward:
          if isFlip and upDownA == -1: # Down
            targets = [i for i, x in enumerate(BOND_STEREO_DICT[nStereo]) if x == 0]
          else:
            targets = [i for i, x in enumerate(BOND_STEREO_DICT[nStereo]) if x == 1]
            
        else:
          if isFlip and upDownA == 1: # Up
            targets = [i for i, x in enumerate(BOND_STEREO_DICT[nStereo]) if x == 0]
          else:
            targets = [i for i, x in enumerate(BOND_STEREO_DICT[nStereo]) if x == -1]
        
        if len(targets) > 1: # Multi choice, e.g. for octahedral
          if stereo[targets[0]] in varAtoms: 
            indexB = targets[1]
            
          elif stereo[targets[1]] in varAtoms:
            indexB = targets[0]
            
          else:
            y = varAtom.coords[1]
            varAtomsB = [stereo[i] for i in targets]
            sortList = [(abs(va.coords[1]-y), va) for va in varAtomsB]
            sortList.sort()
            indexB = stereo.index(sortList[-1][1])
            
        else:
          indexB = targets[0]
          
        if indexA != indexB:
          upDownB = BOND_STEREO_DICT[nStereo][indexB]
        
          if (nStereo == 4) and (upDownB == 0) and isFlip:
            # for tetrahedral, when coming from up/down through flat
            # a stereo flip not done: becomes non-stereo
            stereo = []
            
          else:
            varAtomB = stereo[indexB]
            stereo[indexB] = varAtom
            stereo[indexA] = varAtomB

        centre.setStereo(stereo)
        if self.compoundView.autoChirality:
          centre.autoSetChirality()

  
  def toggleStereoCentres(self, varAtoms):
  
    if varAtoms:
      self.addToHistory()
      
      varAtoms2 = [va for va in varAtoms if len(va.neighbours) > 3]
      
      if not varAtoms2:
        msg = 'An atom must have at least four neighbours to be set as a stereo centre'
        QtWidgets.QMessageBox.warning(self, "Failure", msg)
        return
      
      for va1 in varAtoms2:
        if va1.stereo:
          stereo = []
          
        else:
          # Set the stereochemistry so that the shortest branches point down and up respectively.
          branches = va1.getBranchesSortedByLength()
          if len(branches) >= 4:
            stereo = [branches[3], branches[0], branches[2], branches[1]]
            for i in range(4, len(branches)):
              stereo.append(branches[i])
          
        va1.setStereo(stereo)
        if self.compoundView.autoChirality:
          va1.autoSetChirality()

      self.updateAll()

  
  def autoNameHydrogens(self, hydrogens=None):
  
    variant = self.variant
    
    if variant:    
      if not hydrogens:
        hydrogens = [a for a in variant.varAtoms if a.element == 'H']
      
      if hydrogens:
        self.addToHistory()
        variant.autoNameAtoms(hydrogens)
                  
        self.updateAll()
        self.updateVars()

  def autoNameAtoms(self):
  
    
    variant = self.variant
    if variant:
      sortList = [(a.coords, a) for a in variant.varAtoms]
      sortList.sort()
      allAtoms = [x[1] for x in sortList]
      
      if allAtoms:
        self.addToHistory()
        variant.autoNameAtoms(allAtoms)

        self.updateAll()
        self.updateVars()    

  def minimise(self):

    if self.variant:

      # Switch automatic chirality determination off during minimisation to save time.
      autoChirality = self.compoundView.autoChirality
      self.compoundView.autoChirality=False
      
      self.addToHistory()
      varAtoms = self.getSelectedAtoms()
      if not varAtoms:
        varAtoms = self.variant.varAtoms
            
      drawFunc=self.forceRedraw
      self.setCursor(QtCore.Qt.WaitCursor)
      if self.compoundView.snapToGrid:
        centroidBefore = self.variant.getCentroid()
        self.variant.snapAtomsToGrid(sorted(varAtoms, key=lambda atom: atom.name), ignoreHydrogens=False)
        centroidAfter = self.variant.getCentroid()
        diffX = centroidAfter[0]-centroidBefore[0]
        diffY = centroidAfter[1]-centroidBefore[1]
        for atom in self.variant.varAtoms:
          atom.setCoords(atom.coords[0]-diffX, atom.coords[1]-diffY, atom.coords[2])
        self.updateAll()
      else:
        self.variant.minimise2d(varAtoms, drawFunc=drawFunc)
      atoms = set(self.variant.atomDict.keys())
      
      # If the whole var was selected
      if varAtoms == self.variant.varAtoms:
        for var in self.compound.variants:
          if var is self.variant:
            continue
 
          # Update the atoms in other vars not minimised
          atomsB = set(var.atomDict.keys())
          different = atoms ^ atomsB
          unique = different & atomsB
 
          if unique:
            uniqAtoms = [var.atomDict[a] for a in unique]
            if self.compoundView.snapToGrid:
              centroidBefore = var.getCentroid()
              var.snapAtomsToGrid(sorted(uniqAtoms, key=lambda atom: atom.name), ignoreHydrogens=False)
              centroidAfter = var.getCentroid()
              diffX = centroidAfter[0]-centroidBefore[0]
              diffY = centroidAfter[1]-centroidBefore[1]
              for atom in var.varAtoms:
                atom.setCoords(atom.coords[0]-diffX, atom.coords[1]-diffY, atom.coords[2])
            else:
              var.minimise2d(uniqAtoms, drawFunc=None)
            atoms.update(unique)
      self.unsetCursor()
      self.compoundView.autoChirality = autoChirality
 
  def minimise3D(self):

    if self.variant:
    
      varAtoms = self.getSelectedAtoms()
      if not varAtoms:
        varAtoms = self.variant.varAtoms
      
      drawFunc=self.forceRedraw
      self.variant.minimise3d(varAtoms, drawFunc=drawFunc)
      atoms = set(self.variant.atomDict.keys())
      
      # If the whole var was selected
      if varAtoms == self.variant.varAtoms:
        for var in self.compound.variants:
          if var is self.variant:
            continue
 
          # Update the atoms in other vars not minimised
          atomsB = set(var.atomDict.keys())
          different = atoms ^ atomsB
          unique = different & atomsB
 
          if unique:
            uniqAtoms = [var.atomDict[a] for a in unique]
            var.minimise2d(uniqAtoms, drawFunc=None)
            atoms.update(unique)
 
  def snapToGrid(self):
    
    snap = self.compoundView.snapToGrid
    self.compoundView.snapToGrid = True
    self.minimise()
    self.compoundView.snapToGrid = snap
      
  def forceRedraw(self):
  
    cv = self.compoundView
    cv.updateAll()
    cv.viewport().repaint()

class CompoundTree(QtWidgets.QTreeWidget):

  def __init__(self, parent, chemBuild):
  
    QtWidgets.QTreeWidget.__init__(self, parent)
    
    self.chemBuild = chemBuild
    
  def dragEnterEvent(self, event):
    
    event.ignore()

  def dragMoveEvent(self, event):
    
    event.ignore()
  
  def mousePressEvent(self, event):

    QtWidgets.QTreeWidget.mousePressEvent(self, event)
    
    self.chemBuild.statusBar().showMessage('Drag and drop compounds into main window')
    
    item = self.itemAt(event.pos())
    if item:
      filePath = item.data(0,32)
      
      if filePath is None:
        return
    
    else:
      return 
    
    iconFile = path.join(ICON_DIR, 'list-add.png')
    pixmap = QtGui.QPixmap(iconFile)
    pixmap.setMask(pixmap.createHeuristicMask())
    
    anchor = QtCore.QPoint(16,16)
    
    itemData = QtCore.QByteArray()
    dataStream = QtCore.QDataStream(itemData, QtCore.QIODevice.WriteOnly)
    dataStream << pixmap << anchor

    mimeData = QtCore.QMimeData()
    mimeData.setText(filePath)
    mimeData.setData(MIMETYPE_COMPOUND, itemData)

    drag = QtGui.QDrag(self)
    drag.setMimeData(mimeData)
    drag.setPixmap(pixmap)
    drag.setHotSpot(anchor)
    
    drag.exec_(QtCore.Qt.CopyAction | QtCore.Qt.MoveAction, QtCore.Qt.CopyAction)
