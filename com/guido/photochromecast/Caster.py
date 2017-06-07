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

# Uncomment to enable very verbose pychromecast logging
#import logging

# The socket connection is being setup
CONNECTION_STATUS_CONNECTING = "CONNECTING"
# The socket connection was complete
CONNECTION_STATUS_CONNECTED = "CONNECTED"
# The socket connection has been disconnected
CONNECTION_STATUS_DISCONNECTED = "DISCONNECTED"
# Connecting to socket failed (after a CONNECTION_STATUS_CONNECTING)
CONNECTION_STATUS_FAILED = "FAILED"
# The socket connection was lost and needs to be retried
CONNECTION_STATUS_LOST = "LOST"

# Video is Playing
MEDIA_PLAYER_STATE_PLAYING = "PLAYING"
# Video is Buffering
MEDIA_PLAYER_STATE_BUFFERING = "BUFFERING"
# Video is Paused
MEDIA_PLAYER_STATE_PAUSED = "PAUSED"
# Idle, but maybe displaying a picture :D
MEDIA_PLAYER_STATE_IDLE = "IDLE"
# When pychromecast does not recognize the state :/
MEDIA_PLAYER_STATE_UNKNOWN = "UNKNOWN"

# Max connection failures
MAX_CONNECTION_FAILURES_IN_A_ROW = 10
# Max reconnection retries in a row
MAX_RECONNECTION_RETRIES_IN_A_ROW = 3
# Max timeout between a play request and a real ACK from Chromecast
MAX_PLAYING_REQ_TIMEOUT = 5.0
# Max length of a video on instagram
MAX_INSTAGRAM_VIDEO_DURATION = 10
# Max timeout between an ACK of play and real status change
MAX_PLAYING_STATUS_UPDATE_DELAY = 15.0

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
    mRetryConnection = False
    pendingWaitOnStart = False
    photoIsReallyStarted = False
    videoIsReallyStarted = False
    displayingVideo = False
    videoDuration = 0
    connectionLost = False
    prepareForDisconnection = False
    failTriggers = 0
    
    mFilesMime = None
    mDeque = None
    mDCycle = 0
    mSkip = False
    mPause = False

    mLock = None
    """Just a counter, count seconds"""
    mCurIteration = 0
    """Current file name displaying"""
    displayingMedia = None

    mCaster = None

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
        self.mBlacklistSet = set()
        self.mCaster = self
        # Uncomment to enable very verbose pychromecast logging
        #logging.basicConfig(level=logging.DEBUG)

    def bindWebServer(self, webServer=None):
        '''Link the active web server and retrieve the working folder.'''
        self.mWebs = webServer
        self.mFolder = self.mWebs.getWorkingFolder()
    
    def findChromecasts(self):
        """Finds all chromecasts in range and stores them internally."""
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
        found = False
        if name is not None:
            print("Try connecting to " + str(name))
        self.mFoundChromecasts = pychromecast.get_chromecasts()
        for cc in self.mFoundChromecasts:
            if cc.device.friendly_name == name:
                found = True
                self.mChromecast = cc

        if not found:
            return str(name) + " is not in range"

        if self.mChromecast is not None:
            self.mChromecast.wait()
            self.mConnected = True
            #print("Found device " + str(self.mChromecast.device) + " is " + str(self.mChromecast.status))
            return "Ready to start!"
        else:
            return name + " was not found"

    def start(self,):
        """Starts casting on a connected Chromecast. Any foreground app will be terminated."""
        if not self.mConnected:
            return "Caster is not connected!"

        self.mBaseAddress = self.mWebs.getBaseAddress()
        self.mThread = threading.Thread(target=self.cycle, name="CasterThread")
        self.mThread.daemon = True

        print("Now starting!")
        self.__quit_app__()
        self.__register_listener__()

        self.mThread.start()
        self.mThreadStarted = True

    def stop(self):
        """Stops completely an active Chromecast and disconnects from it."""
        if self.mThreadStarted:
            self.mThreadStarted = False
            self.mStop = True
            self.mThread.join(None)
        if self.mConnected:
            mc = self.mChromecast.media_controller
            if mc is not None:
                mc.stop()
                mc.tear_down()
            self.__quit_app__(wait=False)
            self.mChromecast.disconnect()
            self.mChromecast.join()

    def __is_number__(self, s):
        """Checks whether the passed value is really a number."""
        try:
            int(s)
            return True
        except ValueError:
            return False

    def getSlideShowTimeout(self):
        """Returns the slideshow timing in use."""
        return self.mDCycle

    def changeSlideShowTimeout(self, newTimer):
        """Sets the new passed value as the new slideshow timeout."""
        if newTimer is None or not self.__is_number__(newTimer):
            print("Pass a valid timeout")
            return

        intVal = int(newTimer)
        if intVal == self.mDCycle or intVal <= 5 or intVal > 120:
            '''No change to the current slideshow time'''
            print("Pass a timeout between 6 and 120 seconds")
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
        """Skips the current media displaying on the Chromecast."""
        if self.mThreadStarted:
            self.mLock.acquire()
            try:
                self.mSkip = True
            finally:
                self.mLock.release()
        else:
            print("Maybe you have to start casting first?")

    def pauseOnMedia(self):
        if self.mThreadStarted:
            self.mLock.acquire()
            try:
                self.mPause = True
            finally:
                self.mLock.release()
        else:
            print("Maybe you have to start casting first?")

    def resumeMedia(self):
        if self.mThreadStarted:
            self.mLock.acquire()
            try:
                self.mPause = False
            finally:
                self.mLock.release()
        else:
            print("Maybe you have to start casting first?")

    def removeMedia(self, name=None):
        """Removes the current displaying media from the slideshow queue.
        Pass a name to remove a specific one."""
        if name is not None:
            entry = self.mFilesMime.get(name)
            # If the passed name is something 'known'
            if entry is not None:
                self.mBlacklistSet.add(name)
                currentActive = None
                self.mLock.acquire()
                try:
                    currentActive = self.displayingMedia
                finally:
                    self.mLock.release()
                # If the current media displaying is really the requested one
                if currentActive == name:
                    self.skipCurrentMedia()
                    print(str(currentActive) + " is blacklisted now")
            else:
                print("Media does not exist")
        else:
            # Remove the current one active from the slideshow
            blackListedEntry = None
            self.mLock.acquire()
            try:
                blackListedEntry = self.displayingMedia
                self.displayingMedia = None
            finally:
                self.mLock.release()

            print(str(blackListedEntry) + " is blacklisted now")
            self.mBlacklistSet.add(blackListedEntry)
            self.skipCurrentMedia()


    def new_cast_status(self, new_status):
        """ Called when a new status is received from the Chromecast."""
        #print("new_cast_status: " + str(new_status))

    def new_media_status(self, new_status):
        """ Called when a new media status is received from the Chromecast."""
        #print("new_media_status: " + str(new_status))
        state = new_status.player_state
        content = new_status.content_id

        # Check if the main loop is waiting for a notification after start
        if self.pendingWaitOnStart:
            # Are we displaying really what we sent to Chromecast?
            if content is not None and self.displayingMedia in content:
                # PLAYING is received only for videos, photo keep Chromecast in IDLE
                if state is not None and MEDIA_PLAYER_STATE_PLAYING in state:
                    # We know that a Video is really started after buffering
                    self.videoIsReallyStarted = True
                    # Can we also get the real duration of the video?
                    duration = new_status.duration
                    if duration is not None:
                        self.videoDuration = duration
                    self.pendingWaitOnStart = False
                    return
                # If the main loop is not expecting to retrieve a video update, but a photo update
                elif self.displayingVideo is False:
                    self.photoIsReallyStarted = True
                    self.pendingWaitOnStart = False
                    return

    def new_connection_status(self, new_status):
        """ Called when a new connection status is received from the Chromecast."""
        #print("new_connection_status: " + str(new_status))
        # If it is lost, do not let pychromecast retry internally,
        # instead disconnect from Chromecast and re-connect
        if new_status.status == CONNECTION_STATUS_LOST:
            #pass  # Your code to turn off your speakers here.
            self.connectionLost = True
            self.prepareForDisconnection = False
            self.failTriggers = 0

        # It has been observed that sometimes the pychormecast library is not
        # able to connect again, and it switches continously between
        # connecting<->failed without reporting the LOST status(!)
        elif new_status.status == CONNECTION_STATUS_CONNECTING:
            # Prepare to handle a possible failure
            self.prepareForDisconnection = True

        elif new_status.status == CONNECTION_STATUS_CONNECTED:
            # reset enable triggers, we are connected for real
            self.prepareForDisconnection = False
            self.failTriggers = 0

        elif new_status.status == CONNECTION_STATUS_FAILED:
            self.failTriggers = self.failTriggers + 1
            # if we have reached the maximum failed reports, then trigger
            # the reconnection procedure.
            if self.prepareForDisconnection is True and self.failTriggers > MAX_CONNECTION_FAILURES_IN_A_ROW:
                self.connectionLost = True
                self.prepareForDisconnection = False
                self.failTriggers = 0

    def __register_listener__(self):
        """Registers this Caster as the listener to all the notifications from pychromecast."""
        self.mChromecast.media_controller.register_status_listener(self.mCaster)
        self.mChromecast.register_status_listener(self.mCaster)
        self.mChromecast.register_connection_listener(self.mCaster)

    def __find_media_and_order_by_date__(self, numOfPreviousFiles):
        """Finds all the media and sort by creation date."""
        types = ['*.jpg', '*.jpeg', '*.mp4', '*.png', '*.gif']
        files_grabbed = []
        for extension in types:
            files_grabbed.extend(glob.glob(self.mFolder + "/" + extension))
        if len(files_grabbed) is not numOfPreviousFiles:
            # A file might be removed from the folder while we sort the name
            # Consider a possible failure, and retry again later
            try:
                files_grabbed.sort(key=os.path.getmtime)
            except:
                files_grabbed = []
        return files_grabbed

    def __sleep_now__(self, chromecastDelay=0.0, starttime=0.0):
        """sleeps for just one second, add a delay through chromecast delay.
        Starttime is just the start time when the main thread really started looping."""
        timeout = 1.0 + chromecastDelay +  - ((time.time() - starttime) % 1.0)
        if timeout > 0:
            time.sleep(timeout)
        else:
            time.sleep(1)

    def __disconnect_active_stream_due_to_failure__(self, mc):
        """Destroys the mediacontroller passed and triggers the re-connection flag"""
        mc.tear_down()
        self.mRetryConnection = True

    def __quit_app__(self, wait=True):
        """Quits the active app on Chromecast and waits a bit."""
        if self.mChromecast is not None:
            self.mChromecast.quit_app()
            if wait:
                time.sleep(5)

    def __retry_reconnection__(self):
        """Retry to reconnect to the previous known Chromecast.
        Wait at most for 10 seconds."""
        # We are not reconnected yet
        reconnectedOK = False
        # Get previous name
        myName = self.mChromecast.device.friendly_name
        # Quit current app
        self.__quit_app__()

        # Search again from chromecasts
        self.findChromecasts()
        for cc in self.mFoundChromecasts:
            # If it is really again in range
            if cc.device.friendly_name == myName:
                self.mChromecast = cc
                pre = time.time()
                self.mChromecast.wait(10.0)
                now = (time.time()) - pre
                if now >= 10.0:
                    # If it takes more than 10 seconds to connect to it..
                    # return :(
                    return reconnectedOK
                # If it is connected now
                self.__quit_app__()

                # Success!
                self.mRetryConnection = False
                reconnectedOK = True
                self.__register_listener__()
                break
        return reconnectedOK

    def cycle(self):

        starttime = time.time()
        numOfFoundFiles = 0
        # Internally in use to sleep while playing a video
        # and sleep at most for the associated 'duration' time
        firstTimeSleepingForVideo = 0
        # Internally in use, just to keep track of max re-connection retries
        maxRetry = 0

        """Iterate till mStop is requested.
        Each second:
        - retry reconnection if requested
        - find new files in the passed folder and append them to the support data structures
        - if skip|slideshow timeout reached|connection lost, go on and
            * loop till the video finishes (only in video mode)
            * get the most recent new media file (if present)
            * retrieve a random 'old' media from the already shown list
            * check whether the selected media can be displaying (blacklist)
            * play it on Chromecast"""
        while not self.mStop:

            """Retry Connection due to a failure"""
            if self.mRetryConnection or self.connectionLost:
                if self.connectionLost:
                    mc = self.mChromecast.media_controller
                    self.__disconnect_active_stream_due_to_failure__(mc)
                    self.connectionLost = False

                reconnection = self.__retry_reconnection__()
                if reconnection is False and maxRetry < MAX_RECONNECTION_RETRIES_IN_A_ROW:
                    self.mRetryConnection = True
                    time.sleep(2)
                    maxRetry = maxRetry + 1
                    print("Trying again a re-connection...")
                    continue
                elif reconnection is True:
                    maxRetry = 0
                    continue
                else:
                    print("Unfortunately I was not able to connect to the same Chromecast again!\n" +
                          "Now stopping :(")
                    break;

            """Look for all files in folder and order by date"""
            listOfFiles = self.__find_media_and_order_by_date__(numOfFoundFiles)
            """Don't update internal data structures if there's no need"""
            if numOfFoundFiles is not len(listOfFiles):
                numOfFoundFiles = len(listOfFiles)

                for filename in listOfFiles:
                    base = basename(filename)
                    entry = self.mFilesMime.get(base)
                    """If it is the first time we see it, add to the displaying list"""
                    if entry is None and not entry in self.mBlacklistSet:
                        mime = mimetypes.MimeTypes().guess_type(filename)[0]
                        self.mFilesMime[base] = mime
                        self.mDeque.append(base)
            
            ####### Critical section here #######
            self.mLock.acquire()
            try:
                # Just take note of the current status of these variables
                localCyclingTimeout = self.mDCycle
                localSkip = self.mSkip
                localPause = self.mPause
            finally:
                self.mLock.release()
            ####### END - Critical section here #######

            """If we reached the timeout and we are not pausing on the current displayed media
            or a skip is force, then we need to change media casted"""
            if ((self.mCurIteration % localCyclingTimeout == 0 and not localPause)
                or localSkip or self.displayingVideo or self.connectionLost):

                """Reset cycle for the current media, stop counting seconds."""
                self.mCurIteration = 0

                '''If a video is playing and we are not in skip, do not change it. Wait its end.'''
                if not localSkip and not self.connectionLost:
                    mc = self.mChromecast.media_controller
                    if not mc.status is None:
                        if mc.status.supports_seek and mc.status.player_is_playing:
                            if firstTimeSleepingForVideo == 0:
                                firstTimeSleepingForVideo = time.time()
                            # Current time delta, from first sleep associated to the displaying video
                            now = (time.time()) - firstTimeSleepingForVideo
                            # Skip this check if we already know the connection is lost!
                            if now <= (self.videoDuration + 0.5) and not self.connectionLost:
                                '''Skip increment and re-check next second'''
                                self.__sleep_now__(0, starttime)
                                # go back to 'while' check
                                continue

                """ We are going to change, video will not be there anymore"""
                self.displayingVideo = False
                firstTimeSleepingForVideo = 0

                ####### Critical section here #######
                self.mLock.acquire()
                try:
                    '''Restore skip to false'''
                    self.mSkip = False

                    """If we reached the slideshow cycle, store the current showed media
                    in a 'oldFiles' data structure (with associated prio) and in a  priority queue"""
                    if self.displayingMedia is not None:
                        previousPriority = self.mOldFiles.get(self.displayingMedia)
                        randInt = random.randint(1, 1000)
                        """If None it's the first time we are going to store it in
                        the priority queue"""
                        if previousPriority is None:
                            self.prio_queue.put((1, randInt, self.displayingMedia))
                            self.mOldFiles[self.displayingMedia] = 1
                        else:
                            newPrioInt = previousPriority + 1
                            self.prio_queue.put((newPrioInt, randInt, self.displayingMedia))
                            self.mOldFiles[self.displayingMedia] = newPrioInt

                    """Now check for a 'next' media that needs to be casted - NEW first"""
                    if len(self.mDeque) > 0:
                        """Check whether we have something new to display, directly from folder"""
                        self.displayingMedia = self.mDeque.popleft()
                    elif not self.prio_queue.empty():
                        """If nothing new, we get from the random priority old story"""
                        prio, randomness, self.displayingMedia = self.prio_queue.get()

                    """If it is blacklisted do not go on, skip it."""
                    if self.displayingMedia in self.mBlacklistSet:
                        self.displayingMedia = None

                    """If I was not able to retrieve a media during this cycle, retry again later on..."""
                    if self.displayingMedia is None:
                        self.__sleep_now__(0, starttime)
                        continue

                    """If the file does not exist anymore, treat it as a blacklisted"""
                    if not os.path.isfile(self.mFolder + "/" + self.displayingMedia):
                        self.displayingMedia = None
                        self.__sleep_now__(0, starttime)
                        continue

                    associatedMime = self.mFilesMime[self.displayingMedia]
                finally:
                    self.mLock.release()
                ####### END - Critical section here #######

                """Prepare strings for chromecast interaction"""
                # URL
                string = str(str(self.mBaseAddress) + "/" + str(self.displayingMedia))
                # MIME type associated
                strMime = str(associatedMime)

                mc = self.mChromecast.media_controller
                mc.play_media(string, strMime)

                # Try to play it, and wait at most X seconds
                before = time.time()
                mc.block_until_active(MAX_PLAYING_REQ_TIMEOUT)
                now = (time.time()) - before

                # Sometimes block_until_active will block.. stuck mediaplayer due to a fucked up socket!
                if now >= MAX_PLAYING_REQ_TIMEOUT:
                    self.__disconnect_active_stream_due_to_failure__(mc)
                    continue

                # Wait for a status update directly from Chromecast
                self.pendingWaitOnStart = True

                self.photoIsReallyStarted = False
                self.videoIsReallyStarted = False
                # Assume at most 10 seconds if not communicated by Chromecast
                self.videoDuration = MAX_INSTAGRAM_VIDEO_DURATION

                if "image" not in strMime:
                    self.displayingVideo = True

                # Check if we really started
                oldTime = time.time()
                # Wait here till we get a real confirmation from the statuses update!
                while (not self.videoIsReallyStarted and not self.photoIsReallyStarted
                       and not self.mStop and not self.mSkip):
                    now = (time.time()) - oldTime
                    # If I'm waiting more then 10 second for an effective start
                    if now > MAX_PLAYING_STATUS_UPDATE_DELAY or self.connectionLost:
                        print("Still buffering, force reconnection")
                        self.displayingVideo = False
                        self.mCurIteration = 0
                        self.__disconnect_active_stream_due_to_failure__(mc)
                        break;
                    # Sleep quickly, update should be really in the next seconds
                    time.sleep(0.3)

                # Between a status update and a real screen refresh..it takes 2 seconds circa
                delayChange = 1.2
            else:
                delayChange = 0.0
            
            self.mCurIteration = self.mCurIteration + 1

            self.__sleep_now__(delayChange, starttime)
