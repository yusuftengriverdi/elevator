#! /usr/bin/python
# -*- coding: utf-8 -*-

# ===================================================================
#
# Module dédié à la journalisation des erreurs.
#
# ===================================================================

from logging import getLogger


class Log:
    """Les classes dérivées auront leur nom dans le journal d'erreur"""

    @property
    def logger(self):
        """ Remplace la méthode logging.logger() """
        # récupération du nom de la classe dérivée pour l'afficher
        name = self.__class__.__name__
        logger = getLogger(name)
        return logger
