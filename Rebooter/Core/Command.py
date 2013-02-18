'''
Created on 14 Nov 2012

@author: francis
'''

import time
from Rebooter.Core.Errors.RebootFailure import RebootFailure


class Command(object):
    SEND = "SEND"
    SENT = "SENT"
    RESPONSE = "RESPONSE"
    TERMINATE = "TERMINATE" 
    WORKER_FINISHED = "WORKER_FINISHED"
    def __init__(self, cmd, tId=None, msg=None, time_=None):
        self._cmd = cmd
        self._tId = tId
        self._msg = msg
        if time_==None:
            time_=time.time()
        self._time = time_
    def cmd(self):
        return self._cmd
    def tId(self):
        return self._tId
    def setTid(self, tId):
        self._tId = tId
    def msg(self):
        return self._msg
    def time(self):
        return self._time
    def __str__(self):
        dd = []
        tId = self.tId()
        if tId!=None:
            dd.append(" tId: %(T)s"%{"T":tId})
        msg = self.msg()
        if msg!=None:
            #    truncate the msg to 32 chars:
            msg = str(msg)
            msg = msg[:min(len(msg), 128)]
            dd.append(" msg: <%(M)s>"%{"M":msg})
        d = ",".join(dd)
        return "Command: %(C)s%(D)s @ %(T)s"%{"C":self.cmd(), "T":self.time(), "D":d}
    @staticmethod
    def waitForSuccess(generator, eResult, timeout):
#        eResult = eResult.strip()
        maxTimeout = time.time()+timeout
        while time.time()<maxTimeout:
            remainingTime = maxTimeout-time.time()
            result = generator(remainingTime)
            if not result:
                raise RebootFailure(timeout)
            #    Is the expected string there?
#            data = result.msg().strip()
            data = result.msg()
            if eResult in data:
                return
        raise RebootFailure(timeout)
