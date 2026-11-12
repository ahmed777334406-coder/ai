# Experimental evaluation

The evaluation script compares text-only, image-only and hybrid ranking over the seeded synthetic dataset. It also records English-to-Chinese retrieval for known synthetic pairs. It saves JSON, CSV and an MRR comparison chart under this directory.

The current offline run used:

- `bilingual_rule_hash_fallback` for text, because multilingual E5 weights were not available in the environment.
- `opencv_hsv_histogram_fallback` for image vectors, because OpenCLIP weights were not available in the environment.

The synthetic dataset contains four LOST reports and five FOUND reports, with three known positive pairs and one explicit negative backpack pair. The current metrics are in `evaluation_results.json`. They are descriptive results for this tiny synthetic set, not evidence of real-world performance. A top-five result contains all five found candidates in this dataset, so Recall@5 is not a useful standalone measure here. A larger held-out dataset with more hard negatives is needed for meaningful evaluation.

For the final experiment, install `requirements-ai.txt`, configure Gemini, download E5/OpenCLIP weights, rerun the evaluation and report the exact model methods and latency. Keep the fallback and pretrained-model results in separate tables.
