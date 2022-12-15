#! /usr/bin/python
# -*- coding: utf-8 -*-

"""

Avertissement
=============

 Ce programme est un logiciel libre; vous pouvez le redistribuer
 et/ou le modifier selon les termes de la GNU General Public
 License (Licence Publique Generale GNU) telle qu'elle a ete
 publiee par la Free Software Foundation; soit la version 3 de
 la licence.
 Ce programme est distribue dans l'espoir qu'il sera utile, mais
 SANS LA MOINDRE GARANTIE; pas meme la garantie implicite de
 COMMERCIABILITE ou d'ADEQUATION A UN BUT PARTICULIER. Voir la GNU
 General Public License pour plus de details.


Bibliographie
=============

 @version = "0.1"
 @author = "TartanpionR"
 @contact = "tartanpionrolland@gmx.fr"
 @copyright = "GPL v3"
 @date = 2019-05-01

"""

import sys
from gui.windows import AppWindow
from logging import StreamHandler, Formatter, getLogger, DEBUG

# journalisation des erreurs
logger = getLogger()

# -------------------------------------------------------------------
#
# Point d'entrée de l'application
#
# -------------------------------------------------------------------

if __name__ == '__main__':

    # journalisation dans la console
    logger.setLevel(DEBUG)
    pattern = "[%(levelname)s:%(name)s] %(message)s"
    sh = StreamHandler()
    sh.setFormatter(Formatter(pattern))
    logger.addHandler(sh)
    # initialisation de l'affichage
    application = AppWindow()
    application.run(sys.argv)

