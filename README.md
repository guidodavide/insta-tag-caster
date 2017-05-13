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

### Instagram, access tokens
First retrieve the code from the script (use python-instagram):
```bash
$ cd python-instagram
$ python get_access_token.py
```
Now retrieve a real token:
```bash
$ curl -F 'client_id=YOUR_CLIENT_ID' -F 'client_secret=YOUR_CLIENT_SECRET' -F 'grant_type=authorization_code' -F 'redirect_uri=https://github.com/guidodavide' -F 'code=YOUR_PREV_CODE' https://api.instagram.com/oauth/access_token
```

## Running
Run the Python lib:
```bash
$ python -m com.guido.photochromecast.Test
```

#### In case of This request requires scope=public_content
Scope exception:
http://stackoverflow.com/questions/33863505/oauthpermissionsexception-instagram-api-in-sandbox
```bash
https://api.instagram.com/oauth/authorize/?client_id=CLIENTID&redirect_uri=REDIRECT-URI&response_type=code&scope=SCOPE
```
