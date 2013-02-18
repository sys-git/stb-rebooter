'''
Created on 19 Nov 2012

@author: francis
'''

from Rebooter.Core.Command import Command
from Rebooter.Core.Errors.InvalidTargetError import InvalidTargetError
from Rebooter.Core.Errors.RebootFailure import RebootFailure
from Rebooter.Core.RebooterType import RebooterType
from Rebooter.Core.Synchroniser.TransactionAborted import TransactionAborted
from Rebooter.Core.Target.BaseTarget import BaseTarget
from Rebooter.Core.Target.SSHTarget import SSHTarget
from Rebooter.Impl.Ssh.SshType import SshType
from Rebooter.RebooterFactory import RebooterFactory
from TestUtils.SSHServer1 import SSHServer1, STBProtocol, ProtocolEnumerator
from multiprocessing.synchronize import Semaphore
import copy
import sys
import unittest

sshType = SshType.SIMULATOR
sshServer = None
eResponse = None

#    SSH Params:
if sshType==SshType.STB:
    username = "xxx"
    password = "zzz"
    port = 22
    echoMode = True
    target = SSHTarget("192.168.16.140",
                        port=port,
                        username=username,
                        password=password,
                        sshType=sshType)
elif sshType==SshType.PDUeX:
    assert False, "PDU not supported for these tests!"
elif sshType==SshType.SIMULATOR:
    #    @FIXME: Simulator doesn't work?!
    #    Run on the simulator:
    username = "user"
    password = "user"
    port = 2023
    echoMode = False
    eResponse = STBProtocol.RESPONSE_OK
    target = SSHTarget("127.0.0.1",
                        port=port,
                        username=username,
                        password=password,
                        sshType=sshType)

def setup_module():
    if sshType==SshType.SIMULATOR:
        global sshServer
        sem = Semaphore(0)
        sshServer = SSHServer1(sem, port=port, protocol=ProtocolEnumerator.STB, users={username: password})
        sshServer.start()
        sem.acquire()
        pass

def teardown_module():
    if sshType==SshType.SIMULATOR:
        global sshServer
        try:    sshServer.terminate()
        except: pass

class TestSshRebooter(unittest.TestCase):
    CMD_REBOOT = "reboot -f"
    r"""
    @attention: These tests ask an STB to echo back a string, which we wait for.
    """
    def setUp(self):
        self.port = port
        self.username = username
        self.password = password
        self.echoMode = echoMode
        self.target = copy.deepcopy(target)
    def tearDown(self):
        try:    self.rebooter.terminate()
        except: pass
    def testSSH(self):
        if self.echoMode:
            eResult = "hello world!"
            cmd = "echo '%(E)s'"%{"E":eResult}
        else:
            cmd = TestSshRebooter.CMD_REBOOT
            global eResponse
            eResult = eResponse
        #    Use the defaultCommand:
        self.rebooter = RebooterFactory(RebooterType.SSH, self.target, defaultCommand=cmd)
        result = self.rebooter.reboot()
        try:
            Command.waitForSuccess(result, eResult, 5)
        except RebootFailure, _e:
            sys.stderr.write("Command failed!")
            raise
        else:
            sys.stderr.write("Command ok!")
        #    Now specify a command directly:
        if self.echoMode:
            eResult = ">>> >> > boo! < << <<<"
            cmd = "echo '%(E)s'"%{"E":eResult}
        else:
            cmd = TestSshRebooter.CMD_REBOOT
            global eResponse
            eResult = eResponse
        result = self.rebooter.reboot(command=cmd)
        try:
            Command.waitForSuccess(result, eResult, 5)
        except RebootFailure, _e:
            sys.stderr.write("Command failed!")
            raise
        else:
            sys.stderr.write("Command ok!")
    def testInvalidTargetError(self):
        target = BaseTarget()
        try:
            RebooterFactory(RebooterType.SSH, target)
        except InvalidTargetError:
            assert True
        else:
            assert False
    def testRebootPostTerminate(self):
        #    1st reboot:
        if self.echoMode:
            eResult = "hello world!"
            cmd = "echo '%(E)s'"%{"E":eResult}
        else:
            cmd = TestSshRebooter.CMD_REBOOT
            global eResponse
            eResult = eResponse
        self.rebooter = RebooterFactory(RebooterType.SSH, self.target, defaultCommand=cmd)
        result = self.rebooter.reboot()
        try:
            Command.waitForSuccess(result, eResult, 5)
        except RebootFailure, _e:
            sys.stderr.write("Command failed!")
            raise
        else:
            sys.stderr.write("Command ok!")
        #    Now terminate:
        self.rebooter.terminate()
        #    Now 2nd reboot:
        try:
            self.rebooter.reboot(cmd)
        except RebootFailure, e:
            assert isinstance(e.message, TransactionAborted)
        else:
            assert False

if __name__ == '__main__':
    unittest.main()
