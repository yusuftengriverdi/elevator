#!/usr/bin/python
# -*- Encoding: utf-8 -*-

# ===================================================================
#
# Module regroupant les classes utilisées pour le patron de conception
# d'état remplaçant le classique switch.
#
# ===================================================================

from abc import ABC, abstractmethod
# from core.log import Log


class IEtat(ABC):
    """
    Classe abstraite d'un état générique avec ses méthodes virtuelles
    représentant les transitions. Chaque classe dérivée sera un état
    particulier.
    """
    # ascenseur associé
    ascenseur = None

    def __init__(self, ascenseur):
        self.ascenseur = ascenseur

    @abstractmethod
    def appel(self, automate):
        return

    @abstractmethod
    def etage_demande_atteint(self, automate):
        return

    @abstractmethod
    def fermeture_porte(self, automate):
        return


class EtatArretFerme(IEtat):
    """ En arrêt, porte fermée """

    def appel(self, automate):
        appel = automate.prochaine_destination(self.ascenseur)
        if appel:
            automate.changer_etat(EtatDeplacement(self.ascenseur))
            self.ascenseur.acceder_etage(appel)

    def etage_demande_atteint(self, automate):
        pass

    def fermeture_porte(self, automate):
        pass


class EtatArretOuvert(IEtat):
    """ En arrêt, porte ouverte """

    def appel(self, automate):
        pass

    def etage_demande_atteint(self, automate):
        pass

    def fermeture_porte(self, automate):
        """ Attente d'un déplacement à effectuer """
        # self.logger.debug("Fermeture de la porte.")
        self.ascenseur.fermer_porte()
        # géré par l'ascenseur
        # automate.changer_etat(EtatArretFerme())
        # automate.etat_courant.appel(automate)


class EtatDeplacement(IEtat):
    """ En déplacement vers un étage """

    def appel(self, automate):
        # traité par l'automate
        pass

    def etage_demande_atteint(self, automate, appel):
        # self.logger.debug("Etage demandé atteint.")
        automate.changer_etat(EtatArretOuvert(self.ascenseur))
        # demande d'extinction du bouton
        automate.allumage_bouton(appel, False)
        # purge les demandes pour cet étage
        automate.retirer_appels_etage(self.ascenseur, appel)
        self.ascenseur.ouvrir_porte()

    def fermeture_porte(self, automate):
        pass
