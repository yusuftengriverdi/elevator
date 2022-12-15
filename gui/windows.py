#! /usr/bin/python
# -*- coding: utf-8 -*-

# ===================================================================
#
# Module regroupant les interfaces graphiques.
#
# ===================================================================

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Gio, GObject
from core.log import Log
from core.structures import Batiment

ICON_WINDOW = "./ressources/ascenseur-icon.png"


class Params:
    """
    Options communes échangées entre objets.
    """

    nb_etages = None
    nb_asc = None
    type_appel = None

    def __init__(self, nb_etages, nb_asc, type_appel):
        self.nb_etages = nb_etages
        self.nb_asc = nb_asc
        self.type_appel = type_appel

    def __repr__(self):
        return "Etages: %d - Asc.: %d - appels: %d" % \
            (self.nb_etages, self.nb_asc, self.type_appel)


class AppWindow(Gtk.Application, Log):
    """
    Interface graphique principale.

    Gtk.ApplicationWindow est une classe dérivée de Gtk.Window qui offre des
    fonctionnalités d'intégration.

    Un timer force le rafraîchissement du dessin périodiquement lorsqu'une
    simulation est lancée.
    """

    # composants graphiques
    widgets = None
    batiment = None
    # rafraichissement régulier du dessin
    _timer = None
    # options modifiables
    params = None

    def __init__(self):
        """ Constructeur """
        Gtk.Application.__init__(self)
        self.widgets = {}
        # valeurs par défaut
        self.params = Params(nb_etages = 3, nb_asc = 1, type_appel = 1)

    def do_activate(self):
        """
        Cette fonction est appelée quand l'OS lance l'application.
        """
        window = Gtk.ApplicationWindow(application = self)
        self.widgets["window"] = window
        window.set_title("Simulateur")
        window.set_icon_from_file(ICON_WINDOW)
        window.set_titlebar(self.make_headerbar())
        window.connect("delete_event", self.on_delete_event)
        self.widgets["btn_stop"].set_sensitive(False)
        # dimensionnement de la fenêtre et de la zone de dessin
        self._redimensionner()
        window.set_resizable(False)
        window.show_all()

    def do_startup(self):
        """
        Initialise l'application au lancement de sa 1ere instance.
        """
        Gtk.Application.do_startup(self)

    def on_delete_event(self, gtk_widget, event):
        """ Arrêt de l'application """
        self.on_sim_stop(None)
        Gtk.Application.quit(self)

    def on_sim_start(self, gtk_widget):
        """
        Démarrer une simulation.
        @type  gtk_widget: Button
        @param gtk_widget: Composant lié à l'événement
        """
        self.logger.debug("Démarrage d'une simulation...")
        # activation du bouton stop et désactivation du bouton start
        self.widgets["btn_start"].set_sensitive(False)
        self.widgets["btn_stop"].set_sensitive(True)
        # initialisation
        self.batiment = Batiment(self.widgets["area"], self.params)
        # on démarre le rafraîchissement régulier du dessin,
        # mais on peut l'optimiser en ne l'activant que durant une animation
        self._timer = GObject.timeout_add(200, self.__area_refresh_timeout)
        self.logger.debug("Démarrage de la simulation (%s)." % self.params)

    def _redimensionner(self):
        """
        Détermine la dimension de la fenêtre et de la zone de dessin.
        """
        # suppression de la zone de dessin si elle existe pour la créer
        # avec les dimensions voulues
        window = self.widgets["window"]
        try:
            area = self.widgets["area"]
            window.remove(area)
        except:
            # self.logger.debug("Pas de zone de dessin à remplacer.")
            pass
        # construction du nouveau composant graphique
        area = Gtk.DrawingArea()
        self.widgets["area"] = area
        window.add(area)
        # définition des dimensions requises
        larg = 400 + (100 * self.params.nb_asc)
        ht = 160 + (60 * self.params.nb_etages)
        window.set_default_size(larg, ht)
        # autres options:
        # Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.EXPOSURE_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK
        area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        area.connect("draw", self.on_draw)
        area.connect("button-press-event", self.on_draw_press_event)
        area.set_size_request(larg, ht)
        area.show()

    def on_sim_stop(self, gtk_widget):
        """
        Arrête une simulation.
        @type  gtk_widget: Gtk.Button
        @param gtk_widget: Composant lié à l'événement
        """
        # arrêt des ascenseurs et du simulateur d'appels
        if self.batiment:
            for asc in self.batiment.automate.ascenseurs:
                asc.on_simu_stop()
                self.batiment.sim_appels.flg_stop = True
            self.batiment = None
        if gtk_widget:
            # s'il ne s'agit pas d'un arrêt forcé suite à la modification
            # des options sans avoir lancé de simulation
            GObject.source_remove(self._timer)
            self._timer = None
            # on s'assure d'un dernier rafraichissement pour effacer le dessin
            self.__area_refresh_timeout()
        # déactivation du bouton stop et sactivation du bouton start
        self.widgets["btn_stop"].set_sensitive(False)
        self.widgets["btn_start"].set_sensitive(True)
        self.logger.debug("Arrêt de la simulation.")

    def on_help_about(self, gtk_widget):
        """
        Affiche la fenêtre <A propos>.
        @type  gtk_widget: Button
        @param gtk_widget: Composant lié à l'événement
        """
        self.logger.debug("(stub) Bouton <A propos> activé.")
        img = Gtk.Image()
        img.set_from_file(ICON_WINDOW)
        # FIXME: le bouton Fermer ne réagit pas.
        dialog = Gtk.AboutDialog(self,
                                 authors = ("Nicolas PIRAT\n\nnicolas.pirat@no-log.org",),
                                 logo = img.get_pixbuf(),
                                 program_name = "Simulateur d'ascenseur",
                                 comments = "Test d'algorithmes\n\n2019",
                                 license_type = Gtk.License(3),
                                 version = "0.1")
        dialog.show()

    def on_draw(self, area, context):
        """
        Actualisation du dessin demandée par Gtk.
        @type  area: DrawingArea
        @param area: Composant lié à l'événement
        @type  context: cairo context
        @param context: Surface de dessin
        """
        # arrière-plan
        color = Gdk.RGBA()
        color.parse("#000")
        area.override_background_color(0, color)
        # dessin du bâtiment (qui dessinera le reste)
        if self.batiment:
            self.batiment.dessiner(area, context)

    def on_draw_press_event(self, area, event):
        """
        Clic dans la zone de dessin; on cherche si un bouton d'appel est concerné.
        @type  area: DrawingArea
        @param area: Composant lié à l'événement
        @type  event: EventButton
        @param event: Composant lié à l'événement
        """
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            # cherchons si un bouton d'appel est concerné
            self.logger.debug("Traitement d'un clic...")
            for bouton in self.batiment.boutons:
                if bouton.bouton_gui.region.is_inside(event.x, event.y):
                    self.batiment.automate.appel(bouton.appel)
                    self.logger.debug("Traitement d'un clic pour appel OK.")

    def __area_refresh_timeout(self):
        """
        Demande un refraîchissement du dessin.
        """
        self.widgets["area"].queue_draw()
        # réactive le timer
        return True

    def make_headerbar(self):
        """
        Personnalise l'en-tête de la fenêtre pour y intégrer des composants.
        """
        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.props.title = "Ascenseur"
        # bouton à propos situé à droite
        btn_about = Gtk.Button()
        icon = Gio.ThemedIcon(name = "help-about")
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        btn_about.add(image)
        btn_about.connect("clicked", self.on_help_about)
        hb.pack_end(btn_about)
        # bouton démarrer
        btn_start = Gtk.Button()
        icon = Gio.ThemedIcon(name = "media-playback-start")
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        btn_start.add(image)
        btn_start.connect("clicked", self.on_sim_start)
        self.widgets["btn_start"] = btn_start
        # bouton arrêter
        btn_stop = Gtk.Button()
        icon = Gio.ThemedIcon(name = "media-playback-stop")
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        btn_stop.add(image)
        btn_stop.connect("clicked", self.on_sim_stop)
        self.widgets["btn_stop"] = btn_stop
        # bouton options
        btn_options = Gtk.Button()
        icon = Gio.ThemedIcon(name = "document-properties")
        image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
        btn_options.add(image)
        btn_options.connect("clicked", self.configuration)
        self.widgets["btn_options"] = btn_options
        # groupe des deux boutons de gauche (démarrer et arrêter)
        box = Gtk.Box(orientation = Gtk.Orientation.HORIZONTAL)
        Gtk.StyleContext.add_class(box.get_style_context(), "linked")
        box.add(btn_start)
        box.add(btn_stop)
        box.add(btn_options)
        hb.pack_start(box)
        return hb

    def configuration(self, gtk_widget):
        """
        Affichage des paramètres de simulation
        @type  gtk_widget: Gtk.Button
        @param gtk_widget: Composant lié à l'événement
        """
        cfg = ConfigDialog(self.widgets["window"])
        # valeurs actuelles
        cfg.spin_etages.set_value(self.params.nb_etages)
        if self.params.type_appel == 1:
            cfg.rb_appel.set_active(True)
        else:
            cfg.rb_appel.set_active(False)
        # affichage
        reponse = cfg.run()
        if reponse == Gtk.ResponseType.OK:
            # arrêt de la simulation s'il y en a une en cours
            self.on_sim_stop(None)
            self.params = Params(nb_etages = int(cfg.spin_etages.get_value()),
                                nb_asc = int(cfg.spin_asc.get_value()),
                                type_appel = 1)
            # 1 = un bouton d'appel, 2 = deux boutons (haut et bas)
            if not cfg.rb_appel.get_active(): self.params.type_appel = 2
            # adaptation de la taille nécessaire au dessin
            self._redimensionner()
        cfg.destroy()


class ConfigDialog(Gtk.Dialog):
    """
    Boite de dialogue pour configurer les options de simulation.
    Pour des raisons graphiques uniquement:
     - le nombre d'ascenseurs est limité à 3
     - le nombre d'étages est limité à 10
    """

    spin_etages = None
    spin_asc = None
    rb_algo = None
    rb_appel = None

    def __init__(self, parent = None):
        Gtk.Dialog.__init__(self, "Configuration", parent, 0,
                            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                             Gtk.STOCK_OK, Gtk.ResponseType.OK))
        # layer contenant les lignes d'options
        vertical_box = Gtk.Box(orientation = Gtk.Orientation.VERTICAL,
                               spacing = 10)
        # 1ere ligne d'option: nombre d'étages
        hbox_etages = Gtk.Box(orientation = Gtk.Orientation.HORIZONTAL)
        adj = Gtk.Adjustment(value = 4, lower = 2, upper = 10,
                                    step_increment = 1, page_increment = 2,
                                    page_size = 0)
        spin_etages = Gtk.SpinButton()
        spin_etages.set_adjustment(adj)
        spin_etages.set_numeric(True)
        spin_etages.set_digits(0)
        self.spin_etages = spin_etages
        lbl = Gtk.Label("Nombre d'étages : ")
        hbox_etages.add(lbl)
        hbox_etages.add(spin_etages)
        vertical_box.add(hbox_etages)
        # 2e ligne d'option: nombre d'ascenseurs
        hbox_asc = Gtk.Box(orientation = Gtk.Orientation.HORIZONTAL)
        adj = Gtk.Adjustment(value = 1, lower = 1, upper = 3,
                                    step_increment = 1, page_increment = 1,
                                    page_size = 0)
        spin_asc = Gtk.SpinButton()
        spin_asc.set_adjustment(adj)
        spin_asc.set_numeric(True)
        spin_asc.set_digits(0)
        self.spin_asc = spin_asc
        lbl = Gtk.Label("Nombre d'ascenseurs : ")
        hbox_asc.add(lbl)
        hbox_asc.add(spin_asc)
        vertical_box.add(hbox_asc)
        # 3e ligne d'option: choix des boutons
        rb_3 = Gtk.RadioButton.new_with_label_from_widget(None, "un seul bouton d'appel par étage")
        rb_4 = Gtk.RadioButton.new_from_widget(rb_3)
        self.rb_appel = rb_3
        rb_4.set_label("deux boutons d'appel (haut et bas) par étage")
        vertical_box.add(rb_3)
        vertical_box.add(rb_4)
        # on insère le tout
        gen_box = self.get_content_area()
        gen_box.add(vertical_box)
        self.show_all()
