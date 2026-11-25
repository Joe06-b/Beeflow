"""Outils partagés par les tests du module Environnement."""

import itertools
from datetime import date

_compteur = itertools.count(1)


def creer_utilisateur_test(user_model, username, password, **extra):
    """Crée un utilisateur de test compatible avec le modèle utilisateur du projet.

    Le modèle personnalisé de l'équipe (UtilisateursApp.Utilisateur) impose des
    champs obligatoires et uniques (email, téléphone, date de naissance...).
    Ils ne sont remplis que s'ils existent, pour rester compatible avec le
    modèle User par défaut de Django.
    """
    champs = {f.name for f in user_model._meta.get_fields()}
    n = next(_compteur)
    valeurs_par_defaut = {
        "email": f"{username}@test.beeflow.local",
        "telephone": f"9{n:07d}",
        "date_naissance": date(1990, 1, 1),
        "sexe": "homme",
        "role": "admin" if extra.get("is_staff") else "apiculteur",
        "premiere_connexion": False,
    }
    for champ, valeur in valeurs_par_defaut.items():
        if champ in champs:
            extra.setdefault(champ, valeur)
    return user_model.objects.create_user(username=username, password=password, **extra)
