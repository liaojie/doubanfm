#!/usr/bin/env python

import json
import requests
import subprocess
import sys
import os
import os.path
import signal
from select import select


class DoubanFM():
    def __init__(self):
        self.is_logined = False
        self.history = []
        self.cur_song = {'sid': ''}
        self.channel = 1
        self.song_list = []

    def getUserInfo(self):
        cur_path = os.path.dirname(os.path.abspath(__file__))
        if os.path.exists('%s/user.py' %(cur_path)):
            from user import user, passwd
            return (user,passwd)
        else:
            return ('', '')

    def login(self):
        email, password = self.getUserInfo()
        if email == '' or password == '':
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
            h = '|' + ':p|'.join(x['sid'] for x in self.history) + ':p'
            self.history = []
        else:
            type = 'n'
            h = ''
        if self.is_logined:
            theparams = {
                'app_name': 'radio_desktop_win', 'version': 100,
                'user_id': self.user_id, 'expire': self.expire,
                'token': self.token, 'sid': self.cur_song['sid'],
                'h': h, 'channel': channel, 'type': type
            }
        else:
            theparams = {
                'app_name': 'radio_desktop_win', 'version': 100,
                'sid': self.cur_song['sid'], 'channel': channel, 'type': type
            }
        r = requests.get(url, params=theparams)
        return r.json()['song']

    def getSong(self):
        if len(self.song_list) < 5:
            self.song_list.extend(self.getSongList(self.channel))
        song = self.song_list.pop(0)
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
        while process.poll() == None:
            try:
                rlist,_,_ = select([sys.stdin],[],[],1)
                if rlist:
                    s = sys.stdin.readline()
                    if s[0] == 'n':
                        process.terminate()
                    elif s[0] == 'p':
                        os.kill(process.pid, signal.SIGSTOP)                   
                    elif s[0] == 'c':
                        os.kill(process.pid, signal.SIGCONT)
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
            self.playing(url=song['url'])



if __name__ == '__main__':
    fm = DoubanFM()
    fm.main()
