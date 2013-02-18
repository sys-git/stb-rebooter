'''
Created on 19 Nov 2012

@author: francis
'''

from Rebooter.Core.Errors.UnknownRebooterType import UnknownRebooterType
from Rebooter.Core.RebooterType import RebooterType
from Rebooter.Impl.Pdu.PduRebooter import PduRebooter
from Rebooter.Impl.Ssh.SshRebooter import SshRebooter

class RebooterFactory(object):
    def __new__(self, type_, *args, **kwargs):
        if type_==RebooterType.SSH:
            return SshRebooter(*args, **kwargs)
        elif type_==RebooterType.PDUeX_8:
            return PduRebooter(self, *args, **kwargs)
        raise UnknownRebooterType(type_)
