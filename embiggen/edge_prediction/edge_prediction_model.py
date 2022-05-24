"""Module providing abstract edge prediction model."""
from typing import Optional, Union, List, Dict, Any, Tuple
import pandas as pd
import numpy as np
import math
from ensmallen import Graph
from tqdm.auto import tqdm
from ..utils import AbstractClassifierModel, AbstractEmbeddingModel, abstract_class, format_list


@abstract_class
class AbstractEdgePredictionModel(AbstractClassifierModel):
    """Class defining an abstract edge prediction model."""

    @staticmethod
    def task_name() -> str:
        """Returns name of the task this model is used for."""
        return "Edge Prediction"

    def is_binary_prediction_task(self) -> bool:
        """Returns whether the model was fit on a binary prediction task."""
        # Edge prediction is always a binary prediction task.
        return True

    @staticmethod
    def is_topological() -> bool:
        return True

    def get_available_evaluation_schemas(self) -> List[str]:
        """Returns available evaluation schemas for this task."""
        return [
            "Connected Monte Carlo",
            "Monte Carlo",
            "Kfold"
        ]

    def split_graph_following_evaluation_schema(
        self,
        graph: Graph,
        evaluation_schema: str,
        number_of_holdouts: int,
        random_state: int,
        holdouts_kwargs: Dict[str, Any],
        holdout_number: int
    ) -> Tuple[Graph]:
        """Return train and test graphs tuple following the provided evaluation schema.

        Parameters
        ----------------------
        graph: Graph
            The graph to split.
        evaluation_schema: str
            The evaluation schema to follow.
        number_of_holdouts: int
            The number of holdouts that will be generated throught the evaluation.
        random_state: int
            The random state for the evaluation
        holdouts_kwargs: Dict[str, Any]
            The kwargs to be forwarded to the holdout method.
        holdout_number: int
            The current holdout number.
        """
        if evaluation_schema == "Connected Monte Carlo":
            return graph.connected_holdout(
                **holdouts_kwargs,
                random_state=random_state+holdout_number,
                verbose=False
            )
        if evaluation_schema == "Monte Carlo":
            return graph.random_holdout(
                **holdouts_kwargs,
                random_state=random_state+holdout_number,
                verbose=False
            )
        if evaluation_schema == "Kfold":
            return graph.get_edge_prediction_kfold(
                **holdouts_kwargs,
                k=number_of_holdouts,
                k_index=holdout_number,
                random_state=random_state,
                verbose=False
            )
        raise ValueError(
            f"The requested evaluation schema `{evaluation_schema}` "
            "is not available. The available evaluation schemas "
            f"are: {format_list(self.get_available_evaluation_schemas())}."
        )

    def _evaluate(
        self,
        graph: Graph,
        train: Graph,
        test: Graph,
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[str, pd.DataFrame, np.ndarray]]]] = None,
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[str, pd.DataFrame, np.ndarray]]]] = None,
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[str, pd.DataFrame, np.ndarray]]]] = None,
        subgraph_of_interest: Optional[Graph] = None,
        random_state: int = 42,
        verbose: bool = True,
        validation_sample_only_edges_with_heterogeneous_node_types: bool = False,
        validation_unbalance_rates: Tuple[float] = (1.0, )
    ) -> List[Dict[str, Any]]:
        """Return model evaluation on the provided graphs."""
        performance = []

        existent_train_prediction_probabilities = self.predict_proba(
            train,
            node_features=node_features,
            node_type_features=node_type_features,
            edge_features=edge_features
        )

        if existent_train_prediction_probabilities.shape[1] > 1:
            existent_train_prediction_probabilities = existent_train_prediction_probabilities[
                :, 1]

        existent_test_prediction_probabilities = self.predict_proba(
            test,
            node_features=node_features,
            node_type_features=node_type_features,
            edge_features=edge_features
        )

        if existent_test_prediction_probabilities.shape[1] > 1:
            existent_test_prediction_probabilities = existent_test_prediction_probabilities[
                :, 1]

        if subgraph_of_interest is None:
            sampler_graph = graph
        else:
            sampler_graph = subgraph_of_interest

        train_size = train.get_edges_number() / (train.get_edges_number() + test.get_edges_number())

        for unbalance_rate in tqdm(
            validation_unbalance_rates,
            disable=not verbose or len(validation_unbalance_rates) == 1,
            leave=False,
            dynamic_ncols=True,
            desc=f"Evaluating on unbalances"
        ):
            negative_graph = sampler_graph.sample_negative_graph(
                number_of_negative_samples=int(
                    math.ceil(sampler_graph.get_edges_number()*unbalance_rate)),
                random_state=random_state,
                sample_only_edges_with_heterogeneous_node_types=validation_sample_only_edges_with_heterogeneous_node_types,
                use_zipfian_sampling=True,
                graph_to_avoid=graph
            )

            assert negative_graph.has_edges(), "Negative graph is empty!"

            non_existent_train, non_existent_test = negative_graph.random_holdout(
                train_size=train_size,
                random_state=random_state,
                verbose=False,
            )

            assert non_existent_train.has_edges(), "Negative train graph is empty!"
            assert non_existent_test.has_edges(), "Negative test graph is empty!"

            for evaluation_mode, (existent_prediction_probabilities, non_existent_graph) in (
                (
                    "train",
                    (
                        existent_train_prediction_probabilities,
                        non_existent_train
                    )
                ),
                (
                    "test",
                    (
                        existent_test_prediction_probabilities,
                        non_existent_test
                    )
                ),
            ):
                non_existent_prediction_probabilities = self.predict_proba(
                    non_existent_graph,
                    node_features=node_features,
                    node_type_features=node_type_features,
                    edge_features=edge_features
                )

                if non_existent_prediction_probabilities.shape[1] > 1:
                    non_existent_prediction_probabilities = non_existent_prediction_probabilities[
                        :, 1]

                prediction_probabilities = np.concatenate((
                    existent_prediction_probabilities,
                    non_existent_prediction_probabilities
                ))

                labels = np.concatenate((
                    np.ones_like(existent_prediction_probabilities),
                    np.zeros_like(non_existent_prediction_probabilities),
                ))

                performance.append({
                    "evaluation_mode": evaluation_mode,
                    "validation_unbalance_rate": unbalance_rate,
                    "validation_sample_only_edges_with_heterogeneous_node_types": validation_sample_only_edges_with_heterogeneous_node_types,
                    "train_size": train_size,
                    **self.evaluate_predictions(
                        prediction_probabilities > 0.5,
                        labels
                    ),
                    **self.evaluate_prediction_probabilities(
                        prediction_probabilities,
                        labels
                    ),
                })

        return performance

    def predict(
        self,
        graph: Graph,
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
    ) -> np.ndarray:
        """Execute predictions on the provided graph.

        Parameters
        --------------------
        graph: Graph
            The graph to run predictions on.
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node features to use.
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node type features to use.
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The edge features to use.
        """
        if edge_features is not None:
            raise NotImplementedError(
                "Currently edge features are not supported in edge prediction models."
            )

        return super().predict(
            graph,
            node_features=node_features,
            node_type_features=node_type_features
        )

    def predict_bipartite_graph_from_edge_node_ids(
        self,
        graph: Graph,
        source_node_ids: List[int],
        destination_node_ids: List[int],
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
    ) -> np.ndarray:
        """Execute predictions on the provided graph bipartite portion.

        Parameters
        --------------------
        graph: Graph
            The graph from which to extract the edges.
        source_node_ids: List[int]
            The source nodes of the bipartite graph.
        destination_node_ids: List[int]
            The destination nodes of the bipartite graph.
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node features to use.
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node type features to use.
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The edge features to use.
        """
        return self.predict(
            graph.build_bipartite_graph_from_edge_node_ids(
                source_node_ids=source_node_ids,
                destination_node_ids=destination_node_ids,
                directed=True
            ),
            node_features=node_features,
            node_type_features=node_type_features,
            edge_features=edge_features
        )

    def predict_bipartite_graph_from_edge_node_names(
        self,
        graph: Graph,
        source_node_names: List[str],
        destination_node_names: List[str],
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
    ) -> np.ndarray:
        """Execute predictions on the provided graph bipartite portion.

        Parameters
        --------------------
        graph: Graph
            The graph from which to extract the edges.
        source_node_names: List[str]
            The source nodes of the bipartite graph.
        destination_node_names: List[str]
            The destination nodes of the bipartite graph.
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node features to use.
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node type features to use.
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The edge features to use.
        """
        return self.predict(
            graph.build_bipartite_graph_from_edge_node_names(
                source_node_names=source_node_names,
                destination_node_names=destination_node_names,
                directed=True
            ),
            node_features=node_features,
            node_type_features=node_type_features,
            edge_features=edge_features
        )

    def predict_bipartite_graph_from_edge_node_prefixes(
        self,
        graph: Graph,
        source_node_prefixes: List[str],
        destination_node_prefixes: List[str],
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
    ) -> np.ndarray:
        """Execute predictions on the provided graph bipartite portion.

        Parameters
        --------------------
        graph: Graph
            The graph from which to extract the edges.
        source_node_prefixes: List[str]
            The source node prefixes of the bipartite graph.
        destination_node_prefixes: List[str]
            The destination node prefixes of the bipartite graph.
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node features to use.
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node type features to use.
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The edge features to use.
        """
        return self.predict(
            graph.build_bipartite_graph_from_edge_node_prefixes(
                source_node_prefixes=source_node_prefixes,
                destination_node_prefixes=destination_node_prefixes,
                directed=True
            ),
            node_features=node_features,
            node_type_features=node_type_features,
            edge_features=edge_features
        )

    def predict_bipartite_graph_from_edge_node_types(
        self,
        graph: Graph,
        source_node_types: List[str],
        destination_node_types: List[str],
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
    ) -> np.ndarray:
        """Execute predictions on the provided graph bipartite portion.

        Parameters
        --------------------
        graph: Graph
            The graph from which to extract the edges.
        source_node_types: List[str]
            The source node prefixes of the bipartite graph.
        destination_node_types: List[str]
            The destination node prefixes of the bipartite graph.
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node features to use.
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node type features to use.
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The edge features to use.
        """
        return self.predict(
            graph.build_bipartite_graph_from_edge_node_types(
                source_node_types=source_node_types,
                destination_node_types=destination_node_types,
                directed=True
            ),
            node_features=node_features,
            node_type_features=node_type_features,
            edge_features=edge_features
        )

    def predict_clique_graph_from_node_ids(
        self,
        graph: Graph,
        node_ids: List[int],
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
    ) -> np.ndarray:
        """Execute predictions on the provided graph bipartite portion.

        Parameters
        --------------------
        graph: Graph
            The graph from which to extract the edges.
        node_ids: List[int]
            The nodes of the bipartite graph.
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node features to use.
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node type features to use.
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The edge features to use.
        """
        return self.predict(
            graph.build_clique_graph_from_node_ids(
                node_ids=node_ids,
                directed=True
            ),
            node_features=node_features,
            node_type_features=node_type_features,
            edge_features=edge_features
        )

    def predict_clique_graph_from_node_names(
        self,
        graph: Graph,
        node_names: List[str],
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
    ) -> np.ndarray:
        """Execute predictions on the provided graph bipartite portion.

        Parameters
        --------------------
        graph: Graph
            The graph from which to extract the edges.
        node_names: List[str]
            The nodes of the bipartite graph.
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node features to use.
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node type features to use.
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The edge features to use.
        """
        return self.predict(
            graph.build_clique_graph_from_node_names(
                node_names=node_names,
                directed=True
            ),
            node_features=node_features,
            node_type_features=node_type_features,
            edge_features=edge_features
        )

    def predict_clique_graph_from_node_prefixes(
        self,
        graph: Graph,
        node_prefixes: List[str],
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
    ) -> np.ndarray:
        """Execute predictions on the provided graph bipartite portion.

        Parameters
        --------------------
        graph: Graph
            The graph from which to extract the edges.
        node_prefixes: List[str]
            The node prefixes of the bipartite graph.
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node features to use.
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node type features to use.
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The edge features to use.
        """
        return self.predict(
            graph.build_clique_graph_from_node_prefixes(
                node_prefixes=node_prefixes,
                directed=True
            ),
            node_features=node_features,
            node_type_features=node_type_features,
            edge_features=edge_features
        )

    def predict_clique_graph_from_node_types(
        self,
        graph: Graph,
        node_types: List[str],
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
    ) -> np.ndarray:
        """Execute predictions on the provided graph bipartite portion.

        Parameters
        --------------------
        graph: Graph
            The graph from which to extract the edges.
        node_types: List[str]
            The node prefixes of the bipartite graph.
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node features to use.
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node type features to use.
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The edge features to use.
        """
        return self.predict(
            graph.build_clique_graph_from_node_types(
                node_types=node_types,
                directed=True
            ),
            node_features=node_features,
            node_type_features=node_type_features,
            edge_features=edge_features
        )

    def predict_proba(
        self,
        graph: Graph,
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
    ) -> np.ndarray:
        """Execute predictions on the provided graph.

        Parameters
        --------------------
        graph: Graph
            The graph to run predictions on.
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node features to use.
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node type features to use.
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The edge features to use.
        """
        if edge_features is not None:
            raise NotImplementedError(
                "Currently edge features are not supported in edge prediction models."
            )

        return super().predict_proba(
            graph,
            node_features=node_features,
            node_type_features=node_type_features
        )

    def fit(
        self,
        graph: Graph,
        support: Optional[Graph] = None,
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None,
    ):
        """Execute fitting on the provided graph.

        Parameters
        --------------------
        graph: Graph
            The graph to run predictions on.
        support: Optional[Graph] = None
            The graph describiding the topological structure that
            includes also the above graph. This parameter
            is mostly useful for topological classifiers
            such as Graph Convolutional Networks.
        node_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node features to use.
        node_type_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The node type features to use.
        edge_features: Optional[Union[pd.DataFrame, np.ndarray, List[Union[pd.DataFrame, np.ndarray]]]] = None
            The edge features to use.
        """
        if edge_features is not None:
            raise NotImplementedError(
                "Currently edge features are not supported in edge prediction models."
            )

        super().fit(
            graph=graph,
            support=support,
            node_features=node_features,
            node_type_features=node_type_features,
            edge_features=None,
        )

    def evaluate(
        self,
        graph: Graph,
        evaluation_schema: str,
        holdouts_kwargs: Dict[str, Any],
        node_features: Optional[Union[str, pd.DataFrame, np.ndarray, AbstractEmbeddingModel, List[Union[str, pd.DataFrame, np.ndarray, AbstractEmbeddingModel]]]] = None,
        node_type_features: Optional[Union[str, pd.DataFrame, np.ndarray, AbstractEmbeddingModel, List[Union[str, pd.DataFrame, np.ndarray, AbstractEmbeddingModel]]]] = None,
        edge_features: Optional[Union[str, pd.DataFrame, np.ndarray, List[Union[str, pd.DataFrame, np.ndarray]]]] = None,
        subgraph_of_interest: Optional[Graph] = None,
        number_of_holdouts: int = 10,
        random_state: int = 42,
        smoke_test: bool = False,
        verbose: bool = True,
        validation_sample_only_edges_with_heterogeneous_node_types: bool = False,
        validation_unbalance_rates: Tuple[float] = (1.0, )
    ) -> pd.DataFrame:
        """Execute evaluation on the provided graph.

        Parameters
        --------------------
        graph: Graph
            The graph to run predictions on.
        evaluation_schema: str
            The schema for the evaluation to follow.
        holdouts_kwargs: Dict[str, Any]
            Parameters to forward to the desired evaluation schema.
        node_features: Optional[Union[str, pd.DataFrame, np.ndarray, AbstractEmbeddingModel, List[Union[str, pd.DataFrame, np.ndarray, AbstractEmbeddingModel]]]] = None
            The node features to use.
        node_type_features: Optional[Union[str, pd.DataFrame, np.ndarray, AbstractEmbeddingModel, List[Union[str, pd.DataFrame, np.ndarray, AbstractEmbeddingModel]]]] = None
            The node type features to use.
        edge_features: Optional[Union[str, pd.DataFrame, np.ndarray, List[Union[str, pd.DataFrame, np.ndarray]]]] = None
            The edge features to use.
        subgraph_of_interest: Optional[Graph] = None
            Optional subgraph where to focus the task.
        skip_evaluation_biased_feature: bool = False
            Whether to skip feature names that are known to be biased
            when running an holdout. These features should be computed
            exclusively on the training graph and not the entire graph.
        number_of_holdouts: int = 10
            The number of holdouts to execute.
        random_state: int = 42
            The random state to use for the holdouts.
        smoke_test: bool = False
            Whether this run should be considered a smoke test
            and therefore use the smoke test configurations for
            the provided model names and feature names.
        verbose: bool = True
            Whether to show a loading bar while computing holdouts.
        validation_sample_only_edges_with_heterogeneous_node_types: bool = False
            Whether to sample negative edges exclusively between nodes with different node types.
            This can be useful when executing a bipartite edge prediction task.
        validation_unbalance_rates: Tuple[float] = (1.0, )
            Unbalance rate for the non-existent graphs generation.
        """
        if edge_features is not None:
            raise NotImplementedError(
                "Currently edge features are not supported in edge prediction models."
            )

        return super().evaluate(
            graph=graph,
            evaluation_schema=evaluation_schema,
            holdouts_kwargs=holdouts_kwargs,
            node_features=node_features,
            node_type_features=node_type_features,
            edge_features=None,
            subgraph_of_interest=subgraph_of_interest,
            number_of_holdouts=number_of_holdouts,
            random_state=random_state,
            verbose=verbose,
            smoke_test=smoke_test,
            validation_sample_only_edges_with_heterogeneous_node_types=validation_sample_only_edges_with_heterogeneous_node_types,
            validation_unbalance_rates=validation_unbalance_rates,
        )
