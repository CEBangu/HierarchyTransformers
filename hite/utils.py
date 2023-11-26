from deeponto.onto import Taxonomy
from datasets import Dataset
from sentence_transformers import InputExample
from tqdm.auto import tqdm


def example_generator(
    taxonomy: Taxonomy, dataset: Dataset, hard_negative_first: bool = False, in_triplets: bool = False
):
    """Prepare examples in different formats.

    Args:
        taxonomy (Taxonomy): A taxonomy that can provide names for entities.
        dataset (Dataset): Input dataset to be formatted.
        hard_negative_first (bool, optional): Using hard negative samples (siblings) or not. Defaults to `False`.
        in_triplets (bool, optional): Present in triplets or not. Defaults to `False`.
    """
    examples = []
    for sample in tqdm(dataset, leave=True, desc=f"Prepare examples for {dataset.split._name}"):
        child = taxonomy.get_node_attributes(sample["child"])["name"]
        parent = taxonomy.get_node_attributes(sample["parent"])["name"]
        negative_parents = [taxonomy.get_node_attributes(neg)["name"] for neg in sample["negative_parents"]]
        siblings = [taxonomy.get_node_attributes(sib)["name"] for sib in sample["siblings"]]
        if hard_negative_first:
            # extract siblings first, if not enough, add the random negative parents
            negative_parents = (siblings + negative_parents)[:10]

        if not in_triplets:
            examples.append(InputExample(texts=[child, parent], label=1))
            examples += [InputExample(texts=[child, neg], label=0) for neg in negative_parents]
        else:
            examples += [InputExample(texts=[child, parent, neg]) for neg in negative_parents]
    return examples
