__author__ = 'tanel'

import argparse
from ws4py.client.threadedclient import WebSocketClient
import time
import threading
import sys
import urllib
import queue
import json
import time
import os
import logging

from pydub import AudioSegment
from datetime import datetime

logger = logging.getLogger(__name__)

def rate_limited(maxPerSecond):
    minInterval = 1.0 / float(maxPerSecond)
    def decorate(func):
        lastTimeCalled = [0.0]
        def rate_limited_function(*args,**kargs):
            elapsed = time.clock() - lastTimeCalled[0]
            leftToWait = minInterval - elapsed
            if leftToWait>0:
                time.sleep(leftToWait)
            ret = func(*args,**kargs)
            lastTimeCalled[0] = time.clock()
            return ret
        return rate_limited_function
    return decorate


class MyClient(WebSocketClient):

    def __init__(self, audiofile, url, protocols=None, extensions=None, heartbeat_freq=None, byterate=32000,
                 save_adaptation_state_filename=None, send_adaptation_state_filename=None, mode="partial", starttime=0, duration=0):
        super(MyClient, self).__init__(url, protocols, extensions, heartbeat_freq)
        self.final_hyps = []
        self.audiofile = audiofile
        self.byterate = byterate
        self.final_hyp_queue = queue.Queue()
        self.save_adaptation_state_filename = save_adaptation_state_filename
        self.send_adaptation_state_filename = send_adaptation_state_filename
        self.mode = mode
        self.starttime = starttime
        self.duration = duration

    @rate_limited(4)
    def send_data(self, data):
        self.send(data, binary=True)

    def opened(self):
        logger.debug("Socket opened!")
        def send_data_to_ws():
            if self.send_adaptation_state_filename is not None:
                logger.debug("Sending adaptation state from %s" % self.send_adaptation_state_filename)
                try:
                    adaptation_state_props = json.load(open(self.send_adaptation_state_filename, "r"))
                    self.send(json.dumps(dict(adaptation_state=adaptation_state_props)))
                except:
                    e = sys.exc_info()[0]
                    logger.debug("Failed to send adaptation state: %s" %  e)

            sound = AudioSegment.from_file(self.audiofile)
            if self.starttime != 0 or self.duration != 0:
                sound = sound[self.starttime:self.starttime+self.duration]
            sound = sound.apply_gain(-sound.max_dBFS)
            sound.export(self.audiofile[:-4] + "_tmp" + self.audiofile[-4:], format=self.audiofile[-3:])
            with open(self.audiofile[:-4] + "_tmp" + self.audiofile[-4:], "rb") as audiostream:
                if "partial" == self.mode:
                    for block in iter(lambda: audiostream.read(int(self.byterate)), ""):
                        self.send_data(block)
                elif "final" == self.mode:
                    self.send_data(audiostream.read())
            os.remove(self.audiofile[:-4] + "_tmp" + self.audiofile[-4:])

            logger.debug("Audio sent, now sending EOS")
            self.send("EOS")

        t = threading.Thread(target=send_data_to_ws)
        t.start()


    def received_message(self, m):
        response = json.loads(str(m.data.decode('utf-8')))
        if response['status'] == 0:
            if 'result' in response:
                trans = response['result']['hypotheses'][0]['transcript']
                if response['result']['final']:
                    logger.debug(trans)
                    self.final_hyps.append(trans)
                    logger.debug('Final : %s' % trans)
                else:
                    print_trans = trans
                    if len(print_trans) > 80:
                        print_trans = "... %s" % print_trans[-76:]
                    logger.debug('Partial : %s' % print_trans)
            if 'adaptation_state' in response:
                if self.save_adaptation_state_filename:
                    logger.debug("Saving adaptation state to %s" % self.save_adaptation_state_filename)
                    with open(self.save_adaptation_state_filename, "w") as f:
                        f.write(json.dumps(response['adaptation_state']))
        elif response['status'] == 9:
            connectToWebsocket(self.audiofile, self.url, mode=self.mode, sleeptime = 0.1, starttime=self.starttime, duration=self.duration)            
        else:
            logger.debug("Received error from server (status %d)" % response['status'])
            if 'message' in response:
                logger.debug("Error message:" % response['message'])


    def get_full_hyp(self, timeout=60):
        return self.final_hyp_queue.get(timeout)

    def closed(self, code, reason=None):
        logger.debug("Websocket closed() called")
        self.final_hyp_queue.put("".join(self.final_hyps))

def connectToWebsocket(audiofile, url, protocols=None, extensions=None, heartbeat_freq=None, byterate=32000,
                 save_adaptation_state_filename=None, send_adaptation_state_filename=None, mode="partial", sleeptime = 0, starttime=0, duration=0):                 
    time.sleep(sleeptime)

    ws = MyClient(audiofile, url, mode=mode, starttime=starttime, duration=duration)
	
    ws.connect()
    result = ws.get_full_hyp()
    if str(result) == "":
        return
    else:
        print(result)

def main():
    if not os.path.exists("log"):
        os.makedirs("log")
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(filename="log/client_" + datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + "_" + str(os.getpid()) + ".log" , filemode='a', format='%(asctime)s:%(msecs)d %(name)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)

    parser = argparse.ArgumentParser(description='Command line client for kaldigstserver')
    parser.add_argument('-u', '--uri', default="ws://localhost:8888/client/ws/speech", dest="uri", help="Server websocket URI")
    parser.add_argument('-r', '--rate', default=32000, dest="rate", type=int, help="Rate in bytes/sec at which audio should be sent to the server. NB! For raw 16-bit audio it must be 2*samplerate!")
    parser.add_argument('--save-adaptation-state', help="Save adaptation state to file")
    parser.add_argument('--send-adaptation-state', help="Send adaptation state from file")
    parser.add_argument('--content-type', default='', help="Use the specified content type (empty by default, for raw files the default is  audio/x-raw, layout=(string)interleaved, rate=(int)<rate>, format=(string)S16LE, channels=(int)1")
    parser.add_argument('audiofile', help="Audio file to be sent to the server", type=str)
    parser.add_argument('--mode', help="partial : partial + final, final : final", type=str, default='partial')
    parser.add_argument('-s', '--starttime', default=0, dest="starttime", type=int, help="start time(ms) of audio which is need to be decoded")
    parser.add_argument('-d', '--duration', default=0, dest="duration", type=int, help="duration(ms) of audio which is need to be decoded")
    args = parser.parse_args()

    content_type = args.content_type
    if content_type == '' and args.audiofile.endswith(".raw"):
        content_type = "audio/x-raw, layout=(string)interleaved, rate=(int)%d, format=(string)S16LE, channels=(int)1" %(args.rate/2)

    connectToWebsocket(args.audiofile, args.uri + '?%s' % (urllib.parse.urlencode([("content-type", content_type)])), byterate=args.rate,
                  save_adaptation_state_filename=args.save_adaptation_state, send_adaptation_state_filename=args.send_adaptation_state, mode=args.mode, starttime=args.starttime, duration=args.duration)

    if os.path.isfile(args.audiofile[:-4] + "_tmp" + args.audiofile[-4:]):
        os.remove(args.audiofile[:-4] + "_tmp" + args.audiofile[-4:])

if __name__ == "__main__":
    main()

