'''
Created on 20 Nov 2012

@author: francis
'''

from Rebooter.Core.Errors.UnknownRebooterType import UnknownRebooterType
from Rebooter.Core.RebooterType import RebooterType
from Rebooter.Core.Target.PduSshTarget import PduSshTarget
from Rebooter.Core.Target.SSHTarget import SSHTarget
from Rebooter.Impl.Pdu.PduRebooter import PduRebooter
from Rebooter.RebooterFactory import RebooterFactory
import unittest

class TestFactory(unittest.TestCase):
    def setUp(self):
        pass
    def tearDown(self):
        try:    self.rebooter.terminate()
        except: pass
        PduRebooter.impls = {}
    def testUnknown(self):
        try:
            RebooterFactory(RebooterType.UNKNOWN)
        except UnknownRebooterType:
            assert True
        else:
            assert False
    def testSsh(self):
        target = SSHTarget("127.0.0.1")
        self.rebooter = RebooterFactory(RebooterType.SSH, target)
    def testPduSsh(self):
        target = PduSshTarget("127.0.0.1", mapping={"127.0.0.1":0})
        self.rebooter = RebooterFactory(RebooterType.PDUeX_8, RebooterType.SSH, target)

if __name__ == '__main__':
    unittest.main()
