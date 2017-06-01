'''
Created on May 13, 2017

@author: guido
'''

from __future__ import print_function
import time
import pychromecast
import os
from os.path import basename
import itertools as it, glob
import threading
import mimetypes
from collections import deque
import Queue as queue
import random

class CasterThread(object):
    '''
    classdocs
    '''
    mFolder = None
    mBaseAddress = None
    mThread = None
    
    mStop = False
    mConnected = False
    mThreadStarted = False
    
    mFoundChromecasts = None
    mChromecast = None
    mWebs = None
    
    mFilesMime = None
    mDeque = None
    mDCycle = 0

    def __init__(self, dutyCycle=10):
        '''
        Constructor
        '''
        self.mDCycle = dutyCycle
        '''Most recent files are in mDeque'''
        self.mDeque = deque([])
        '''Randomness'''
        self.prio_queue = queue.PriorityQueue()
        '''Just to keep track of known (indexed) files'''
        self.mFilesMime = {}
        '''Just to keep track of old files'''
        self.mOldFiles = {}

    def bindWebServer(self, webServer=None):
        self.mWebs = webServer
        self.mFolder = self.mWebs.getWorkingFolder()
    
    def findChromecasts(self):
        self.mFoundChromecasts = pychromecast.get_chromecasts()
    
    def printChromecasts(self):
        if self.mFoundChromecasts is not None and len(self.mFoundChromecasts) > 0:
            string = 'Chromecasts in range: '
            for cc in self.mFoundChromecasts:
                string += cc.device.friendly_name + "\n"
            return string
        else:
            return "Please, search again.. no Chromecasts found"
            

    def isStarted(self):
        if self.mThreadStarted:
            return True
        else:
            return False

    def isConnected(self):
        if self.mConnected:
            return True
        else:
            return False

    def connectTo(self, name):
        self.mFoundChromecasts = pychromecast.get_chromecasts()
        self.mChromecast = next(cc for cc in self.mFoundChromecasts if cc.device.friendly_name == name)
        if self.mChromecast is not None:
            self.mChromecast.wait()
            self.mConnected = True
            return "Found device " + str(self.mChromecast.device) + " is " + str(self.mChromecast.status)
        else:
            return name + " was not found"

    def start(self, ):
        self.mBaseAddress = self.mWebs.getBaseAddress()
        self.mThread = threading.Thread(target=self.cycle, name="CasterThread")
        self.mThread.daemon = True
        self.mThread.start()
        self.mThreadStarted = True
    
    def stop(self):
        if self.mThreadStarted:
            self.mThreadStarted = False
            self.mStop = True
            self.mThread.join(None)
        if self.mConnected:
            mc = self.mChromecast.media_controller
            if mc is not None:
                mc.stop()
                mc.tear_down
            self.mChromecast.disconnect()
            self.mChromecast.join()
     
    def __multiple_file_types__(self, *patterns):
        return it.chain.from_iterable(glob.iglob(self.mFolder+"/"+pattern) for pattern in patterns)

    def __find_media_and_order_by_date__(self):
        files = glob.glob(self.mFolder + "/*")
        files.sort(key=os.path.getmtime)
        return files

    def cycle(self):
        
        """Just a counter, count seconds"""
        currentIteration = 0
        """Current file name displaying"""
        displayingName = None
        
        """Iterate till mStop is requested"""
        while not self.mStop:

            """Look for all files in folder and order by date"""
            for filename in self.__find_media_and_order_by_date__():
                base = basename(filename)
                entry = self.mFilesMime.get(base)
                """If it is the first time we see it, add to the displaying list"""
                if entry is None:
                    mime = mimetypes.MimeTypes().guess_type(filename)[0]
                    self.mFilesMime[base] = mime
                    self.mDeque.append(base)
            
            if currentIteration % self.mDCycle == 0:
                mc = self.mChromecast.media_controller
                if not mc.status is None:
                    if not mc.status.media_is_photo and mc.status.player_is_playing:
                        time.sleep(1)
                        continue

                """If we reached the slideshow cycle, store the value"""
                if displayingName is not None:
                    entry = self.mOldFiles.get(displayingName)
                    randInt = random.randint(1, 200)
                    """If None it's the first time we are going to store it"""
                    if entry is None:
                        self.prio_queue.put((1, randInt, displayingName))
                        self.mOldFiles[displayingName] = 1
                    else:
                        newPrioInt = entry + 1
                        self.prio_queue.put((newPrioInt, randInt, displayingName))
                        self.mOldFiles[displayingName] = newPrioInt
                
                if len(self.mDeque) > 0:
                    """Check whether we have something new to display"""
                    displayingName = self.mDeque.popleft()
                else:
                    """If nothing new, we get from the random priority old story"""
                    associatedPrio, associatedRandom, displayingName = self.prio_queue.get()
                    if displayingName is None:
                        continue


                associatedMime = self.mFilesMime[displayingName]
                
                string = str(str(self.mBaseAddress)+"/"+str(displayingName))
                strMime = str(associatedMime)
                print("displaying url ", string)

                mc.play_media(string, strMime)
                mc.block_until_active()
                mc.pause()
                mc.play()
            
            currentIteration = currentIteration + 1

            time.sleep(1)
            

        