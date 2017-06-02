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
    mSkip = False

    mLock = None
    """Just a counter, count seconds"""
    mCurIteration = 0
    """Current file name displaying"""
    displayingMedia = None

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
        self.mLock = threading.Lock()

    def bindWebServer(self, webServer=None):
        '''Link the active web server and retrieve the working folder'''
        self.mWebs = webServer
        self.mFolder = self.mWebs.getWorkingFolder()
    
    def findChromecasts(self):
        self.mFoundChromecasts = pychromecast.get_chromecasts()
    
    def printChromecasts(self):
        '''Return a string containing the Chromecasts in range'''
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
        '''Connect to a Chromecast in range, given the name'''
        self.mFoundChromecasts = pychromecast.get_chromecasts()
        self.mChromecast = next(cc for cc in self.mFoundChromecasts if cc.device.friendly_name == name)
        if self.mChromecast is not None:
            self.mChromecast.wait()
            self.mConnected = True
            return "Found device " + str(self.mChromecast.device) + " is " + str(self.mChromecast.status)
        else:
            return name + " was not found"

    def start(self,):
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
                mc.tear_down()
            self.mChromecast.quit_app()
            self.mChromecast.disconnect()
            self.mChromecast.join()

    def __is_number__(self, s):
        try:
            int(s)
            return True
        except ValueError:
            return False

    def changeSlideShowTimeout(self, newTimer):
        if newTimer is None or not self.__is_number__(newTimer):
            print("Pass a valid timeout")
            return

        intVal = int(newTimer)
        if intVal == self.mDCycle or intVal <= 0 or intVal > 60:
            '''No change to the current slideshow time'''
            return

        self.mLock.acquire()
        try:
            if intVal < self.mDCycle:
                self.mSkip = True
                self.mDCycle = intVal
            else:
                self.mDCycle = intVal
        finally:
            self.mLock.release()

    def skipCurrentMedia(self):
        self.mLock.acquire()
        try:
            self.mSkip = True
        finally:
            self.mLock.release()

    def __multiple_file_types__(self, *patterns):
        return it.chain.from_iterable(glob.iglob(self.mFolder + "/" + pattern) for pattern in patterns)

    def __find_media_and_order_by_date__(self):
        types = ('*.jpg', '*.jpeg', '*.mp4', '*.png', '*.gif')
        files_grabbed = []
        for extension in types:
            files_grabbed.extend(glob.glob(self.mFolder + "/" + extension))
        files_grabbed.sort(key=os.path.getmtime)
        return files_grabbed

    def cycle(self):

        starttime = time.time()

        """Iterate till mStop is requested each second"""
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
            
            self.mLock.acquire()
            try:
                localCyclingTimeout = self.mDCycle
                localSkip = self.mSkip
            finally:
                self.mLock.release()

            if self.mCurIteration % localCyclingTimeout == 0 or localSkip:

                self.mCurIteration = 0

                '''If a video is playing and we are not in skip, do not change it'''
                if not localSkip:
                    mc = self.mChromecast.media_controller
                    if not mc.status is None:
                        if not mc.status.media_is_photo and mc.status.player_is_playing:
                            '''Skip increment and re-check next second'''
                            time.sleep(1.0 - ((time.time() - starttime) % 1.0))
                            continue

                '''Restore skip to false'''
                if localSkip is True:
                    self.mLock.acquire()
                    try:
                        self.mSkip = False
                    finally:
                        self.mLock.release()

                """If we reached the slideshow cycle, store the value"""
                if self.displayingMedia is not None:
                    entry = self.mOldFiles.get(self.displayingMedia)
                    randInt = random.randint(1, 1000)
                    """If None it's the first time we are going to store it"""
                    if entry is None:
                        self.prio_queue.put((1, randInt, self.displayingMedia))
                        self.mOldFiles[self.displayingMedia] = 1
                    else:
                        newPrioInt = entry + 1
                        self.prio_queue.put((newPrioInt, randInt, self.displayingMedia))
                        self.mOldFiles[self.displayingMedia] = newPrioInt
                
                if len(self.mDeque) > 0:
                    """Check whether we have something new to display"""
                    self.displayingMedia = self.mDeque.popleft()
                else:
                    """If nothing new, we get from the random priority old story"""
                    associatedPrio, associatedRandom, self.displayingMedia = self.prio_queue.get()
                    if self.displayingMedia is None:
                        continue


                associatedMime = self.mFilesMime[self.displayingMedia]
                
                string = str(str(self.mBaseAddress) + "/" + str(self.displayingMedia))
                strMime = str(associatedMime)
                # print("casting ", str(self.displayingMedia))

                mc.play_media(string, strMime)
                mc.block_until_active()
                mc.pause()
                mc.play()
                delayChange = 2.1
            else:
                delayChange = 0
            
            self.mCurIteration = self.mCurIteration + 1

            time.sleep(1.0 + delayChange - ((time.time() - starttime) % 1.0))
