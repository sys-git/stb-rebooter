'''
Created on 15 Nov 2012

@author: francis
'''

from Queue import Empty
from Rebooter.Core.Command import Command
from Rebooter.Impl.Ssh.SshClient import SshClientFactory
from twisted.internet import reactor
import sys
import traceback

class SshWorker(object):
    def __init__(self, target):
        self._target = target
    def __call__(self, qTx, qRx, sem, exitCmd="exit", closeOnData=False):
        sys.stderr.write("SshWorker thread: started.\n")
        if sem!=None:
            sem.release()
        self._qRx = qRx
        self._qTx = qTx
        err = None
        sshType = self._target.sshType()
        sys.stderr.write("SshWorker thread: sshType: %(T)s\n"%{"T":sshType})
        username = self._target.username()
        password = self._target.password()
        host = self._target.host()
        port = self._target.port()
        postConnectionTimeout = self._target.postConnectionTimeout()
        #    Create the channel/client factory:
        self.clientFactory = SshClientFactory(host,
                                              port,
                                              username,
                                              password,
                                              dataQ=self._qRx,
                                              exitCmd=exitCmd,
                                              postConnectionTimeout=postConnectionTimeout,
                                              sshType=sshType,
                                              )
        try:
            while True:
                if self._process()==False:
                    sys.stderr.write("SshWorker thread: exiting process loop.\n")
                    break
            sys.stderr.write("SshWorker thread: finished naturally.\n")
        except Exception, err:
            sys.stderr.write("SshWorker thread: unhandled error: %(T)s\n"%{"T":traceback.format_exc()})
        finally:
            sys.stderr.write("SshWorker thread: finished with err: %(E)s\n"%{"E":err})
            self._retire(Command(Command.WORKER_FINISHED, msg=err))
            sys.stderr.write("SshWorker thread: Stopping reactor\n")
            self.clientFactory.terminate()
            if reactor.running:     #@UndefinedVariable
                reactor.stop()       #@UndefinedVariable
    def _process(self):
        r"""
        @summary: This worker multiplexes the channels for a single target
        across qRx and qTx.
        """
        try:
            data = self._qRx.get(block=True, timeout=0.1)
        except Empty:
            pass
        else:
            cmd = data.cmd()        #    Command
            tId = data.tId()        #    Client's transaction identifier.
            msg = data.msg()        #    Command's data.
            sys.stderr.write("Process cmd: %(C)s, tId: %(TI)s\n"%{"TI": tId, "C":cmd})
            if cmd==Command.SEND:
                sys.stderr.write("Command.SEND[tId: %(T)s]: <%(C)s>\n"%{"C":msg, "T":tId})
                err = self._sendToClient(tId, msg)
                if err!=None:
                    #    Send error back immediately, there will be no further result!
                    self._retire(Command(Command.SENT, msg=err), tId=tId)
            elif cmd==Command.SENT:
                #    SSHClient sent the data, return this over out multiplex.
                self._retire(data)
            elif cmd==Command.RESPONSE:
                #    SSHClient received some data, return this over out multiplex.
                self._retire(data)
            elif cmd==Command.TERMINATE:
                return False
        return True
    def _sendToClient(self, tId, command):
        self.clientFactory.send(command, tId)
        sys.stderr.write("Sent data from tId: %(T)s.\n"%{"T":tId})
    def _retire(self, cmd, tId=None):
        if tId!=None:
            cmd.setTid(tId)
        try:
            sys.stderr.write("RETIRE: %(R)s\n"%{"R":cmd})
            self._qTx.put(cmd)
        except Exception, _e:
            sys.stderr.write("Unable to retire: <%(C)s>\n"%{"C":cmd})
        else:
            sys.stderr.write("RETIRED: %(R)s\n"%{"R":cmd})









