from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'commitfest.views.home'),
    url(r'^activity(?P<rss>\.rss)?/', 'commitfest.views.activity'),
    url(r'^(\d+)/$', 'commitfest.views.commitfest'),
    url(r'^(open|inprogress)/$', 'commitfest.views.redir'),
    url(r'^(?P<cfid>\d+)/activity(?P<rss>\.rss)?/$', 'commitfest.views.activity'),
    url(r'^(\d+)/(\d+)/$', 'commitfest.views.patch'),
    url(r'^(\d+)/(\d+)/edit/$', 'commitfest.views.patchform'),
    url(r'^(\d+)/new/$', 'commitfest.views.newpatch'),
    url(r'^(\d+)/(\d+)/status/(review|author|committer)/$', 'commitfest.views.status'),
    url(r'^(\d+)/(\d+)/close/(reject|feedback|committed|next)/$', 'commitfest.views.close'),
    url(r'^(\d+)/(\d+)/reviewer/(become|remove)/$', 'commitfest.views.reviewer'),
    url(r'^(\d+)/(\d+)/committer/(become|remove)/$', 'commitfest.views.committer'),
    url(r'^(\d+)/(\d+)/(comment|review)/', 'commitfest.views.comment'),
    url(r'^(\d+)/send_email/$', 'commitfest.views.send_email'),
    url(r'^(\d+)/\d+/send_email/$', 'commitfest.views.send_email'),
    url(r'^search/$', 'commitfest.views.global_search'),
    url(r'^ajax/(\w+)/$', 'commitfest.ajax.main'),

    url(r'^selectable/', include('selectable.urls')),

    # Auth system integration
    (r'^(?:account/)?login/?$', 'auth.login'),
    (r'^(?:account/)?logout/?$', 'auth.logout'),
    (r'^auth_receive/$', 'auth.auth_receive'),

    # Account management
    (r'^account/profile/$', 'userprofile.views.userprofile'),
    (r'^account/profile/delmail/$', 'userprofile.views.deletemail'),
    (r'^account/profile/confirm/([0-9a-f]+)/$', 'userprofile.views.confirmemail'),

    # Examples:
    # url(r'^$', 'pgcommitfest.views.home', name='home'),
    # url(r'^pgcommitfest/', include('pgcommitfest.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
