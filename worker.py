import random
import threading
from time import sleep, time

import httplib2
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

import http.client as httplib

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, httplib.NotConnected,
                        httplib.IncompleteRead, httplib.ImproperConnectionState,
                        httplib.CannotSendRequest, httplib.CannotSendHeader,
                        httplib.ResponseNotReady, httplib.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

MAX_RETRIES = 3


class Worker(threading.Thread):

    def __init__(self, queue, app, credentials):
        super(Worker, self).__init__()

        self.queue = queue
        self.app = app
        self._stop_event = threading.Event()
        self.credentials = credentials

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        while not self.queue.empty():
            item = self.queue.get()
            if not item.completed:
                item.status = 'uploading...'
                self.initialize_upload(self.credentials, item)
                self.queue.task_done()

    def initialize_upload(self, youtube, item):
        body = dict(
            snippet=dict(
                title=item.title,
            ),
            status=dict(
                privacyStatus='private'
            )
        )

        # Call the API's videos.insert method to create and upload the video.
        insert_request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            # The chunksize parameter specifies the size of each chunk of data, in
            # bytes, that will be uploaded at a time. Set a higher value for
            # reliable connections as fewer chunks lead to faster uploads. Set a lower
            # value for better recovery on less reliable connections.
            #
            # Setting 'chunksize' equal to -1 in the code below means that the entire
            # file will be uploaded in a single HTTP request. (If the upload fails,
            # it will still be retried where it left off.) This is usually a best
            # practice, but if you're using Python older than 2.6 or if you're
            # running on App Engine, you should set the chunksize to something like
            # 1024 * 1024 (1 megabyte).
            media_body=MediaFileUpload(item.path, chunksize=262144, resumable=True)

        )

        self.resumable_upload(insert_request, item)

    def resumable_upload(self, request, item):
        response = None
        error = None
        retry = 0
        while response is None:
            try:

                if self.stopped():
                    item.status = 'stopped'
                    break

                status, response = request.next_chunk()

                if status:
                    item.progress = round(status.progress() * 100)

                if response is not None:
                    if 'id' in response:
                        item.status = 'https://youtube.com/watch?v=%s' % response['id']
                        item.progress = 100
                        item.completed = True
                        self.app.on_upload_end()
                    else:
                        item.status = 'The upload failed with an unexpected response: %s' % response

                self.app.dvc.Refresh()

            except HttpError as e:
                if e.resp.status in RETRIABLE_STATUS_CODES:
                    error = 'A retriable HTTP error %d occurred:\n%s' % (e.resp.status,
                                                                         e.content)
                else:
                    raise
            except RETRIABLE_EXCEPTIONS as e:
                error = 'A retriable error occurred: %s' % e

            if error is not None:
                print(error)
                retry += 1
                if retry > MAX_RETRIES:
                    return

                max_sleep = 2 ** retry
                sleep_seconds = random.random() * max_sleep
                item.status = 'Sleeping %f seconds and then retrying...' % sleep_seconds
                sleep(sleep_seconds)
