## Cast Instagram photos to Chromecast

Requires pip:
```bash
$ sudo apt-get install python-pip
$ pip install --upgrade pip
```
Requires pychromecast:
```bash
$ git clone https://github.com/balloob/pychromecast
$ cd pychromecast
$ pip install -r requirements.txt
$ pip install . --user
```
Requires python-instagram:
```bash
$ git clone https://github.com/facebookarchive/python-instagram
$ cd python-instagram
$ pip install -r requirements.txt
$ pip install . --user
```

## Running
Run the Python lib:
```bash
$ python -m com.guido.photochromecast.App
```
### Usage
Type help for help on commands.

##### web
`> web [folder]`

will create a web server on port 8080, with selected folder as root.

`> stopWeb`
will stop the web server.

#### find
`> find`

will find reachable (in your subnet) Chromecasts.

#### connect
`> connect <name>`

will connect photochromecast to the desired Chromecast, given the name.

`> stop`
will stop current casting (if active) and disconnect from Chromecast.

#### displaying media
`> cast`

will start iterating on the selected folder, file by file.

`> pause | resume`

will pause/resume current slideshow.

`> skip`

will skip to the next media.

`> time <timeout>`

will change the slideshow timeout (accepts values in range [1,60])

`> rm [filename]`

will remove current displayed media from the slideshow list or remove the passed one.
It's possible to remove directly files from the served folder too (same expected behavior).