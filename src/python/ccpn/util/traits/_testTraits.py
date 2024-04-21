""""
--------------------------------------------------------------------------------------------
 Testing
--------------------------------------------------------------------------------------------
"""

from ccpn.util.traits.CcpNmrTraits import Dict, Odict, Int, List, CPath, Adict, Set
from ccpn.util.traits.CcpNmrJson import CcpNmrJson
from ccpn.util.traits.CcpNmrTraits import RecursiveDict, RecursiveList, RecursiveOdict, RecursiveSet

class TestObj(CcpNmrJson):

    saveAllTraitsToJson = True
    classVersion = 0.1

    odict = RecursiveOdict()
    adict = Adict()

    theDict = RecursiveDict()
    theDict2 = Dict(default_value=dict(app=1,noot=2, mies=3))

    theList = RecursiveList()
    theList2 = List(default_value=[1,2,3])

    thePath = CPath(default_value='bla.dat')
    theSet = RecursiveSet()

TestObj.register()


class TestObj2(CcpNmrJson):
    saveAllTraitsToJson = True
    value = Int(default_value = 1)

    def __init__(self, value=0):
        self.value = value

    # hash and eq determine uniqueness for set and dict 'keys'; see https://hynek.me/articles/hashes-and-equality/
    # hash need to be based upon some inmutable attributes
    # for dict's and set's: if two objects compare equal, their hash must be equal
    def __eq__(self, other):
        return self.value == other.value

    def __le__(self, other):
        return self.value <= other.value

    def __lt__(self, other):
        return self.value < other.value

    def __hash__(self):
        return self.value
    def __str__(self):
        return '<TestObj2: value=%s>' % self.value

    def __repr__(self):
        return str(self)

TestObj2.register()


def atest():
    "Test it; returns two objects"

    obj1 = TestObj(id='obj1')

    print('>> hasTrait(odict):', obj1.hasTrait('odict'))
    print('>> isMutableTrait(odict):', obj1.isMutableTrait('odict'))

    for v in [10, 11, 12]:
        obj2 = TestObj2(v)
        obj1.theDict[str(v)] = obj2
    obj1.theDict['aap'] = 'noot'

    obj1.odict['test'] = TestObj2(0)
    for v in [20, 21, 22]:
        obj1.odict[str(v)] = v

    for v in [30, 31, 32]:
        obj1.adict[str(v)] = v*10

    obj1.theList.append('mies')
    for v in [40, 41, 42, 42]:
        obj2 = TestObj2(v)
        obj1.theList.append(obj2)

    obj1.theSet = obj1.theList

    js = obj1.toJson(ident=None)
    print(js)
    obj2 = TestObj().fromJson(js)
    obj2.setMetadata(key='id', value='copy from obj1')
    print(obj2)

    return (obj1, obj2)



if __name__ == '__main__':

    atest()
