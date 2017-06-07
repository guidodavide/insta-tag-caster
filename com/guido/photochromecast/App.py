'''
Created on May 13, 2017

@author: guido
'''

from cmd import Cmd
from WebServer import WebServerClass
from Caster import CasterThread

class MyPrompt(Cmd):
    '''
    It's like a main.
    A looping cmd prompt with basic commands for Cast interactions.
    '''
    # The Web Server, required to provide urls for Chromecast
    WebS = None
    # A running thread for Chromecast interactions
    Caster = None

    '''
    Find Chromecasts, start web service, connect to Chromecast and then cast media.
    '''

    def do_web(self, args):
        """Starts web server, serving on port 8080.
By default, 'demo-test' is used as a folder if no path is passed."""
        if len(args) == 0:
            print("Using demo-test folder")
            folder = 'demo-test'
        else:
            l = args.split()
            if len(l) > 1:
                print("Too many arguments dude!")
                return
            else:
                folder = l[0]

        if self.WebS is None:
            self.WebS = WebServerClass(folder)
        
        if not self.WebS.isRunning():
            self.WebS.startServingRequests()
    
    def do_stopWeb(self, args):
        """Stops an active web server."""
        if not self.WebS is None and self.WebS.isRunning():
            self.WebS.stopServingRequests()
    
    def do_connect(self, args):
        """Connects to a Chromecast with the given [name]."""
        l = args.split()
        if len(l) != 1:
            print("I need a name to connect to...")
            return
        else:
            if self.WebS is None:
                print "First of all you need to start the web server!"
            else:
                msg = self.Caster.connectTo(l[0])
                self.Caster.bindWebServer(self.WebS)
                print(msg)
    
    def do_cast(self, args):
        """Starts casting to an already connected Chromecast device."""
        if not self.Caster.isStarted() and self.Caster.isConnected():
            self.Caster.start()
        elif self.Caster.isStarted():
            print("Casting is already running!")
        else:
            print("Please connect to a Chromecast first!")

    def do_pause(self, args):
        """Pause active casting on a connected Chromecast."""
        if self.Caster.isStarted():
            self.Caster.pauseOnMedia()
        else:
            print("Casting is not started yet! Please start it first.")

    def do_resume(self, args):
        """Resume casting on a connected Chromecast, slideshow will continue."""
        if self.Caster.isStarted():
            self.Caster.resumeMedia()
        else:
            print("Casting is not started yet! Please start it first.")
        
    def do_stop(self, args):
        """Stops casting to a connected Chromecast.
After this command you must issue a 'connect' again."""
        if self.Caster.isStarted():
            self.Caster.stop()
        else:
            print("Casting is not started yet! Please start it first.")
    
    def do_time(self, args):
        """Change current slideshow time in use."""
        l = args.split()
        if len(l) != 1:
            print("Pass a new slideshow timeout")
            return

        if self.Caster.isStarted():
            self.Caster.changeSlideShowTimeout(l[0])
        else:
            print("Start Casting first!")

    def do_getTime(self, args):
        """Return the current slideshow timeout set"""
        if self.Caster.isStarted():
            print("Current timeout " + str(self.Caster.getSlideShowTimeout()))
        else:
            print("Start Casting first!")

    def do_skip(self, args):
        """Skip current displaying media."""
        if self.Caster.isStarted():
            self.Caster.skipCurrentMedia()
        else:
            print("Start Casting first!")

    def do_rm(self, args):
        """Removes a media file from the queue of displaying media."""
        if self.Caster.isStarted():
            self.Caster.removeMedia()
        else:
            print("Start Casting first!")

    def do_find(self, args):
        """Finds Chromecasts in range."""
        self.Caster.findChromecasts()
        print(self.Caster.printChromecasts())

    def do_quit(self, args):
        """Quits the program. You can use this directly, stop is implied."""
        if self.Caster.isConnected():
            self.Caster.stop()
        self.do_stopWeb(None)
        print("Quit.")
        raise SystemExit

    # Avoids to repeat the previous command on RETURN pressure!
    def emptyline(self):
        return


if __name__ == '__main__':
    prompt = MyPrompt()
    prompt.prompt = '> '
    
    prompt.Caster = CasterThread(10)
    prompt.Caster.findChromecasts()
    casts = prompt.Caster.printChromecasts()
    prompt.cmdloop('Welcome! Type "help" for further info\n'
                   + '1. If found, available Chromecasts will be reported immediately\n'
                   + '2. Find Chromecasts with the command "find"\n'
                   + '3. Start web engine with "web"\n'
                   + '4. Connect with "connect" and then "cast"\n\n'
                   + casts)
