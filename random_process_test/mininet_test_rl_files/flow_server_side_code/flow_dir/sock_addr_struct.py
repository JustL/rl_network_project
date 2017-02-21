'''
This file contains C struct that are required by Linux socket programming.
The sturcutres use the same names as the Linux ones so that it would be
easier to understand this file and extedn it in the future if Linux changes its socket API.

For more reference please refer to the Linux counterparts.
'''

from ctypes import Structure
from ctypes import c_uint32
from ctypes import c_ushort
from ctypes import c_uint16
from ctypes import c_char


'''
The Internet Address class stores an IPv4 address.
'''
class In_Address(Structure):
    _fields_ = [("s_addr", c_uint32)]


'''
The Socket Address Interet class stores values that its Linux
counterpart stores.
'''
class Sockaddr_In(Structure):
    _fields_ = [("sin_family", c_ushort), ("sin_port", c_uint16), ("sin_addr", In_Address), ("sin_zero", (c_char*8))]

