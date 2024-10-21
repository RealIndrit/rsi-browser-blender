import typing as t
import pathlib
import json
import logging
import urllib.request
import urllib.parse

log = logging.getLogger(__name__)

class RSIException(Exception):
    pass

class RSIApiWrapper:
    def __init__(self):
        self.cache_dir = pathlib.Path("./cache")

    def _get(
        self,
        url: str,
        params: t.Dict[str, str] = {},
        headers: t.Dict[str, str] = {},
    ) -> str:
        try:
            return urllib.request.urlopen(
                urllib.request.Request(
                    url + "?" + urllib.parse.urlencode(params), headers=headers
                )
            ).read()
        except Exception as e:
            log.exception(f"Error fetching {url}:")
            raise RSIException(f"Error fetching {url}: {e}")

    def _post(self,
            url: str,
            headers: t.Dict[str, str] = {},
            data: bytes = None,
    ) -> str:
        try:
            return urllib.request.urlopen(
                urllib.request.Request(
                    url, headers=headers, data=data
                )
            ).read()
        except Exception as e:
            log.exception(f"Error fetching {url}:")
            raise Exception(f"Error fetching {url}: {e}")

    def _get_json(
        self,
        url: str,
        headers: t.Dict[str, str] = {},
    ) -> t.Dict[str, t.Any]:
        return json.loads(self._get(url, headers=headers))

    def _post_json(
        self,
        url: str,
        headers: t.Dict[str, str] = {},
        data: bytes = None,
    ) -> t.Dict[str, t.Any]:
        return json.loads(self._post(url, headers=headers, data=data))

    def search(self, query: str) -> t.List[t.Dict[str, t.Any]]:
        try:
            url = f"https://robertsspaceindustries.com/graphql"
            data = ("""
            [
                {
                    "operationName": "GetShipList",
                    "variables": {
                        "query": {
                            "limit": 20,
                            "ships": {
                                "name": "SHIP_NAME"
                            }
                        }
                    },
                    "query": "query GetShipList($query: SearchQuery!) {\\n  store(name: \\"pledge\\", browse: true) {\\n    search(query: $query) {\\n      resources {\\n        ...RSIShipFragment\\n        __typename\\n      }\\n      __typename\\n    }\\n    __typename\\n  }\\n}\\n\\nfragment RSIShipFragment on RSIShip {\\n  title\\n  name\\n  url\\n  media {\\n    thumbnail {\\n      storeSmall\\n      __typename\\n    }\\n    __typename\\n  }\\n  __typename\\n}"
                }
            ]""".replace("SHIP_NAME", query))
            headers = {"content-type": "application/json"}
            search_results = self._post_json(url, headers=headers, data=data.encode("utf-8"))

        except Exception as e:
            log.exception(f"Error searching for {query}:")
            raise RSIException(f"Error searching for {query}: {e}")

        results = []
        for ship in search_results[0]["data"]["store"]["search"]["resources"]:
            results.append(
                {
                    "name": ship["name"],
                    "title": ship["title"],
                    "thumbnail": ship["media"]["thumbnail"]["storeSmall"],
                    "url": ship["url"]
                }
            )
        return results

    def get_si(self, name: str) -> t.Dict[str, t.Any]:
        """
        Get ship information for the given name.
        """
        log.debug(f"Getting SI for #{name}")
        cache_path = self.cache_dir / name / "pip.json"

        if not cache_path.exists():
            try:
                log.info(f"Downloading SI for #{name}")
                url = f"https://robertsspaceindustries.com/graphql"
                data = ("""
                            [
                                {
                                    "operationName": "GetShipList",
                                    "variables": {
                                        "query": {
                                            "limit": 20,
                                            "ships": {
                                                "name": "SHIP_NAME"
                                            }
                                        }
                                    },
                                    "query": "query GetShipList($query: SearchQuery!) {\\n  store(name: \\"pledge\\", browse: true) {\\n    search(query: $query) {\\n      resources {\\n        ...RSIShipFragment\\n        __typename\\n      }\\n      __typename\\n    }\\n    __typename\\n  }\\n}\\n\\nfragment RSIShipFragment on RSIShip {\\n  title\\n  name\\n  url\\n  type\\n  focus\\n  msrp\\n  productionStatus\\n  purchasable\\n  minCrew\\n  maxCrew\\n  manufacturer {\\n    name\\n    __typename\\n  }\\n  imageComposer {\\n    name\\n    url\\n    __typename\\n  }\\n  media {\\n    thumbnail {\\n      slideshow\\n      storeSmall\\n      __typename\\n    }\\n    __typename\\n  }\\n  __typename\\n}"
                                }
                            ]""".replace("SHIP_NAME", name))

                headers = {"content-type": "application/json"}
                data = self._post_json(url, headers=headers, data=data.encode("utf-8"))[0]["data"]["store"]["search"]["resources"][0]
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps(data))
            except Exception as e:
                log.exception(f"Error downloading SI for #{name}")
                raise RSIException(f"Error downloading SI for #{name}: {e}")

        return json.loads(cache_path.read_text())

    def get_thumbnail(self, name: str, url: str) -> str:
        """
        Get a thumbnail for the given ship.

        Returns the path to the downloaded thumbnail in JPEG format.
        """
        log.debug(f"Getting thumbnail for #{name}")
        cache_path = self.cache_dir / name / "thumbnail.jpg"

        if not cache_path.exists():
            try:
                log.info(f"Downloading thumbnail for #{name}")
                data = self._get(url)
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_bytes(data)
            except Exception as e:
                log.exception(f"Error downloading thumbnail for #{name}:")
                raise RSIException(f"Error downloading thumbnail for #{name}: {e}")

        return str(cache_path)

    def get_model(self, name: str) -> str:
        """
        Get a 3D model for the given ship.

        Returns the path to the downloaded model in GLB format.
        """
        log.debug(f"Getting model for #{name}")
        cache_path = self.cache_dir / name / "model.glb"
        # if not cache_path.exists():
    #         log.info(f"Downloading model for #{itemNo}")
    #         try:
    #             # This ID appears to be hard-coded in the website source code?
    #             headers = {"X-Client-Id": "4863e7d2-1428-4324-890b-ae5dede24fc6"}
    #             rotera_exists = self._get_json(
    #                 f"https://web-api.ikea.com/{self.country}/{self.language}/rotera/data/exists/{itemNo}",
    #                 headers=headers,
    #             )
    #             log.debug("Exists data: %r", rotera_exists)
    #             if not rotera_exists["exists"]:
    #                 raise IkeaException(f"No model available for #{itemNo}")
    #
    #             rotera_data = self._get_json(
    #                 f"https://web-api.ikea.com/{self.country}/{self.language}/rotera/data/model/{itemNo}",
    #                 headers=headers,
    #             )
    #             log.debug("Model metadata: %r", rotera_data)
    #             data = self._get(rotera_data["modelUrl"])
    #             cache_path.parent.mkdir(parents=True, exist_ok=True)
    #             cache_path.write_bytes(data)
    #         except Exception as e:
    #             log.exception(f"Error downloading model for #{itemNo}:")
    #             raise RSIException(f"Error downloading model for #{itemNo}: {e}")
    #
        return str(cache_path)

    if __name__ == "__main__":
        logging.basicConfig(
            level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s %(message)s"
        )