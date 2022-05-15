"""Module providing abstract Node2Vec implementation."""
from typing import Dict, Any, Union
from ensmallen import Graph
import numpy as np
import pandas as pd
from ensmallen import models
from ...utils import AbstractEmbeddingModel


class WeightedSPINE(AbstractEmbeddingModel):
    """Abstract class for Node2Vec algorithms."""

    def __init__(
        self,
        embedding_size: int = 100,
        use_edge_weights_as_probabilities: bool = False,
    ):
        """Create new abstract Node2Vec method.

        Parameters
        --------------------------
        embedding_size: int = 100
            Dimension of the embedding.
        use_edge_weights_as_probabilities: bool = False
            Whether to treat the weights as probabilities.
        """
        self._model = models.WeightedSPINE(
            embedding_size=embedding_size,
            use_edge_weights_as_probabilities=use_edge_weights_as_probabilities
        )

        super().__init__(
            embedding_size=embedding_size,
        )

    def parameters(self) -> Dict[str, Any]:
        """Returns parameters of the model."""
        return {
            **super().parameters(),
            **dict(
                dtype=self._dtype
            )
        }

    @staticmethod
    def smoke_test_parameters() -> Dict[str, Any]:
        """Returns parameters for smoke test."""
        return dict(
            embedding_size=5,
        )

    def _fit_transform(
        self,
        graph: Graph,
        return_dataframe: bool = True,
        verbose: bool = True
    ) -> Union[np.ndarray, pd.DataFrame]:
        """Return node embedding."""
        node_embedding = self._model.fit_transform(
            graph,
            verbose=verbose,
        ).T
        if return_dataframe:
            return pd.DataFrame(
                node_embedding,
                index=graph.get_node_names()
            )
        return node_embedding

    @staticmethod
    def task_name() -> str:
        return "Node Embedding"

    @staticmethod
    def model_name() -> str:
        """Returns name of the model."""
        return "WeightedSPINE"

    @staticmethod
    def library_name() -> str:
        return "Ensmallen"

    @staticmethod
    def requires_nodes_sorted_by_decreasing_node_degree() -> bool:
        return False

    @staticmethod
    def is_topological() -> bool:
        return True

    @staticmethod
    def requires_edge_weights() -> bool:
        return True

    @staticmethod
    def requires_positive_edge_weights() -> bool:
        return True

    @staticmethod
    def requires_node_types() -> bool:
        return False

    @staticmethod
    def requires_edge_types() -> bool:
        return False