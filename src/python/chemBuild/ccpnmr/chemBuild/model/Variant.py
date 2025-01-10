"""
CcpNmr ChemBuild is a tool to create chemical compound descriptions.

Copyright Tim Stevens and Magnus Lundborg, University of Cambridge 2010-2012
"""

from ccpnmr.chemBuild.model.VarAtom import VarAtom
from ccpnmr.chemBuild.model.AtomGroup import AtomGroup
from ccpnmr.chemBuild.model.Bond import Bond, BOND_TYPE_VALENCES

from math import degrees, radians, cos, sin, hypot, atan2, sqrt

from ccpnmr.chemBuild.general.Constants import LINK, AROMATIC, PI, ELEMENT_ISO_ABUN
from ccpnmr.chemBuild.general.Geometry import dotProduct, crossProduct, vectorsSubtract

class Variant:

  def __init__(self, compound, templateVarAtoms=None):

    self.compound = compound
    self.polyLink = None # Auto derived
    self.descriptor = None # Auto derived
    self.varAtoms = set()
    self.bonds = set()
    self.atomDict = {}
    self.atomGroups = set()
    self.elementDict = {}
    self._name = None
    self._id = None
    self._type = None
    self._formula = None
    self._one_letter_code = None
    self._three_letter_code = None
    self._pdbx_processing_site = None
    
    compound.isModified = True
    compound.variants.add(self)
    
    if templateVarAtoms:
      self.copyAtoms(templateVarAtoms, (0,0), False)
    
    self.updatePolyLink()
    self.updateDescriptor()
  
  
  def __repr__(self):
  
    h, l, s = self.descriptor
    return '<Variant %s %s %s %s>' % (self.polyLink, h, l, s)
      
  def delete(self):
    
    compound = self.compound
    compound.isModified = True
    for varAtom in list(self.varAtoms):
      varAtom.delete()
      
    self.varAtoms = set()
    self.bonds = set()
    self.atomDict = {}
    self.elementDict = {}
    
    if len(compound.variants) > 1:
      if self in compound.variants:
        compound.variants.remove(self)

      del self
    
    nVars = len(compound.variants)
    for atom in compound.atoms:
      if atom.isVariable and (len(atom.varAtoms) == nVars):
        atom.isVariable = False
    
    for var in compound.variants:
      var.updatePolyLink()
      var.updateDescriptor()
  
  def setDefault(self,  value=True):
    
    compound = self.compound
    compound.isModified = True
    defaultVars = compound.defaultVars
    current = set([v for v in defaultVars if v.polyLink == self.polyLink])
    
    if value:
      for var in current: 
        defaultVars.remove(var)
      defaultVars.add(self)
    
    elif self in current:
      defaultVars.remove(self)

    
  def getRings(self, varAtoms):
  
    for varAtom in varAtoms:
      if varAtom.variant is not self:
        msg = 'Variant.getRings: Input VarAtom does not belong to Variant'
        raise Exception(msg)
    
    varAtoms = set(varAtoms)
    rings = []
    
    while varAtoms:
      varAtom = varAtoms.pop()
      rings += varAtom.getRings()
      
      for varAtoms2 in rings:
        varAtoms = varAtoms - varAtoms2
      
    return rings
  
  def checkBaseValences(self):  
    
    for varAtom in self.varAtoms:
      baseValances = len(varAtom.freeValences) - varAtom.charge
      for bond in varAtom.bonds:
        baseValances += BOND_TYPE_VALENCES[bond.bondType]
      
      if varAtom.isAromatic():
        baseValances += 1
      
      if varAtom.atom.baseValences != baseValances:
        varAtom.atom.setBaseValences(baseValances)
  
  def shuffleStereo(self):
  
    for varAtom in self.varAtoms:
      stereo = varAtom.stereo
 
      if stereo:
        if len(stereo) != 4:
          continue
 
        indices = {}
        for i, va in enumerate(stereo):
          indices[va] = i
 
        sortList = [(len(va.neighbours),va.name,va) for va in stereo]
        sortList.sort()
 
        a, b, c, d = stereo
 
        perms = [[a,b,c,d], [a,c,d,b], [a,d,b,c],
                 [b,a,d,c], [b,d,c,a], [b,c,a,d],
                 [c,a,b,d], [c,b,d,a], [c,d,a,b],
                 [d,a,c,b], [d,c,b,a], [d,b,a,c]]
 
        w, x, y, z = [v[2] for v in sortList]
 
        for p, q, r, s in perms:
          if p in (y,z) and r in (y,z):
            varAtom.stereo = [p, q, r, s]
            break
 
  
  def deduceStereo(self):
    
    for varAtom in self.varAtoms:
      neighbours = list(varAtom.neighbours)
 
      if len(neighbours) < 4:
        continue
 
      center = varAtom.coords
      
      vecs = [(vectorsSubtract(va.coords, center), va) for va in neighbours]
      vec1, va1 = vecs[0]
      
      dotProds = [(dotProduct(vec, vec1), vec, va) for vec, va in vecs[1:]]
      dotProds.sort()
      
      dp, vec2, va2 = dotProds[0]
      
      norm = crossProduct(vec1, vec2)
      len1 = sqrt(dotProduct(norm, norm))
      
      angles = []
      for dp, vec, va in dotProds[1:]:
        len2 = sqrt(dotProduct(vec, vec))*len1
        
        c = dotProduct(vec, norm)/len2
        cp = crossProduct(vec, norm)
        s =  sqrt(dotProduct(cp, cp))/len2

        angle = atan2(s,c)
        angles.append((angle, va))
        
      angles.sort()
      
      stereo = [va1,]
      stereo += [x[1] for x in angles]
      stereo += [va2,]
      
      varAtom.stereo = stereo
      
    self.shuffleStereo()

  
  def addLink(self, linkType, replaceAtoms):
    
    from ccpnmr.chemBuild.model.Atom import Atom
  
    compound = self.compound
    compound.isModified = True
    
    #existing = self.elementDict[LINK]
    hydrogens = [va for va in replaceAtoms if va.element == 'H']
    oxygens = [va for va in replaceAtoms if va.element == 'O']
    
    if not hydrogens:
      return
  
    linkH = None
    linkO = None
    bound = None
    context = None
    
    for o in oxygens:
      oNeighbours = set(o.neighbours)
      for h in hydrogens:
        if h in oNeighbours:
          linkH = h.atom
          linkO = o.atom
          oNeighbours.remove(h)
          if oNeighbours:
            boundAtom = oNeighbours.pop()
            bound = boundAtom.atom
            context = boundAtom.getContext()
          break
      else:
        continue
      break
    
    if not linkH:
      h = hydrogens[0]  
      linkH = h.atom
      hNeighbours = set(h.neighbours)
      
      if hNeighbours:
        boundAtom = hNeighbours.pop()
        bound = boundAtom.atom
        context = boundAtom.getContext()
    
    variants = list(compound.variants)
    newAtom = None
    
    for va in bound.varAtoms:
      for va2 in va.neighbours:
        if va2.element == LINK:
          return va2
	
    linkMasterAtom = compound.getAtom(LINK, linkType)

    # Replace terminal Hs
    if linkO:
      oldOtherH = []
    else:  
      oldOtherH = [a for a in context if a.element == 'H']
      oldOtherH.remove(linkH)
      
    # New middle Hs
    newOtherH = [Atom(compound, 'H', None) for a in oldOtherH]
    
    for var in variants:
      atomH = var.atomDict.get(linkH)
      
      if not atomH:
        continue
        
      atomO = None
      if linkO:
        atomO = var.atomDict.get(linkO)
        
        if not atomO:
          continue
          
      atomB = None
      contextB = None
      if bound:
        atomB = var.atomDict[bound]
        
        if not atomB:
          continue

        contextB = atomB.getContext()
        if contextB != context:
          continue
      
      atoms = set(var.varAtoms)
      atoms.remove(atomH)
      coordsH = []
      
      if atomO:
        coords = atomO.coords
        atoms.remove(atomO)
        
      else:
        coords = atomH.coords  
      
        for atomH2 in oldOtherH:
          varAtomH2 = var.atomDict.get(atomH2)
          coordsH.append(varAtomH2.coords)
          atoms.remove(varAtomH2)
      
      newVar = Variant(compound, atoms)
      
      varAtom = VarAtom(newVar, linkMasterAtom, coords=coords)


      if atomB:
        varAtomB = newVar.atomDict[bound]
        varAtomB.updateValences()
        newVar.getBond(varAtom, varAtomB, autoVar=False)
      
      if var is self:
        newAtom = varAtom
      
      for i, newH in enumerate(newOtherH):
        varAtomB = newVar.atomDict[bound]
        varAtomB.updateValences()
        varAtom = VarAtom(newVar, newH, coords=coordsH[i])
        newVar.getBond(varAtom, varAtomB, autoVar=False)

      newVar.updatePolyLink()
      newVar.updateDescriptor()
    
    # Try auto amide name
    if bound and (bound.element == 'N') and len(newOtherH) == 1:   
      if 'H' not in compound.atomDict:
        newOtherH[0].setName('H')
    
    return newAtom
  
  def getBond(self, varAtomA, varAtomB, autoVar=True):
  
    if not varAtomA.freeValences:
      return

    if not varAtomB.freeValences:
      return
  
    if varAtomA in varAtomB.neighbours:
      common = set(varAtomA.bonds & varAtomB.bonds)
      return common.pop()
  
    return Bond((varAtomA, varAtomB), autoVar=autoVar)
  
  def updatePolyLink(self):
  
    linkNames = [a.name for a in self.elementDict.get(LINK, [])]
    
    prevLink = [x for x in linkNames if 'prev' in x]
    nextLink = [x for x in linkNames if 'next' in x]
  
    if prevLink and nextLink:
      self.polyLink = 'middle'
    elif prevLink:
      self.polyLink = 'end'
    elif nextLink:
      self.polyLink = 'start'
    elif linkNames:
      self.polyLink = 'linked'
    else:
      self.polyLink = 'free'

  def updateDescriptor(self):
    
    self.descriptor = self.getDescriptor()

  def getCommonIsoMass(self):
    
    mass = 0.0
    for element in self.elementDict:
      if element == LINK:
        continue
      
      n = len(self.elementDict[element])
      mass += n * ELEMENT_ISO_ABUN[element][0][2]
    
    return  mass
    
  def getMolFormula(self):
  
    counts = {}
    for element in self.elementDict:
      if element == LINK:
        continue
      
      counts[element] = len(self.elementDict[element])
    
    elements = list(counts.keys())
    elements.sort()
    if 'H' in elements:
      elements.remove('H')
      elements.insert(0, 'H')
  
    if 'C' in elements:
      elements.remove('C')
      elements.insert(0, 'C')
    
    formula = []
    for elem in elements:
      n = counts[elem]
      if n > 1:
        text = '%s%d' % (elem, n)
      else:
        text = elem
        
      formula.append(text)
    
    formula = ' '.join(formula)
    
    return formula
    
  def getDescriptor(self):
    
    prot = '+'
    deprot = '-'
    link = ''
    sep = ''
    joinStr = ','
    neutral = 'neutral'
    
    equivVars = [v for v in self.compound.variants if v.polyLink == self.polyLink]

    hAtomVars = {}
    stereoTypes = {}
    
    for var in equivVars:
      for atom in var.varAtoms:
        name = atom.name
        if name not in stereoTypes:
          stereoTypes[name] = set()
        
        stereoTypes[name].add(atom.chirality)
        
        if (atom.element == 'H') and atom.atom.isVariable:
          if name not in hAtomVars:
            hAtomVars[name] = set()
          
          hAtomVars[name].add(var)
          
    tagsLink = []
    tagsStereo = []
    tagsProton = []
    
    # Links
    
    linkAtoms = self.elementDict.get(LINK, [])
    genLinks = [a for a in linkAtoms
                if ('prev' not in a.name) \
                and ('next' not in a.name)]
    
    for atom in genLinks:
      neighbours = atom.neighbours
      name = ','.join([a.name for a in neighbours])
      tagsLink.append((link, name))
    
    # Protonation
    isNeutral = sum([abs(va.charge) for va in self.varAtoms]) == 0

    # Names of variable atoms
    for name in hAtomVars:
 
      # Vars that have this hydrogen
      varsA = hAtomVars[name]
 
      if self in varsA:
        tagsProton.append((prot, name))
 
      else:
        tagsProton.append((deprot, name))
      
    # stereochemistry
    for atom in self.varAtoms:
      name = atom.name
      if (atom.chirality) and stereoTypes.get(name):
        tagsStereo.append((atom.chirality, name))
    
    if isNeutral:
      defaultH = neutral
    else:
      defaultH = 'default'
    
    tagsProton.sort()
    tagsProton = joinStr.join(['%s%s' % x for x in tagsProton]) or defaultH
    tagsStereo.sort()
    tagsStereo = joinStr.join(['(%s)%s' % x for x in tagsStereo]) or 'default'
    tagsLink.sort()
    tagsLink = joinStr.join(['%s%s' % x for x in tagsLink]) or 'none'
 
    return tagsProton, tagsLink, tagsStereo




  def copyAtoms(self, varAtoms, coords=None, tempNames=True):
  
    if not varAtoms:
      return
    
    compound = self.compound
    compound.isModified = True
    
    cx = 0.0
    cy = 0.0
    n = 0.0
    
    for atom in varAtoms:
      x,y,z = atom.coords
      cx += x
      cy += y
      n += 1.0
      
    cx /= n
    cy /= n  
   
    if coords is None:
      x0, y0 = cx, cy
    else:
      x0, y0 = coords
    
    mapping = {}
    bonds = set()
    groups = set()

    newAtoms = set()
    addList = [(a.name, a) for a in varAtoms]
    addList.sort()
    
    for name, atom in addList:
      
      if atom.element == LINK:
        if 'prev' in name:
          if self.polyLink == 'middle':
            continue
          elif self.polyLink == 'end':
            continue
        if 'next' in name:
          if self.polyLink == 'middle':
            continue
          elif self.polyLink == 'start':
            continue
      
      x,y,z = atom.coords
      dx = x - cx
      dy = y - cy
      
      bonds.update(atom.bonds)
      groups.update(atom.atomGroups)
      
      if tempNames:
        name = '@%s' % name
      
      masterAtom = compound.getAtom(atom.element, name, atom.atom.isVariable)
      masterAtom.baseValences = atom.atom.baseValences
      
      newAtom = VarAtom(self, masterAtom, atom.freeValences,
                        atom.chirality, (x0+dx, y0+dy, z),
                        atom.isLabile, atom.charge)
      newAtoms.add(newAtom)
      
      mapping[atom] = newAtom
    
    for bond in bonds:
      atomA, atomB = bond.varAtoms
      newAtomA = mapping.get(atomA)
      newAtomB = mapping.get(atomB)
      
      if newAtomA and newAtomB:
        Bond((newAtomA, newAtomB), bondType=bond.bondType, autoVar=False)
    
    for group in groups:
      
      newAtomsG = set()
      for varAtom in group.varAtoms:
        if varAtom not in mapping:
          break
        
        newAtomsG.add(mapping[varAtom])
      
      else:
        AtomGroup(compound, newAtomsG, groupType=group.groupType)
    
    for varAtom in mapping:
      if varAtom.stereo:
        stereo = []
        for varAtom2 in varAtom.stereo:
          newAtom = mapping.get(varAtom2)
          
          if newAtom:
            stereo.append(newAtom)
          else:
            break        
        
        else:
          mapping[varAtom].setStereo(stereo) 
    
    for var in self.compound.variants:
      var.updatePolyLink()
      var.updateDescriptor()
    
    return newAtoms

  def minimise2d(self, atoms=None, maxCycles=250, bondLength=50.0, drawFunc=None):
    
    
    from math import sqrt
     
    allAtoms = list(self.varAtoms)
    if not atoms:
      atoms = set(self.varAtoms)
      
      if len(atoms) < 2:
        return
      
      atoms.pop()

    if not atoms:
      return      

    compound = self.compound
    compound.isModified = True
    
    
    from random import random, shuffle
    
    cx = 0.0
    cy = 0.0
    cz = 0.0
    for atom in atoms:
      x, y, z = atom.coords
      x += random()
      y += random()
      atom.coords = x, y, z
      cx += x
      cy += y
      cz += x
    
    n = float(len(atoms))
    cx /= n
    cy /= n
    cz /= n
      
    #self.minimise3d(atoms, maxCycles*5, bondLength, drawFunc)
    #self.center(atoms, (cx, cy, cz))
    
    distances = {}
    distances2 = {}
    bondLengths = {}
    getBond = self.getBond
    
    aromatics = set()
    for varAtom in atoms:
      elem = varAtom.element
      neighbours = varAtom.neighbours
      n = float(len(neighbours))
      
      for atomGroup in varAtom.atomGroups:
        if atomGroup.groupType == AROMATIC:
          aromatics.add(atomGroup)
      
      for varAtom2 in neighbours:
        elem2 = varAtom2.element
        
        if 'H' in (elem2, elem):
          bl = 0.75 * bondLength
        else:
          bond = set(varAtom2.bonds & varAtom.bonds).pop()
          
          if bond.bondType in ('double','triple'):
            bl = 0.87 * bondLength
          else:
            bl = bondLength  
        
        key = frozenset([varAtom2, varAtom])
        bondLengths[key] = bl
    
    for group in aromatics:
      varAtoms = group.varAtoms
      n = float(len(varAtoms))
      t = (n-2.0) * PI / (2.0*n)
      dist = bondLength * 2.0 * sin(t)
      
      for varAtom in varAtoms:
        neighbours = [va for va in varAtom.neighbours if va in varAtoms]
        
        if len(neighbours) == 2:
          distances2[frozenset(neighbours)] = dist
    
    b2 = bondLength*bondLength
    r2limit = 4 * b2
    
    for c in range(maxCycles):
      change = 0.0
      
      g = 0.005 * float(maxCycles - c)/maxCycles
      
      for atom in atoms:
        neighbours = atom.neighbours
      
        if not neighbours:
          continue

        vx = 0.0
        vy = 0.0
        x,y,z = atom.coords
 
        for atom2 in allAtoms: # only neighbours?
          if atom2 is atom:
            continue

          x2,y2,z2 = atom2.coords
        
          dx = x-x2
          dy = y-y2
          r2 = (dx*dx) + (dy*dy)
          pair = frozenset([atom, atom2])
          
          if pair in distances2:
            f = distances2[pair] - sqrt(r2)     
          
          elif atom2 in neighbours:
            f = bondLengths[pair] - sqrt(r2)

          elif r2 < r2limit:
            if (r2*r2) == 0:
              continue
            else:
              f = 5e6 / (r2*r2)
          
          else:
            continue
          
          f = min(2.0, max(-2.0, f))
          vx += dx * f * g
          vy += dy * f * g
                
        x += max(min(10.0*vx, 10.0), -10.0)
        y += max(min(10.0*vy, 10.0), -10.0)
        
        atom.coords = (x,y,z)
        change += abs(vx)
        change += abs(vy)
      
      if (c%5 == 0) and drawFunc:
        self.center(atoms, (cx, cy, cz))
        drawFunc()
      
      shuffle(allAtoms)

      # quit early if nothing happens
      if change < 0.01:
        break
    
    for atom in atoms:
      x,y,z = atom.coords
      atom.setCoords(x,y,0.0) # updates all vars
      atom.updateValences()

    if drawFunc:
      drawFunc()
  
  def getCentroid(self, atoms=None):
      
    if not atoms:
      atoms = self.varAtoms
    
    xs = 0.0
    ys = 0.0
    zs = 0.0
    n = 0.0
 
    for varAtom in atoms:
      x1, y1, z1 = varAtom.coords
      xs += x1
      ys += y1
      zs += z1
      n += 1.0
    
    if n:
      xs /= n
      ys /= n
      zs /= n
      return (xs, ys, zs)
    
    else:
      return (0.0, 0.0, 0.0)  
      
  def center(self, atoms=None, origin=None):
    
    if not atoms:
      atoms = self.varAtoms
    
    if origin:
      x0,  y0,  z0 = origin
    
    else:
      x0 = 0.0
      y0 = 0.0
      z0 = 0.0
    
    xs, ys, zs = self.getCentroid(atoms)
    xs -= x0
    ys -= y0
    zs -= z0
    
    for varAtom in atoms:
      x1, y1, z1 = varAtom.coords
 
      x1 -= xs
      y1 -= ys
      z1 -= zs
 
      varAtom.coords = x1, y1, z1
      
  def minimise3d(self, atoms=None, maxCycles=100, bondLength=50.0, drawFunc=None):
    
    from math import sqrt
    from random import random, shuffle
     
    allAtoms = list(self.varAtoms)
    if not atoms:
      atoms = set(self.varAtoms)
      
      if len(atoms) < 2:
        return
      
      atoms.pop()

    if not atoms:
      return

    compound = self.compound
    compound.isModified = True
    
    distances = {}
    
    aromatics = set()
    bl = bondLength * 2.0
    for varAtom in atoms:
      neighbours = [n for n in varAtom.neighbours if n.element != 'H']
      n = float(len(neighbours))
      
      for varAtom2 in neighbours:      
        for varAtom3 in neighbours:
            
          if varAtom2 is not varAtom3:

            if n == 3.0:
              distances[frozenset([varAtom2, varAtom3])] = bl * 0.8660254
            else:
              distances[frozenset([varAtom2, varAtom3])] = bl * 0.5  
               
    for group in aromatics:
      varAtoms = group.varAtoms
      n = float(len(varAtoms))
      
      for varAtom in varAtoms:
        neighbours = [va for va in varAtom.neighbours if va in varAtoms]
        
        if len(neighbours) == 2:
          varAtomA, varAtomB = neighbours
          distances[frozenset([varAtom, varAtomA])] = bondLength
          distances[frozenset([varAtom, varAtomB])] = bondLength
          t = (n-2.0) * PI / n
          distances[frozenset([varAtomA, varAtomB])] = bondLength * 2.0 * sin(t)

    cx = 0.0
    cy = 0.0
    cz = 0.0
    for atom in atoms:
      x, y, z = atom.coords
      x += random()
      y += random()
      z += random()
      atom.coords = x, y, z
      cx += x
      cy += y
      cz += z
    
    n = float(len(atoms))
    cx /= n
    cy /= n
    cz /= n
         
    b2 = bondLength*bondLength
    r2limit = 4 * b2
    
    for c in range(maxCycles):
      change = 0.0
      g = 5.0*float(c)/maxCycles
      
      for atom in atoms:
        neighbours = atom.neighbours
      
        if not neighbours:
          continue
        
        
        vx = 0.0
        vy = 0.0
        vz = 0.0
        x,y,z = atom.coords
 
        for atom2 in allAtoms: # only neighbours?
          if atom2 is atom:
            continue

          x2,y2,z2 = atom2.coords
        
          dx = x-x2
          dy = y-y2
          dz = z-z2
          r2 = max(0.001, (dx*dx) + (dy*dy)+ (dz*dz))
          
          pair = frozenset([atom, atom2])
          if pair in distances:
            dl = 1*(distances[pair] - sqrt(r2))
            vx += dx*dl/r2
            vy += dy*dl/r2
            vz += dz*dl/r2       
          
          elif atom2 in neighbours:
            dl = 1*(bondLength - sqrt(r2))
            vx += dx*dl/r2
            vy += dy*dl/r2
            vz += dz*dl/r2

          else:
            f = 5*b2/(r2*r2)
            vx += dx*f
            vy += dy*f
            vz += dz*f
          
          f = dz/r2
          vz += g*dz*f
                
        x += max(min(10.0*vx, 10), -10)
        y += max(min(10.0*vy, 10), -10)
        z += max(min(10.0*vz, 10), -10)
        
        atom.coords = (x,y,z)
        change += vx
        change += vy
        change += vz
      
      if (c%5 == 0) and drawFunc:
        self.center(atoms, (cx, cy, cz))
        drawFunc()
      shuffle(allAtoms)
          
      # quit early if nothing happens
      if abs(change) < 1e-4:
        break
    
    for atom in atoms:
      x,y,z = atom.coords
      atom.setCoords(x,y,z) # updates all vars
      atom.updateValences()
      
    if drawFunc:
      drawFunc()

  # This function snaps the atoms in atoms to suitable bond angles. When determining where to place atoms
  # only already placed atoms are taken into account (i.e. those that are not present in atoms)
  def snapAtomsToGrid(self, atoms=None, prevAtom=None, ignoreHydrogens=True, bondLength=50.0):

    if not atoms:
      atoms = sorted(self.varAtoms, key=lambda atom: atom.name)
      prevX = prevY = prevZ = None
    else:
      if len(atoms) < 1:
        return
        
    chiralities = []
    for atom in atoms:
      if atom.chirality:
        for c in chiralities:
          if c[0]==atom.name:
            break
        else:
          chiralities.append((atom.name, atom.chirality))

    # Make a separate list of hydrogens, which will be placed last.
    hydrogens = []
    atomsTemp = list(atoms)
    for atom in atomsTemp:
      if atom.element == 'H':
        #if ignoreHydrogens:
        atoms.remove(atom)
        hydrogens.append(atom)
        
    atom = None
    neighbour = None
    
    molCnt = 0
    
    prevAngle = None

    # prevAtom is an already positioned atom and is used as a reference for placing its neighbouring atoms.
    if prevAtom:
      prevX, prevY, prevZ = prevAtom.coords
      neighbours = sorted(prevAtom.neighbours, key=lambda atom: atom.name)
      for neighbour in neighbours:
        if neighbour.element != 'H' and neighbour in atoms:
          atom = neighbour
          break
      # Find a reference angle to an already placed atom.
      for neighbour in neighbours:
        if neighbour != prevAtom and neighbour.element != 'H' and neighbour not in atoms:
          prevAngle = degrees(prevAtom.getBondAngle(neighbour))
          break

      # If a reference atom was submitted and it is in a ring snap the ring before proceeding to other atoms.
      atom = prevAtom
      rings = sorted(atom.getRings(), key=lambda ring: len(ring), reverse=True)
      atom.snapRings(rings, neighbours, atoms, prevAngle, bondLength)
      atom = None
    
    while atoms:
      # Find an atom with an already placed neighbour
      for atom in atoms:
        neighbours = sorted(atom.neighbours, key=lambda atom: atom.name)
        for neighbour in neighbours:
          if neighbour.element != 'H' and neighbour not in atoms:
            prevX, prevY, prevZ = neighbour.coords
            prevAtom = neighbour
            neighbours2 = sorted(neighbour.neighbours, key=lambda atom: atom.name[-1])
            # Try to find a reference angle (if the neighbour has a neighbour that has been placed).
            for neighbour2 in neighbours2:
              if neighbour2 != atom and neighbour2 not in atoms and (not ignoreHydrogens or neighbour2.element != 'H'):
                prevAngle = round(degrees(neighbour.getBondAngle(neighbour2)), 0)
                break
            else:
              prevAngle = None
            break
        else:
          continue
        break
      else:
        prevAtom = None
        atom = None

      if atom and atom in atoms:
        atoms.remove(atom)
      if not atom:
        # Start by placing the atom involved in most rings. This can help avoid clashes.
        atomWithMostRings = None
        mostRings = 0
        for atom in atoms:
          nRings = len(atom.getRings())
          if nRings > mostRings:
            atomWithMostRings = atom
            mostRings = nRings
        if mostRings > 0:
          atom = atomWithMostRings
          atoms.remove(atom)
        else:
          atom = atoms.pop(0)
        # Set default coordinates since this is the first atom.
        atom.coords = (20 + 250 * molCnt, 20, atom.coords[2])
        molCnt += 1
            
      angles = []

      neighbours = sorted(atom.neighbours, key=lambda atom: atom.name)
      if prevAtom:
        prevChiral = prevAtom.chirality
        angles = prevAtom.getPreferredBondAngles(prevAngle, None, atoms + [atom])
        if prevChiral and prevChiral.upper() in ('E', 'Z'):
          for prevNeighbour in prevAtom.neighbours:
            if prevAtom.getBondToAtom(prevNeighbour).bondType=='double' and not prevNeighbour in atoms:
              prio = prevAtom.getPriorities()
              prioIndex = prio.index(atom)
              if prioIndex == 0 or (prioIndex == 1 and prio[0] == prevNeighbour):
                selfHeavy = True
              else:
                selfHeavy = False
              prevPrio = prevNeighbour.getPriorities()
              for p in prevPrio:
                if prevAtom != p:
                  if p not in atoms:
                    prevAngle = round(degrees(prevAtom.getBondAngle(prevNeighbour)), 0)
                    angles = prevAtom.getPreferredBondAngles(prevAngle, None, atoms + [atom], ignoreHydrogens)
                    prevHeavyNeighbourAngle = degrees(p.getBondAngle(prevNeighbour))
                    if (selfHeavy and prevChiral.upper() in ('Z')) or \
                    (not selfHeavy and prevChiral.upper() in ('E')):
                      angles = [round(prevAngle-prevHeavyNeighbourAngle, 0)]
                    else:
                      angles = [-round(prevAngle-prevHeavyNeighbourAngle, 0)]
                  break
              break
          
      if not prevAtom or prevX == None or prevY == None:
        prevX, prevY, prevZ = atom.coords
        prevAtom = atom
        prevAngle = None
      else:
        bonds = set(prevAtom.bonds & atom.bonds)
        if len(bonds) > 0:
          bond = bonds.pop()
        else:
          msg = 'Variant.snapAtomsToGrid: Cannot find bond between atoms to snap (%s and %s).' % (atom, prevAtom)
          raise Exception(msg)

        if bond.bondType == 'triple' or bond.bondType == 'double':
          bl = bondLength * 0.87
        else:
          bl = bondLength
        
        prevAngle = atom.snapToGrid(prevAtom, bl, prevAngle, angles, atoms, ignoreHydrogens)
        prevAngle = (180 + prevAngle)%360

      rings = sorted(atom.getRings(), key=lambda ring: len(ring), reverse=True)
      if len(rings) > 0:
        atom.snapRings(rings, neighbours, atoms, prevAngle, bondLength)

    # Place the hydrogens
    if hydrogens:
      while hydrogens:
        atom = hydrogens.pop()
        # If placing hydrogens bound to a ring make sure that the prevAtom
        # is also in a ring. This makes it possible to avoid hydrogens
        # inside the ring.
        if atom.getRings():
          for prevAtom in atom.neighbours:
            if prevAtom.getRings():
              break
        else:
          prevAtom = set(atom.neighbours)
          if prevAtom:
            prevAtom.pop()

        if prevAtom:
          prevX, prevY, prevZ = prevAtom.coords
          neighbours = sorted(prevAtom.neighbours, key=lambda atom: atom.name)
          for neighbour in neighbours:
            if neighbour != atom and not neighbour in hydrogens:
              prevAngle = round(degrees(prevAtom.getBondAngle(neighbour)), 0)
              break

          angles = prevAtom.getPreferredBondAngles(prevAngle, neighbours, hydrogens + [atom], ignoreHydrogens = False)

          atom.snapToGrid(prevAtom, bondLength*0.75, prevAngle, angles, hydrogens, ignoreHydrogens = False)

    for c in chiralities:
      for a in self.varAtoms:
        if a.name == c[0]:
          sc = a.getStereochemistry()
          if sc and sc.upper() != c[1].upper():
            if sc.upper() in ('R', 'S'):
              temp = a.stereo[3]
              a.stereo[3] = a.stereo[1]
              a.stereo[1] = temp
            



  # Snap the atoms in a ring to the preferred bond angles.
  def snapRingToGrid(self, ring, anchor = None, prevAngle=None, bondLength=45.0, skippedAtoms=set([])):
    
#    ringAtoms = set(ring)
    ringAtoms = sorted(ring, key=lambda atom: atom.name)
    ringSize = len(ringAtoms)
    
    if ringSize < 3:
      msg = 'Variant.snapRingToGrid: Ring size must be larger than 2'
      raise Exception(msg)
      
    prevAtom = None
    
    ringAngle = ((ringSize-2) * 180)/ringSize
    
    if anchor and anchor in ringAtoms:
      ringAtoms.remove(anchor)
        
    for skippedAtom in skippedAtoms:
      if skippedAtom in ringAtoms:
        ringAtoms.remove(skippedAtom)
      
    # Find a suitable angle of the "anchor atom" relative to a neighbour outside the ring.
    if anchor:
      atom = anchor
      neighbours = anchor.neighbours
      nNeighbours = len(neighbours)
      for neighbour in neighbours:
        if neighbour.element == 'H':
          nNeighbours -= 1
      angle = (180 - 0.5 * ringAngle)
      if nNeighbours > 3:
        angle /= nNeighbours - 2
      angles = [angle]
      if not prevAngle:
        for neighbour in neighbours:
          if neighbour in ring and neighbour not in ringAtoms:
            prevAngle = degrees(atom.getBondAngle(neighbour))
            break
          if neighbour in skippedAtoms:
            d = atom.getAtomDist(neighbour)
            if abs(d - bondLength) < 0.001:
              prevAngle = degrees(atom.getBondAngle(neighbour))
        else:
          if not prevAngle:
            prevAngle = 330
    else:
      atom = ringAtoms.pop(0)
      prevAngle = 330
      angles = [-ringAngle]
      
    if len(skippedAtoms) > 1:
      skippedNeighbours = anchor.neighbours & skippedAtoms

      if skippedNeighbours:
        sortedSkippedAtoms = sorted(skippedAtoms, key=lambda atom: atom.name)
#        for skippedNeighbour in skippedNeighbours:
#          if sortedSkippedAtoms.index(skippedNeighbour) != 0:
#            ringAngle = -ringAngle
#            break
        angles = [-ringAngle,  ringAngle]
        anchor = None
          
    prevAtom = atom
    while ringAtoms:
      neighbours = sorted(prevAtom.neighbours & ring - skippedAtoms, key=lambda atom: atom.name)
      found = False
      atom = None
      if len(neighbours) != 0:
        for atom in neighbours:
          if atom in ringAtoms:
            break
      if not atom:
        for atom in ringAtoms:
          neighbours = atom.neighbours & ring
          if len(neighbours) > 0:
            neighbour = neighbours.pop()
            nextNeighbours = neighbour.neighbours & ring - set(ringAtoms)
            if atom in nextNeighbours:
              nextNeighbours.remove(atom)
            nextNeighbour = nextNeighbours.pop()
            prevAtom = neighbour
            prevAngle = degrees(neighbour.getBondAngle(nextNeighbour))
      oldPrevAngle = prevAngle
      prevAngle = atom.snapToGrid(prevAtom, bondLength, prevAngle, angles)
      if not anchor and abs((oldPrevAngle + ringAngle) % 360 - prevAngle) < 1:
        angles = [ringAngle]
        anchor = None
      else:
        angles = [-ringAngle]
      prevAngle = (180 + prevAngle)%360
      ringAtoms.remove(atom)
      prevAtom = atom

  def autoNameAtoms(self, varAtoms):
    # TODO rename also the (NMR) AtomGroups.

    used = self.compound.atomDict
    nonH = [a for a in varAtoms if a.element not in ('H',LINK)]
    hydrogens = [a for a in varAtoms if a.element == 'H']
    
    if nonH:
      nAtoms = 1
      nPrev = 0
      atom = nonH[0]
      atoms = set([atom,])
      orderList = [atom]
 
      while nAtoms != nPrev:
        nPrev = nAtoms
        for atom in list(atoms):
          for atomB in atom.neighbours:
            if atomB.element in ('H',LINK):
              continue
 
            if atomB not in atoms:
              orderList.append(atomB)
              atoms.add(atomB)
 
        nAtoms = len(atoms)

      for i, atom in enumerate(orderList):
        atom.setName('@%d%s' %(i, atom.name))
      
      i = 1
      for atom in orderList:
        
        name = '%s%d' % (atom.element,i)
        while name in used:
          i += 1
          name = '%s%d' % (atom.element,i)
        
        atom.setName(name)
    
    if hydrogens:
      for i, atom in enumerate(hydrogens):
        atom.setName('@%d%s' % (i, atom.name))
        
      for atom in hydrogens:
        for atomB in atom.neighbours:
          if atomB.element in ('H',LINK):
            continue
            
          totalH = [a for a in atomB.neighbours if a.element == 'H']
          
          name = nameBase = 'H%s' % (atomB.name[len(atomB.element):])
          
          if len(totalH) > 1:
            index = totalH.index(atom)
            number = '%d' % (index+1)
            if nameBase[-1].isdigit():
              name = nameBase + '_' + number
            else:
              name = nameBase + number
            
            i = 1
            while name in used:
              number = '%d' % (i)
              if nameBase[-1].isdigit():
                name = nameBase + '_' + number
              else:
                name = nameBase + number
              i += 1
              
          if atomB.element != 'C':
            i = 1
            while name in used:
              name = 'H%s_%d' % (atomB.name, i)
              i += 1
           
          i = 1
          while name in used:
            name = 'H%d' % (i)
            i += 1
              
          atom.setName(name)
          break

