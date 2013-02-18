'''
Created on 15 Nov 2012

@author: francis
'''

from Rebooter.Impl.Ssh.SshWorker import SshWorker
from multiprocessing.process import Process
from twisted.internet import reactor
import threading

def SshProcess(target, qTx, qRx, sem):
    def startWorker(target, qTx, qRx, sem):
        t = threading.Thread(target=SshWorker(target), args=[qTx, qRx, sem])
        t.setName("ProcessWorker")
        t.setDaemon(True)
        t.start()
    print "starting worker..."
    startWorker(target, qTx, qRx, sem)
    reactor.run()   #@UndefinedVariable
    print "worker finished!"

def bootstrapSshProcess(target, qRx, qTx, sem):
    process = Process(target=SshProcess, args=[target, qRx, qTx, sem])
    process.start()
    return process
