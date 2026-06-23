from __future__ import annotations

import requests
from urllib.parse import urlparse, parse_qs

from singer_sdk import Tap, typing as th
from singer_sdk.streams import RESTStream


class BreedsStream(RESTStream):
    name = "breeds"
    url_base = "https://dogapi.dog/api/v2"
    path = "/breeds"
    primary_keys = ["id"]
    replication_key = None

    schema = th.PropertiesList(
        th.Property("id", th.StringType, required=True),
        th.Property("name", th.StringType),
        th.Property("description", th.StringType),
        th.Property("life_min", th.IntegerType),
        th.Property("life_max", th.IntegerType),
        th.Property("male_weight_min", th.IntegerType),
        th.Property("male_weight_max", th.IntegerType),
        th.Property("female_weight_min", th.IntegerType),
        th.Property("female_weight_max", th.IntegerType),
        th.Property("hypoallergenic", th.BooleanType),
        th.Property("group_id", th.StringType),
        th.Property("group_name", th.StringType),
    ).to_dict()

    @property
    def _group_lookup(self) -> dict:
        if not hasattr(self, "_groups_cache"):
            resp = requests.get(f"{self.url_base}/groups", timeout=30)
            resp.raise_for_status()
            self._groups_cache = {
                g["id"]: g["attributes"]["name"]
                for g in resp.json()["data"]
            }
        return self._groups_cache

    def get_next_page_token(self, response, previous_token):
        return response.json().get("links", {}).get("next")

    def get_url_params(self, context, next_page_token):
        if next_page_token is None:
            return {}
        qs = parse_qs(urlparse(next_page_token).query)
        page = qs.get("page[number]", [None])[0]
        return {"page[number]": page} if page else {}

    def parse_response(self, response):
        for breed in response.json().get("data", []):
            attrs = breed.get("attributes", {})
            group_id = (
                breed.get("relationships", {})
                .get("group", {})
                .get("data", {})
                .get("id")
            )
            yield {
                "id": breed["id"],
                "name": attrs.get("name"),
                "description": attrs.get("description"),
                "life_min": (attrs.get("life") or {}).get("min"),
                "life_max": (attrs.get("life") or {}).get("max"),
                "male_weight_min": (attrs.get("male_weight") or {}).get("min"),
                "male_weight_max": (attrs.get("male_weight") or {}).get("max"),
                "female_weight_min": (attrs.get("female_weight") or {}).get("min"),
                "female_weight_max": (attrs.get("female_weight") or {}).get("max"),
                "hypoallergenic": attrs.get("hypoallergenic"),
                "group_id": group_id,
                "group_name": self._group_lookup.get(group_id),
            }


class TapDogAPI(Tap):
    name = "tap-dogapi"

    def discover_streams(self):
        return [BreedsStream(self)]


if __name__ == "__main__":
    TapDogAPI.cli()
