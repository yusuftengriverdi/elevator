#! /usr/bin/python
# -*- coding: utf-8 -*-

# ===================================================================
#
# Module regroupant les interfaces graphiques des composants.
#
# ===================================================================

from gi.repository import Gdk
from abc import ABC, abstractmethod
from threading import Thread
from time import sleep
# from core.log import Log
from core.activite import SENS

# constantes
HAUTEUR_ETAGE = 60
LRG_BAT_1 = 100
LRG_BAT_ASC = 50
MARGE_ASC = 5
MARGE_PORTE = 2

# leurs valeurs seront actualisées en fonction des options
HAUTEUR_SOL = 350
LONG_SOL = 400
ORG_BAT_X = 100

# couleurs utilisables
COULEUR_ORANGE = "#F05D00"
COULEUR_VERTE = "#04b90e"


class Region:
    """
    Zone de dessin sensible au clic.
    """
    x_min = None
    x_max = None
    y_min = None
    y_max = None

    def __init__(self, x_min = 0, x_max = 0, y_min = 0, y_max = 0):
        """
        Constructeur prenant les coordonnées d'un rectangle.
        @param x_min: abcisse minimale
        @param x_max: abcisse maximale
        @param y_min: ordonnée minimale
        @param y_max: ordonnée maximale
        """
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max

    def is_inside(self, x, y):
        """
        Retourne True si le point est dans la zone.
        @type x: valeur numérique
        @param x: abscisse
        @type y: valeur numérique
        @param y: ordonnée
        @return: True si le point est dans la zone, False sinon.
        @rtype: Boolean
        """
        if x < self.x_max and x > self.x_min and \
           y < self.y_max and y > self.y_min:
            return True
        else:
            return False


class BatimentGui:
    """
    Représentation du bâtiment composé de 3 parties:
     - une colonne symbolisant les étages
     - une colonne regroupant les boutons d'appel
     - une ou deux colonnes servant de cage(s) d'ascenseur
    """

    # options générales
    params = None

    def __init__(self, area, params):
        """
        Représentation graphique du bâtiment.
        @type  area: DrawingArea
        @param area: Composant Gtk contenant les dessins
        @type  params: objet Params
        @param params: regroupe les options communes
        """
        self.params = params
        # actualisation des valeurs de référence du dessin
        largeur = area.get_allocated_width()
        hauteur = area.get_allocated_height()
        # 87 % de la hauteur
        global HAUTEUR_SOL
        HAUTEUR_SOL = int(hauteur * 0.87)
        # 20 % de la largeur
        global ORG_BAT_X
        ORG_BAT_X = int(largeur * 0.2)
        # 80 % de la largeur
        global LONG_SOL
        LONG_SOL = int(largeur * 0.8)

    def on_draw(self, area, context):
        """
        Dessin de tout les objets.
        @type  area: DrawingArea
        @param area: Composant lié à l'événement
        @type  context: cairo context
        @param context: Surface de dessin
        """
        color = Gdk.RGBA()
        Gdk.RGBA.parse(color, COULEUR_ORANGE)
        # FIXME: context.set_source_rgba(color)
        context.set_source_rgb(color.red, color.green, color.blue)
        # sol
        context.rectangle(50, HAUTEUR_SOL, LONG_SOL, 20)
        context.fill()
        for etage in range(self.params.nb_etages):
            offset = etage * HAUTEUR_ETAGE
            # partie gauche du bâtiment (attente des personnes)
            context.rectangle(ORG_BAT_X,
                              HAUTEUR_SOL - offset,
                              LRG_BAT_1,
                              -HAUTEUR_ETAGE)
            context.stroke()
            # partie centrale contenant les boutons d'appel
            context.rectangle(ORG_BAT_X + LRG_BAT_1,
                              HAUTEUR_SOL - offset,
                              LRG_BAT_ASC,
                              -HAUTEUR_ETAGE)
            context.stroke()
            # partie droite du bâtiment (attente des personnes)
            bonus_x = self.params.nb_asc * LRG_BAT_ASC
            context.rectangle(ORG_BAT_X + LRG_BAT_1 + LRG_BAT_ASC + bonus_x,
                              HAUTEUR_SOL - offset,
                              LRG_BAT_1,
                              -HAUTEUR_ETAGE)
            context.stroke()
        # partie droite contenant les cages d'ascenseur
        for idx_asc in range(self.params.nb_asc):
            # pour avoir 1-2 et non 0-1
            idx_asc += 1
            context.rectangle(ORG_BAT_X + LRG_BAT_1 + (idx_asc * LRG_BAT_ASC),
                              HAUTEUR_SOL,
                              LRG_BAT_ASC,
                              -self.params.nb_etages * HAUTEUR_ETAGE)
        context.stroke()


class AscenseurGui:
    """
    Dessin d'un ascenseur.
    """
    # position de l'ascenseur
    POS_X_GAUCHE = None
    POS_X_DROITE = None
    pos_y = None
    # valeur de l'écartement d'un battant, laissant 1 de côté lorsqu'il est
    # ouvert en grand. Un battant fait 20 de large.
    largeur_battant = None
    LRG_BATTANT_MAX = 20.0
    OUV_INCREMENT = 3
    OUVRIR_PORTE = 1
    FERMER_PORTE = 2

    ascenseur = None
    # demande d'arrêt d'un thread si actif
    flg_simu_stop = None

    def __init__(self, ascenseur, etage = 0):
        """ Constructeur
        @type  ascenseur: objet Ascenseur
        @param ascenseur: ascenseur à représenter
        @type  etage: nombre entier
        @param etage: étage de départ de l'ascenseur
        """
        self.ascenseur = ascenseur
        # portes fermées par défaut
        self.largeur_battant = self.LRG_BATTANT_MAX
        # positions de départ
        self.POS_X_GAUCHE = ORG_BAT_X + LRG_BAT_1 + MARGE_ASC + (ascenseur.num_asc * LRG_BAT_ASC)
        self.POS_X_DROITE = self.POS_X_GAUCHE + LRG_BAT_ASC - (2 * MARGE_ASC)
        self.pos_y = self._conv_pos_depuis_etage(etage)

    def _conv_pos_depuis_etage(self, etage):
        """ Conversion du numéro d'étage en ordonnée. """
        return HAUTEUR_SOL - MARGE_ASC - (etage * HAUTEUR_ETAGE)

    def ouvrir_porte(self, delai, fn_retour):
        """
        Ouverture progressive de la porte dans le délai en seconde(s).
        """
        t = Thread(target = self.__actionner_porte, \
                                    args = (delai, self.OUVRIR_PORTE, fn_retour))
        t.start()

    def fermer_porte(self, delai, fn_retour):
        """
        Ouverture progressive de la porte dans le délai en seconde(s).
        """
        t = Thread(target = self.__actionner_porte, \
                                    args = (delai, self.FERMER_PORTE, fn_retour))
        t.start()

    def __actionner_porte(self, delai, action, fn_retour = None):
        """
        Ouverture progressive de la porte dans le délai en seconde(s) par
        pas de 6 étapes.
        """
        # if self.OUVRIR_PORTE:
            # self.logger.debug("Ascenseur <%d>: ouverture de la porte..." % self.ascenseur.idx_asc)
        # else:
            # self.logger.debug("Ascenseur <%d>: fermeture de la porte..." % self.ascenseur.idx_asc)
        for i in range(6):
            if action == self.OUVRIR_PORTE:
                self.largeur_battant -= self.OUV_INCREMENT
            elif action == self.FERMER_PORTE:
                self.largeur_battant += self.OUV_INCREMENT
            else:
                pass
            sleep(float(delai / 6))
            # si arrêt de la simulation
            if self.flg_simu_stop:
                break
        fn_retour(self.ascenseur)
        # self.logger.debug("Ascenseur <%d>: action de la porte OK." % self.ascenseur.idx_asc)

    def deplacement(self, delai_etage, nb_etages, sens, fn_situation):
        """
        Déplacement avec un délai sous-traité.
        Les batiments avec moins de 15 étages ont des ascenseurs mettant 3s / étage;
        entre 15 et 30 étages c'est 1s / étage, et les grandes tours peuvent avoir
        des asccenseurs mettant 0.5s / étage.
        @type  delai_etage: nombre entier
        @param delai_etage: temps de transition entre deux étage en seconde(s)
        @type  nb_etages: nombre entier
        @param nb_etages: nombre d'étages à passer
        @type  sens: Enum SENS
        @param sens: sens croissant, décroissant, ou aucunn
        """
        t = Thread(target = self.__deplacement, \
                                    args = (delai_etage, nb_etages, sens, fn_situation))
        t.start()

    def __deplacement(self, delai_etage, nb_etages, sens, fn_situation):
        """
        Déplacement progressif géré par un thread.
        @type  fn_situation: fonction
        @param fn_situation: fonction appelée en fin de tâche
        """
        NB_ETAPES = 10
        for etage in range(nb_etages):
            # si demandé, arrêt
            if self.flg_simu_stop:
                break
            # incrémentation en 6 étapes pour aller vers l'étage adjacent
            for inc in range(NB_ETAPES):
                # si demandé, arrêt
                if self.flg_simu_stop:
                    break
                sleep(float(delai_etage / NB_ETAPES))
                if sens == SENS.HAUT:
                    self.pos_y -= HAUTEUR_ETAGE / NB_ETAPES
                else:
                    self.pos_y += HAUTEUR_ETAGE / NB_ETAPES
            # on s'est déplacé d'un étage, information partagée
            fn_situation(sens)
        # on est arrivé à destination, information partagée
        fn_situation(SENS.AUCUN)

    def on_draw(self, area, context):
        """
        Dessin de l'ascenseur.
        @type  area: DrawingArea
        @param area: Composant lié à l'événement
        @type  context: cairo context
        @param context: Surface de dessin
        """
        hauteur_asc = -(HAUTEUR_ETAGE - (2 * MARGE_ASC))
        largeur_asc = LRG_BAT_ASC - (2 * MARGE_ASC)
        # contour
        context.rectangle(self.POS_X_GAUCHE,
                          self.pos_y,
                          largeur_asc,
                          hauteur_asc)
        context.stroke()
        # battant gauche de la porte
        context.rectangle(self.POS_X_GAUCHE,
                          self.pos_y,
                          self.largeur_battant,
                          hauteur_asc)
        context.stroke()
        # battant droit de la porte
        context.rectangle(self.POS_X_DROITE,
                          self.pos_y,
                          -self.largeur_battant,
                          hauteur_asc)
        context.stroke()


class BoutonGui(ABC):
    """ Interface """

    # zone graphique sensible au clic
    region = None
    # objet Bouton rattaché
    bouton = None

    @abstractmethod
    def on_draw(self, area, context):
        return


class BoutonExterneSimpleGui(BoutonGui):
    """
    Dessin d'un bouton d'appel de l'ascenseur.
    """

    centre_x = None
    centre_y = None
    RAYON = 5

    def __init__(self, bouton):
        """ Constructeur
        @type  bouton: objet Bouton
        @param bouton: bouton d'appel
        """
        self.bouton = bouton
        pas_v = HAUTEUR_ETAGE / 8
        self.centre_x = ORG_BAT_X + LRG_BAT_1 + (LRG_BAT_ASC / 2)
        self.centre_y = HAUTEUR_SOL - (HAUTEUR_ETAGE / 2) \
                        -(self.bouton.appel.etage * HAUTEUR_ETAGE) \
                        -pas_v
        self.region = Region(self.centre_x - self.RAYON,
                             self.centre_x + self.RAYON,
                             self.centre_y - self.RAYON,
                             self.centre_y + self.RAYON)

    def on_draw(self, area, context):
        """
        Dessin du bouton
        @type  area: DrawingArea
        @param area: Composant lié à l'événement
        @type  context: cairo context
        @param context: Surface de dessin
        """
        if self.bouton.etat == True:
            context.arc(self.centre_x, self.centre_y, self.RAYON, 0, 200)
            context.fill()
        else:
            context.arc(self.centre_x, self.centre_y, self.RAYON, 0, 200)
            context.stroke()


class BoutonInterneSimpleGui(BoutonGui):
    """
    Dessin d'un bouton d'appel interne de l'ascenseur.
    """

    centre_x = None
    centre_y = None
    RAYON = 2.5

    def __init__(self, bouton):
        """ Constructeur
        @type  bouton: objet Bouton
        @param bouton: bouton d'appel
        """
        self.bouton = bouton
        pas_h = LRG_BAT_ASC / 4
        pas_v = HAUTEUR_ETAGE / 4

        self.centre_x = ORG_BAT_X + LRG_BAT_1 + (pas_h * bouton.appel.num_asc)
        self.centre_y = HAUTEUR_SOL - (HAUTEUR_ETAGE / 2) \
                        -(self.bouton.appel.etage * HAUTEUR_ETAGE) \
                        +pas_v
        self.region = Region(self.centre_x - self.RAYON,
                             self.centre_x + self.RAYON,
                             self.centre_y - self.RAYON,
                             self.centre_y + self.RAYON)

    def on_draw(self, area, context):
        """
        Dessin du bouton
        @type  area: DrawingArea
        @param area: Composant lié à l'événement
        @type  context: cairo context
        @param context: Surface de dessin
        """
        if self.bouton.etat == True:
            context.arc(self.centre_x, self.centre_y, self.RAYON, 0, 200)
            context.fill()
        else:
            context.arc(self.centre_x, self.centre_y, self.RAYON, 0, 200)
            context.stroke()
        # n° ascenseur en-dessous
        context.set_font_size(8)
        context.move_to(self.centre_x - 2, self.centre_y + 12)
        context.show_text("%d" % self.bouton.appel.num_asc)
        context.stroke()


class BoutonInterneDoubleGui(BoutonGui):
    """
    Dessin d'un bouton d'appel interne de l'ascenseur.
    """

    centre_x = None
    centre_y = None
    RAYON = 2.5

    def __init__(self, bouton):
        """ Constructeur
        @type  bouton: objet Bouton
        @param bouton: bouton d'appel
        """
        self.bouton = bouton
        pas_h = LRG_BAT_ASC / 4
        self.centre_x = ORG_BAT_X + LRG_BAT_1 + (pas_h * bouton.appel.num_asc)
        self.centre_y = HAUTEUR_SOL - (HAUTEUR_ETAGE / 2) \
                        -(self.bouton.appel.etage * HAUTEUR_ETAGE)
        self.region = Region(self.centre_x - self.RAYON,
                             self.centre_x + self.RAYON,
                             self.centre_y - self.RAYON,
                             self.centre_y + self.RAYON)

    def on_draw(self, area, context):
        """
        Dessin du bouton
        @type  area: DrawingArea
        @param area: Composant lié à l'événement
        @type  context: cairo context
        @param context: Surface de dessin
        """
        if self.bouton.etat == True:
            context.arc(self.centre_x, self.centre_y, self.RAYON, 0, 200)
            context.fill()
        else:
            context.arc(self.centre_x, self.centre_y, self.RAYON, 0, 200)
            context.stroke()
        # n° ascenseur en-dessous
        context.set_font_size(8)
        context.move_to(self.centre_x + 4, self.centre_y + 2)
        context.show_text("%d" % self.bouton.appel.num_asc)
        context.stroke()


class BoutonExterneHautGui(BoutonGui):
    """
    Représentation du bouton d'appel en montant.
    """

    # point à gauche
    pt1_x = None
    pt1_y = None
    # point à droite
    pt2_x = None
    pt2_y = None
    # point en haut
    pt3_x = None
    pt3_y = None

    def __init__(self, bouton):
        """ Constructeur
        @type  bouton: objet Bouton
        @param bouton: bouton d'appel
        """
        self.bouton = bouton
        pas_v = HAUTEUR_ETAGE / 4
        pas_h = LRG_BAT_ASC / 4
        # coordonnées du point à gauche en bas de la case
        pos_x = ORG_BAT_X + LRG_BAT_1
        pos_y = HAUTEUR_SOL - (self.bouton.appel.etage * HAUTEUR_ETAGE)
        self.pt1_x = float(pos_x + pas_h)
        self.pt1_y = float(pos_y - (pas_v * 2.5))
        self.pt2_x = float(pos_x + (pas_h * 3))
        self.pt2_y = self.pt1_y
        self.pt3_x = float(pos_x + (pas_h * 2))
        self.pt3_y = float(pos_y - (pas_v * 3.5))
        # région sensible au clic (forme en carré simplifiée)
        self.region = Region(self.pt1_x, self.pt2_x, self.pt3_y, self.pt1_y)

    def on_draw(self, area, context):
        """
        Dessin du bouton
        @type  area: DrawingArea
        @param area: Composant lié à l'événement
        @type  context: cairo context
        @param context: Surface de dessin
        """
        context.move_to(self.pt1_x, self.pt1_y)
        context.line_to(self.pt2_x, self.pt2_y)
        context.line_to(self.pt3_x, self.pt3_y)
        context.line_to(self.pt1_x, self.pt1_y)
        if self.bouton.etat == True:
            context.fill()
        else:
            context.stroke()


class BoutonExterneBasGui(BoutonGui):
    """
    Représentation graphique du bouton d'appel en descente.
    """

    # point à gauche
    pt1_x = None
    pt1_y = None
    # point à droite
    pt2_x = None
    pt2_y = None
    # point en haut
    pt3_x = None
    pt3_y = None

    def __init__(self, bouton):
        """ Constructeur
        @type  bouton: objet Bouton
        @param bouton: bouton d'appel
        """
        self.bouton = bouton
        pas_v = HAUTEUR_ETAGE / 4
        pas_h = LRG_BAT_ASC / 4
        # coordonnées du point à gauche en bas de la case
        pos_x = ORG_BAT_X + LRG_BAT_1
        pos_y = HAUTEUR_SOL - (self.bouton.appel.etage * HAUTEUR_ETAGE)
        self.pt1_x = float(pos_x + pas_h)
        self.pt1_y = float(pos_y - (pas_v * 1.5))
        self.pt2_x = float(pos_x + (pas_h * 3))
        self.pt2_y = self.pt1_y
        self.pt3_x = float(pos_x + (pas_h * 2))
        self.pt3_y = float(pos_y - (pas_v * 0.5))
        # région sensible au clic (forme en carré simplifiée)
        self.region = Region(self.pt1_x, self.pt2_x, self.pt1_y, self.pt3_y)

    def on_draw(self, area, context):
        """
        Dessin du bouton
        @type  area: DrawingArea
        @param area: Composant lié à l'événement
        @type  context: cairo context
        @param context: Surface de dessin
        """
        context.move_to(self.pt1_x, self.pt1_y)
        context.line_to(self.pt2_x, self.pt2_y)
        context.line_to(self.pt3_x, self.pt3_y)
        context.line_to(self.pt1_x, self.pt1_y)
        if self.bouton.etat == True:
            context.fill()
        else:
            context.stroke()
