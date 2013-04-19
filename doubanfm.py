#!/usr/bin/env python

import json
import requests
import pygst
import subprocess

class DoubanFM():
    def __init__(self):
        self.is_logined = False
        self.history = []
        self.cur_song = {'sid': ''}
        self.channel = 1
        self.song_list = []

    def login(self):
        import getpass
        email = raw_input('email:')
        password = getpass.getpass('password:')
        url = 'http://www.douban.com/j/app/login'
        params = {'app_name': 'radio_desktop_win',
                  'version': 100, 'email': email, 'password': password}
        r = requests.post(url, data=params)
        data = r.json()
        if data['err'] != 'ok':
            print 'login failed!'
            print data['err']
            return False
        # print data
        self.user_id = data['user_id']
        self.expire = data['expire']
        self.token = data['token']
        self.is_logined = True
        return True

    def getChannels(self):
        url = 'http://www.douban.com/j/app/radio/channels'
        r = requests.get(url)
        data = r.json()['channels']
        print data
        for channel in data:
            print '%d\t%s\t%s' % (channel['channel_id'], channel['name'], channel['name_en'])

    def changeChannel(self, channel):
        self.channel = channel

    def getSongList(self, channel):
        url = 'http://www.douban.com/j/app/radio/people'
        if len(self.history) > 0:
            type = 'p'
            h = '|' + ':p|'.join(x['sid'] for x in self.history) + ':p'
            self.history = []
        else:
            type = 'n'
            h = ''
        if self.is_logined:
            theparams = {
                'app_name': 'radio_desktop_win', 'version': 100,
                'user_id': self.user_id, 'expire': self.expire,
                'token': self.token, 'sid': self.cur_song,
                'h': h, 'channel': channel, 'type': type
            }
        else:
            theparams = {
                'app_name': 'radio_desktop_win', 'version': 100,
                'sid': self.cur_song, 'channel': channel, 'type': type
            }
        r = requests.get(url, params = theparams,proxies = None)
        return r.json()['song']

    def getSong(self):
        if len(self.song_list) < 5:
            self.song_list.extend(self.getSongList(self.channel))
        song = self.song_list.pop(0)
        if len(self.history) > 20:
            self.history.pop(0)
        self.cur_song = song

        print '%s %s' % (song['artist'], song['title'])
        return song

    def run(self):
        self.getChannels()
        while True:
            channel = raw_input('choose channel:')
            if channel != '0':
                break
            if self.login():
                break
        self.changeChannel(int(channel))
        while True:
            song  = self.getSong()
            self.playing(url = song['url'])

    def playing(self, url):
        cmd = ['ffplay', url, '-nodisp', '-autoexit']
        process = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        try:
            process.communicate()
        except Exception,e:
            process.terminate()
        
            


if __name__ == '__main__':
    fm = DoubanFM()
    fm.run()
