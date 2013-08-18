#!/usr/bin/env python
#
# check_patches_in_archives.py
#
# Download and check attachments in the archives, to see if they are
# actually patches. We do this asynchronously in a separate script
# so we don't block the archives unnecessarily.
#

import os
import sys
import socket
import httplib
import magic

# Set up for accessing django
from django.core.management import setup_environ
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), '../../pgcommitfest'))
import settings
setup_environ(settings)

from commitfest.models import MailThreadAttachment

if __name__ == "__main__":
	socket.setdefaulttimeout(settings.ARCHIVES_TIMEOUT)
	mag = magic.open(magic.MIME)
	mag.load()
	
	# Try to fetch/scan all attachments that haven't already been scanned.
	# If they have already been scanned, we don't bother.
	# We will hit the archives without delay when doing this, but that
	# should generally not be a problem because it's not going to be
	# downloading a lot...
	for a in MailThreadAttachment.objects.filter(ispatch=None):
		url = "/message-id/attachment/%s/attach" % a.attachmentid
		h = httplib.HTTPConnection(settings.ARCHIVES_SERVER,
								   settings.ARCHIVES_PORT,
								   True,
								   settings.ARCHIVES_TIMEOUT)
		h.request('GET', url, headers={
			'Host': settings.ARCHIVES_HOST,
			})
		resp = h.getresponse()
		if resp.status != 200:
			print "Failed to get %s: %s" % (url, resp.status)

		contents = resp.read()
		resp.close()
		h.close()

		# Attempt to identify the file using magic information
		mtype = mag.buffer(contents)

		# We don't support gzipped or tar:ed patches or anything like
		# that at this point - just plain patches.
		if mtype.startswith('text/x-diff'):
			a.ispatch = True
		else:
			a.ispatch = False
		a.save()
