from __future__ import unicode_literals
import socket, threading, os
import tornado.web, tornado.websocket, tornado.ioloop, tornado.iostream
import json

class NADClient(object):

    def __init__(self, host, receive_callback):
        self.host = host
        self.port = 23
        self.receive_callback = receive_callback
        self.stream = None
        self.socket = None
        self.try_connect()

    def try_connect(self):
        print "trying to connect to receiver..."

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.stream = tornado.iostream.IOStream(self.socket)
	print 'Connecting to: %s' % self.host
        self.stream.connect((self.host, self.port), self.send_request)

    def send_request(self):
#	self.stream.write("\n")
        self.stream.read_until_close(self.on_close, self.handle_read)

    def on_close(self, res):
        self.stream.close()

    def handle_connect(self):
        pass

    def handle_error(self):
        print "problem reaching server."
        self.try_connect()

    def handle_read(self, data):
        data = data.splitlines()[-1].strip()
        self.receive_callback(data)

    def write_data(self, data):
	print 'Write', data
        self.stream.write(str(data))

    def close(self):
        print 'Stopped NAD listener...'
        self.stream.close()

class NADThread(threading.Thread):

    def __init__(self, parent, ip_address):
        threading.Thread.__init__(self)
        self.client = NADClient(ip_address, parent.on_read)
    def run(self):
        print 'Starting NAD listner..'

    def stop(self):
        self.client.close()
        #self.join()
    def send_cmd(self, cmd):
	self.client.write_data(cmd)

    def send(self, key, value):
        self.send_cmd('%s=%s\n' % (key, str(value)))

    def ask_device(self, key):
        self.send_cmd('%s?\n' % key)

class IndexHandler(tornado.web.RequestHandler):
    '''Serve index page'''

    def initialize(self, core):
        self.core = core
    
    @tornado.web.asynchronous
    def get(request):
        '''Index page'''
	index_page = os.path.join(os.path.dirname(__file__), 'index.html')
        request.render(index_page)

    def data_received(self, data):
        pass

class WebSocketHandler(tornado.websocket.WebSocketHandler):
    
    def initialize(self, core, config):
	self.core = core
	self.ip_address = config.get('nadsettings')['ip_address']
	print self.ip_address
        self.clients = []
        self.nadclient = None

    def open(self):
        print("open", "WebSocketHandler")
        self.clients.append(self)
        if self.nadclient is None:
            self.nadclient = NADThread(self, self.ip_address)
            self.nadclient.start()
            asks = ['Main.Volume', 'Main.Power', 'Main.Source']
            for ask in asks:
                self.nadclient.ask_device(ask)

    def on_read(self, message):
        if message is None:
            return
        msg = ParentTest().process_data(message)
        if msg is None:
            return
        self.write_message(json.dumps(msg))

    def on_message(self, message):
        msg_dict = json.loads(message)
        if msg_dict['type'] == 'Main.Volume':
            vol = msg_dict['val']
            db_vol = ParentTest().get_dbvol(float(vol))
            self.nadclient.send('Main.Volume', db_vol)
            return
        if msg_dict['type'] in ('Main.Power', 'Main.Source'):
            val = msg_dict['val']
            msgtype = msg_dict['type']
            self.nadclient.send(msgtype, val)

    def on_close(self):
        self.clients.remove(self)
        if self.nadclient is not None:
            self.nadclient.stop()

# Test class
class ParentTest(object):

    _min_volume = -78
    _max_volume = 0

    def __init__(self):
        #self.clientthread = NADThread(self)
        self.clientthread = None

    def start(self):
        self.clientthread.start()
        while True:
            char = sys.stdin.read(1)
            print 'You pressed %s' % char
            if (char == 'q'):
                self.clientthread.stop()
                sys.exit()
            if (char == 's'):
                self._ask_device('Main.Power')
            if (char == 'v'):
                self._ask_device('Main.Volume')
            if (char == 'd'):
                self._dec_vol()
            if (char == 'i'):
                self._inc_vol()
            if (char == 'o'):
                self._send_cmd('Main.Power', 'on')
            if (char == 'p'):
                self._send_cmd('Main.Power', 'off')


    def on_read(self, data):
        print 'Received...'
        self.process_data(data)

    def _ask_device(self, key):
        self.clientthread.send_cmd('%s?\n' % key)

    def _send_cmd(self, key, value):
        self.clientthread.send_cmd('%s=%s\n' % (key, value))

    def _dec_vol(self):
        self.clientthread.send_cmd('Main.Volume-\n')

    def _inc_vol(self):
        self.clientthread.send_cmd('Main.Volume+\n')

    def process_data(self, data):
        print data
        if '=' in data:
            ret = {}

            key, value = data.split('=', 2)
            if key == 'Main.Volume':
                vol = self.get_volume(float(value.rstrip()))
                ret['type'] = key
                ret['val'] = str(int(vol))
            if key in ('Main.Power', 'Main.Source'):
                ret['type'] = key
                ret['val'] = value
            if len(ret) > 0:
                return ret

        return None

    def get_volume(self, db):
        norm = (self._min_volume - self._max_volume)
        normdb = (db - self._max_volume)
        percentage_volume = abs((-(normdb - norm) / (norm) ) * 100)
        return percentage_volume

    def set_volume(self, percent):
        norm = (self._min_volume - self._max_volume)
        db = ((-percent / 100) * norm) + (norm + self._max_volume)

    def get_dbvol(self, percent):
        norm = (self._min_volume - self._max_volume)
        db = ((-percent / 100) * norm) + (norm + self._max_volume)
        return int(db)

def sig_handler(sig, frame):
    print 'Caught signal: %s' % sig
    tornado.ioloop.IOLoop.instance().add_callback(shutdown)

def shutdown(self):
    self.stop();

# -- Here we can run the web extension using a stand along tornado server. 
#app = tornado.web.Application([(r'/nadws', WebSocketHandler), (r'/', IndexHandler)], debug=True)
#app.listen(8080)
#tornado.ioloop.IOLoop.instance().start()

