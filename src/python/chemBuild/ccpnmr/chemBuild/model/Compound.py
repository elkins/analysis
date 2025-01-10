"""
CcpNmr ChemBuild is a tool to create chemical compound descriptions.

Copyright Tim Stevens, University of Cambridge December 2010-2012
"""
import pickle, json
from math import cos, sin

from ccpnmr.chemBuild.general.Constants import PROCHIRAL, EQUIVALENT, AROMATIC, NONSTEREO
from ccpnmr.chemBuild.general.Constants import ELEMENT_DATA, ELEMENT_DEFAULT

from ccpnmr.chemBuild.model.Atom import Atom
from ccpnmr.chemBuild.model.AtomGroup import AtomGroup
from ccpnmr.chemBuild.model.Bond import Bond
from ccpnmr.chemBuild.model.VarAtom import VarAtom
from ccpnmr.chemBuild.model.Variant import Variant

def loadCompoundPickle(fileName):
  
  fileObj = open(fileName, 'rb')
  compound = pickle.load(fileObj)
  fileObj.close()

  for var in compound.variants:
    var.updatePolyLink()
    var.updateDescriptor()
    
    for bond in var.bonds:
      if not hasattr(bond, 'direction'):
        bond.direction = None
  
  # Back compat - new attr
  for atom in compound.atoms:
    if not hasattr(atom, 'baseValences'):
      atom.baseValences = ELEMENT_DATA.get(atom.element,  ELEMENT_DEFAULT)[0]
    
    for varAtom in atom.varAtoms:
      if not hasattr(varAtom, 'stereo'):
        varAtom.stereo = []
        
    
  compound.isModified = False
  return compound
  
class Compound:

  def __init__(self, name):
  
    self.name = name
    self.keywords = set()
    self.details = None
    self.variants = set()
    self.atoms = set()
    self.atomDict = {}
    self.atomGroups = set()
    self.defaultVars = set()
    self.ccpCode = None
    self.ccpMolType = 'other'
    self.isModified = True
    self.one_letter_code = None
    self.three_letter_code = None
  
  def hasSubGraph(self,  fragement):
    
    pass
  
  def getAtom(self, element, name, isVariable=False):
    
    atom = self.atomDict.get(name)
    
    if not atom:
      atom = Atom(self, element, name, isVariable)
      
    return atom

  def getCcpMolType(self):
  
    from ChemBuildClassifiers import ccpnMolTypeFragments

    # protein, DNA, RNA, carbohydrate or other
    
    for fragment in ccpnMolTypeFragments:
      if self.hasSubGraph(fragment):
        return fragment.ccpMolType
  
    return 'other'
    
  def save(self, filePath):
    
    #import json
    
    if not filePath.endswith('.pickle'):
      filePath += '.pickle'
    # Add more checks
    
    fileObj = open(filePath, 'wb')
    pickle.dump(self, fileObj)
    fileObj.close()
    self.isModified = False
    
    return filePath

  def delete(self):
    
    for var in list(self.variants):
      var.delete()
    
    del self
    
  def center(self,  origin=None):
  
    if origin:
      x0,  y0,  z0 = origin
    
    else:
      x0 = 0.0
      y0 = 0.0
      z0 = 0.0
    
    xs = 0.0
    ys = 0.0
    zs = 0.0
    n = 0.0
    
    for atom in self.atoms:
      for varAtom in atom.varAtoms:
        x1, y1, z1 = varAtom.coords
        xs += x1
        ys += y1
        zs += z1
        n += 1.0
    
    if n:
      xs /= n
      ys /= n
      zs /= n
      
      xs -= x0
      ys -= y0
      zs -= z0
      
      for atom in self.atoms:
        for varAtom in atom.varAtoms:
          x1, y1, z1 = varAtom.coords
 
          x1 -= xs
          y1 -= ys
          z1 -= zs
 
          varAtom.coords = x1, y1, z1
   
  def setAromatic(self, atoms):
    
    atoms = set([a for a in atoms if a.element != 'H'])
    self.unsetAromatic(atoms)
    
    # TBD check ring
    
    for var in self.variants:
      varAtoms = set([var.atomDict.get(a) for a in atoms]) - set([None,])
      
      rings = var.getRings(varAtoms)
      
      for varAtoms2 in rings:
        AtomGroup(self, varAtoms2, AROMATIC)
    
  
  def unsetAromatic(self, atoms):
  
   atoms = set([a for a in atoms if a.element != 'H'])
   
   for atom in atoms:
     for varAtom in atom.varAtoms:
       groups = [g for g in varAtom.atomGroups if g.groupType == AROMATIC]
       for group in groups:
         group.delete()
         
  
  def setAtomGroup(self, atoms, groupType):
  
    self.unsetAtomGroup(atoms, groupType)
    
    elements = set([a.element for a in atoms])
  
    for elem in elements:
      atomsB = [a for a in atoms if a.element == elem] 
      nAtoms = len(atomsB)
      if nAtoms < 2:
        continue
     
      for var in self.variants:
        varAtoms = set([var.atomDict.get(a) for a in atomsB])
        
        if None in varAtoms:
          # This var cannot support group
          continue
        
        AtomGroup(self, varAtoms, groupType)

        
  def unsetAtomGroup(self, atoms, groupType):
  
    for atom in atoms:
      if hasattr(atom, 'varAtoms'):
        for varAtom in atom.varAtoms:
          for group in list(varAtom.atomGroups):
            if group.groupType == groupType:
              group.delete()
      
  def setAtomsEquivalent(self, atoms):
    
    self.setAtomGroup(atoms, EQUIVALENT)
   
   
  def setAtomsProchiral(self, atoms):

    self.setAtomGroup(atoms, PROCHIRAL)
  
  
  def unsetAtomsEquivalent(self, atoms):
  
    self.unsetAtomGroup(atoms, EQUIVALENT)


  def unsetAtomsProchiral(self, atoms):
    
    self.unsetAtomGroup(atoms, PROCHIRAL)
  
  def resolveTempAtomNames(self):
    
    used = self.atomDict
    for var in self.variants:
      renameVarAtoms = []
      
      for varAtom in var.varAtoms:
        name = varAtom.name
        
        if name[0] == '@':
          if name[1:] in used:
            renameVarAtoms.append(varAtom)
          else:
            varAtom.setName(name[1:])
    
      if renameVarAtoms:
        var.autoNameAtoms(renameVarAtoms)

     
  def copyVarAtoms(self, atoms, coords=None):
  
    if not atoms:
      return

    for var in self.variants:
      var.copyAtoms(atoms, coords=coords)
      
    self.resolveTempAtomNames()
    self.isModified = True
     
  def copyCompound(self, compoundB, coords=None, refVar=None):
    
    if not coords:
      coords = (0,0)  
    
    atomVarsA = [(list(v.varAtoms), v) for v in self.variants]
    polyLinks = set([v.polyLink for v in self.variants]) - set(['none','free'])        
    newRefAtoms = []
      
    for atomsA, varA in atomVarsA:
      
      i = 0
      for varB in compoundB.variants:
        if polyLinks and (varB.polyLink not in ('none','free')):
          continue
      
        atomsB = varB.varAtoms
        
        if i == 0:
          if refVar and varA is refVar:
            newRefAtoms = varA.copyAtoms(atomsB, coords)
          
          else:
            varA.copyAtoms(atomsB, coords)
            
        else:
          varC = Variant(self, atomsA)
          varC.copyAtoms(atomsB, coords)
        
        i += 1
      
    self.resolveTempAtomNames()
    self.isModified = True
    
    return newRefAtoms

  def addHydrogens(self):
    
    hydrogens = set()
    
    for var in self.variants:
      for varAtom in set(var.varAtoms):
        if varAtom.element == 'H':
          continue
        
        newAtoms = []
        x, y, z = varAtom.coords
        
        for angle in list(varAtom.freeValences):
          x2 = x + 34.0 * sin(angle)
          y2 = y + 34.0 * cos(angle)
          
          masterAtom = Atom(self, 'H', None)
          VarAtom(var, masterAtom, coords=(x2,y2, 0.0)) # All vars

          hydrogen = var.atomDict[masterAtom]
          newAtoms.append(hydrogen)
          hydrogens.add(hydrogen)
      
        for newAtom in newAtoms:
          Bond((varAtom, newAtom), autoVar=True)
              
    return hydrogens