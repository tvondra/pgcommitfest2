from django.template.defaultfilters import stringfilter
from django import template

from pgcommitfest.commitfest.models import PatchOnCommitFest

register = template.Library()

@register.filter(name='patchstatusstring')
@stringfilter
def patchstatusstring(value):
	i = int(value)
	return [v for k,v in PatchOnCommitFest._STATUS_CHOICES if k==i][0]

@register.filter(is_safe=True)
def label_class(value, arg):
	return value.label_tag(attrs={'class': arg})

@register.filter(name='alertmap')
@stringfilter
def alertmap(value):
	if value in ('error', 'success'): return 'alert-%s' % value
	return ''

@register.filter(name='hidemail')
@stringfilter
def hidemail(value):
	return value.replace('@', ' at ')
