from django import forms
from django.forms import ValidationError
from django.forms.widgets import HiddenInput
from django.db.models import Q
from django.contrib.auth.models import User

from selectable.forms.widgets import AutoCompleteSelectMultipleWidget

from models import Patch, MailThread, PatchOnCommitFest
from lookups import UserLookup
from widgets import ThreadPickWidget
from ajax import _archivesAPI

class CommitFestFilterForm(forms.Form):
	text = forms.CharField(max_length=50, required=False)
	status = forms.ChoiceField(required=False)
	author = forms.ChoiceField(required=False)
	reviewer = forms.ChoiceField(required=False)
	sortkey = forms.IntegerField(required=False)

	def __init__(self, cf, *args, **kwargs):
		super(CommitFestFilterForm, self).__init__(*args, **kwargs)

		self.fields['sortkey'].widget = forms.HiddenInput()

		c = [(-1, '* All')] + list(PatchOnCommitFest._STATUS_CHOICES)
		self.fields['status'] = forms.ChoiceField(choices=c, required=False)

		q = Q(patch_author__commitfests=cf) | Q(patch_reviewer__commitfests=cf)
		userchoices = [(-1, '* All'), (-2, '* None'), (-3, '* Yourself') ] + [(u.id, '%s %s (%s)' % (u.first_name, u.last_name, u.username)) for u in User.objects.filter(q).distinct().order_by('last_name', 'first_name')]
		self.fields['author'] = forms.ChoiceField(choices=userchoices, required=False)
		self.fields['reviewer'] = forms.ChoiceField(choices=userchoices, required=False)

		for f in ('status', 'author', 'reviewer',):
			self.fields[f].widget.attrs = {'class': 'input-medium'}

class PatchForm(forms.ModelForm):
	class Meta:
		model = Patch
		exclude = ('commitfests', 'mailthreads', 'modified', 'lastmail', )
		widgets = {
			'authors': AutoCompleteSelectMultipleWidget(lookup_class=UserLookup, position='top'),
			'reviewers': AutoCompleteSelectMultipleWidget(lookup_class=UserLookup, position='top'),
		}

	def __init__(self, *args, **kwargs):
		super(PatchForm, self).__init__(*args, **kwargs)
		self.fields['authors'].help_text = 'Enter part of name to see list'
		self.fields['reviewers'].help_text = 'Enter part of name to see list'
		self.fields['committer'].label_from_instance = lambda x: '%s %s (%s)' % (x.user.first_name, x.user.last_name, x.user.username)


class NewPatchForm(forms.ModelForm):
	threadmsgid = forms.CharField(max_length=200, required=True, label='Specify thread msgid', widget=ThreadPickWidget)
#	patchfile = forms.FileField(allow_empty_file=False, max_length=50000, label='or upload patch file', required=False, help_text='This may be supported sometime in the future, and would then autogenerate a mail to the hackers list. At such a time, the threadmsgid would no longer be required.')

	class Meta:
		model = Patch
		exclude = ('commitfests', 'mailthreads', 'modified', 'authors', 'reviewers', 'committer', 'wikilink', 'gitlink', 'lastmail', )

def _fetch_thread_choices(patch):
	for mt in patch.mailthread_set.order_by('-latestmessage'):
		ti = sorted(_archivesAPI('/message-id.json/%s' % mt.messageid), key=lambda x: x['date'], reverse=True)
		yield [mt.subject,
			   [('%s,%s' % (mt.messageid, t['msgid']),'From %s at %s' % (t['from'], t['date'])) for t in ti]]


review_state_choices = (
	(0, 'Tested'),
	(1, 'Passed'),
)

def reviewfield(label):
	return forms.MultipleChoiceField(choices=review_state_choices, label=label, widget=forms.CheckboxSelectMultiple, required=False)

class CommentForm(forms.Form):
	responseto = forms.ChoiceField(choices=[], required=True, label='In response to')

	# Specific checkbox fields for reviews
	review_installcheck = reviewfield('make installcheck-world')
	review_implements = reviewfield('Implements feature')
	review_spec = reviewfield('Spec compliant')
	review_doc = reviewfield('Documentation')

	message = forms.CharField(required=True, widget=forms.Textarea)
	newstatus = forms.ChoiceField(choices=PatchOnCommitFest.OPEN_STATUS_CHOICES, label='New status')

	def __init__(self, patch, poc, is_review, *args, **kwargs):
		super(CommentForm, self).__init__(*args, **kwargs)
		self.is_review = is_review

		self.fields['responseto'].choices = _fetch_thread_choices(patch)
		self.fields['newstatus'].initial = poc.status
		if not is_review:
			del self.fields['review_installcheck']
			del self.fields['review_implements']
			del self.fields['review_spec']
			del self.fields['review_doc']

	def clean_responseto(self):
		try:
			(threadid, respid) = self.cleaned_data['responseto'].split(',')
			self.thread = MailThread.objects.get(messageid=threadid)
			self.respid = respid
		except MailThread.DoesNotExist:
			raise ValidationError('Selected thread appears to no longer exist')
		except:
			raise ValidationError('Invalid message selected')
		return self.cleaned_data['responseto']

	def clean(self):
		if self.is_review:
			for fn,f in self.fields.items():
				if fn.startswith('review_') and self.cleaned_data.has_key(fn):
					if '1' in self.cleaned_data[fn] and not '0' in self.cleaned_data[fn]:
						self.errors[fn] = (('Cannot pass a test without performing it!'),)
		return self.cleaned_data

class BulkEmailForm(forms.Form):
	reviewers = forms.CharField(required=False, widget=HiddenInput())
	authors = forms.CharField(required=False, widget=HiddenInput())
	subject = forms.CharField(required=True)
	body = forms.CharField(required=True, widget=forms.Textarea)
	confirm = forms.BooleanField(required=True, label='Check to confirm sending')

	def __init__(self, *args, **kwargs):
		super(BulkEmailForm, self).__init__(*args, **kwargs)
