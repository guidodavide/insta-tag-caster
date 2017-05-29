'''
Created on May 13, 2017

@author: guido
'''

from SimpleHTTPServer import SimpleHTTPRequestHandler
from BaseHTTPServer import HTTPServer

import os
import urllib
import posixpath
import threading
import urllib2
import socket

PORT = 8080
NAME = "Insta-Caching-WebServer"

class RootedHTTPServer(HTTPServer):

    stopped = False
    allow_reuse_address = True

    def __init__(self, base_path, *args, **kwargs):
        HTTPServer.__init__(self, *args, **kwargs)
        self.RequestHandlerClass.base_path = base_path
        
    def serve_forever(self):
        while not self.stopped:
            self.handle_request()
    
    def force_stop(self):
        self.stopped = True
        try:
            urllib2.urlopen(
                'http://%s:%s/' % (self.server_name, self.server_port))
        except urllib2.URLError:
            # If the server is already shut down, we receive a socket error,
            # which we ignore.
            pass
        self.server_close()


class RootedHTTPRequestHandler(SimpleHTTPRequestHandler):

    def translate_path(self, path):
        path = posixpath.normpath(urllib.unquote(path))
        words = path.split('/')
        words = filter(None, words)
        path = self.base_path
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir):
                continue
            path = os.path.join(path, word)
        return path


class WebServerClass(object):
    '''
    classdocs
    '''
    mRunning = False
    mMyIp = None
    mServingAddress = None


    def __init__(self, folder=None):
        '''
        Constructor
        '''
        if folder is None:
            self.mFolder = '.'
        else:
            self.mFolder = folder
        
        if isinstance(self.mFolder, basestring):
            pass
        
        if os.path.isabs(self.mFolder):
            pass
        else:
            self.mFolder = os.path.join(os.getcwd(), self.mFolder)
        
        if not os.path.exists(self.mFolder):
            os.makedirs(self.mFolder)
            
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        self.mMyIp = s.getsockname()[0]
        s.close()

        self.startServingRequests()

    def getWorkingFolder(self):
        return self.mFolder
    
    def getBaseAddress(self):
        return self.mServingAddress

    def startServingRequests(self):
        RootedHTTPServer.allow_reuse_address = True
        self.mHttpd = RootedHTTPServer(self.mFolder, ('', PORT), RootedHTTPRequestHandler)
        sa = self.mHttpd.socket.getsockname()
        
        self.mThread = threading.Thread(target=self.mHttpd.serve_forever, name=NAME)
        self.mThread.daemon = True
        self.mThread.start()
        print "Serving HTTP ", NAME, " on ", self.mMyIp, "port", sa[1], "-> folder:\n", self.mFolder
        self.mRunnnig = True
        self.mServingAddress = str("http://"+str(self.mMyIp)+":"+str(sa[1]))

    def stopServingRequests(self):
        if not self.mThread is None and not self.mHttpd is None:
            self.mHttpd.force_stop()
            self.mThread.join(None)  
        self.mRunnnig = False
    
    def isRunning(self):
        if self.mRunnnig:
            return True
        else:
            return False
        
