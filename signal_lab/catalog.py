from .records import Correction, Source


class SourceCatalog:
    def __init__(self, sources=()):
        self._sources = {source.source_id: source for source in sources}

    def get(self, source_id):
        return self._sources.get(source_id)

    def active_sources(self, region=None):
        values = (source for source in self._sources.values() if source.active)
        if region is not None:
            values = (source for source in values if source.region == region)
        return tuple(sorted(values, key=lambda source: source.source_id))


class CorrectionLog:
    """来源更正记录，供结论可用性评估查询。"""

    def __init__(self, corrections=()):
        self._corrections = tuple(corrections)

    def add(self, correction):
        self._corrections = self._corrections + (correction,)

    def all(self):
        return self._corrections

    def for_observation(self, observation_id):
        return tuple(
            correction for correction in self._corrections
            if observation_id in correction.observation_ids
        )
