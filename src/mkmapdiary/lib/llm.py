import dataclasses
import itertools
import logging
import random
from typing import Any, Callable, List

import llm_dataclass

logger = logging.getLogger(__name__)


def batch_reduce(
    count: int,
    prompt: str,
    llm_callback: Callable[[str], str],
    input_data: List[Any],
    selector_type: Any,
    context: int = 128000,
    estimate: int = 250,
    max_iter: int = 5,
) -> List[Any]:
    """Reduce a data using a prompt in batches to fit within context limits.

    Args:
        prompt (str): The input prompt to be reduced.
        llm_callback (callable): A function that takes a prompt and returns the reduced text.
        batch_size (int, optional): The number of items to process in each batch. Defaults to 5.

    Returns:
        str: The reduced prompt after processing all batches.
    """
    assert dataclasses.is_dataclass(selector_type), "Output type must be a dataclass"
    assert count >= 0, "Count must be greater than 0"

    if count == 0:
        return []

    if len(input_data) == 0:
        return []

    input_class = input_data[0].__class__
    assert dataclasses.is_dataclass(input_class), "Input type must be a dataclass"
    assert isinstance(input_class, type), "Input type must be a class type"
    assert dataclasses.is_dataclass(selector_type), "Output type must be a dataclass"
    assert isinstance(selector_type, type), "Output type must be a class type"

    input_schema: llm_dataclass.Schema = llm_dataclass.Schema(input_class)
    output_schema: llm_dataclass.Schema = llm_dataclass.Schema(selector_type)
    id_attribute = selector_type.__dataclass_fields__.keys().__iter__().__next__()  # type: ignore

    # Determine max items per batch
    max_input_tokens = context - estimate
    max_input_items = max_input_tokens // estimate

    # If input size is already within count, return as is
    for _ in range(max_iter):
        if len(input_data) <= count:
            return input_data

        # Serialize input
        serialized_input = []
        lookup = {}

        # Verify that input can fit in the estimated context
        for item in input_data:
            serialized_item = input_schema.dumps(item)
            serialized_input.append(serialized_item)
            if len(serialized_item) > estimate:
                logger.warning(
                    "Input item exceeds estimated context size, consider increasing estimate."
                )
            lookup[getattr(item, id_attribute)] = item

        batches = itertools.batched(serialized_input, max_input_items)
        next_data = []
        for batch in batches:
            batch_prompt = prompt + "\n\n" + "\n".join(batch)
            reduced_text = llm_callback(batch_prompt)

            # Deserialize reduced text
            reduced_items = output_schema.loads(reduced_text)

            # Select items
            output_items = []
            for item in getattr(reduced_items, id_attribute):
                try:
                    output_items.append(lookup[item])
                except KeyError:
                    logger.warning(
                        f"Item with id {getattr(item, id_attribute)} not found during lookup."
                    )

            next_data.extend(output_items)
        input_data = next_data

    if len(input_data) <= count:
        return input_data
    logger.warning("Maximum iterations reached, returning random reduced input.")
    return random.sample(input_data, count)
