"""
download_data.py

Downloads SPARQ datasets from HuggingFace Hub (zayanhugsAI) and writes a manifest
to DATA_MANIFEST_PATH (~/.config/sparq/data/data_manifest.json) mapping each dataset
name to its local cache location.

Called automatically by setup() on first run, or manually:
    uv run python -m sparq.utils.download_data

Requires HF_TOKEN to be set in .env or environment.

Docs:
- https://huggingface.co/docs/huggingface_hub/en/guides/download#download-an-entire-repository
- https://huggingface.co/docs/datasets/en/cache
- https://huggingface.co/docs/datasets/load_hub#configurations
"""


from huggingface_hub import snapshot_download
from sparq.utils.helpers import dump_dict_to_json

from sparq.settings import ENVSettings, DATA_MANIFEST_PATH

REPO_ID = "zayanhugsAI"
datasets = [
    "census_population",
    "naco",
    "nors",
    "pulsenet",
    # "socioecono_salmonella",
    "map_the_meal_gap",
    "social_vulnerability_index"
]

def download_dataset_repo(repo_id, dataset_name, token, output_dir=None):
    """
    Download a specific dataset from the Hugging Face Hub.
    
    Args:
        repo_id (str): The repository ID on Hugging Face Hub.
        dataset_name (str): The name of the dataset to download.
        token (str): The Hugging Face token for authentication.
        output_dir (str) [Optional]: The directory where the dataset will be saved. If
        output_dir is not provided, the dataset will be saved in the default cache directory
        and this is recommended
    
    Returns: Folder path where the dataset is downloaded.
    """
    path = snapshot_download(repo_id=f"{repo_id}/{dataset_name}", repo_type="dataset", local_dir=output_dir if output_dir is not None else None, token=token)
    return path

def main():
    """
    Main function to download all datasets.
    """
    HF_TOKEN = ENVSettings().hf_token
    print(f"Using Hugging Face token: {HF_TOKEN}")

    if HF_TOKEN is None:
        raise ValueError("HF_TOKEN is not set. Please add it to your .env file.")

    manifest = {}

    for dataset in datasets:
        print(f"Downloading dataset: {dataset}")
        cache_location = download_dataset_repo(REPO_ID, dataset, token=HF_TOKEN)
        print(f"Dataset {dataset} downloaded successfully.")

        manifest[dataset] = {
            "cache_location": cache_location,
            "repo_id": f"{REPO_ID}/{dataset}"
        }

    dump_dict_to_json(manifest, DATA_MANIFEST_PATH)

if __name__ == "__main__":
    main()
