#!/usr/bin/python
# -*- Encoding: utf-8 -*-

# ===================================================================
#
# Module regroupant les classes liées à la simulation d'appels.
#
# ===================================================================

from core.log import Log
from random import randint, random
from threading import Thread
from time import sleep
from enum import Enum
from .group import People

class SENS(Enum):
    """ Demande en descente, en montée ou sans. """
    AUCUN = 0
    BAS = 1
    HAUT = 2


class Appel:
    """
    Cette classe a deux utilités:
     - un appel d'ascenseur
     - un appel lié à un bouton d'appel

     Une demande d'appel peut ainsi facilement être rattachée à un bouton d'appel.
    """

    # étage demandé (appel interne) ou étage de la demande (appel externe)
    etage = None
    # sens
    sens = None
    # si zéro, appel externe, sinon n° de l'ascenseur concerné
    num_asc = None
    # group of people who called l'ascenseur.
    people = None
    # boolean, valid call or not
    valid = True


    def __init__(self, etage, sens, people, num_asc = 0):
        """
        @type  etage: nombre entier
        @param etage: étage demandé ou étage lié à un bouton d'appel
        @type  sens: Enum SENS
        @param sens: sens demandé (ex. appel externe haut ou bas)
        @type  num_asc: nombre entier
        @param num_asc: Numéro de l'ascenseur concerné (ex. appel interne)
        @type  people: Enum People
        @param people: Group of people who called l'ascenseur.
        """
        self.etage = etage
        if isinstance(sens, SENS):
            self.sens = sens
        else:
            self.sens = SENS.AUCUN
        self.num_asc = num_asc

        if isinstance(people, People):
            self.people = people
        else:
            self.people = None
        
        if self.people: 
            if len(self.people)== 0:
                self.valid = False

            # check age requirement.
            if len(self.people) == 1:
                person = self.people.people[0]
                if person.age <= 10:
                    self.valid = False

            # check weight requirement.
            if self.people.weight > 700:
                self.valid = False
        else: 
            self.valid = False

    def __repr__(self):
        """ Représentation """
        return "E=%d|%s|A=%d" % (self.etage, self.sens, self.num_asc)

    def __eq__(self, appel):
        """ Comparaison de deux appels """
        if appel == None:
            return False
        if self.etage == appel.etage and \
           self.sens == appel.sens and \
           self.num_asc == appel.num_asc:
            return True
        else:
            return False


class SimAppels(Log):
    """
    Génère des appels d'ascenseur.
    Des appels externes sont régulièrement générés aléatoirement; et chaque
    appel externe déclenche à l'arrivée d'un ascenseur une demande d'appel
    interne.
    """

    batiment = None
    # Arrêt du thread si True
    flg_stop = None

    def __init__(self, batiment):
        self.batiment = batiment
        self.flg_stop = False
        thrd = Thread(target = self.__generer_appels_externes,
                           args = (8, batiment.automate.appel))
        thrd.start()

    def __generer_appels_externes(self, delai, fn_appel):
        """
        @type  delai: nombre
        @param delai: durée d'attente en secondes souhaitée
        @type  fn_appel: fonction de retour
        @param fn_appel: fonction appelée à la génération d'un appel
        """
        self.logger.debug("Génération d'appels externes OK.")
        idx_etage_max = self.batiment.params.nb_etages - 1
        while not self.flg_stop:
            # temps d'attente, avec une variation max de 1 seconde.
            variation = random()
            sleep(variation + (1 * delai))
            # on liste les etages courant des ascenseurs pour éviter les doubles
            # appels inutiles
            _etages_exclus = []
            for asc in self.batiment.automate.ascenseurs:
                if asc.appel:
                    _etages_exclus.append(asc.appel.etage)
                _etages_exclus.append(asc.etage_courant)
            # choix d'un étage
            etage = _etages_exclus[0]
            while etage in _etages_exclus:
                etage = randint(0, idx_etage_max)
            # choix du sens demandé
            if self.batiment.params.type_appel == 1:
                appel = Appel(etage, SENS.AUCUN)
            else:
                # si on est au dernier étage, on ne peut que descendre
                if etage == idx_etage_max:
                    sens = SENS.BAS
                # si on est au RDC, on ne peut que monter
                elif etage == 0:
                    sens = SENS.HAUT
                # sinon c'est aléatoire
                else:
                    sens = randint(1, 2)
                    if sens == 1: sens = SENS.BAS
                    if sens == 2: sens = SENS.HAUT
                appel = Appel(etage, sens)
            # self.logger.debug("Nouvel appel externe: %s" % appel)
            fn_appel(appel)
        self.logger.debug("Arrêt de la simulation d'appels.")

    def generer_appel_interne(self, ascenseur, appel):
        """
        Après l'arrivée d'un ascenseur suite à un appel externe,
        un appel interne est généré.
        @type  ascenseur: objet Ascenseur
        @param ascenseur: ascenseur concerné
        @type  appel: objet Appel
        @param appel: données sur l'appel concerné
        """
        # on s'attend à une demande d'étage différent de celui actuel
        etage = appel.etage
        while etage == appel.etage:
            idx_etage_max = self.batiment.params.nb_etages - 1
            etage = randint(0, idx_etage_max)
        appel_interne = Appel(etage, SENS.AUCUN, ascenseur.num_asc)
        # self.logger.debug("A l'étage <%d>, nouvel appel interne: %s" % \
        #                  (appel.etage, appel_interne))
        self.batiment.automate.appel(appel_interne)
