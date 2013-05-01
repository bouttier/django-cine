#-*- coding: utf-8 -*-

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from cine.models import *

from datetime import date


def home(request):
    c = {}
    films = []
    N = len(Film.objects.filter(vu=False)) * len(get_cinephiles()) + 1
    for soiree in Soiree.objects.order_by('date').filter(date__gte=date.today()):
        if DispoToWatch.objects.filter(dispo='O', soiree=soiree):
            films.append((soiree, []))
            for film in Film.objects.filter(categorie=soiree.categorie, vu=False):
                if film.respo.dispotowatch_set.filter(soiree=soiree, dispo='O'):
                    score = N
                    for dispo in DispoToWatch.objects.filter(dispo='O', soiree=soiree):
                        vote = Vote.objects.get(cinephile=dispo.cinephile, film=film)
                        score -= vote.choix
                        if vote.plusse:
                            score += 1
                    films[-1][1].append((score, film))
            films[-1][1].sort()
            films[-1][1].reverse()
    c['films'] = films
    return render(request, 'cine/home.html', c)


@login_required
def films(request):
    c = {
            'films': Film.objects.filter(vu=False),
            'films_vu': Film.objects.filter(vu=True),
            'edit': True
            }
    new = True
    if request.method == 'POST':
        form = FilmForm(request.POST)
        if 'slug' in form.data and form.data['slug']:
            film = Film.objects.get(slug=form.data['slug'])
            if film.respo == request.user:
                form = FilmForm(request.POST, instance=film)
                new = False
            else:
                messages.error(request, u"Vous n’êtes pas respo pour ce film…")
        if form.is_valid():
            form.instance.respo = request.user
            form.save()
            form = FilmForm()
            if new:
                messages.success(request, u'Film ajouté :D')
            else:
                messages.success(request, u'Film modifié')
            c['edit'] = False
        else:
            messages.error(request, u'Le formulaire n’est pas valide.')
    else:
        if 'edit' in request.GET:
            film = Film.objects.get(slug=request.GET['edit'])
            c['slug'] = film.slug
            form = FilmForm(instance=film)
        else:
            form = FilmForm()
            c['edit'] = False
        if 'respo' in request.GET:
            respo = User.objects.get(username=request.GET['respo'])
            c['films'] = Film.objects.filter(respo=respo,)
    c['filmform'] = form
    return render(request, 'cine/films.html', c)


@login_required
def comms(request, slug):
    film = get_object_or_404(Film, slug=slug)
    edit = False  # Not yet implemented
    if request.method == 'POST':
        form = CommForm(request.POST)
        if form.is_valid():
            form.instance.posteur = request.user
            form.instance.film = film
            form.save()
    c = {
            'film': film,
            'comms': film.commentaire_set.all().order_by('date'),
            'form': CommForm(),
            'edit': edit,
            }
    return render(request, 'cine/comms.html', c)


@login_required
def dispos(request):
    dispos = DispoToWatch.objects.filter(cinephile=request.user, soiree__date__gte=date.today()).order_by('soiree__date')
    c = {'dispos': dispos}
    if request.method == 'POST':
        for dispo in dispos:
            strdate = dispo.soiree.date.strftime('%Y-%m-%d')
            if strdate in request.POST:
                dispo.dispo = request.POST[strdate]
                dispo.save()
            else:
                print strdate, 'not in POST:', request.POST
    return render(request, 'cine/dispos.html', c)


@login_required
def votes(request):
    if request.method == 'POST':
        ordre = request.POST['ordre'].split(',')[:-1]
        if ordre:
            i = 1
            for vote in ordre:
                film = Film.objects.get(slug=vote)
                v = Vote.objects.get(film=film, cinephile=request.user)
                v.choix = i
                v.save()
                i += 1
    c = {'votes': Vote.objects.filter(cinephile=request.user, film__vu=False).order_by("choix")}
    return render(request, 'cine/votes.html', c)


@login_required
def cinephiles(request):
    c = {'cinephiles': get_cinephiles()}
    return render(request, 'cine/cinephiles.html', c)
