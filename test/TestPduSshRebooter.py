'''
Created on 19 Nov 2012

@author: francis
'''

from Rebooter.Core.Errors.InvalidTargetError import InvalidTargetError
from Rebooter.Core.Errors.RebootFailure import RebootFailure
from Rebooter.Core.Errors.UnknownRebooterType import UnknownRebooterType
from Rebooter.Core.RebooterType import RebooterType
from Rebooter.Core.Synchroniser.TransactionAborted import TransactionAborted
from Rebooter.Core.Target.PduSshTarget import PduSshTarget
from Rebooter.Core.Target.SSHTarget import SSHTarget
from Rebooter.Impl.Pdu.InvalidPduType import InvalidPduType
from Rebooter.Impl.Pdu.PduRebooter import PduRebooter
from Rebooter.Impl.Ssh.SshType import SshType
from Rebooter.RebooterFactory import RebooterFactory
from TestUtils.SSHServer1 import SSHServer1, PDUeXProtocol, ProtocolEnumerator
from multiprocessing.synchronize import Semaphore
import copy
import threading
import unittest

sshType = SshType.PDUeX
sshServer = None

#    SSH Params:
if sshType==SshType.STB:
    #    STB:
    echoMode = True
    port = 22
    username = "xxx"
    password = "yyy"
    eResponse = None
    target = PduSshTarget("192.168.16.140",
                           port=port,
                           username=username,
                           password=password,
                           sshType=sshType,
                           )
elif sshType==SshType.PDUeX:
    #    PDU:
    echoMode = False
    port = 22
    username = "admin"
    password = "admin"
    eResponse = None
    target = PduSshTarget("192.168.16.78",
                           port=port,
                           username=username,
                           password=password,
                           postConnectionTimeout=0,
                           sendBufferTimeout=2,
                           sshType=sshType,
                           )
elif sshType==SshType.SIMULATOR:
    #    STB:
    echoMode = False
    port = 2023
    username = "user"
    password = "user"
    eResponse = PDUeXProtocol.RESPONSE_OK
    target = PduSshTarget("127.0.0.1",
                           port=port,
                           username=username,
                           password=password,
                           sshType=sshType,
                           )

def setup_module():
    if sshType==SshType.SIMULATOR:
        global sshServer
        sem = Semaphore(0)
        sshServer = SSHServer1(sem, port=port, protocol=ProtocolEnumerator.PDUeX, users={username: password})
        sshServer.start()
        sem.acquire()
        pass

def teardown_module():
    if sshType==SshType.SIMULATOR:
        global sshServer
        try:    sshServer.terminate()
        except: pass

class TestPduSshRebooter(unittest.TestCase):
    def setUp(self):
        self.target = copy.deepcopy(target)
        #    PDU params:
        self.target.setMapping({"127.0.0.1":1, "127.0.0.2":2, "127.0.0.3":3})
        self.timeoutCycle = 2
        self.timeoutCommand = 20
        self.timeoutResponse = 5
        global eResponse
        self.kwargs = {"timeoutCycle":self.timeoutCycle,
                       "timeoutCommand":self.timeoutCommand,
                       "timeoutResponse":self.timeoutResponse,
                       "echoMode":echoMode,
                       "eResponse":eResponse,
        }
    def tearDown(self):
        try:    self.rebooter.terminate()
        except: pass
        PduRebooter.impls = {}
    def testOn(self):
        self.rebooter = RebooterFactory(RebooterType.PDUeX_8, RebooterType.SSH, self.target, **copy.deepcopy(self.kwargs))
        self.rebooter.on("127.0.0.1")
        self.rebooter.on("127.0.0.2")
        self.rebooter.on("127.0.0.3")
    def testOff(self):
        self.rebooter = RebooterFactory(RebooterType.PDUeX_8, RebooterType.SSH, self.target, **copy.deepcopy(self.kwargs))
        self.rebooter.off("127.0.0.1")
        self.rebooter.off("127.0.0.2")
        self.rebooter.off("127.0.0.3")
    def testRebooter(self):
        self.rebooter = RebooterFactory(RebooterType.PDUeX_8, RebooterType.SSH, self.target, **copy.deepcopy(self.kwargs))
        self.rebooter.reboot("127.0.0.1")
        self.rebooter.reboot("127.0.0.2")
        self.rebooter.reboot("127.0.0.3")
    def testCycle(self):
        self.rebooter = RebooterFactory(RebooterType.PDUeX_8, RebooterType.SSH, self.target, **copy.deepcopy(self.kwargs))
        self.rebooter.cycle("127.0.0.1")
        self.rebooter.cycle("127.0.0.2")
        self.rebooter.cycle("127.0.0.3")
    def testInvalidTargetError(self):
        target = SSHTarget("192.168.16.140")
        try:
            RebooterFactory(RebooterType.PDUeX_8, RebooterType.SSH, target, **copy.deepcopy(self.kwargs))
        except InvalidTargetError:
            assert True
        else:
            assert False
    def testPduUnknown(self):
        try:
            RebooterFactory(RebooterType.PDUeX_8, RebooterType.UNKNOWN, self.target, **copy.deepcopy(self.kwargs))
        except UnknownRebooterType:
            assert True
        else:
            assert False
    def testPduPdu(self):
        try:
            RebooterFactory(RebooterType.PDUeX_8, RebooterType.PDUeX_8, self.target, **copy.deepcopy(self.kwargs))
        except InvalidPduType:
            assert True
        else:
            assert False
    def testRebootPostTerminate(self):
        self.rebooter = RebooterFactory(RebooterType.PDUeX_8, RebooterType.SSH, self.target, **copy.deepcopy(self.kwargs))
        self.rebooter.cycle("127.0.0.1")
        self.rebooter.terminate()
        try:
            self.rebooter.cycle("127.0.0.1")
        except RebootFailure, e:
            assert isinstance(e.message, TransactionAborted)
        else:
            assert False
    def testConcurrentReboots(self):
        #    The PduSshRebooter is thread-safe!
        self.rebooter = RebooterFactory(RebooterType.PDUeX_8, RebooterType.SSH, self.target, **copy.deepcopy(self.kwargs))
        def cycle(ip, sem):
            self.rebooter.cycle(ip)
            sem.release()
        sem = Semaphore(0)
        threading.Timer(1, cycle, args=["127.0.0.1", sem]).start()
        threading.Timer(1, cycle, args=["127.0.0.2", sem]).start()
        threading.Timer(1, cycle, args=["127.0.0.3", sem]).start()
        sem.acquire()
        sem.acquire()
        sem.acquire()
    def testRebootDuringConcurrentReboots(self):
        #    The PduSshRebooter is thread-safe!
        self.rebooter = RebooterFactory(RebooterType.PDUeX_8, RebooterType.SSH, self.target, **copy.deepcopy(self.kwargs))
        results = {}
        def cycle(ip, sem):
            try:
                self.rebooter.cycle(ip)
            except Exception, e:
                results[ip] = e
            sem.release()
        def terminate():
            self.rebooter.terminate()
        sem = Semaphore(0)
        threading.Timer(1, cycle, args=["127.0.0.1", sem]).start()
        threading.Timer(1, cycle, args=["127.0.0.2", sem]).start()
        threading.Timer(1, cycle, args=["127.0.0.3", sem]).start()
        threading.Timer(2, terminate).start()
        sem.acquire()
        sem.acquire()
        sem.acquire()
        assert not sem.acquire(block=True, timeout=5)
        #    Expect 3 RebootFailure(TransactionAborted)'s.
        for result in results.values():
            assert isinstance(result, RebootFailure)
            assert isinstance(result.message, TransactionAborted)

if __name__ == '__main__':
    unittest.main()
