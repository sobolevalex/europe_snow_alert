import unittest
from unittest.mock import MagicMock, patch

from europe_snow_alert.main import City, check_snow


class TestSnowCheckValidation(unittest.TestCase):
    @patch("europe_snow_alert.main.requests.get")
    def test_temperature_below_zero_validation(self, mock_get):
        # 4 test cities:
        # City 1: Snow on Friday (2.0 cm), temp -2.5°C -> valid
        # City 2: Snow on Friday (5.0 cm), but temp +3.0°C; Saturday no snow -> invalid
        # City 3: Snow on Saturday (3.0 cm), temp -1.0°C; Friday temp +1.0°C (no snow) -> valid
        # City 4: Snow on Friday (4.0 cm) at 0.0°C (not below 0) -> invalid
        test_cities = [
            City(name="SubZeroCity", latitude=45.0, longitude=10.0, country="CountryA"),
            City(name="WarmSnowCity", latitude=46.0, longitude=11.0, country="CountryB"),
            City(name="SatSubZeroCity", latitude=47.0, longitude=12.0, country="CountryC"),
            City(name="ZeroDegreeCity", latitude=48.0, longitude=13.0, country="CountryD"),
        ]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {
                "daily": {
                    "snowfall_sum": [2.0, 0.0],
                    "temperature_2m_max": [-2.5, -1.0],
                }
            },
            {
                "daily": {
                    "snowfall_sum": [5.0, 0.0],
                    "temperature_2m_max": [3.0, 2.0],
                }
            },
            {
                "daily": {
                    "snowfall_sum": [0.0, 3.0],
                    "temperature_2m_max": [1.0, -1.0],
                }
            },
            {
                "daily": {
                    "snowfall_sum": [4.0, 0.0],
                    "temperature_2m_max": [0.0, 1.0],
                }
            },
        ]
        mock_get.return_value = mock_resp

        results, fri_str, sat_str = check_snow(test_cities)

        # Only SubZeroCity and SatSubZeroCity should match
        matched_city_names = [entry for entry in results]
        self.assertEqual(len(results), 2)
        self.assertTrue(any("SubZeroCity" in r for r in results))
        self.assertTrue(any("SatSubZeroCity" in r for r in results))
        self.assertFalse(any("WarmSnowCity" in r for r in results))
        self.assertFalse(any("ZeroDegreeCity" in r for r in results))


if __name__ == "__main__":
    unittest.main()
