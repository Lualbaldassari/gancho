"""Contratos deterministas de Gancho (sin API, stdlib).

Corre con:  .venv/bin/python -m unittest discover tests -v
"""

import unittest

from common import leer_json_seguro, normalizar_hueco
from entrevista import es_no_tiene
from verificar import chequeo_copia, chequeo_precios


class TestNormalizarHueco(unittest.TestCase):
    def test_variantes_casan_igual(self):
        self.assertEqual(normalizar_hueco("[Combo para Compartir]"),
                         normalizar_hueco("combo  para compartir"))
        self.assertEqual(normalizar_hueco("(producto estrella)"), "producto estrella")

    def test_vacio_se_mantiene_vacio(self):
        self.assertEqual(normalizar_hueco("  []  "), "")


class TestLeerJsonSeguro(unittest.TestCase):
    def test_extrae_json_con_ruido(self):
        self.assertEqual(leer_json_seguro('Claro:\n```json\n{"a": 1}\n```'), {"a": 1})

    def test_rechaza_sin_json(self):
        with self.assertRaises(ValueError):
            leer_json_seguro("no hay json aquí")


class TestEsNoTiene(unittest.TestCase):
    def test_negaciones(self):
        for r in ("", "  ", "no", "No Tengo", "n/a", "-"):
            self.assertTrue(es_no_tiene(r), r)

    def test_respuesta_real_no_es_negacion(self):
        self.assertFalse(es_no_tiene("surtido con kion"))


class TestChequeoPrecios(unittest.TestCase):
    def test_precio_inventado_se_reporta(self):
        probs = chequeo_precios("Todo a S/ 15.", "Jugos a S/ 8.")
        self.assertEqual(len(probs), 1)
        self.assertEqual(probs[0]["tipo"], "precio")

    def test_precio_real_no_se_reporta(self):
        self.assertEqual(chequeo_precios("Jugo a S/8.", "Jugos a S/ 8."), [])

    def test_confirmar_no_es_error(self):
        self.assertEqual(
            chequeo_precios("[CONFIRMAR: precio del combo S/ 20]", "Jugos a S/ 8."),
            [])


class TestChequeoCopia(unittest.TestCase):
    def test_frase_copiada_se_reporta(self):
        original = "nos fuimos a big boy porque tienen un nuevo combo disponible"
        guion = "HOY: Nos fuimos a Big Boy porque tienen un nuevo combo disponible para ti"
        probs = chequeo_copia(guion, original)
        self.assertEqual(len(probs), 1)
        self.assertEqual(probs[0]["tipo"], "copia")

    def test_parafrasis_corta_no_se_reporta(self):
        self.assertEqual(chequeo_copia("ven a mi puesto", "ven a mi local grande"), [])


if __name__ == "__main__":
    unittest.main()
