# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import json
import logging
import re
from datetime import datetime, timedelta
from StringIO import StringIO

import requests
from PIL import Image
from pytz import timezone

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.contrib.sites.models import Site
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.core.urlresolvers import reverse
from django.db.models import (BooleanField, CharField, DateTimeField, ForeignKey, ImageField, IntegerField, Manager, ManyToManyField, Model, SlugField,
                              TextField, URLField)
from django.template.defaultfilters import slugify
from django.utils.encoding import python_2_unicode_compatible

logger = logging.getLogger(__name__)
tz = timezone(settings.TIME_ZONE)
tzloc = tz.localize


CHOIX_CATEGORIE = (
        ('D', 'Divertissement'),
        ('C', 'Culture'),
        )
CHOIX_CATEGORIE_DICT = dict(CHOIX_CATEGORIE)

CHOIX_ANNEES = [(annee, annee) for annee in range(datetime.now().year + 1, 1900, -1)]

IMDB_API_URL = 'http://www.omdbapi.com/'


def get_cinephiles():
    return User.objects.filter(groups__name='cine')


def full_url(path):
    return 'http://%s%s' % (Site.objects.get_current().domain, path)


def get_verbose_name(model, name):
    try:
        return model._meta.get_field(name).verbose_name
    except:
        return None


@python_2_unicode_compatible
class Film(Model):
    titre = CharField(max_length=200, unique=True)
    respo = ForeignKey(User)
    description = TextField()
    slug = SlugField(unique=True, blank=True)

    categorie = CharField(max_length=1, choices=CHOIX_CATEGORIE, default='D')
    annee_sortie = IntegerField(max_length=4, choices=CHOIX_ANNEES, blank=True, null=True, verbose_name="Année de sortie")

    titre_vo = CharField(max_length=200, blank=True, null=True, verbose_name="Titre en VO")
    imdb = URLField(blank=True, null=True, verbose_name="IMDB")
    allocine = URLField(blank=True, null=True, verbose_name="Allociné")
    realisateur = CharField(max_length=200, null=True, blank=True, verbose_name="Réalisateur")
    duree = CharField(max_length=20, null=True, blank=True, verbose_name="Durée")
    duree_min = IntegerField("Durée en minutes", null=True)

    vu = BooleanField(default=False)

    imdb_id = CharField(max_length=10, verbose_name="id IMDB", null=True, blank=True)

    imdb_poster_url = URLField(blank=True, null=True, verbose_name="URL du poster")
    imdb_poster = ImageField(upload_to='cine/posters', blank=True, null=True)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.titre)
        img = requests.get(self.imdb_poster_url)
        if img.status_code == requests.codes.ok:
            img_temp = NamedTemporaryFile(delete=True)
            img_temp.write(img.content)
            img_temp.flush()
            self.imdb_poster.save(self.slug, File(img_temp), save=False)
            img_temp.close()
        super(Film, self).save(*args, **kwargs)

        # Création des votes & envoi des mails de notif
        film_url = self.get_full_url()
        vote_url = full_url(reverse('cine:votes'))

        message = "Hello :)\n\n%s a proposé un nouveau film : %s (%s)' ; " % (self.respo, self.titre, film_url)
        message += "tu peux donc aller actualiser ton classement (%s) \\o/ \n\n @+!" % vote_url

        for cinephile in get_cinephiles():
            vote = Vote.objects.get_or_create(film=self, cinephile=cinephile)
            if vote[1] and not settings.DEBUG:
                cinephile.email_user('[CinéNim] Film ajouté !', message)

    def get_absolute_url(self):
        return reverse('cine:film', kwargs={'slug': self.slug})

    def get_full_url(self):
        return full_url(self.get_absolute_url())

    def get_categorie(self):
        return CHOIX_CATEGORIE_DICT[self.categorie]

    def get_description(self):
        return self.description.replace('\r\n', '\\n')

    def score_absolu(self):
        score = 0
        for vote in self.vote_set.all():
            score -= vote.choix
            if vote.plusse:
                score += 1
        return score

    @staticmethod
    def get_imdb_dict(imdb_id):
        try:
            imdb_id = re.search(r'tt\d+', imdb_id).group()
            imdb_infos = requests.get(IMDB_API_URL, params={'i': imdb_id}).json()
            return {
                    'realisateur': imdb_infos['Director'],
                    'description': imdb_infos['Plot'],
                    'imdb_poster_url': imdb_infos['Poster'],
                    'annee_sortie': imdb_infos['Year'],
                    'titre': imdb_infos['Title'],
                    'titre_vo': imdb_infos['Title'],
                    'duree_min': timedelta(**dict([
                        (key, int(value) if value else 0) for key, value in
                        re.search(r'((?P<hours>\d+) h )?(?P<minutes>\d+) min', imdb_infos['Runtime']).groupdict().items()
                        ])).seconds / 60,  # TGCM
                    'imdb_id': imdb_id,
                    }
        except:
            return {}

    def __str__(self):
        return self.titre


@python_2_unicode_compatible
class Vote(Model):
    film = ForeignKey(Film)
    cinephile = ForeignKey(User)
    choix = IntegerField(default=9999)
    plusse = BooleanField(default=False)  # TODO: NYI

    unique_together = ("film", "cinephile")

    def __str__(self):
        if self.plusse:
            return '%s \t %i + \t %s' % (self.film, self.choix, self.cinephile)
        return '%s \t %i \t %s' % (self.film, self.choix, self.cinephile)

    class Meta:
        ordering = ['choix', 'film']


class SoireeAVenirManager(Manager):
    def get_query_set(self):
        return super(SoireeAVenirManager, self).get_query_set().filter(date__gte=tzloc(datetime.now() - timedelta(hours=5)))


@python_2_unicode_compatible
class Soiree(Model):
    date = DateTimeField()
    categorie = CharField(max_length=1, choices=CHOIX_CATEGORIE, default='D', blank=True)
    hote = ForeignKey(User)
    favoris = ForeignKey(Film, null=True)

    objects = Manager()
    a_venir = SoireeAVenirManager()

    def save(self, *args, **kwargs):
        if not self.id:
            try:
                if Soiree.objects.latest().categorie == 'C':
                    self.categorie = 'D'
                else:
                    self.categorie = 'C'
            except:
                self.categorie = 'D'  # Si c’est la première soirée
        super(Soiree, self).save(*args, **kwargs)

        dispos_url = full_url(reverse('cine:dispos'))

        message = 'Hello :) \n\n%s a proposé une soirée %s le %s ; ' % (self.hote, self.get_categorie(), self.date)
        message += 'tu peux donc aller mettre à jour tes disponibilités (%s) \\o/ \n\n@+ !' % dispos_url

        for cinephile in get_cinephiles():
            dtw = DispoToWatch.objects.get_or_create(soiree=self, cinephile=cinephile)
            if not settings.DEBUG and dtw[1]:
                cinephile.email_user('[CinéNim] Soirée Ajoutée !', message)

    def get_categorie(self):
        return CHOIX_CATEGORIE_DICT[self.categorie]

    def presents(self):
        return ", ".join([cinephile.cinephile.username for cinephile in self.dispotowatch_set.filter(dispo='O')])

    def pas_surs(self):
        return ", ".join([cinephile.cinephile.username for cinephile in self.dispotowatch_set.filter(dispo='N')])

    def __str__(self):
        return '%s:%s' % (self.date, self.categorie)

    class Meta:
        ordering = ["date"]
        get_latest_by = 'date'


@python_2_unicode_compatible
class DispoToWatch(Model):
    soiree = ForeignKey(Soiree)
    cinephile = ForeignKey(User)

    unique_together = ("soiree", "cinephile")

    CHOIX_DISPO = (
            ('O', 'Dispo'),
            ('P', 'Pas dispo'),
            ('N', 'Ne sais pas'),
            )

    dispo = CharField(max_length=1, choices=CHOIX_DISPO, default='N')

    def __str__(self):
        return '%s %s %s' % (self.soiree, self.dispo, self.cinephile)

    class Meta:
        ordering = ['soiree__date']
