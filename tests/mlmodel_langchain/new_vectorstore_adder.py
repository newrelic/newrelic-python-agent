"""
This script is used to automatically add new vectorstore classes to the newrelic-python-agent.
To run this script, start from the root of the newrelic-python-agent repository and run:
    `python tests/mlmodel_langchain/new_vectorstore_adder.py`
This will generate the necessary code to instrument the new vectorstore classes in the local
copy of the newrelic-python-agent repository.
"""

import os
from textwrap import dedent

from langchain_community import vectorstores

from newrelic.hooks.mlmodel_langchain import VECTORSTORE_CLASSES

dir_path = os.path.dirname(os.path.realpath(__file__))
test_dir = os.path.abspath(os.path.join(dir_path, os.pardir))
REPO_PATH = os.path.abspath(os.path.join(test_dir, os.pardir))


def add_to_config(directory, instrumented_class=None):
    # Only implement this if there is not an instrumented class within the directory already.
    if instrumented_class:
        return

    with open(f"{REPO_PATH}/newrelic/config.py", "r+") as file:
        text = file.read()
        text = text.replace(
            "VectorStores with similarity_search method",
            dedent(
                f"""
                    VectorStores with similarity_search method
                        _process_module_definition(
                            "{directory}",
                            "newrelic.hooks.mlmodel_langchain",
                            "instrument_langchain_vectorstore_similarity_search",
                        )
                """.lstrip("\n")
            ),
            1,
        )
        file.seek(0)
        file.write(text)


def add_to_hooks(class_name, directory, instrumented_class=None):
    with open(f"{REPO_PATH}/newrelic/hooks/mlmodel_langchain.py", "r+") as file:
        text = file.read()

        # The directory does not exist yet.  Add the new directory and class name to the beginning of the dictionary
        if not instrumented_class:
            text = text.replace(
                "VECTORSTORE_CLASSES = {", "VECTORSTORE_CLASSES = {\n    " + f'"{directory}": "{class_name}",', 1
            )

        # The directory exists, and there are multiple instrumented classes in it.  Append to the list.
        elif isinstance(instrumented_class, list):
            original_list = str(instrumented_class).replace("'", '"')
            instrumented_class.append(class_name)
            instrumented_class = str(instrumented_class).replace("'", '"')
            text = text.replace(
                f'"{directory}": {original_list}',
                f'"{directory}": {instrumented_class}',  # TODO: NOT WORKING
            )

        # The directory exists, but it only has one class.  We need to convert this to a list.
        else:
            text = text.replace(f'"{instrumented_class}"', f'["{instrumented_class}", "{class_name}"]', 1)

        file.seek(0)
        file.write(text)


def main():
    _test_vectorstore_modules_instrumented_ignored_classes = set(
        [
            "VectorStore",  # Base class
            "Zilliz",  # Inherited from Milvus, which we are already instrumenting.
        ]
    )

    vector_store_class_directory = vectorstores._module_lookup
    for class_name, directory in vector_store_class_directory.items():
        class_ = getattr(vectorstores, class_name)
        instrumented_class = VECTORSTORE_CLASSES.get(directory, None)

        if (
            not hasattr(class_, "similarity_search")
            or class_name in _test_vectorstore_modules_instrumented_ignored_classes
        ):
            continue

        if not instrumented_class or class_name not in instrumented_class:
            if class_name in vector_store_class_directory:
                uninstrumented_directory = vector_store_class_directory[class_name]

                # Add in newrelic/config.py if there is not an instrumented directory
                # Otherwise, config already exists, so no need to duplicate it.
                add_to_config(uninstrumented_directory, instrumented_class)

                # Add in newrelic/hooks/mlmodel_langchain.py
                add_to_hooks(class_name, uninstrumented_directory, instrumented_class)


if __name__ == "__main__":
    main()
