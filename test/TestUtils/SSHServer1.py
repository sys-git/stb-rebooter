#!/usr/bin/env python

# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

from multiprocessing.process import Process
from twisted.conch import avatar
from twisted.conch.checkers import SSHPublicKeyDatabase
from twisted.conch.ssh import factory, userauth, connection, keys, session
from twisted.cred import portal, checkers
from twisted.internet import reactor, protocol
from twisted.python import components, log
from zope.interface import implements
import sys
#import pydevd
log.startLogging(sys.stderr)

"""
Example of running another protocol over an SSH channel.
log in with username "user" and password "password".
"""

class ExampleAvatar(avatar.ConchUser):

    def __init__(self, username):
        avatar.ConchUser.__init__(self)
        self.username = username
        self.channelLookup.update({'session':session.SSHSession})

        self.shell = "/bin/bash"

class ExampleRealm:
    implements(portal.IRealm)

    def requestAvatar(self, avatarId, mind, *interfaces):
        return interfaces[0], ExampleAvatar(avatarId), lambda: None

class EchoProtocol(protocol.Protocol):
    """this is our example protocol that we will run over SSH
    """
    def dataReceived(self, data):
        sys.stderr.write("Echo rx: <%(D)s>"%{"D":data})
        if data == '\r':
            data = '\r\n'
        elif data == '\x03': #^C
            self.transport.loseConnection()
            return
        self.transport.write(data)

class STBProtocol(protocol.Protocol):
    """this is our STB protocol that we will run over SSH
    """
    RESPONSE_OK = "\n"
    def dataReceived(self, data):
        sys.stderr.write("STB rx: <%(D)s>"%{"D":data})
        if data == '\x03': #^C
            self.transport.loseConnection()
            return
        if data.strip()==STBProtocol.REBOOT:
            self.transport.write(STBProtocol.RESPONSE_OK)
        else:
            self.transport.write("error: <%(D)s>"%{"D":data})

class PDUeXProtocol(protocol.Protocol):
    """this is our PDUeX protocol that we will run over SSH
    """
    RESPONSE_OK = "\n"
    def dataReceived(self, data):
        sys.stderr.write("PDUeX rx: <%(D)s>"%{"D":data})
        if data == '\x03': #^C
            self.transport.loseConnection()
            return
        if data.strip()==STBProtocol.REBOOT:
            self.transport.write(PDUeXProtocol.RESPONSE_OK)
        else:
            self.transport.write("error: <%(D)s>"%{"D":data})

publicKey = 'ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAGEArzJx8OYOnJmzf4tfBEvLi8DVPrJ3/c9k2I/Az64fxjHf9imyRJbixtQhlH9lfNjUIx+4LmrJH5QNRsFporcHDKOTwTTYLh5KmRpslkYHRivcJSkbh/C+BR3utDS555mV'

privateKey = """-----BEGIN RSA PRIVATE KEY-----
MIIByAIBAAJhAK8ycfDmDpyZs3+LXwRLy4vA1T6yd/3PZNiPwM+uH8Yx3/YpskSW
4sbUIZR/ZXzY1CMfuC5qyR+UDUbBaaK3Bwyjk8E02C4eSpkabJZGB0Yr3CUpG4fw
vgUd7rQ0ueeZlQIBIwJgbh+1VZfr7WftK5lu7MHtqE1S1vPWZQYE3+VUn8yJADyb
Z4fsZaCrzW9lkIqXkE3GIY+ojdhZhkO1gbG0118sIgphwSWKRxK0mvh6ERxKqIt1
xJEJO74EykXZV4oNJ8sjAjEA3J9r2ZghVhGN6V8DnQrTk24Td0E8hU8AcP0FVP+8
PQm/g/aXf2QQkQT+omdHVEJrAjEAy0pL0EBH6EVS98evDCBtQw22OZT52qXlAwZ2
gyTriKFVoqjeEjt3SZKKqXHSApP/AjBLpF99zcJJZRq2abgYlf9lv1chkrWqDHUu
DZttmYJeEfiFBBavVYIF1dOlZT0G8jMCMBc7sOSZodFnAiryP+Qg9otSBjJ3bQML
pSTqy7c3a2AScC/YyOwkDaICHnnD3XyjMwIxALRzl0tQEKMXs6hH8ToUdlLROCrP
EhQ0wahUTCk1gKA4uPD6TMTChavbh4K63OvbKg==
-----END RSA PRIVATE KEY-----"""


class InMemoryPublicKeyChecker(SSHPublicKeyDatabase):

    def checkKey(self, credentials):
        return credentials.username == 'user' and \
            keys.Key.fromString(data=publicKey).blob() == credentials.blob

class ExampleSession:
    def __init__(self, avatar):
        """
        We don't use it, but the adapter is passed the avatar as its first
        argument.
        """
        self.user = avatar

    def getPty(self, term, windowSize, attrs):
        pass
    
    def execCommand(self, proto, cmd):
#        raise Exception("no executing commands")
        sys.stderr.write("execCommand: %(P)s"%{"P":cmd})
        cmd = (self.user.shell, "-c", cmd)
        reactor.spawnProcess(proto, self.user.shell, cmd)                       #@UndefinedVariable

    def openShell(self, trans):
        sys.stderr.write("openShell: %(P)s"%{"P":trans})
        ep = EchoProtocol()
        ep.makeConnection(trans)
        trans.makeConnection(session.wrapProtocol(ep))

    def eofReceived(self):
        pass

    def closed(self):
        pass

components.registerAdapter(ExampleSession, ExampleAvatar, session.ISession)

class ExampleFactory(factory.SSHFactory):
    publicKeys = {
        'ssh-rsa': keys.Key.fromString(data=publicKey)
    }
    privateKeys = {
        'ssh-rsa': keys.Key.fromString(data=privateKey)
    }
    services = {
        'ssh-userauth': userauth.SSHUserAuthServer,
        'ssh-connection': connection.SSHConnection
    }

class ProtocolEnumerator(object):
    ECHO = "ECHO"
    STB = "STB"
    PDUeX = "PDUeX"
    @staticmethod
    def get(value):
        if value==ProtocolEnumerator.ECHO:
            return EchoProtocol
        elif value==ProtocolEnumerator.STB:
            return STBProtocol
        elif value==ProtocolEnumerator.PDUeX:
            return PDUeXProtocol

class SSHServer1(Process):
    def __init__(self, sem, port=2022, protocol=ProtocolEnumerator.ECHO, users={}):
        Process.__init__(self, name = "SSHServer")
        self.port = port
        self.users = users
        self.privateKeys = {}
        self.publicKeys = {}
        self.protocol_ = protocol
        self.exitCmd = "exit"
        self.messages = []
        self.sem = sem
    def run(self):
        sys.stderr.write("> RUNNING <\n")
        self.protocol = ProtocolEnumerator.get(self.protocol_)
#        pydevd.settrace(stdoutToServer = True, stderrToServer = True)
        sys.stderr.write("Running server with protocol: %(P)s\n"%{"P":str(self.protocol_)})
        self.sem.release()
        portal_ = portal.Portal(ExampleRealm())
        passwdDB = checkers.InMemoryUsernamePasswordDatabaseDontUse()
        for user, password in self.users.items():
            passwdDB.addUser(user, password)
        portal_.registerChecker(passwdDB)
        portal_.registerChecker(InMemoryPublicKeyChecker())
        ExampleFactory.portal = portal_
        reactor.listenTCP(self.port, ExampleFactory())                          #@UndefinedVariable
        reactor.run()                                                           #@UndefinedVariable

