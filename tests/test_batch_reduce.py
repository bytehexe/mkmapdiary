import dataclasses
import logging
from typing import Generator, List

import pytest

from mkmapdiary.lib.llm import batch_reduce

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class InputClass:
    id: int
    name: str


@dataclasses.dataclass
class SelectorClass:
    id: List[int]


def test_batch_reduce_small_input() -> None:
    def llm_callback(prompt: str) -> str:
        raise NotImplementedError("LLM callback is not implemented for testing.")

    input_data = [InputClass(id=1, name="Test 1"), InputClass(id=2, name="Test 2")]
    selector_type = SelectorClass
    result = batch_reduce(2, "Test prompt", llm_callback, input_data, selector_type)
    assert result == input_data


def test_batch_reduce_empty_input() -> None:
    def llm_callback(prompt: str) -> str:
        raise NotImplementedError("LLM callback is not implemented for testing.")

    input_data: List[InputClass] = []
    selector_type = SelectorClass
    result = batch_reduce(2, "Test prompt", llm_callback, input_data, selector_type)
    assert result == []


def test_batch_reduce_medium_input() -> None:
    def llm_callback(prompt: str) -> str:
        raise NotImplementedError("LLM callback is not implemented for testing.")

    input_data = [InputClass(id=i, name=f"Test {i}") for i in range(3)]
    selector_type = SelectorClass
    with pytest.raises(NotImplementedError):
        batch_reduce(2, "Test prompt", llm_callback, input_data, selector_type)


def test_batch_reduce_large_input() -> None:
    def llm_callback_gen() -> Generator:
        yield """
        <SelectorClass><id>0</id><id>1</id></SelectorClass>
        """
        yield """
        <SelectorClass><id>4</id><id>5</id></SelectorClass>
        """
        yield """
        <SelectorClass><id>0</id><id>4</id></SelectorClass>
        """
        yield """
        <SelectorClass><id>5</id></SelectorClass>
        """
        yield """
        <SelectorClass><id>0</id><id>5</id></SelectorClass>
        """
        yield "done"

    input_data = [InputClass(id=i, name=f"Test {i}") for i in range(6)]
    selector_type = SelectorClass

    llm_callback_iter = iter(llm_callback_gen()).__next__

    def llm_callback(prompt: str) -> str:
        ret = llm_callback_iter()
        logger.warning(
            f"LLM callback called with prompt: {prompt}... returning: {ret.strip()}"
        )
        return ret

    result = batch_reduce(
        2,
        "Test prompt",
        llm_callback,
        input_data,
        selector_type,
        context=4000,
        estimate=1000,
    )
    expected_ids = [0, 5]
    result_ids = [item.id for item in result]
    assert result_ids == expected_ids
    assert llm_callback("") == "done"
