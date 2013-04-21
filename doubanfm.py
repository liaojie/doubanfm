#!/usr/bin/env python

import json
import requests
import pygst
import subprocess
import termios
import fcntl
import sys
import os
from user import user, passwd


class DoubanFM():
    def __init__(self):
        self.is_logined = False
        self.history = []
        self.cur_song = {'sid': ''}
        self.channel = 1
        self.song_list = []

    def login(self):
        if user != '' and passwd != '':
            email = user
            password = passwd
        else:
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
        self.user_id = data['user_id']
        self.expire = data['expire']
        self.token = data['token']
        self.is_logined = True
        return True

    def getChannels(self):
        url = 'http://www.douban.com/j/app/radio/channels'
        r = requests.get(url)
        data = r.json()['channels']
        for channel in data:
            print '%d\t%s\t%s' % (channel['channel_id'], channel['name'], channel['name_en'])

    def changeChannel(self, channel):
        self.channel = channel

    def getSongList(self, channel):
        url = 'http://www.douban.com/j/app/radio/people'
        if len(self.history) > 0:
            type = 'p'
            #h = '|' + ':p|'.join(x['sid'] for x in self.history) + ':p'
            h = ''
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
        r = requests.get(url, params=theparams, proxies=None)
        print r
        print r.json()
        return r.json()['song']

    def getSong(self):
        print len(self.song_list)
        if len(self.song_list) < 5:
            self.song_list.extend(self.getSongList(self.channel))
        song = self.song_list.pop(0)
        print len(self.song_list)
        self.history.append(song)
        if len(self.history) > 15:
            self.history.pop(0)
        self.cur_song = song
        print 'artist:%s\ttitle:%s\talbum:%s' % (song['artist'], song['title'], song['albumtitle'])
        return song

    def playing(self, url):
        cmd = ['ffplay', url, '-nodisp', '-autoexit']
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            process.communicate()
        except Exception, e:
            process.terminate()

    def main(self):
        self.getChannels()
        while True:
            channel = raw_input('choose channel:')
            if channel != '0':
                break
            if self.login():
                break
        self.changeChannel(int(channel))
        while True:
            song = self.getSong()
            print song
            self.playing(url=song['url'])


if __name__ == '__main__':
    fm = DoubanFM()
    fm.main()
