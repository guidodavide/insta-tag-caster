'''
Created on May 13, 2017

@author: guido
'''

from __future__ import print_function
import time
import pychromecast
from os.path import basename
import itertools as it, glob
import threading
import mimetypes
from collections import deque
from WebServer import WebServerClass

class CasterThread(object):
    '''
    classdocs
    '''
    mFolder = None
    mBaseAddress = None
    mStop = False
    mTread = None
    mFoundChromecasts = None
    mChromecast = None
    mWebs = None
    
    mFilesMime = None
    mDeque = None
    mDCycle = 0

    def __init__(self, folder=None, dutyCycle=10, webServer=None):
        '''
        Constructor
        '''
        self.mFolder = folder
        self.mDCycle = dutyCycle
        self.mDeque = deque([])
        self.mFilesMime = {}
        self.mWebs = webServer

    def start(self, ):
        self.mBaseAddress = self.mWebs.getBaseAddress()
        self.mThread = threading.Thread(target=self.cycle, name="CasterThread")
        self.mThread.daemon = True
        self.mThread.start()
    
    def connectTo(self, name):
        self.mFoundChromecasts = pychromecast.get_chromecasts()
        self.mChromecast = next(cc for cc in self.mFoundChromecasts if cc.device.friendly_name == name)
        if self.mChromecast is not None:
            self.mChromecast.wait()
            print("Found device ", self.mChromecast.device)
            print("Is ", self.mChromecast.status)
        else:
            print("%s was not found", name)
    
    def stop(self):
        self.mStop = True
        self.mThread.join(None)
     
    def __multiple_file_types__(self, *patterns):
        return it.chain.from_iterable(glob.iglob(self.mFolder+"/"+pattern) for pattern in patterns)

    def cycle(self):
        
        currentIteration = 0
        displayingName = None
        
        while not self.mStop:

            for filename in self.__multiple_file_types__("*.jpg",
                                                         "*.png",
                                                         "*.bmp",
                                                         "*.jpeg",
                                                         "*.gif",
                                                         "*.mp4",
                                                         "*.avi"):
                base = basename(filename)
                entry = self.mFilesMime.get(base)
                if entry is None:
                    mime = mimetypes.MimeTypes().guess_type(filename)[0]
                    self.mFilesMime[base] = mime
                    self.mDeque.append(base)
            
            if currentIteration % self.mDCycle == 0:
                if displayingName is not None:
                    self.mDeque.append(displayingName)
                currentIteration = currentIteration + 1
                displayingName = self.mDeque.popleft()
                associatedMime = self.mFilesMime[displayingName]
                mc = self.mChromecast.media_controller
                string = str(str(self.mBaseAddress)+"/"+str(displayingName))
                strMime = str(associatedMime)
                print("displaying url ", string)
                if not mc.status is None:
                    if not mc.status.media_is_photo and mc.status.player_is_playing:
                        currentIteration = currentIteration - 1
                        time.sleep(1)
                        continue
                mc.play_media(string, strMime)
                mc.block_until_active()
                mc.pause()
                mc.play()
            else:
                currentIteration = currentIteration + 1
               
            time.sleep(1)
            

        