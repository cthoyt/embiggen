"""Wrapper for Role2Vec model provided from the Karate Club package."""
from typing import Dict, Any
from karateclub.node_embedding import Role2Vec
from multiprocessing import cpu_count
from embiggen.embedders.karateclub_embedders.abstract_karateclub_embedder import AbstractKarateClubEmbedder


class Role2VecKarateClub(AbstractKarateClubEmbedder):

    def __init__(
        self,
        embedding_size: int = 100,
        iterations: int = 10,
        walk_length: int = 128,
        window_size: int = 5,
        epochs: int = 10,
        learning_rate: float = 0.05,
        down_sampling: float = 0.0001,
        min_count: int = 1,
        weisfeiler_lehman_hashing_iterations: int = 2,
        erase_base_features: bool = False,
        random_state: int = 42,
        ring_bell: bool = False,
        enable_cache: bool = False
    ):
        """Return a new Role2Vec embedding model.

        Parameters
        ----------------------
        embedding_size: int = 100
            Size of the embedding to use.
        iterations: int = 10
            Number of random walks. Default is 10.
        walk_length: int = 128
            Length of random walks. Default is 80.
        window_size: int = 5
            Matrix power order. Default is 5.
        epochs: int = 10
            Number of epochs. Default is 1.
        learning_rate: float = 0.05
            HogWild! learning rate. Default is 0.05.
        down_sampling: float = 0.0001
            Down sampling frequency. Default is 0.0001.
        min_count: int = 1
            Minimal count of node occurrences. Default is 1.
        weisfeiler_lehman_hashing_iterations: int = 2
            Number of Weisfeiler-Lehman hashing iterations. Default is 2.
        erase_base_features: bool = False
            Removing the base features. Default is False.
        random_state: int = 42
            Random state to use for the stocastic
            portions of the embedding algorithm.
        ring_bell: bool = False,
            Whether to play a sound when embedding completes.
        enable_cache: bool = False
            Whether to enable the cache, that is to
            store the computed embedding.
        """
        self._iterations = iterations
        self._walk_length = walk_length
        self._workers = cpu_count()
        self._window_size = window_size
        self._epochs = epochs
        self._learning_rate = learning_rate
        self._down_sampling = down_sampling
        self._min_count = min_count
        self._weisfeiler_lehman_hashing_iterations = weisfeiler_lehman_hashing_iterations
        self._erase_base_features = erase_base_features
        super().__init__(
            embedding_size=embedding_size,
            enable_cache=enable_cache,
            ring_bell=ring_bell,
            random_state=random_state
        )

    def parameters(self) -> Dict[str, Any]:
        """Returns the parameters used in the model."""
        return dict(
            **super().parameters(),
            walk_number=self._iterations,
            walk_length=self._walk_length,
            window_size=self._window_size,
            epochs=self._epochs,
            learning_rate=self._learning_rate,
            min_count=self._min_count,
            down_sampling=self._down_sampling,
            weisfeiler_lehman_hashing_iterations=self._weisfeiler_lehman_hashing_iterations,
            erase_base_features=self._erase_base_features,
        )

    @classmethod
    def smoke_test_parameters(cls) -> Dict[str, Any]:
        """Returns parameters for smoke test."""
        return dict(
            **AbstractKarateClubEmbedder.smoke_test_parameters(),
            iterations=1,
            weisfeiler_lehman_hashing_iterations=1,
            walk_length=8,
            window_size=2,
            epochs=1,
        )

    def _build_model(self) -> Role2Vec:
        """Return new instance of the Role2Vec model."""
        return Role2Vec(
            iterations=self._iterations,
            walk_length=self._walk_length,
            dimensions=self._embedding_size,
            workers=self._workers,
            window_size=self._window_size,
            epochs=self._epochs,
            down_sampling=self._down_sampling,
            wl_iterations=self._weisfeiler_lehman_hashing_iterations,
            erase_base_features=self._erase_base_features,
            learning_rate=self._learning_rate,
            min_count=self._min_count,
            seed=self._random_state
        )

    @classmethod
    def model_name(cls) -> str:
        """Returns name of the model"""
        return "Role2Vec"

    @classmethod
    def requires_nodes_sorted_by_decreasing_node_degree(cls) -> bool:
        return False

    @classmethod
    def is_topological(cls) -> bool:
        return True

    @classmethod
    def can_use_edge_weights(cls) -> bool:
        """Returns whether the model can optionally use edge weights."""
        return False

    @classmethod
    def can_use_node_types(cls) -> bool:
        """Returns whether the model can optionally use node types."""
        return False

    @classmethod
    def can_use_edge_types(cls) -> bool:
        """Returns whether the model can optionally use edge types."""
        return False

