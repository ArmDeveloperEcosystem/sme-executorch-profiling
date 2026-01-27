# Copyright 2025 Arm Limited (or its affiliates)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Common interface for ExecuTorch-compatible eager models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Tuple


class EagerModelBase(ABC):
    """Subset of the ExecuTorch model interface we rely on for exports."""

    @abstractmethod
    def get_eager_model(self):
        """Return the instantiated eager PyTorch module ready for export."""

    @abstractmethod
    def get_example_inputs(self) -> Tuple[Any, ...]:
        """Return positional example inputs used for tracing/export."""

    def get_example_kwarg_inputs(self) -> dict:
        """Optional keyword inputs; override when the model needs them."""

        return {}

    def get_dynamic_shapes(self):
        """Optional dynamic shape info; override if needed."""

        return None
