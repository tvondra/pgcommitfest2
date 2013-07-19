from django.contrib import admin

from models import *

class PatchOnCommitFestInline(admin.TabularInline):
	model = PatchOnCommitFest
	extra=1

class PatchAdmin(admin.ModelAdmin):
	inlines = (PatchOnCommitFestInline,)
	list_display = ('name', )
#	list_filter = ('commitfests_set__commitfest__name',)

admin.site.register(Committer)
admin.site.register(CommitFest)
admin.site.register(Topic)
admin.site.register(Patch, PatchAdmin)
admin.site.register(PatchHistory)