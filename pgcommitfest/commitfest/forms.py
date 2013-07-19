from django import forms
from django.forms import ValidationError

from selectable.forms.widgets import AutoCompleteSelectMultipleWidget

from models import Patch, MailThread
from lookups import UserLookup
from ajax import _archivesAPI

class PatchForm(forms.ModelForm):
	class Meta:
		model = Patch
		exclude = ('commitfests', 'mailthreads', 'modified', )
		widgets = {
			'authors': AutoCompleteSelectMultipleWidget(lookup_class=UserLookup, position='top'),
			'reviewers': AutoCompleteSelectMultipleWidget(lookup_class=UserLookup, position='top'),
		}

	def __init__(self, *args, **kwargs):
		super(PatchForm, self).__init__(*args, **kwargs)
		self.fields['authors'].help_text = 'Enter part of name to see list'
		self.fields['reviewers'].help_text = 'Enter part of name to see list'
		self.fields['committer'].label_from_instance = lambda x: '%s %s (%s)' % (x.user.first_name, x.user.last_name, x.user.username)


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
	review_installcheck = reviewfield('make installcheck')
	review_implements = reviewfield('Implements feature')
	review_spec = reviewfield('Spec compliant')
	review_doc = reviewfield('Documentation')

	message = forms.CharField(required=True, widget=forms.Textarea)

	def __init__(self, patch, is_review, *args, **kwargs):
		super(CommentForm, self).__init__(*args, **kwargs)
		self.is_review = is_review

		self.fields['responseto'].choices = _fetch_thread_choices(patch)
		if not is_review:
			del self.fields['reviewtype']

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
