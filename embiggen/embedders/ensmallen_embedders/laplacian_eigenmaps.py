"""Module providing Laplacian Eigenmaps implementation."""
from ensmallen import Graph
import pandas as pd
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import eigsh
from embiggen.embedders.ensmallen_embedders.ensmallen_embedder import EnsmallenEmbedder
from embiggen.utils import EmbeddingResult


class LaplacianEigenmapsEnsmallen(EnsmallenEmbedder):
    """Class implementing the Laplacian Eigenmaps algorithm."""

    def __init__(
        self,
        embedding_size: int = 100,
        ring_bell: bool = False,
        enable_cache: bool = False
    ):
        """Create new Laplacian Eigenmaps method.

        Parameters
        --------------------------
        embedding_size: int = 100
            Dimension of the embedding.
        ring_bell: bool = False,
            Whether to play a sound when embedding completes.
        enable_cache: bool = False
            Whether to enable the cache, that is to
            store the computed embedding.
        """
        super().__init__(
            embedding_size=embedding_size,
            ring_bell=ring_bell,
            enable_cache=enable_cache,
        )

    def _fit_transform(
        self,
        graph: Graph,
        return_dataframe: bool = True,
    ) -> EmbeddingResult:
        """Return node embedding."""
        edges, weights = graph.get_symmetric_normalized_laplacian_coo_matrix()

        coo = coo_matrix(
            (weights, (edges[:, 0], edges[:, 1])),
            shape=(
                graph.get_number_of_nodes(),
                graph.get_number_of_nodes()
            ),
            dtype=np.float32
        )

        embedding = eigsh(
            coo,
            k=self._embedding_size,
            which="SM",
            maxiter=graph.get_number_of_nodes()*100,
            return_eigenvectors=True
        )[1]

        if return_dataframe:
            node_names = graph.get_node_names()
            embedding = pd.DataFrame(
                embedding,
                index=node_names
            )
        return EmbeddingResult(
            embedding_method_name=self.model_name(),
            node_embeddings=embedding
        )

    @classmethod
    def model_name(cls) -> str:
        """Returns name of the model."""
        return "Laplacian Eigenmaps"

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

    @classmethod
    def is_stocastic(cls) -> bool:
        """Returns whether the model is stocastic and has therefore a random state."""
        return False
