import json
import yaml


class DotDict:
    """A dictionary that supports dot notation access to its keys."""
    def __init__(self, dictionary):
        for key, value in dictionary.items():
            if isinstance(value, dict):
                value = DotDict(value)
            if isinstance(value, list):
                value = [DotDict(item) if isinstance(item, dict) else item for item in value]
            setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def to_dict(self):
        result = {}
        for key in self.__dict__:
            value = getattr(self, key)
            if isinstance(value, DotDict):
                value = value.to_dict()
            result[key] = value
        return result


class ConfigLoader:
    """Loads configuration from a YAML file and provides dot notation access."""
    def __init__(self, filepath: str):
        with open(filepath, 'r') as file:
            self.config = yaml.safe_load(file)
        self.dotdict = DotDict(self.config)


