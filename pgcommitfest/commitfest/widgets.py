from django.forms import TextInput
from django.utils.safestring import mark_safe

class ThreadPickWidget(TextInput):
	def render(self, name, value, attrs=None):
		html = super(ThreadPickWidget, self).render(name, value, attrs)
		html = html + '&nbsp;<button class="btn attachThreadButton" id="btn_%s">Find thread</button>' % name
		return mark_safe(html)
