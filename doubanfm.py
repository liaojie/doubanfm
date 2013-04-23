#!/usr/bin/env python
#-*- coding:utf-8 -*-

import json
import requests
import sys
import os
import os.path
import termios
import fcntl
import gobject
import thread
import glib
import pygst
pygst.require('0.10')
import gst
from select import select


class DoubanFM():
    def __init__(self):
        self.is_logined = False
        self.history = []
        self.cur_song = {'sid': ''}
        self.channel = 1
        self.song_list = []
        self.playmode = False
        self.player = gst.element_factory_make('playbin2', 'player')
        self.bus = self.player.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message', self.onMessage)

    def onMessage(self, bus, message):
        url = 'http://www.douban.com/j/app/login'
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.player.set_state(gst.STATE_NULL)
            self.playmode = False
            theparams = self.get_params('e')
            r = requests.get(url, params=theparams)
        elif t == gst.MESSAGE_ERROR:
            self.player.set_state(gst.STATE_NULL)
            err, debug = message.parse_error()
            print 'Error: %s' % err, debug
            self.playmode = False

    def getUserInfo(self):
        cur_path = os.path.dirname(os.path.abspath(__file__))
        if os.path.exists('%s/user.py' % (cur_path)):
            from user import user, passwd
            return (user, passwd)
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
            print '%d\t%s' % (channel['channel_id'], channel['name'])

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
        theparams = self.get_params(type)
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

    def get_params(self, type):
        app_name = 'radio_desktop_win'
        version = 100
        if self.is_logined:
            params = {'app_name': 'radio_desktop_win', 'version': 100,
                      'user_id': self.user_id, 'expire': self.expire,
                      'token': self.token, 'sid': self.cur_song['sid'],
                      'channel': self.channel, 'type': type}
        else:
            params = {'app_name': 'radio_desktop_win', 'version': 100,
                      'sid': self.cur_song['sid'], 'channel': self.channel,
                      'type': type}
        return params

    def skip(self):
        self.player.set_state(gst.STATE_NULL)
        self.playmode = False

    def pauseAndPlay(self):
        success, state, pending = self.player.get_state(1)
        if state == gst.STATE_PLAYING:
            self.player.set_state(gst.STATE_PAUSED)
            print 'now paused'
        elif state == gst.STATE_PAUSED:
            self.player.set_state(gst.STATE_PLAYING)

    def like(self, song):
        url = 'http://www.douban.com/j/app/radio/people'
        theparams = self.get_params('r')
        r = requests.get(url, params=theparams)
        data = r.json()
        # print data
        if data['r'] == 0:
            print 'You just starred this song.'
        else:
            print data['err']

    def dislike(self, song):
        url = 'http://www.douban.com/j/app/radio/people'
        theparams = self.get_params('u')
        r = requests.get(url, params=theparams)
        data = r.json()
        if data['r'] == 0:
            print 'You just canceled starring this song.'
        else:
            print data['err']

    def delete(self, song):
        url = 'http://www.douban.com/j/app/radio/people'
        theparams = self.get_params('b')
        r = requests.get(url, params=theparams)
        data = r.json()
        if data['r'] == 0:
            print 'No longer play this song.'
        else:
            print data['err']
        self.player.set_state(gst.STATE_NULL)
        self.playmode = False

    def control(self, song):
        fd = sys.stdin.fileno()
        oldterm = termios.tcgetattr(fd)
        newattr = oldterm[:]
        newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, newattr)
        oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)
        try:
            rlist, _, _ = select([fd], [], [], 1)
            if rlist:
                s = sys.stdin.read(1)
                if s[0] == 'n':
                    self.skip()
                elif s[0] == ' ':
                    self.pauseAndPlay()
                elif s[0] == 'f':
                    self.like(song)
                elif s[0] == 'u':
                    self.dislike(song)
                elif s[0] == 'd':
                    self.delete(song)
        except IOError:
            pass
        finally:
            termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
            fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)
            # pass

    def playing(self, song):
        self.player.set_property('uri', song['url'])
        self.playmode = True
        self.player.set_state(gst.STATE_PLAYING)
        while self.playmode:
            c = self.control(song)

    def usage(self):
        u = """
            跳过输入n, 加心输入f, 取消加心输入u, 不再播放输入d
            暂停输入空格键,退出Control + c
            """
        print u

    def main(self):
        self.getChannels()
        while True:
            channel = raw_input('choose channel:')
            if channel != '0':
                break
            if self.login():
                break
        self.changeChannel(int(channel))
        self.usage()
        while True:
            self.song_list = self.getSongList(self.channel)
            self.playing(self.getSong())

if __name__ == '__main__':
    fm = DoubanFM()
    while True:
        thread.start_new_thread(fm.main, ())
        gobject.threads_init()
        loop = glib.MainLoop()
        loop.run()
