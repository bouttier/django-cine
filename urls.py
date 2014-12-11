from __future__ import unicode_literals

from django.conf.urls import patterns, url
from django.views.generic import RedirectView, DetailView, ListView

from .models import Soiree, Film
from .views import votes, SoireeCreateView, FilmListView, FilmCreateView, FilmUpdateView, FilmVuView, CinephileListView, ICS

urlpatterns = patterns('',
    url(r'^votes$', votes, name='votes'),

    url(r'^$', ListView.as_view(model=Soiree), name='home'),
    url(r'^soiree$', SoireeCreateView.as_view(), name='ajout_soiree'),

    url(r'^films$', FilmListView.as_view(), name='films'),
    url(r'^film/ajout$', FilmCreateView.as_view(), name='ajout_film'),
    url(r'^film/maj/(?P<slug>[^/]+)$', FilmUpdateView.as_view(), name='maj_film'),
    url(r'^film/vu/(?P<slug>[^/]+)$', FilmVuView.as_view(), name='film_vu'),
    url(r'^film/(?P<slug>[^/]+)$', DetailView.as_view(model=Film), name='film'),
    url(r'^comms/(?P<slug>[^/]+)$', RedirectView.as_view(pattern_name='film')),

    url(r'^cinephiles$', CinephileListView.as_view(), name='cinephiles'),

    url(r'^cinenim.ics$', ICS.as_view(), name='ics'),
)
