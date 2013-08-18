from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db import transaction

import httplib
import socket
import urllib
import simplejson

class HttpResponseServiceUnavailable(HttpResponse): 
	status_code = 503

class Http503(Exception):
	pass

from models import CommitFest, Patch, MailThread, MailThreadAttachment, PatchHistory

def _archivesAPI(suburl, params=None):
	try:
		socket.setdefaulttimeout(settings.ARCHIVES_TIMEOUT)
		h = httplib.HTTPConnection(settings.ARCHIVES_SERVER,
								   settings.ARCHIVES_PORT,
								   True,
								   settings.ARCHIVES_TIMEOUT)
		if params:
			url = "%s?%s" % (suburl, urllib.urlencode(params))
		else:
			url = suburl
		h.request('GET', url, headers={
			'Host': settings.ARCHIVES_HOST,
			})
		resp = h.getresponse()
		if resp.status != 200:
			if resp.status == 404:
				raise Http404()
			raise Exception("JSON call failed: %s" % resp.status)

		r = simplejson.load(resp)
		resp.close()
		h.close()
	except socket.error, e:
		raise Http503("Failed to communicate with archives backend: %s" % e)
	return r

def getThreads(request):
	search = request.GET.has_key('s') and request.GET['s'] or None

	# Make a JSON api call to the archives server
	r = _archivesAPI('/list/pgsql-hackers/latest.json', {'n': 100})
	if search:
		return sorted([x for x in r if x['subj'].lower().find(search)>=0 or x['from'].lower().find(search)>=0], key=lambda x: x['date'], reverse=True)
	else:
		return sorted(r, key=lambda x: x['date'], reverse=True)


def parse_and_add_attachments(threadinfo, mailthread):
	for t in threadinfo:
		if len(t['atts']):
			# One or more attachments. For now, we're only actually going
			# to store and process the first one, even though the API gets
			# us all of them.
			MailThreadAttachment.objects.get_or_create(mailthread=mailthread,
													   messageid=t['msgid'],
													   defaults={
														   'date': t['date'],
														   'author': t['from'],
														   'attachmentid': t['atts'][0],
													   })
		# In theory we should remove objects if they don't have an
		# attachment, but how could that ever happen? Ignore for now.

@transaction.commit_on_success
def attachThread(request):
	cf = get_object_or_404(CommitFest, pk=int(request.POST['cf']))
	patch = get_object_or_404(Patch, pk=int(request.POST['p']), commitfests=cf)
	msgid = request.POST['msg']

	if doAttachThread(cf, patch, msgid, request.user):
		return 'OK'
	else:
		raise Exception("Something happened that cannot happen")

def doAttachThread(cf, patch, msgid, user):
	r = sorted(_archivesAPI('/message-id.json/%s' % msgid), key=lambda x: x['date'])
	# We have the full thread metadata - using the first and last entry,
	# construct a new mailthread in our own model.
	# First, though, check if it's already there.
	if MailThread.objects.filter(messageid=r[0]['msgid'], patch=patch).exists():
		# It already existed. Pretend everything is fine.
		return True

	# Now create a new mailthread entry
	m = MailThread(messageid=r[0]['msgid'],
				   patch=patch,
				   subject=r[0]['subj'],
				   firstmessage=r[0]['date'],
				   firstauthor=r[0]['from'],
				   latestmessage=r[-1]['date'],
				   latestauthor=r[-1]['from'],
				   latestsubject=r[-1]['subj'],
				   latestmsgid=r[-1]['msgid'],
				   )
	m.save()
	parse_and_add_attachments(r, m)
	PatchHistory(patch=patch, by=user, what='Attached mail thread %s' % r[0]['msgid']).save()
	patch.update_lastmail()
	patch.set_modified()
	patch.save()

	return True

@transaction.commit_on_success
def detachThread(request):
	cf = get_object_or_404(CommitFest, pk=int(request.POST['cf']))
	patch = get_object_or_404(Patch, pk=int(request.POST['p']), commitfests=cf)
	thread = get_object_or_404(MailThread, patch=patch, messageid=request.POST['msg'])

	thread.delete()
	PatchHistory(patch=patch, by=request.user, what='Detached mail thread %s' % request.POST['msg']).save()
	patch.update_lastmail()
	patch.set_modified()
	patch.save()

	return 'OK'


_ajax_map={
	'getThreads': getThreads,
	'attachThread': attachThread,
	'detachThread': detachThread,
}

# Main entrypoint for /ajax/<command>/
@csrf_exempt
@login_required
def main(request, command):
	if not _ajax_map.has_key(command):
		raise Http404
	try:
		resp = HttpResponse(content_type='application/json')
		simplejson.dump(_ajax_map[command](request), resp)
		return resp
	except Http503, e:
		return HttpResponseServiceUnavailable(e, mimetype='text/plain')

