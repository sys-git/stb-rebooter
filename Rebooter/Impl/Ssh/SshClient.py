
from Rebooter.Core.Command import Command
from Rebooter.Impl.Ssh.SshSendFailedError import SshSendFailedError
from Rebooter.Impl.Ssh.SshType import SshType
from multiprocessing.synchronize import Semaphore
from twisted.conch.ssh import transport, userauth, connection, channel, common
from twisted.internet import defer, protocol, reactor, threads
import copy
import itertools
import sys
import time

class Status(object):
    CLOSED = 0
    SENT = -1
    CHANNEL = -2
    STARTED = -3
    PASSWORD = -4
    SECURED = -5
    VERIFIED = -6
    FAILURE = -7

class ClientTransport(transport.SSHClientTransport):
    def __init__(self, sshClientFactory):
        sys.stderr.write("Creating ClientTransport\n")
        self.sshClientFactory = sshClientFactory
        self.connection = None

    def verifyHostKey(self, hostKey, fingerprint):
        sys.stderr.write("verifyHostKey...\n")
        return defer.succeed(1)

    def connectionSecure(self):
        sys.stderr.write("Connection secured!\n")
        self.connection = ClientConnection(self.sshClientFactory)
        self.requestService(ClientUserAuth(self.sshClientFactory, self.connection))

    def connectionLost(self, reason):
        #    Connection is lost, do stuff - wrap up 
        if reactor.running:                  #@UndefinedVariable
            reactor.stop()                  #@UndefinedVariable

class SSHFactory(protocol.ClientFactory):
    def __init__(self, sshClientFactory):
        sys.stderr.write("Creating SSHFactory\n")
        self.protocol = ClientTransport
        self.sshClientFactory = sshClientFactory

    def buildProtocol(self, addr):
        sys.stderr.write("Building protocol for: %(A)s\n"%{"A":addr})
        p = self.protocol(self.sshClientFactory)
        p.factory = self
        return p

class ClientUserAuth(userauth.SSHUserAuthClient):
    def __init__(self, sshClientFactory, options):
        sys.stderr.write("Authenticating with user: %(U)s\n"%{"U":sshClientFactory.username})
        userauth.SSHUserAuthClient.__init__(self, sshClientFactory.username, options)
        self.sshClientFactory = sshClientFactory

    def getPassword(self, prompt = None):
        sys.stderr.write("getPassword: %(P)s\n"%{"P":self.sshClientFactory.password})
        return defer.succeed(self.sshClientFactory.password)

class ClientConnection(connection.SSHConnection):
    def __init__(self, sshClientFactory):
        connection.SSHConnection.__init__(self)
        self.sshClientFactory = sshClientFactory
        self.sshClientFactory.connection = self
        sys.stderr.write("connection: %(M)s\n"%{"M":self.sshClientFactory.connection})

    def serviceStarted(self):
        sys.stderr.write("serviceStarted...\n")
        self.sshClientFactory.serviceStarted()
#        sshClientData = ClientData(self.sshClientFactory)
#        self._openChannel(sshClientData)

    def _openChannel(self, sshClientData):
        sys.stderr.write("_openChannel...\n")
        channel = CatChannel(sshClientData, conn=self)
        sys.stderr.write("myChannel: %(C)s\n"%{"C":channel})
        self.openChannel(channel)

    def channelClosed(self, channel):
        sys.stderr.write("channelClosed %(D)s\n"%{"D":channel})
        connection.SSHConnection.channelClosed(self, channel)

    def openAChannel(self, sshClientData):
        sys.stderr.write("restartChannel for connection: %(D)s\n"%{"D":self})
        #    Now restart a channel for when we need it next:
        reactor.callLater(0, self._openChannel, sshClientData)  #@UndefinedVariable

class CatChannel(channel.SSHChannel):
    name = 'session'

    def __init__(self, sshClientData, localWindow = 0, localMaxPacket = 0,
        remoteWindow = 0, remoteMaxPacket = 0,
        conn = None, data = None, avatar = None):

        channel.SSHChannel.__init__(self, localWindow = localWindow,
            localMaxPacket = localMaxPacket, remoteWindow = remoteWindow,
            remoteMaxPacket = remoteMaxPacket, conn = conn, data = data,
            avatar = avatar)
        self.sshClientData = sshClientData
        self._d = None

    def channelOpen(self, data):
        sys.stderr.write("channelOpen %(D)s\n"%{"D":data})
#        self._sendData()
        self.write("\r")
        timeout = self.sshClientData.factory.postConnectionTimeout
        sys.stderr.write("Waiting %(D)s seconds before sending data...\n"%{"D":timeout})
        reactor.callLater(timeout, self._sendData) #@UndefinedVariable
        sys.stderr.write("channelOpen 1\n")

    def _sendData(self, ignored = None):
        #    Expect the channel to be closed after this send completes.
        if self.remoteClosed:
            return
        data = self.sshClientData
        #    Send the data:
        cmd = data.cmd
        if cmd!=None:
            sys.stderr.write("Tx: <%(C)s>\r\n"%{"C":cmd})
            #    Must copy, for some reason the data is destroyed on send by twisted!
            data.sentData = copy.deepcopy(cmd)
            if data.factory.sshType==SshType.STB:
                sys.stderr.write(">>> STB <<<\n")
                self._d = self.conn.sendRequest(self, 'exec', common.NS(cmd), wantReply=1)
                self._d.addCallback(self._notifySentOk, data.sentData)
            elif data.factory.sshType==SshType.PDUeX:
                #    Send no data initially
                sys.stderr.write(">>> PDUeX <<<\n")
                self._d = self.conn.sendRequest(self, 'exec', common.NS(''), wantReply=1)
                self._d.addCallback(self._cbSendRequest)
            elif data.factory.sshType==SshType.SIMULATOR:
                #    Send no data initially
                sys.stderr.write(">>> SIMULATOR <<<\n")
                self._d = self.conn.sendRequest(self, 'shell', common.NS(''), wantReply=1)
                self._d.addCallback(self._cbSendRequest)
            self._d.addErrback(self._sendFailed)

    def _cbSendRequest(self, ignored = None):
        data = self.sshClientData
        cmd = data.cmd
        self.write("%s\r" % cmd)
        self._notifySentOk(data.sentData)

    def _sendFailed(self, failure):
        sys.stderr.write("Send failed: %(F)s"%{"F":failure})
        #    Better inform our client that the command failed!
        self._notifySentData(SshSendFailedError(failure))
        #    And close this channel to the target (as before).
        self.close()

    def _notifySentOk(self, msg, ignore=None):
        sys.stderr.write("Send ok!: %(M)s"%{"M":msg})
        self._notifySentData(msg)

    def _notifySentData(self, msg):
        #    Data was dispatched to the remote-side, inform our client:
        try:
            data = self.sshClientData
            cmd = data.sentData
            tId = data.tId
            self.sshClientData.factory.dataQ.put(Command(Command.SENT, msg=cmd, tId=tId))
        except Exception, _e:
            #    Failure to send means it's all for closing...
            sys.stderr.write("notifySentData will close in 2 seconds...\n")
            reactor.callLater(2, self.close) #@UndefinedVariable

    def dataReceived(self, rx):
        data = self.sshClientData
        tId = data.tId
        sys.stderr.write("Rx: (tId: %(T)s)<%(D)s>\n"%{"D":rx, "T":tId})
        rc = Command(Command.RESPONSE, tId=tId, msg=rx)
        rcc = copy.deepcopy(rc)
        try:
            self.sshClientData.factory.dataQ.put(rcc)
        except Exception, _e:
            #    Q closed means it's all for closing...
            sys.stderr.write("Rx will close in 2 seconds [0]...\n"%{"D":data})
            reactor.callLater(2, self.close) #@UndefinedVariable
        else:
            sys.stderr.write("Rx data sent to dataQ!\n"%{"D":data})

    def close(self, ignored = None):
        sys.stderr.write("CLOSE called!\n")
        #    Attempt to cleanly close the channel:
        self.write("%s\r"%self.sshClientData.factory.exitCmd)
        self.loseConnection()

    def closed(self):
        sys.stderr.write("CatChannel.closed: %(S)s\n"%{"S":self})

    def closeReceived(self):
        #    Cancel any deferreds:
        if self._d!=None:
            self._d.cancel()
            self._d = None
        if self.sshClientData.factory.isClosing==False:
            sys.stderr.write("STB closed SSH!\n")
            self.loseConnection()

    def getCurrentDeferred(self):
        return self._d

class ClientData(object):
    r"""
    @summary: One client per channel (each channel 'exec's a single command only).
    """
    _uId = itertools.count(0)
    def __init__(self, factory, cmd=None, tId=None):
        self.cId = ClientData._uId.next()
        self.cmd = cmd
        self.tId = tId
        #
        self.sentData = None
        #
        self.factory = factory

class SshClientFactory(object):
    DEFAULT_PORT = 22
    def __init__(self, host, port, username, password, dataQ=None, exitCmd="exit", sshType=SshType.STB, postConnectionTimeout=0):
        self.username = username
        self.password = password
        self.exitCmd = exitCmd
        self.postConnectionTimeout = postConnectionTimeout
        self.host = host
        self.sshType = sshType
        if port==None:
            port = SshClientFactory.DEFAULT_PORT
        self.port = int(port)
        if dataQ==None:
            def dummyPut(*args, **kwargs):
                sys.stderr.write("SshClientFactory consumed data!\n")
            dataQ = dummyPut
        self.dataQ = dataQ
        #
        self.isClosing = False
        self.lastSendTime = time.time()
        #
        self.connection = None
        self.run()
    def run(self):
        sys.stderr.write("SshClientFactory running!\n")
        self.factory = SSHFactory(self)
        self.sem = Semaphore(0)
        def _connectLater():
            sys.stderr.write("SshClientFactory connecting asynchronously\n")
            reactor.connectTCP(self.host, self.port, self.factory)      #@UndefinedVariable
            sys.stderr.write("SshClientFactory connected\n")
        threads.blockingCallFromThread(reactor, _connectLater)          #@UndefinedVariable
        self.sem.acquire()
    def send(self, data, tId, timeout=None):
        client = ClientData(self, cmd=data, tId=tId)
        reactor.callFromThread(self.connection.openAChannel, client)       #@UndefinedVariable
    def terminate(self):
        self.isClosing = True
        if reactor.running:                  #@UndefinedVariable
            reactor.stop()                  #@UndefinedVariable
    def isOk(self):
        return reactor.running          #@UndefinedVariable
    def serviceStarted(self):
        self.sem.release()
