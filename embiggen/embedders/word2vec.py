"""Abstract class for sequence embedding models."""
from typing import Dict, List, Tuple, Union

import numpy as np
import pandas as pd
from tensorflow.keras import backend as K  # pylint: disable=import-error
from tensorflow.keras import regularizers
from tensorflow.keras.constraints import UnitNorm
from tensorflow.keras.layers import Embedding  # pylint: disable=import-error
from tensorflow.keras.layers import Flatten, Input, Lambda, Layer
from tensorflow.keras.models import Model  # pylint: disable=import-error
from tensorflow.keras.optimizers import \
    Optimizer  # pylint: disable=import-error

from .embedder import Embedder
from .layers import NoiseContrastiveEstimation


class Word2Vec(Embedder):
    """Abstract class for sequence embedding models."""

    def __init__(
        self,
        vocabulary_size: int = None,
        embedding_size: int = None,
        embedding: Union[np.ndarray, pd.DataFrame] = None,
        model_name: str = "Word2Vec",
        optimizer: Union[str, Optimizer] = None,
        window_size: int = 8,
        negative_samples: int = 10
    ):
        """Create new sequence Embedder model.

        Parameters
        -------------------------------------------
        vocabulary_size: int = None,
            Number of terms to embed.
            In a graph this is the number of nodes, while in a text is the
            number of the unique words.
            If None, the seed embedding must be provided.
            It is not possible to provide both at once.
        embedding_size: int = None,
            Dimension of the embedding.
            If None, the seed embedding must be provided.
            It is not possible to provide both at once.
        embedding: Union[np.ndarray, pd.DataFrame] = None,
            The seed embedding to be used.
            Note that it is not possible to provide at once both
            the embedding and either the vocabulary size or the embedding size.
        model_name: str = "Word2Vec",
            Name of the model.
        optimizer: Union[str, Optimizer] = "nadam",
            The optimizer to be used during the training of the model.
        window_size: int = 8,
            Window size for the local context.
            On the borders the window size is trimmed.
        negative_samples: int = 10,
            The number of negative classes to randomly sample per batch.
            This single sample of negative classes is evaluated for each element in the batch.
        """
        self._model_name = model_name
        self._window_size = window_size
        self._negative_samples = negative_samples
        super().__init__(
            vocabulary_size=vocabulary_size,
            embedding_size=embedding_size,
            optimizer=optimizer
        )

    def _get_true_input_length(self) -> int:
        """Return length of true input layer."""
        raise NotImplementedError((
            "The method '_get_true_input_length' "
            "must be implemented in child class."
        ))

    def _get_true_output_length(self) -> int:
        """Return length of true output layer."""
        raise NotImplementedError((
            "The method '_get_true_output_length' "
            "must be implemented in child class."
        ))

    def _sort_input_layers(
        self,
        true_input_layer: Layer,
        true_output_layer: Layer
    ) -> Tuple[Layer, Layer]:
        """Return input layers for training with the same input sequence.

        Parameters
        ----------------------------
        true_input_layer: Layer,
            The input layer that will contain the true input.
        true_output_layer: Layer,
            The input layer that will contain the true output.

        Returns
        ----------------------------
        Return tuple with the tuple of layers.
        """
        raise NotImplementedError((
            "The method '_sort_input_layers' "
            "must be implemented in child class."
        ))

    def _build_model(self):
        """Return Node2Vec model."""
        # Creating the inputs layers
        true_input_layer = Input(
            (self._get_true_input_length(), ),
        )
        true_output_layer = Input(
            (self._get_true_output_length(), ),
        )

        # Creating the embedding layer for the contexts
        embedding = Embedding(
            input_dim=self._vocabulary_size,
            output_dim=self._embedding_size,
            input_length=self._get_true_input_length(),
            embeddings_regularizer=regularizers.l1_l2(l1=1e-5, l2=1e-4),
            embeddings_constraint=UnitNorm(),
            name=Embedder.EMBEDDING_LAYER_NAME
        )(true_input_layer)

        # If there is more than one value per single sample
        # as there is for instance in CBOW-like models
        if self._get_true_input_length() > 1:
            # Computing mean of the embedding of all the contexts
            mean_embedding = Lambda(
                lambda x: K.mean(x, axis=1),
                output_shape=(self._embedding_size,)
            )(embedding)
        else:
            # Otherwise we passthrough the previous result with a simple flatten.
            mean_embedding = Flatten()(embedding)

        # Adding layer that also executes the loss function
        nce_loss = NoiseContrastiveEstimation(
            vocabulary_size=self._vocabulary_size,
            embedding_size=self._embedding_size,
            negative_samples=self._negative_samples,
            positive_samples=self._get_true_output_length()
        )((mean_embedding, true_output_layer))

        # Creating the actual model
        model = Model(
            inputs=self._sort_input_layers(
                true_input_layer,
                true_output_layer
            ),
            outputs=nce_loss,
            name=self._model_name
        )
        return model

    def _compile_model(self) -> Model:
        """Compile model."""
        # No loss function is needed because it is already executed in
        # the NCE loss layer.
        self._model.compile(
            optimizer=self._optimizer
        )

    def fit(
        self,
        *args: List,
        epochs: int = 10000,
        early_stopping_monitor: str = "loss",
        early_stopping_min_delta: float = 0.1,
        early_stopping_patience: int = 5,
        early_stopping_mode: str = "min",
        reduce_lr_monitor: str = "loss",
        reduce_lr_min_delta: float = 1,
        reduce_lr_patience: int = 3,
        reduce_lr_mode: str = "min",
        reduce_lr_factor: float = 0.9,
        verbose: int = 1,
        **kwargs: Dict
    ) -> pd.DataFrame:
        """Return pandas dataframe with training history.

        Parameters
        -----------------------
        *args: List,
            List of parameters to pass to the fit call.
        epochs: int = 10000,
            Epochs to train the model for.
        early_stopping_monitor: str = "loss",
            Metric to monitor for early stopping.
        early_stopping_min_delta: float = 0.1,
            Minimum delta of metric to stop the training.
        early_stopping_patience: int = 5,
            Number of epochs to wait for when the given minimum delta is not
            achieved after which trigger early stopping.
        early_stopping_mode: str = "min",
            Direction of the variation of the monitored metric for early stopping.
        reduce_lr_monitor: str = "loss",
            Metric to monitor for reducing learning rate.
        reduce_lr_min_delta: float = 1,
            Minimum delta of metric to reduce learning rate.
        reduce_lr_patience: int = 3,
            Number of epochs to wait for when the given minimum delta is not
            achieved after which reducing learning rate.
        reduce_lr_mode: str = "min",
            Direction of the variation of the monitored metric for learning rate.
        reduce_lr_factor: float = 0.9,
            Factor for reduction of learning rate.
        verbose: int = 1,
            Wethever to show the loading bar.
            Specifically, the options are:
            * 0 or False: No loading bar.
            * 1 or True: Showing only the loading bar for the epochs.
            * 2: Showing loading bar for both epochs and batches.
        **kwargs: Dict,
            Additional kwargs to pass to the Keras fit call.

        Returns
        -----------------------
        Dataframe with training history.
        """
        super().fit(
            *args,
            epochs=epochs,
            early_stopping_monitor=early_stopping_monitor,
            early_stopping_min_delta=early_stopping_min_delta,
            early_stopping_patience=early_stopping_patience,
            early_stopping_mode=early_stopping_mode,
            reduce_lr_monitor=reduce_lr_monitor,
            reduce_lr_min_delta=reduce_lr_min_delta,
            reduce_lr_patience=reduce_lr_patience,
            reduce_lr_mode=reduce_lr_mode,
            reduce_lr_factor=reduce_lr_factor,
            verbose=verbose,
            **kwargs
        )
