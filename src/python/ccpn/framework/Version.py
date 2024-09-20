"""Top level application version file

"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Morgan Hayward, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Daniel Thompson",
               "Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-09-09 19:06:21 +0100 (Mon, September 09, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================


_DEBUG = False


class VersionString(str):
    """Version-string routines, adapted from path idea in: Python Cookbook,
    A. Martelli and D. Ascher (eds), O'Reilly 2002, pgs 140-142

    A VersionString is a string with extra functionality.
    It consists of three non-empty and one optional substrings separated by a mandatory dot '.' character:

        majorVersion.minorVersion.microVersion[.release]

      Examples: 3.0.4; 3.1.0.alpha

    If the optional release is included it must be alphanumeric, and of the form [label][releaseNumber]
    If only the label is supplied, the releaseNumber defaults to 0.

    NOTE: in order that the update script operates correctly, ALL fields (including .release if specified) must
    be monotonically increasing in steps of 1. They don't necessarily have to start from 0.

    The majorVersion, minorVersion, microVersion and release fields are available as properties.

    A VersionString instance supports comparisons with either another VersionString instance or a suitable
    formatted string; e.g.

      VersionString('3.1.0.alpha') > VersionString('3.0.4')    returns True
      VersionString('3.1.0.alpha') < '3.0.2'                   returns False

    On a technical note: a hash is generated from the last bit of each of the fields, and a change in the hash is
    recognised as an increase in version-numbering by the shell-script implementing the sequential update mechanism.
    In particular, A step from 3.2.1.0 -> 3.2.1.2 will not be recognised and the update sequence will terminate early.
    """

    def __new__(cls, value=None, *args, **kwargs):
        """First argument ('string' must be a valid pid string with at least one, non-initial PREFIXSEP
        Additional arguments are converted to string with disallowed characters changed to altCharacter
        """
        if not isinstance(value, str):
            raise TypeError('Invalid versionString "{}"; must be a string'.format(value))
        if args or kwargs:
            raise TypeError('Invalid versionString; too many arguments')

        _fields = tuple(value.split('.'))
        if len(_fields) < 3:
            raise ValueError('Invalid VersionString "{}"; expected at least 3 fields'.format(value))
        if len(_fields) > 4:
            raise ValueError('Invalid VersionString "{}"; too many fields'.format(value))

        for name, val in zip('majorVersion minorVersion microVersion'.split(), _fields[:3]):
            try:
                int(val)
            except Exception:
                raise ValueError('Invalid VersionString "{}"; expected integer for field '
                                 '"{}" ("{}")'.format(value, name, val)) from None
        if len(_fields) == 4:
            try:
                cls._validateField(_fields[3])
            except Exception:
                raise ValueError('Invalid VersionString "{}"; expected release ("{}") to be alphanumeric '
                                 'of the form [label][int]'.format(value, _fields[3])) from None

        if _DEBUG:
            print('--> {} "{}" created'.format(cls.__name__, value))

        _new = super().__new__(cls, value)
        _new._fields = _fields

        return _new

    @property
    def majorVersion(self) -> str:
        """return majorVersion field of self"""
        return self.fields[0]

    @property
    def minorVersion(self) -> str:
        """return minorVersion field of self"""
        return self.fields[1]

    @property
    def microVersion(self) -> str:
        """return microVersion field of self"""
        return self.fields[2]

    @property
    def release(self) -> str:
        """return release field of self, or None if it does not exist
        """
        fields = self.fields
        return self.fields[3] if len(fields) >= 4 else None

    @property
    def fields(self) -> tuple:
        """Return a tuple of the fields of self
        """
        return self._fields

    @property
    def asStr(self) -> str:
        """Convenience: return as string rather than object;
        allows to do things as obj.asPid.str rather then str(obj.asPid)
        """
        return str(self)

    def withoutRelease(self) -> str:
        """Convenience: return self as str without the release field
        """
        return '.'.join(self.fields[:3])

    @staticmethod
    def _validateField(field):
        """Validate that the field is of the form [label][int],
        with label and int both optional. Missing int will default to 0.
        """
        if not field:
            return 0

        # get the positions of the label/int parts
        ll = rr = 0
        for ch in field:
            if not ch.isalpha(): break
            ll += 1
        for ch in reversed(field):
            if not ch.isnumeric(): break
            rr += 1

        if ll + rr < len(field):
            raise

        return int(field[ll:]) if rr else 0

    @staticmethod
    def _versionBit(value) -> int:
        """Return the last bit of the integer conversion of the version-field.
        """
        return int(VersionString._validateField(value) or 0) & 0x01

    def _bitHash(self) -> int:
        """Return the last bits of major/minor/micro/release.
        CCPN Internal - used by update to check whether the version is incrementing.

          Example: version '3.20.15.12' => 0b11010
        """
        from operator import or_
        from functools import reduce

        bits = reduce(or_, (self._versionBit(val) << shift
                            for shift, val in enumerate([self.release,
                                                         self.microVersion,
                                                         self.minorVersion,
                                                         self.majorVersion,
                                                         '1',  # add high bit to ensure code >= 16
                                                         ])
                            )
                      )
        if _DEBUG:
            print(bin(bits))

        return bits

    def __len__(self):
        return len(self.fields)

    def __getitem__(self, item):
        return self.fields[item]

    @staticmethod
    def _getSortField(field) -> tuple:
        """Return the release field as a tuple(<label>, <int>) if exist, for sorting.
        """
        if not field:
            return ('', 0)

        ll = rr = 0
        for ch in field:
            if not ch.isalpha(): break
            ll += 1
        for ch in reversed(field):
            if not ch.isnumeric(): break
            rr += 1

        return (field[:ll], int(field[ll:])) if rr else (field, 0)

    def __eq__(self, other):
        """Check if self equals other
        """
        if isinstance(other, str):
            try:
                other = VersionString(other)
            except ValueError:
                return False

        if len(self) != len(other):
            return False

        return all(fs == fo for fs, fo in zip(self.fields, other.fields))

    def __lt__(self, other):
        """Check if self is lower than other;
         raise Value Error if other is an invalid object.
         Presence of development field implies an earlier version (i.e. __lt__ is True) compared to
         the absence of the field
        """
        if isinstance(other, str):
            other = VersionString(other)

        fields_S = self.fields
        fields_O = other.fields

        for fs, fo in zip(fields_S[:3], fields_O[:3]):
            if int(fs) != int(fo):
                return int(fs) < int(fo)
        # At this point, majorVersion, minorVersion and revision are all equal
        # Check development field
        if len(fields_S) == 4 and len(fields_O) == 3:
            return self._getSortField(fields_S[3]) < self._getSortField('')

        elif len(fields_S) == 3 and len(fields_O) == 4:
            return self._getSortField('') < self._getSortField(fields_O[3])

        elif len(fields_S) == 4 and len(fields_O) == 4:
            return self._getSortField(fields_S[3]) < self._getSortField(fields_O[3])

        return False

    def __gt__(self, other):
        """Check if self is greater than other;
         raise Value Error if other is an invalid object.
         Presence of development field implies an earlier version (i.e. __gt__ is False) compared to
         the absence of the field
        """
        if isinstance(other, str):
            other = VersionString(other)

        fields_S = self.fields
        fields_O = other.fields

        for fs, fo in zip(fields_S[:3], fields_O[:3]):
            if int(fs) != int(fo):
                return int(fs) > int(fo)
        # At this point, majorVersion, minorVersion and revision are all equal
        # Check development field
        if len(fields_S) == 4 and len(fields_O) == 3:
            return self._getSortField(fields_S[3]) > self._getSortField('')

        elif len(fields_S) == 3 and len(fields_O) == 4:
            return self._getSortField('') > self._getSortField(fields_O[3])

        elif len(fields_S) == 4 and len(fields_O) == 4:
            return self._getSortField(fields_S[3]) > self._getSortField(fields_O[3])

        return False

    def __le__(self, other):
        return self.__lt__(other) or self.__eq__(other)

    def __ge__(self, other):
        return self.__gt__(other) or self.__eq__(other)


#=========================================================================================
# Top level application version
# - also imported by git pre-commit
# - previous is included as a reference (not currently used)
#=========================================================================================

_previousApplicationVersion = VersionString('3.2.6')
applicationVersion = VersionString('3.2.7')
_lastApplicationVersion = VersionString('4.0.0')  # hide any messages beyond this point
revision = '3'


#=========================================================================================
# main - quick validation
#=========================================================================================

def main():
    """Quick validation for versionString.
    """
    # check versionString creation
    valid = []
    for ver in ['3.21.13',
                '3.2.1.',
                '3.20.15.13',
                '3.2.1.alpha',
                '3.2.1.alpha1',

                '3.2.1.123alpha',
                '3.2.1.alp2ha',
                '3.2.1.3er2',
                '3.2.1.%',
                '3.2.1. ',
                '3.2.1.alpha 34',

                'alpha.2.1.',
                '3.alpha.1.',
                '3.2.alpha1.',
                'alpha.2.1.23',

                '1.23',
                '3.2.1.23.2',
                ]:
        try:
            val = VersionString(ver)._bitHash()
            print(f'--> bit_hash   {val}:{bin(val)}')
            valid.append(True)
        except Exception as es:
            print('assert fail: {:<20}  {}'.format(ver, es))
            valid.append(False)

    assert valid == [True, True, True, True, True,
                     False, False, False, False, False, False,
                     False, False, False, False,
                     False, False]

    # check sorting conditions
    valid = [VersionString('3.2.1.alpha19') > VersionString('3.2.1.alpha2'),
             VersionString('3.2.1.alpha2') < VersionString('3.2.1.alpha19'),
             VersionString('3.2.1.2') < VersionString('3.2.1.alpha19'),
             VersionString('3.2.1.alpha2') > VersionString('3.2.1.19'),
             VersionString('3.2.1.45') > VersionString('3.2.1.23'),
             VersionString('1.0.0.0') < VersionString('2.0.0.0'),
             VersionString('1.1.0.0') < VersionString('1.2.0.0'),
             VersionString('1.0.1.0') < VersionString('1.0.2.0'),
             VersionString('1.0.0.1') < VersionString('1.0.0.2'),
             VersionString('2.0.0.0') > VersionString('1.0.0.0'),
             VersionString('1.2.0.0') > VersionString('1.1.0.0'),
             VersionString('1.0.2.0') > VersionString('1.0.1.0'),
             VersionString('1.0.0.2') > VersionString('1.0.0.1'),
             # missing digit is assumed to be '' or 0
             VersionString('1.1.1.1') > VersionString('1.1.1'),
             VersionString('1.1.1') > VersionString('1.1.1.1'),
             VersionString('1.1.1.1') < VersionString('1.1.1'),
             VersionString('1.1.1') < VersionString('1.1.1.1'),
             ]
    print('\n'.join([str(bb) for bb in valid]))

    assert valid == [True, True, True, True, True,
                     True, True, True, True,
                     True, True, True, True,
                     True, False, False, True]

    # check only one argument allowed
    try:
        VersionString()
    except Exception as es:
        print('assert fail: {:<20}  {}'.format('', es))
    try:
        VersionString('4.3.2.1', '1.1.1.1')
    except Exception as es:
        print('assert fail: {:<20}  {}'.format('', es))

    from datetime import datetime, timezone

    timeformat = '%Y-%m-%d %H:%M:%S %z'
    timeoutput = '0000-00-00 00:00:00 +0000'
    now = datetime.now(timezone.utc)

    then = datetime.strptime(__dateModified__[len('$dateModified: '): len('$dateModified: ') + len(timeoutput)],
                             timeformat)

    print(timeformat)
    print(now.strftime(timeformat), int(now.timestamp()))
    print(then.strftime(timeformat), then.timestamp())
    print(int((now - then).total_seconds()))


if __name__ == '__main__':
    main()
