"""Run from bem/: uv run python -m unittest discover tests"""

import unittest

from pipeline import coordinate_systems as cs


class ResolveEpsg(unittest.TestCase):
    def test_utm_with_explicit_datum_and_zone_letter(self):
        # Seen in production: "Kartdatum WGS 84, UTM Sone 32" (Norwegian well log).
        self.assertEqual(cs.resolve_epsg("Kartdatum WGS 84, UTM Sone 32"), 32632)

    def test_utm_zone_hemisphere_suffix(self):
        self.assertEqual(cs.resolve_epsg("UTM Zone 48N"), 32648)
        self.assertEqual(cs.resolve_epsg("UTM Zone 23S"), 32723)

    def test_utm_band_letter(self):
        # MGRS-style "32U" like the Baden-Wuerttemberg LGRB map (band U -> north).
        self.assertEqual(cs.resolve_epsg(None, "32U O: 462112.739 | N: 5349047.1"), 32632)

    def test_utm_default_datum_is_wgs84(self):
        self.assertEqual(cs.resolve_epsg("UTM zone 31N"), 32631)

    def test_utm_other_datums(self):
        self.assertEqual(cs.resolve_epsg("ETRS89 UTM zone 32N"), 25832)
        self.assertEqual(cs.resolve_epsg("ED50 UTM zone 30N"), 23030)
        self.assertEqual(cs.resolve_epsg("NAD83 UTM zone 17N"), 26917)

    def test_dhdn_gauss_krueger(self):
        self.assertEqual(cs.resolve_epsg("Gauss-Krueger Zone 3 (DHDN)"), 31467)
        self.assertEqual(cs.resolve_epsg("Gauß-Krüger, Streifen 4"), 31468)

    def test_named_systems(self):
        self.assertEqual(cs.resolve_epsg("Lambert 93"), 2154)
        self.assertEqual(cs.resolve_epsg("NTF Lambert II etendu"), 27572)
        self.assertEqual(cs.resolve_epsg("CH1903+ / LV95"), 2056)
        self.assertEqual(cs.resolve_epsg("Amersfoort / RD New"), 28992)
        self.assertEqual(cs.resolve_epsg("OSGB36 National Grid"), 27700)
        self.assertEqual(cs.resolve_epsg("GDM2000 / Peninsula RSO"), 3375)
        self.assertEqual(cs.resolve_epsg("Kertau RSO Malaya"), 29873)

    def test_gda_mga_is_not_treated_as_utm(self):
        self.assertEqual(cs.resolve_epsg("GDA94 / MGA Zone 56"), 28356)
        self.assertEqual(cs.resolve_epsg("GDA2020 MGA zone 50"), 7850)

    def test_unknown_system_returns_none(self):
        self.assertIsNone(cs.resolve_epsg("Local site grid, arbitrary origin"))
        self.assertIsNone(cs.resolve_epsg(None, None))
        self.assertIsNone(cs.resolve_epsg("Gauss-Krueger"))  # no zone number: ambiguous

    def test_resolve_fills_epsg_only_when_coordinates_present(self):
        b = {"x": 591097, "y": 6648286, "epsg": None, "source_coordinate_system": "WGS 84 UTM 32"}
        cs.resolve(b)
        self.assertEqual(b["epsg"], 32632)

    def test_resolve_is_noop_without_coordinates(self):
        b = {"x": None, "y": None, "epsg": None, "source_coordinate_system": "WGS 84 UTM 32"}
        cs.resolve(b)
        self.assertIsNone(b["epsg"])

    def test_resolve_never_overwrites_existing_epsg(self):
        b = {"x": 1, "y": 2, "epsg": 1234, "source_coordinate_system": "Lambert 93"}
        cs.resolve(b)
        self.assertEqual(b["epsg"], 1234)


if __name__ == "__main__":
    unittest.main()
