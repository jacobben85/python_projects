# System modules
from Queue import Queue
from threading import Thread
import time
import subprocess

# Local modules
# import feedparser
import xml.etree.ElementTree as ET
import requests
import urllib
import datetime
import os

# Set up some global variables
num_fetch_threads = 10
enclosure_queue = Queue()

# A real app wouldn't use hard-coded data...
source_xml = 'http://nfl.univision.com/feed/sports/american-football/nfl/2014/scheduleWithScores.xml'


def send_notification(display_message):
    subprocess.check_call(['/usr/bin/osascript', '-e', 'display notification "' + display_message + '" with title "NFL ping test"'])
    print "[" + str(datetime.datetime.now()) + "]: " + display_message


def downloadEnclosures(i, q):
    while True:
        event_id = q.get()
        print '%s: Validating:' % i, event_id
        event_response = requests.get('http://nfl.univision.com/feed/sports/american-football/nfl/2014/event-nfl-' + event_id + '.xml')
        if event_response.status_code != 200:
            send_notification("event:" + event_id + " error code:" + str(event_response.status_code))

        q.task_done()


def addEnclosures(q):
    message = ''

    # download the source xml
    # urllib.urlopen(source_xml)
    source_xml = 'http://nfl.univision.com/feed/sports/american-football/nfl/2014/scheduleWithScores.xml'
    response = requests.get(source_xml)
    if response.status_code == 200:
        if response.headers['Content-Type'].find('xml') > -1:
            urllib.urlretrieve(source_xml, '/tmp/scheduleWithScores.xml')
            xml_data = ET.parse('/tmp/scheduleWithScores.xml')
            for node in xml_data.iter('uim-american-football'):
                last_update = node.attrib.get('last-updated')
                received = datetime.datetime.strptime(last_update, "%Y-%m-%dT%H:%MZ")
                utc_now = datetime.datetime.utcnow()
                time_diff = utc_now - received
                print last_update

                if int(time_diff.total_seconds() / 60) > 62:
                    print 'Schedule last updated at :' + last_update + ", UTC time now :" + str(utc_now)

                for tournament in node.iter('tournament-stage'):

                    for tournament_round in tournament.iter('tournament-round'):

                        for event_meta in tournament_round.iter('event-metadata'):
                            event_name = event_meta.attrib.get('event-key')

                            for event_status in event_meta.iter('sports-property'):
                                event_status_id = event_status.attrib.get('id')
                                if int(event_status_id) > 0:
                                    q.put(event_name[22:])

            os.remove('/tmp/scheduleWithScores.xml')

        else:
            message = 'XML not found, header detail' + response.headers['Content-Type']
    else:
        message = 'Http request failed, status code : ' + response.status_code

    if message != '':
        send_notification(message)


addEnclosures(enclosure_queue)


# Set up some threads to fetch the enclosures
for i in range(num_fetch_threads):
    worker = Thread(target=downloadEnclosures, args=(i, enclosure_queue,))
    worker.setDaemon(True)
    worker.start()


# Now wait for the queue to be empty, indicating that we have
# processed all of the downloads.
print '*** Main thread waiting'
enclosure_queue.join()
print '*** Done'