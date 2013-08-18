from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, Http404
from django.template import RequestContext
from django.db import transaction
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from datetime import datetime
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid

from mailqueue.util import send_mail

from models import CommitFest, Patch, PatchOnCommitFest, PatchHistory, Committer
from forms import PatchForm, NewPatchForm, CommentForm, CommitFestFilterForm
from ajax import doAttachThread

def home(request):
	commitfests = list(CommitFest.objects.all())
	opencf = next((c for c in commitfests if c.status == CommitFest.STATUS_OPEN), None)
	inprogresscf = next((c for c in commitfests if c.status == CommitFest.STATUS_INPROGRESS), None)

	return render_to_response('home.html', {
		'commitfests': commitfests,
		'opencf': opencf,
		'inprogresscf': inprogresscf,
		'title': 'Commitfests',
		}, context_instance=RequestContext(request))

def commitfest(request, cfid):
	# Find ourselves
	cf = get_object_or_404(CommitFest, pk=cfid)

	# Build a dynamic filter based on the filtering options entered
	q = Q()
	if request.GET.has_key('status') and request.GET['status'] != "-1":
		q = q & Q(patchoncommitfest__status=int(request.GET['status']))
	if request.GET.has_key('author') and request.GET['author'] != "-1":
		if request.GET['author'] == '-2':
			q = q & Q(authors=None)
		else:
			q = q & Q(authors__id=int(request.GET['author']))
	if request.GET.has_key('reviewer') and request.GET['reviewer'] != "-1":
		if request.GET['reviewer'] == '-2':
			q = q & Q(reviewers=None)
		else:
			q = q & Q(reviewers__id=int(request.GET['reviewer']))

	if request.GET.has_key('text') and request.GET['text'] != '':
		q = q & Q(name__icontains=request.GET['text'])

	# Not sure if this is correct?
	has_filter = len(q.children) > 0
	if not has_filter and request.GET:
		# Redirect to get rid of the ugly url
		return HttpResponseRedirect('/%s/' % cf.id)

	patches = cf.patch_set.filter(q).select_related().extra(select={
		'status':'commitfest_patchoncommitfest.status',
		'author_names':"SELECT string_agg(first_name || ' ' || last_name || ' (' || username || ')', ', ') FROM auth_user INNER JOIN commitfest_patch_authors cpa ON cpa.user_id=auth_user.id WHERE cpa.patch_id=commitfest_patch.id",
		'reviewer_names':"SELECT string_agg(first_name || ' ' || last_name || ' (' || username || ')', ', ') FROM auth_user INNER JOIN commitfest_patch_reviewers cpr ON cpr.user_id=auth_user.id WHERE cpr.patch_id=commitfest_patch.id",
		'is_open':'commitfest_patchoncommitfest.status IN (%s)' % ','.join([str(x) for x in PatchOnCommitFest.OPEN_STATUSES]),
	}).order_by('-is_open', 'topic__topic', 'created')

	# Generates a fairly expensive query, which we shouldn't do unless
	# the user is logged in. XXX: Figure out how to avoid doing that..
	form = CommitFestFilterForm(cf, request.GET)

	return render_to_response('commitfest.html', {
		'cf': cf,
		'form': form,
		'patches': patches,
		'has_filter': has_filter,
		'title': 'Commitfest %s' % cf.name,
		}, context_instance=RequestContext(request))

def patch(request, cfid, patchid):
	cf = get_object_or_404(CommitFest, pk=cfid)
	patch = get_object_or_404(Patch.objects.select_related(), pk=patchid, commitfests=cf)
	patch_commitfests = PatchOnCommitFest.objects.select_related('commitfest').filter(patch=patch).order_by('-commitfest__startdate')

	#XXX: this creates a session, so find a smarter way. Probably handle
	#it in the callback and just ask the user then?
	if request.user.is_authenticated():
		is_committer = Committer.objects.filter(user=request.user).exists()
		is_reviewer = request.user in patch.reviewers.all()
#		is_reviewer = len([x for x in patch.reviewers.all() if x==request.user]) > 0
	else:
		is_committer = False
		is_reviewer = False

	return render_to_response('patch.html', {
		'cf': cf,
		'patch': patch,
		'patch_commitfests': patch_commitfests,
		'is_committer': is_committer,
		'is_reviewer': is_reviewer,
		'title': 'View patch',
		'breadcrumbs': [{'title': cf.name, 'href': '/%s/' % cf.pk},],
		}, context_instance=RequestContext(request))

@login_required
@transaction.commit_on_success
def patchform(request, cfid, patchid):
	cf = get_object_or_404(CommitFest, pk=cfid)
	patch = get_object_or_404(Patch, pk=patchid, commitfests=cf)

	if request.method == 'POST':
		form = PatchForm(data=request.POST, instance=patch)
		if form.is_valid():
			# Some fields need to be set when creating a new one
			r = form.save(commit=False)
			# Fill out any locked fields here

			form.save_m2m()

			# Track all changes
			for field, values in r.diff.items():
				PatchHistory(patch=patch, by=request.user, what='Changed %s to %s' % (field, values[1])).save()
			r.set_modified()
			r.save()
			return HttpResponseRedirect('../../%s/' % r.pk)
		# Else fall through and render the page again
	else:
		form = PatchForm(instance=patch)

	return render_to_response('base_form.html', {
		'cf': cf,
		'form': form,
		'patch': patch,
		'title': 'Edit patch',
		'breadcrumbs': [{'title': cf.name, 'href': '/%s/' % cf.pk},
						{'title': 'View patch', 'href': '/%s/%s/' % (cf.pk, patch.pk)}],
	}, context_instance=RequestContext(request))

@login_required
@transaction.commit_on_success
def newpatch(request, cfid):
	cf = get_object_or_404(CommitFest, pk=cfid)
	if not cf.status == CommitFest.STATUS_OPEN and not request.user.is_staff:
		raise Http404("This commitfest is not open!")

	if request.method == 'POST':
		form = NewPatchForm(data=request.POST)
		if form.is_valid():
			patch = Patch(name=form.cleaned_data['name'],
						  topic=form.cleaned_data['topic'])
			patch.set_modified()
			patch.save()
			poc = PatchOnCommitFest(patch=patch, commitfest=cf, enterdate=datetime.now())
			poc.save()
			# Now add the thread
			try:
				doAttachThread(cf, patch, form.cleaned_data['threadmsgid'], request.user)
				return HttpResponseRedirect("/%s/%s/" % (cf.id, patch.id))
			except Http404:
				# Thread not found!
				# This is a horrible breakage of API layers
				form._errors['threadmsgid'] = form.error_class(('Selected thread did not exist',))
			except Exception:
				form._errors['threadmsgid'] = form.error_class(('An error occurred looking up the thread in the archives.',))
	else:
		form = NewPatchForm()

	return render_to_response('base_form.html', {
		'form': form,
		'title': 'New patch',
		'breadcrumbs': [{'title': cf.name, 'href': '/%s/' % cf.pk},],
		'savebutton': 'Create patch',
		'threadbrowse': True,
	}, context_instance=RequestContext(request))

def _review_status_string(reviewstatus):
	if '0' in reviewstatus:
		if '1' in reviewstatus:
			return "tested, passed"
		else:
			return "tested, failed"
	else:
		return "not tested"

@login_required
@transaction.commit_on_success
def comment(request, cfid, patchid, what):
	cf = get_object_or_404(CommitFest, pk=cfid)
	patch = get_object_or_404(Patch, pk=patchid)
	is_review = (what=='review')

	if request.method == 'POST':
		try:
			form = CommentForm(patch, is_review, data=request.POST)
		except Exception, e:
			messages.add_message(request, messages.ERROR, "Failed to build list of response options from the archives: %s" % e)
			return HttpResponseRedirect('/%s/%s/' % (cf.id, patch.id))

		if form.is_valid():
			if is_review:
				txt = "The following review has been posted through the commitfest application:\n%s\n\n%s" % (
					"\n".join(["%-25s %s" % (f.label + ':', _review_status_string(form.cleaned_data[fn])) for (fn, f) in form.fields.items() if fn.startswith('review_')]),
					form.cleaned_data['message']
				)
				msg = MIMEText(txt, _charset='utf-8')
			else:
				msg = MIMEText(form.cleaned_data['message'], _charset='utf-8')
			if form.thread.subject.startswith('Re:'):
				msg['Subject'] = form.thread.subject
			else:
				msg['Subject'] = 'Re: %s' % form.thread.subject
			msg['To'] = 'magnus@hagander.net'
			msg['From'] = "%s %s <%s>" % (request.user.first_name, request.user.last_name, request.user.email)
			msg['Date'] = formatdate(localtime=True)
			msg['User-Agent'] = 'pgcommitfest'
			msg['In-Reply-To'] = '<%s>' % form.respid
			# We just add the "top" messageid and the one we're responding to.
			# This along with in-reply-to should indicate clearly enough where
			# in the thread the message belongs.
			msg['References'] = '<%s> <%s>' % (form.thread.messageid, form.respid)
			msg['Message-ID'] = make_msgid('pgcf')

			send_mail(request.user.email, 'magnus@hagander.net', msg)

			PatchHistory(patch=patch, by=request.user, what='Posted %s with messageid %s' % (what, msg['Message-ID'])).save()

			messages.add_message(request, messages.INFO, "Your email has been queued for pgsql-hackers, and will be sent within a few minutes.")

			return HttpResponseRedirect('/%s/%s/' % (cf.id, patch.id))
	else:
		try:
			form = CommentForm(patch, is_review)
		except Exception, e:
			messages.add_message(request, messages.ERROR, "Failed to build list of response options from the archives: %s" % e)
			return HttpResponseRedirect('/%s/%s/' % (cf.id, patch.id))

	return render_to_response('base_form.html', {
		'cf': cf,
		'form': form,
		'patch': patch,
		'extraformclass': 'patchcommentform',
		'breadcrumbs': [{'title': cf.name, 'href': '/%s/' % cf.pk},
						{'title': 'View patch', 'href': '/%s/%s/' % (cf.pk, patch.pk)}],
		'title': "Add %s" % what,
		'note': '<b>Note!</b> This form will generate an email to the public mailinglist <i>pgsql-hackers</i>, with sender set to %s!' % (request.user.email),
		'savebutton': 'Send %s' % what,
	}, context_instance=RequestContext(request))

@login_required
@transaction.commit_on_success
def status(request, cfid, patchid, status):
	poc = get_object_or_404(PatchOnCommitFest.objects.select_related(), commitfest__id=cfid, patch__id=patchid)

	if poc.is_closed:
		messages.add_message(request, messages.INFO, "The status of this patch cannot be changed in this commitfest. You must modify it in the one where it's open!")
	else:
		if status == 'review':
			newstatus = PatchOnCommitFest.STATUS_REVIEW
		elif status == 'author':
			newstatus = PatchOnCommitFest.STATUS_AUTHOR
		elif status == 'committer':
			newstatus = PatchOnCommitFest.STATUS_COMMITTER
		else:
			raise Exception("Can't happen")

		if newstatus != poc.status:
			# Only save it if something actually changed
			poc.status = newstatus
			poc.patch.set_modified()
			poc.patch.save()
			poc.save()

			PatchHistory(patch=poc.patch, by=request.user, what='New status: %s' % poc.statusstring).save()

	return HttpResponseRedirect('/%s/%s/' % (poc.commitfest.id, poc.patch.id))


@login_required
@transaction.commit_on_success
def close(request, cfid, patchid, status):
	poc = get_object_or_404(PatchOnCommitFest.objects.select_related(), commitfest__id=cfid, patch__id=patchid)

	if poc.is_closed:
		messages.add_message(request, messages.INFO, "The status of this patch cannot be changed in this commitfest. You must modify it in the one where it's open!")
	else:
		poc.leavedate = datetime.now()

		# We know the status can't be one of the ones below, since we
		# have checked that we're not closed yet. Therefor, we don't
		# need to check if the individual status has changed.
		if status == 'reject':
			poc.status = PatchOnCommitFest.STATUS_REJECT
		elif status == 'feedback':
			poc.status = PatchOnCommitFest.STATUS_RETURNED
			# Figure out the commitfest to actually put it on
			newcf = CommitFest.objects.filter(status=CommitFest.STATUS_OPEN)
			if len(newcf) == 0:
				# Ok, there is no open CF at all. Let's see if there is a
				# future one.
				newcf = CommitFest.objects.filter(status=CommitFest.STATUS_FUTURE)
				if len(newcf) == 0:
					raise Exception("No open and no future commitfest exists!")
				elif len(newcf) != 1:
					raise Exception("No open and multiple future commitfests exists!")
			elif len(newcf) != 1:
				raise Exception("Multiple open commitfests exists!")
			# Create a mapping to the new commitfest that we are bouncing
			# this patch to.
			newpoc = PatchOnCommitFest(patch=poc.patch, commitfest=newcf[0], enterdate=datetime.now())
			newpoc.save()
		elif status == 'committed':
			poc.status = PatchOnCommitFest.STATUS_COMMITTED
			#XXX: need to prompt for a committer here!
			raise Exception("Need to prompt for committed if the user who just committed isn't one!")
			poc.patch.committer = Committer.objects.get(user=request.user)
		else:
			raise Exception("Can't happen")

		poc.patch.set_mofified()
		poc.patch.save()
		poc.save()

		PatchHistory(patch=poc.patch, by=request.user, what='Closed in commitfest %s with status: %s' % (poc.commitfest, poc.statusstring)).save()

	return HttpResponseRedirect('/%s/%s/' % (poc.commitfest.id, poc.patch.id))

@login_required
@transaction.commit_on_success
def reviewer(request, cfid, patchid, status):
	get_object_or_404(CommitFest, pk=cfid)
	patch = get_object_or_404(Patch, pk=patchid)

	is_reviewer = request.user in patch.reviewers.all()

	if status=='become' and not is_reviewer:
		patch.reviewers.add(request.user)
		patch.set_modified()
		PatchHistory(patch=patch, by=request.user, what='Added self as reviewer').save()
	elif status=='remove' and is_reviewer:
		patch.reviewers.remove(request.user)
		patch.set_modified()
		PatchHistory(patch=patch, by=request.user, what='Removed self from reviewers').save()
	return HttpResponseRedirect('../../')
