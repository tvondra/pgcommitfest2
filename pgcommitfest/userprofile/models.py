from django.db import models
from django.contrib.auth.models import User

class UserExtraEmail(models.Model):
	user = models.ForeignKey(User, null=False, blank=False, db_index=True)
	email = models.EmailField(max_length=100, null=False, blank=False, unique=True)
	confirmed = models.BooleanField(null=False, blank=False, default=False)
	token = models.CharField(max_length=100, null=False, blank=True)
	tokensent = models.DateTimeField(null=False, blank=False)

	def __unicode__(self):
		return self.email

	class Meta:
		ordering = ('user', 'email')
		unique_together = (('user', 'email'),)


class UserProfile(models.Model):
	user = models.ForeignKey(User, null=False, blank=False)
	selectedemail = models.ForeignKey(UserExtraEmail, null=True, blank=True,
									  verbose_name='Sender email')

	def __unicode__(self):
		return unicode(self.user)
