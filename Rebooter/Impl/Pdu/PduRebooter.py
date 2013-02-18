'''
Created on 19 Nov 2012

@author: francis
'''

from Rebooter.Core.Command import Command
from Rebooter.Core.Errors.InvalidTargetError import InvalidTargetError
from Rebooter.Core.Errors.RebootFailure import RebootFailure
from Rebooter.Core.RebooterType import RebooterType
from Rebooter.Core.Target.BasePduTarget import BasePduTarget
from Rebooter.Core.Target.PduSshTarget import PduSshTarget
from Rebooter.Impl.Pdu.InvalidPduType import InvalidPduType
from Rebooter.Impl.Pdu.PduRebootError import PduRebootError
import sys
import time

class PduRebooter(object):
    _MINIMUM_CYCLE_TIMEOUT = 2
    RESULT_OK = "Operate success."
    r"""
    @attention: Responsible for multiplexing a single SshRebooter.
    """
    def __init__(self, rebooterFactory, type_, target, timeoutCycle=None, timeoutCommand=1, timeoutResponse=5, echoMode=False, eResponse=None):
        if not isinstance(target, BasePduTarget):
            raise InvalidTargetError(target)
        if type_==RebooterType.PDUeX_8:
            raise InvalidPduType(type_)
        self._target = target
        self._mapping = target.mapping()
        self._echoMode = echoMode
        if eResponse==None:
            if self._echoMode==False:
                eResponse = PduRebooter.RESULT_OK
        self._eResponse = eResponse
        self._impl = rebooterFactory(type_, target)
        if timeoutCycle==None or timeoutCycle<PduRebooter._MINIMUM_CYCLE_TIMEOUT:
            timeoutCycle = PduRebooter._MINIMUM_CYCLE_TIMEOUT
        self._timeoutCycle = timeoutCycle             #    Between OFF and ON.
        self._timeoutCommand = timeoutCommand         #    Between CONNECTION AND SENT.
        self._timeoutResponse = timeoutResponse       #    Between SEND and SUCCESSFUL RESPONSE.
    def terminate(self, timeout=None):
        return self._impl.terminate()
    def isIpMapped(self, ip):
        return ip in self._mapping.keys()
    def isPortMapped(self, port):
        return port in self._mapping.values()
    def setMapItem(self, ip, port):
        self._mapping[ip] = port
    def getMappedIp(self, ip):
        return self._mapping[ip]
    def getMappedPort(self, port):
        for ip, port_ in self._mapping.items():
            if port_==port:
                return ip
    def reboot(self, ip):
        return self.cycle(ip)
    def _port(self, ip):
        return self._mapping[ip]
    def cycle(self, ip, timeout=None):
        r"""
        @summary: Turn the PDU port OFF then ON.
        """
        if timeout==None or timeout<PduRebooter._MINIMUM_CYCLE_TIMEOUT:
            timeout = self._timeoutCycle
        self.off(ip)
        timeout = self._timeoutCycle
        if timeout!=None and timeout>0:
            time.sleep(timeout)
        self.on(ip)
    def on(self, ip):
        r"""
        @summary: Turn the PDU port ON
        """
        cmd = eResult = "PDU ON 1-A%(I)s"%{"I":self._port(ip)}
        if self._echoMode==True:
            cmd = "echo '%(E)s'"%{"E":eResult}
        else:
            eResult = self._eResponse
        timeout = self._timeoutCommand
        result = self._impl.reboot(command=cmd, timeout=timeout)
        #    Now wait for 'operation success'
        try:
            Command.waitForSuccess(result, eResult, self._timeoutResponse)
        except RebootFailure, e:
            sys.stderr.write("PDU sent ON fail!")
            raise PduRebootError(e)
        else:
            sys.stderr.write("PDU sent ON ok!")
    def off(self, ip):
        r"""
        @summary: Turn the PDU port OFF
        """
        cmd = eResult = "PDU OFF 1-A%(I)s"%{"I":self._port(ip)}
        if self._echoMode==True:
            cmd = "echo '%(E)s'"%{"E":eResult}
        else:
            eResult = self._eResponse
        timeout = self._timeoutCommand
        result = self._impl.reboot(command=cmd, timeout=timeout)
        #    Now wait for 'operation success'
        try:
            Command.waitForSuccess(result, eResult, self._timeoutResponse)
        except RebootFailure, e:
            sys.stderr.write("PDU sent OFF fail!")
            raise PduRebootError(e)
        else:
            sys.stderr.write("PDU sent OFF ok!")

if __name__ == '__main__':
    target = PduSshTarget("192.168.16.140", username="root", password="onlydebug")
    #    3 STBs:
    target.setMapping({"127.0.0.2":0, "127.0.0.2":1, "127.0.0.3":2})
    rebooter = PduRebooter(RebooterType.SSH, target)
    rebooter.reboot("127.0.0.2")
    rebooter.terminate()
    print "done!"




