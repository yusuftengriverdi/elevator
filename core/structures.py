#!/usr/bin/python
# -*- Encoding: utf-8 -*-

# ===================================================================
#
# Module regroupant les classes "contrôleurs".
#
# ===================================================================

from threading import Thread
from time import sleep
from core.log import Log
from gui.units import BatimentGui, AscenseurGui, \
                      BoutonInterneSimpleGui, BoutonExterneSimpleGui, \
                      BoutonInterneDoubleGui, BoutonExterneHautGui, BoutonExterneBasGui
from core.etats import EtatArretFerme
from core.activite import SENS, Appel, SimAppels


class Bouton(Log):
    """
    Bouton d'appel de l'ascenseur.
    L'objet <appel> contient les mêmes valeurs qu'un appel attendu sur ce bouton.
    """
    batiment = None
    # regroupe l'étage, l'ascenseur et le sens
    appel = None
    # False si le bouton est éteint
    etat = None
    # représentation graphique
    bouton_gui = None
    # etage actuel
    etage = None
    def __init__(self, batiment, etage, sens, num_asc = 0):
        """
        Constructeur.
        Par défaut, si num_asc == 0 alors aucun ascenseur n'est lié, il s'agit
        donc d'un bouton pour un appel externe. Sinon, c'est un bouton pour un
        appel interne de l'ascenseur spécifié.

        Exemples:
            E=1|SENS.AUCUN|A=0 => bouton externe seul
            E=1|SENS.HAUT|A=0 => bouton externe pour monter
            E=1|SENS.AUCUN|A=1 => bouton interne de l'ascenseur n°1
        """
        self.etage = etage
        self.batiment = batiment
        # bouton éteint par défaut
        self.etat = False
        # s'il s'agit d'un bouton interne, le sens est ignoré (logiquement,
        # il est à SENS.AUCUN)
        self.appel = Appel(self.etage, SENS.AUCUN, [])
        if num_asc != 0:
            if sens != SENS.AUCUN:
                self.logger.warning("Le sens est ignoré pour un bouton d'appel interne (%s)." % self.appel)
            if self.batiment.params.type_appel == 1:
                self.bouton_gui = BoutonInterneSimpleGui(self)
            else:
                self.bouton_gui = BoutonInterneDoubleGui(self)
        # s'il s'agit d'un bouton externe
        else:
            if sens == SENS.HAUT:
                self.bouton_gui = BoutonExterneHautGui(self)
            elif sens == SENS.BAS:
                self.bouton_gui = BoutonExterneBasGui(self)
            else:
                # sens == SENS.AUCUN ou autre
                self.bouton_gui = BoutonExterneSimpleGui(self)
        

    def __repr__(self):
        return "<A:%s E: %s>" % (self.appel, self.etat)

    def clicked(self, sens, people):
        self.appel = Appel(self.etage, sens, people)
        self.etat = True


class Batiment(Log):
    """
    Gestion du bâtiment (boutons d'appels)
    """

    params = None
    boutons = None
    # gestionnaire du ou des ascenseurs
    automate = None
    # représentation graphique
    batiment_gui = None
    # simulation d'appels
    sim_appels = None

    def __init__(self, area, params):
        """
        @type  area: nombre entier
        @param area: nombre d'étages du bâtiment
        @type  params: objet Params
        @param params: regroupe les options communes
        """
        self.params = params
        # actualisation des variables servant au dessin en général
        self.batiment_gui = BatimentGui(area, params)
        # lancement de l'automate
        self.automate = Automate(self, params.nb_asc)
        # création des boutons d'appel externe
        if self.params.type_appel == 1:
            # un bouton d'appel externe par étage
            self.boutons = [Bouton(self, etage, SENS.AUCUN) for etage in range(params.nb_etages)]
        else:
            # deux par étage, un haut et un bas, sauf pour le 1er et le dernier étage
            self.boutons = [Bouton(self, etage, SENS.HAUT) for etage in range(params.nb_etages - 1)]
            self.boutons.extend([Bouton(self, etage, SENS.BAS) for etage in range(1, params.nb_etages)])
        # création des boutons d'appel interne, un par ascenseur et part étage
        for asc in self.automate.ascenseurs:
            self.boutons.extend([Bouton(self, etage, SENS.AUCUN, asc.num_asc) for etage in range(params.nb_etages)])
        # self.logger.debug("Boutons créés: %s" % self.boutons)
        # lancement de la simulation d'appels
        self.sim_appels = SimAppels(self)

    def dessiner(self, area, context):
        """
        @type  area: DrawingArea
        @param area: Composant lié à l'événement
        @type  context: cairo context
        @param context: Surface de dessin
        """
        self.batiment_gui.on_draw(area, context)
        for asc in self.automate.ascenseurs:
            asc.ascenseur_gui.on_draw(area, context)
        for bouton in self.boutons:
            bouton.bouton_gui.on_draw(area, context)

    def on_simu_stop(self):
        """ Arrêt de la simulation """
        for asc in self.automate.ascenseurs:
            asc.on_simu_stop()


class Automate(Log):
    """
    Donneur d'ordre d'un ascenseur.
    Les appels sont pris dans l'ordre d'arrivée des demandes, sans
    optimisation; une demande à mi-parcours sera ignorée.
    """

    batiment = None
    ascenseurs = None
    appels = None

    def __init__(self, batiment, nb_asc):
        """
        L'automate crée les ascenseurs nécessaires.
        @type  batiment: Batiment
        @param batiment: objet Batiment
        @type  nb_asc: nombre entier
        @param nb_asc: nombre d'ascenseurs à gérer
        """
        self.batiment = batiment
        self.ascenseurs = []
        self.appels = []
        for idx_asc in range(nb_asc):
            # création des ascenseurs avec leur état par défaut
            asc = Ascenseur(self, idx_asc + 1)
            asc.etat = EtatArretFerme(asc)
            self.ascenseurs.append(asc)

    def allumage_bouton(self, appel, flg_status):
        """
        Demande d'allumage ou d'extinction du bouton d'appel externe.
        @type  appel: objet Appel
        @param appel: données sur l'appel
        @type  flg_status: Boolean
        @param flg_status: True s'il faut allumer, False sinon
        """
        bouton = None
        # si c'est un appel interne
#         if appel.num_asc != 0:
#             for _btn in self.batiment.boutons:
#                 if _btn.appel.etage == appel.etage \
#                 and _btn.appel.num_asc == appel.num_asc:
#                     bouton = _btn
#                     break
        # si c'est un appel externe, l'appel correspond aux données du bouton
        # elif appel.num_asc == 0:
        for _btn in self.batiment.boutons:
            if _btn.appel == appel:
                bouton = _btn
                break
        if not bouton:
            self.logger.warning("Impossible de trouver le bouton d'appel :")
            self.logger.warning(" * Appel: %s" % appel)
            self.logger.warning(" * Boutons: %s" % [bouton.appel for bouton in self.batiment.boutons])
        else:
            bouton.etat = flg_status
            # TODO: éteindre aussi le bouton d'appel interne

    def alarme_declenchee(self):
        """ bouton alarme de l'ascenseur """
        self.logger.debug("Alarme déclenchée: Driiiiing !")
        # TODO: gérer l'alarme
        # ...

    def appel(self, appel):
        """
        Réception d'un appel d'ascenseur, il est aiguillé en fonction
        du type d'appel renseigné.
        """
        if appel.num_asc == 0:
            self._appel_externe(appel)
        else:
            self._appel_interne(appel)

    def _appel_interne(self, appel):
        """
        Un appel interne ne concerne que l'ascenseur recevant la demande.
        @type  idx_asc: nombre entier
        @param idx_asc: index de l'ascenseur (0 pour le 1er)
        @type  appel: nombre entier
        @param appel: numéro de l'étage
        """
        flg_appel = False
        for memo_appel in self.appels:
            # s'il y a un appel pour cet étage depuis cet ascenseur
            if memo_appel.num_asc == appel.num_asc \
               and memo_appel.etage == appel.etage:
                flg_appel = True
        # si l'appel n'est pas déjà mémorisé...
        if not flg_appel:
            self.appels.append(appel)
            self.allumage_bouton(appel, True)
            self.logger.debug("Appel interne reçu: %s" % appel)
            self.ascenseurs[appel.num_asc - 1].etat.appel(self)

    def _appel_externe(self, appel):
        """
        Un appel externe concerne tous les ascenseurs.
        @type  appel: nombre entier
        @param appel: numéro de l'étage
        """
        flg_appel = False
        for memo_appel in self.appels:
            if memo_appel.etage == appel.etage:
                flg_appel = True

        if not flg_appel:
            # c'est un nouvel appel, il est enregistré
            self.appels.append(appel)
            self.allumage_bouton(appel, True)
            self.logger.debug("Appel externe reçu: %s" % appel)
            # Si un ascenseur est dispo il prendra l'appel
            for asc in self.ascenseurs:
                asc.etat.appel(self)

    def prochaine_destination(self, ascenseur):
        """
        Algorithme optimisé: l'ascenseur essaie de prendre les appels en montant
        puis en descendant. En cours de montée, il ignore les appel pour descendre,
        et inversement. S'il y a plusieurs ascenseurs, ils se partagent les appels;
        ils ne se réservent pas une liste d'appels saus leurs appels internes.
        Retourne un appel en attente à traiter.
        @type  ascenseur: Ascenseur
        @param ascenseur: objet Ascenseur demandant une destination
        """
        _appels = None
        # self.logger.debug("Ascenseur <%d>: appels en attente: %s" % \
        #                  (ascenseur.num_asc, self.appels))
        # si l'ascenseur n'était pas en train de descendre et qu'il peut monter,
        # on liste les appels internes à l'ascenseur et les appels externes
        # qui concernent les étages supérieurs
        if ascenseur.sens != SENS.BAS and \
           ascenseur.etage_courant < self.batiment.params.nb_etages - 1:
            _appels = [appel for appel in self.appels \
                       if (appel.num_asc == ascenseur.num_asc or appel.num_asc == 0) \
                           and appel.etage >= ascenseur.etage_courant]
            _appels.sort(key = lambda appel: appel.etage)
            # self.logger.debug("Ascenseur <%d> à l'étage <%d>: appels retenus en montée: %s" % \
            #                  (ascenseur.num_asc, ascenseur.etage_courant, _appels))
        # sinon si l'ascenseur était en train de descendre et qu'il peut encore le faire,
        # on liste les appels internes à l'ascenseur et les appels externes
        # qui concernent les étages inférieurs
        elif ascenseur.sens != SENS.HAUT and ascenseur.etage_courant > 0:
            _appels = [appel for appel in self.appels \
                       if (appel.num_asc == ascenseur.num_asc or appel.num_asc == 0) \
                           and appel.etage <= ascenseur.etage_courant]
            _appels.sort(key = lambda appel: appel.etage, reverse = True)
            # self.logger.debug("Ascenseur <%d> à l'étage <%d>: appels retenus en descente: %s" % \
            #                  (ascenseur.num_asc, ascenseur.etage_courant, _appels))
        else:
            self.logger.warning("Ascenseur <%d>: aucun choix valide !" % ascenseur.num_asc)
        # si on est dans aucun cas à optimiser et qu'il y a un appel, on le prend
        if not _appels and len(self.appels) > 0:
            _appels = (self.appels[0],)
        # on finalise...
        traitement_appel = None
        if _appels:
            traitement_appel = _appels[0]
            # retrait de la liste d'attente
            self.appels.remove(traitement_appel)
            self.logger.debug("Ascenseur <%d>: appel <%s> pris en compte." % \
                              (ascenseur.num_asc, traitement_appel))
        else:
            self.logger.debug("Ascenseur <%d>: aucun appel choisi parmi: %s" % \
                                (ascenseur.num_asc, self.appels))
        return traitement_appel

    def retirer_appels_etage(self, ascenseur, appel):
        """
        Efface toutes les demandes d'appels externes pour un étage.
        Utile uniquement en cas de doubles boutons d'appel.
        @type  appel: objet Appel
        @param appel: données sur l'appel concerné
        """
        self.logger.debug("Ascenseur <%d>: arrivée à l'étage <%d>." % (ascenseur.num_asc, appel.etage))
        # on indique au simulateur d'appel qu'un appel externe a reçu l'ascenseur,
        # afin qu'il puisse générer un appel interne.
        if appel.num_asc == 0:
            self.batiment.sim_appels.generer_appel_interne(ascenseur, appel)
        # extinction des boutons d'appels doubles
        if self.batiment.params.type_appel == 2:
            for _appel in self.appels:
                if appel.etage == _appel.etage and _appel.num_asc == 0:
                    self.logger.debug("Appel <%s> retiré, car c'est l'étage courant." % appel)
                    self.allumage_bouton(_appel, False)
                    self.appels.remove(_appel)

    def changer_etat(self, etat):
        """
        Actualise l'état d'un ascenseur.
        @type  etat: Etat
        @param etat: objet Etat
        """
        asc = etat.ascenseur
        asc.etat = etat

    def decompte(self, delai, fn_retour):
        """
        Durée d'ouverture de la porte simulée par un thread.
        @type  delai: nombre entier
        @param delai: temps d'attente en seconde(s)
        @type  fn_retour: fonction de retour
        @param fn_retour: fonction appelée à la fin du décompte
        """
        # self.logger.debug("Décompte enclenché...")
        t = Thread(target = self.__decompte, args = (delai, fn_retour))
        t.start()

    def __decompte(self, delai, fn_retour):
        """ Temps d'attente géré par un thread. """
        sleep(delai)
        # self.logger.debug("Décompte terminé.")
        fn_retour()

    def porte_ouverte(self, ascenseur):
        """
        Evénement en fin d'ouverture de la porte.
        @type  ascenseur: Ascenseur
        @param ascenseur: objet Ascenseur concerné
        """
        # self.logger.debug("Porte ouverte.")
        self.decompte(4, ascenseur.fermer_porte)

    def porte_fermee(self, ascenseur):
        """
        Evénement en fin de fermeture de la porte.
        @type  ascenseur: Ascenseur
        @param ascenseur: objet Ascenseur concerné
        """
        self.changer_etat(EtatArretFerme(ascenseur))
        ascenseur.etat.appel(self)


class Ascenseur(Log):
    """
    Ordres exécutés par l'ascenseur
    """

    automate = None
    # objet dérivé de la classe IEtat
    etat = None
    num_asc = None
    etage_courant = None
    # sens du dernier mouvement (haut ou bas ou aucun)
    sens = None
    # Null si aucun appel en cours de traitement, sinon n° d'étage
    appel = None
    # représentation graphique
    ascenseur_gui = None

    def __init__(self, automate, num_asc):
        """
        Constructeur de l'ascenseur avec son automate et sa partie graphique.
        @type  batiment: Batiment
        @param batiment: objet parent
        @type  idx_asc: nombre entier
        @param idx_asc: numéro d'ordre (1er ou 2e asenseur)
        """
        self.automate = automate
        self.num_asc = num_asc
        self.etage_courant = 0
        self.sens = SENS.AUCUN
        self.appel = None
        self.ascenseur_gui = AscenseurGui(self)

    def on_simu_stop(self):
        """ Arrêt de la simulation """
        self.ascenseur_gui.flg_simu_stop = True

    def ouvrir_porte(self):
        """ Ouverture durant 1 seconde """
        self.ascenseur_gui.ouvrir_porte(1, self.automate.porte_ouverte)

    def fermer_porte(self):
        """ Fermeture durant 1 seconde """
        self.ascenseur_gui.fermer_porte(1, self.automate.porte_fermee)

    def acceder_etage(self, appel):
        """
        Lance un déplacement.
        @type  appel: nombre entier
        @param appel: étage demandé
        """
        self.appel = appel
        # self.logger.debug("Déplacement de l'ascenseur de l'étage <%d> au <%d>..." % (self.etage_courant, etage_courant))
        nb_etages = abs(self.etage_courant - appel.etage)
        if appel.etage > self.etage_courant:
            self.sens = SENS.HAUT
        else:
            self.sens = SENS.BAS
        # self.logger.debug("Ascenseur <%d>: %s" % (self.num_asc, self.sens))
        self.ascenseur_gui.deplacement(2, nb_etages, self.sens, self._etat_deplacement)

    def _etat_deplacement(self, sens):
        """
        Appel à chaque passage d'étage.
        @type  sens: Enum SENS
        @param sens: sens croissant, décroissant, ou aucun (fin du déplacement)
        """
        if sens == SENS.AUCUN:
            # fin du déplacement
            # self.logger.debug("Déplacement de l'ascenseur OK.")
            self.etat.etage_demande_atteint(self.automate, self.appel)
            # éteindre le bouton d'appel
            self.automate.allumage_bouton(self.appel, False)
            self.appel = None
            # si on est au dernier ou au premier étage, on modifie le sens
            # du prochain déplacement
            if self.etage_courant == self.automate.batiment.params.nb_etages - 1:
                self.sens = SENS.BAS
            elif self.etage_courant == 0:
                self.sens = SENS.HAUT
        else:
            # on s'est déplacé d'un étage
            if sens == SENS.HAUT:
                self.etage_courant += 1
            else:
                self.etage_courant -= 1
            # self.logger.debug("Déplacement d'un étage, étage actuel <%d>." % self.etage_courant)

