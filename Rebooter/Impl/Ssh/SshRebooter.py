'''
Created on 16 Nov 2012

@author: francis
'''

from Queue import Empty, Full
from Rebooter.Core.Command import Command
from Rebooter.Core.Errors.InvalidTargetError import InvalidTargetError
from Rebooter.Core.Errors.NoCommandError import NoCommandError
from Rebooter.Core.Errors.RebootFailure import RebootFailure
from Rebooter.Core.Synchroniser.Synchroniser import Synchroniser
from Rebooter.Core.Synchroniser.TransactionAborted import TransactionAborted
from Rebooter.Core.Target.BaseSshTarget import BaseSshTarget
from Rebooter.Core.Target.SSHTarget import SSHTarget
from Rebooter.Impl.Ssh.SshProcess import bootstrapSshProcess
from Rebooter.Impl.Ssh.SshSendFailedError import SshSendFailedError
from Rebooter.Impl.Ssh.UnknownSshCommandError import UnknownSshCommandError
from multiprocessing.queues import Queue
from multiprocessing.synchronize import Semaphore
import sys
import threading
import traceback

class SshRebooter(object):
    r"""
    @summary: Reboots a target using SSH.
    boot the SshProcess.
    create one process per target.
    """
    def __init__(self, target, defaultCommand=None):
        if not isinstance(target, BaseSshTarget):
            raise InvalidTargetError(target)
        self._target = target
        self._defaultCommand = defaultCommand
        self._sendBufferTimeout = target.sendBufferTimeout()
        self._qRx = Queue()
        self._qTx = Queue()
        self._synchroniser = Synchroniser()
        self._sendMutex = Semaphore(1)
        self._threads = {"rx":None}
        self._close = False
        self._process = None
        self._startLock = Semaphore(1)
    def _start(self):
        with self._startLock:
            self._synchroniser.checkDestroyed()
            if self._process!=None:
                return
            try:
                sem = Semaphore(0)
                self._process = bootstrapSshProcess(self._target, self._qRx, self._qTx, sem)
                sem.acquire()
                #    Now start the read thread:
                t = threading.Thread(target=self._rx)
                t.setName("SSHRebooter_%(T)s"%{"T":self._target.uId()})
                t.setDaemon(True)
                t.start()
                self._threads["rx"] = t
            except Exception, _e:
                #    Cleanup.
                self.terminate()
    def _rx(self):
        exc = None
        try:
            while self._close==False:
                #    Read responses from the qRx and pipe them to the synchroniser:
                try:
                    data = self._qRx.get(block=True, timeout=0.1)
                except Empty:
                    pass
                else:
                    if not isinstance(data, Command):
                        sys.stderr.write("Unknown response received: <%(R)s>\n"%{"R":str(data)})
                        raise UnknownSshCommandError(data)
                    elif data.cmd()==Command.WORKER_FINISHED:
                        self._close = True
                        break
                        #    Worker finished, that's it!
                    tId = data.tId()        #    Client's transaction identifier.
                    #    Release the transaction:
                    sys.stderr.write("Releasing transaction: %(T)s: %(R)s\n"%{"T":tId, "R":str(data)})
                    self._synchroniser.release(tId, data)
        except Exception, exc:
            pass
        finally:
            kwargs = {}
            if exc!=None:
                kwargs["exc"] = exc
            self._synchroniser.destroy(**kwargs)
            sys.stderr.write("rx thread finished\n")
    def terminate(self, timeout=None):
        r"""
        @attention: Do not call from the _rx thread!
        """
        self._synchroniser.destroy()
        try:
            self._qTx.put(Command(Command.TERMINATE))
        except:
            pass
        else:
            #    Now wait for the Rx thread to close:
            self._close = True
            try:
                self._threads["rx"].join(timeout)
            except:
                pass
            self._threads["rx"] = None
        self._process.join(5)
        try:
            self._process.terminate()
        except:
            pass
        self._process = None
        try:    self._qRx.close()
        except: pass
        self._qRx = None
        try:    self._qTx.close()
        except: pass
        self._qTx = None
    def _allowSend(self):
        timeout = self._sendBufferTimeout
        if (timeout==None) or (timeout<=0):
            self._sendMutex.release()
            return
        t = threading.Timer(timeout, self._sendMutex.release)
        t.setName("allowMutex_%(T)s"%{"T":timeout})
        t.setDaemon(True)
        t.start()
    def reboot(self, command=None, timeout=None):
        if command==None:
            command = self._defaultCommand
        if (command==None) or (len(command)==0):
            raise NoCommandError()
        #    Ask for permission to send.
        self._sendMutex.acquire()
        try:
            #    Start the process if not already started:
            self._start()
            tId = self._synchroniser.create()
            try:
                self._qTx.put(Command(Command.SEND, tId=tId, msg=command))
            except Full:
                #    Queue has been closed:
                raise TransactionAborted()
            #    Now wait for the 'sent' response.
            data = self._synchroniser.acquire(tId, timeout=timeout)
            cmd = data.cmd()        #    Command
            msg = data.msg()
            if cmd==Command.WORKER_FINISHED:
                #    Externally terminated!
                sys.stderr.write("Interrupted command: <%(C)s>\n"%{"C":command})
                raise RebootFailure(cmd)
            if cmd!=Command.SENT:
                sys.stderr.write("Unexpected response to command: <%(C)s>: %(R)s\n"%{"C":command, "R":cmd})
                raise RebootFailure(cmd)
            elif isinstance(msg, SshSendFailedError):
                sys.stderr.write("Failed to send command: <%(C)s>: %(R)s\n"%{"C":command, "R":msg})
                raise RebootFailure(msg)
            #    Command is SENT!
            def getResult(tOut=None):
                return self._synchroniser.acquire(tId, timeout=tOut)
            return getResult
        except TransactionAborted, e:
            sys.stderr.write("Reboot command aborted: <%(C)s>:\n%(T)s\n"%{"C":command, "T":traceback.format_exc()})
            raise RebootFailure(e)
        else:
            sys.stderr.write("Reboot command successful: <%(C)s>\n"%{"C":command})
        finally:
            #    Allow permission to send.
            self._allowSend()

if __name__ == '__main__':
    t = SSHTarget("192.168.16.140", "root", "onlydebug")
    eResult = "hello world!"
    rebooter = SshRebooter(t, defaultCommand="echo '%(E)s'"%{"E":eResult})
    result = rebooter.reboot(waitForResponse=True)
    assert result.strip()==eResult
    sys.stderr.write("RESULT:::::\n\n%(R)s\n"%{"R":result})
    eResult = ">>> >> > boo! < << <<<"
    result = rebooter.reboot(command="echo '%(E)s'"%{"E":eResult}, waitForResponse=True)
    assert result.strip()==eResult
    sys.stderr.write("RESULT:::::\n\n%(R)s\n"%{"R":result})
    rebooter.terminate()

    sys.stderr.write("done!\n")

