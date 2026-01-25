"""
Abstract base class for lineup optimizers.
"""
from abc import ABC, abstractmethod
from typing import List, Any, Dict
import yaml
from rower import Rower


class Optimizer(ABC):
    """
    Abstract base class for lineup optimizers.
    """

    def __init__(self, rowers: List[Rower], scoring_config: Dict[str, Any] = None):
        self.rowers = rowers
        if scoring_config:
            self.scoring_weights = scoring_config
        else:
            self.scoring_weights = self._load_scoring_config()

    def _load_scoring_config(self) -> Dict[str, Any]:
        """Loads scoring configuration from a YAML file."""
        try:
            with open('scoring_config.yaml', 'r') as f:
                return yaml.safe_load(f)
        except (FileNotFoundError, yaml.YAMLError) as e:
            print(f"Warning: Could not load or parse scoring_config.yaml: {e}. Using default weights.")
            return self.get_default_scoring_weights()

    @abstractmethod
    def get_default_scoring_weights(self) -> Dict[str, Any]:
        """
        Returns a dictionary of default scoring weights if the config file is not available.
        """
        pass

    @abstractmethod
    def optimize(self) -> Any:
        """
        Run the optimization algorithm.
        The return type will vary depending on the optimizer.
        """
        pass

    @abstractmethod
    def print_results(self):
        """
        Print the results of the optimization.
        """
        pass
