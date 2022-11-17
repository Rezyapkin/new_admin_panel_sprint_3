"""A module for batch uploading Pydantic documents to ElasticSearch."""
from abc import abstractmethod
from typing import Tuple, Union, List, Dict, Any

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

from decorators import backoff
from models import FilmWork, ElasticModel


class ElasticLoad:
    def __init__(self, es: Elasticsearch):
        self.es = es

    def get_elastic(self) -> Elasticsearch:
        return self.es

    @staticmethod
    def _get_data_for_elastic(data: list[ElasticModel]):
        return [record.dict(by_alias=True) for record in data]

    @abstractmethod
    def load(self, data: list[ElasticModel]):
        pass


class MoviesESLoad(ElasticLoad):
    @backoff()
    def load(self, data: list[FilmWork], index: str) -> Tuple[int, Union[int, List[Dict[str, Any]]]]:
        return bulk(self.es, self._get_data_for_elastic(data), index=index)
