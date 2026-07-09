# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT


import pytest

from api_common.exceptions import ExternalServiceError, ForbiddenException, NotFoundException, ValidationException
from app.custom_models.constants import HF_API_BASE
from app.custom_models.enums import OnboardPhase
from app.custom_models.schemas import WeightFile
from app.custom_models.utils import (
    _assign_weight_roles,
    _extract_revision,
    _get_file_extension,
    build_description,
    build_display_name,
    classify_siblings,
    get_layout_hint,
    hub_request_args,
    normalize_hf_source,
    raise_for_hub_status,
    resolve_onboard_phase,
    validate_hf_repo_id,
)


def test_extract_revision_no_marker_returns_segments_unchanged() -> None:
    segments, revision = _extract_revision(["meta-llama", "Meta-Llama-3-8B"])
    assert segments == ["meta-llama", "Meta-Llama-3-8B"]
    assert revision is None


def test_extract_revision_empty_segments() -> None:
    segments, revision = _extract_revision([])
    assert segments == []
    assert revision is None


def test_extract_revision_tree_with_revision() -> None:
    segments, revision = _extract_revision(["owner", "model", "tree", "v1.0"])
    assert segments == ["owner", "model"]
    assert revision == "v1.0"


def test_extract_revision_blob_with_revision() -> None:
    segments, revision = _extract_revision(["owner", "model", "blob", "main"])
    assert segments == ["owner", "model"]
    assert revision == "main"


def test_extract_revision_blob_with_revision_and_trailing_filepath() -> None:
    """``/owner/model/blob/<rev>/path/to/file`` — segments after the revision
    are dropped along with the marker tail."""
    segments, revision = _extract_revision(["owner", "model", "blob", "abc123", "path", "to", "file.txt"])
    assert segments == ["owner", "model"]
    assert revision == "abc123"


def test_extract_revision_resolve_with_revision_and_trailing_filepath() -> None:
    """``/owner/model/resolve/<rev>/file.safetensors`` — the raw-download form
    that CLI tools paste; the trailing filename is dropped just like blob."""
    segments, revision = _extract_revision(["owner", "model", "resolve", "main", "model.safetensors"])
    assert segments == ["owner", "model"]
    assert revision == "main"


def test_extract_revision_tree_marker_at_end_with_no_value() -> None:
    segments, revision = _extract_revision(["owner", "model", "tree"])
    assert segments == ["owner", "model"]
    assert revision is None


def test_extract_revision_blob_marker_at_end_with_no_value() -> None:
    segments, revision = _extract_revision(["owner", "model", "blob"])
    assert segments == ["owner", "model"]
    assert revision is None


def test_extract_revision_first_marker_wins() -> None:
    """When both markers appear the first one wins; anything after the first
    revision is treated as the discarded tail."""
    segments, revision = _extract_revision(["owner", "model", "tree", "main", "blob", "other"])
    assert segments == ["owner", "model"]
    assert revision == "main"


def test_extract_revision_marker_word_in_owner_position_is_not_a_marker() -> None:
    """When a marker word appears at index 0 it is the owner part of the
    repo id, not a revision introducer; the function must leave it intact."""
    segments, revision = _extract_revision(["tree", "model"])
    assert segments == ["tree", "model"]
    assert revision is None


def test_extract_revision_marker_word_in_model_position_is_not_a_marker() -> None:
    """When a marker word appears at index 1 it is the model part of the
    repo id, not a revision introducer."""
    segments, revision = _extract_revision(["org", "resolve"])
    assert segments == ["org", "resolve"]
    assert revision is None


def test_extract_revision_marker_only_recognised_after_owner_model_pair() -> None:
    """``["owner", "model", "tree", "v1"]`` is a valid /tree/<rev> URL; the
    marker is at index 2 (after owner+model) and must be honoured."""
    segments, revision = _extract_revision(["owner", "model", "tree", "v1"])
    assert segments == ["owner", "model"]
    assert revision == "v1"


def test_extract_revision_marker_at_index_1_with_url_shape_is_ignored() -> None:
    """``["org", "blob", "tree", "rev"]`` — the ``blob`` at index 1 is part
    of the repo id (model name), only the ``tree`` at index 2 introduces
    the revision."""
    segments, revision = _extract_revision(["org", "blob", "tree", "rev"])
    assert segments == ["org", "blob"]
    assert revision == "rev"


def test_normalize_hf_source_bare_repo_id() -> None:
    repo_id, revision = normalize_hf_source("meta-llama/Meta-Llama-3-8B-Instruct")
    assert repo_id == "meta-llama/Meta-Llama-3-8B-Instruct"
    assert revision is None


def test_normalize_hf_source_full_url() -> None:
    repo_id, revision = normalize_hf_source("https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct")
    assert repo_id == "meta-llama/Meta-Llama-3-8B-Instruct"
    assert revision is None


def test_normalize_hf_source_url_with_tree_segment() -> None:
    repo_id, revision = normalize_hf_source("https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct/tree/main")
    assert repo_id == "meta-llama/Meta-Llama-3-8B-Instruct"
    assert revision == "main"


def test_normalize_hf_source_url_with_tree_segment_percent_encoded_slash_revision() -> None:
    repo_id, revision = normalize_hf_source(
        "https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct/tree/release%2Fv1"
    )
    assert repo_id == "meta-llama/Meta-Llama-3-8B-Instruct"
    assert revision == "release/v1"


def test_normalize_hf_source_url_with_blob_segment() -> None:
    repo_id, revision = normalize_hf_source(
        "https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct/blob/v1.0/config.json"
    )
    assert repo_id == "meta-llama/Meta-Llama-3-8B-Instruct"
    assert revision == "v1.0"


def test_normalize_hf_source_url_with_blob_segment_percent_encoded_slash_revision() -> None:
    repo_id, revision = normalize_hf_source(
        "https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct/blob/release%2Fv1/config.json"
    )
    assert repo_id == "meta-llama/Meta-Llama-3-8B-Instruct"
    assert revision == "release/v1"


def test_normalize_hf_source_url_with_resolve_segment() -> None:
    """``/resolve/<rev>/...`` URLs are the raw-download form that CLI tools
    and wget-style instructions paste; they must resolve like ``/blob/``."""
    repo_id, revision = normalize_hf_source(
        "https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct/resolve/main/model.safetensors"
    )
    assert repo_id == "meta-llama/Meta-Llama-3-8B-Instruct"
    assert revision == "main"


def test_normalize_hf_source_url_with_resolve_segment_percent_encoded_slash_revision() -> None:
    repo_id, revision = normalize_hf_source(
        "https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct/resolve/release%2Fv1/model.safetensors"
    )
    assert repo_id == "meta-llama/Meta-Llama-3-8B-Instruct"
    assert revision == "release/v1"


def test_normalize_hf_source_url_with_sha_revision() -> None:
    sha = "abc123def456"
    repo_id, revision = normalize_hf_source(f"https://huggingface.co/org/model/tree/{sha}")
    assert repo_id == "org/model"
    assert revision == sha


def test_normalize_hf_source_strips_leading_slash_from_url_path() -> None:
    repo_id, _ = normalize_hf_source("https://huggingface.co/org/model")
    assert repo_id == "org/model"


def test_normalize_hf_source_url_with_trailing_slash() -> None:
    repo_id, revision = normalize_hf_source("https://huggingface.co/org/model/")
    assert repo_id == "org/model"
    assert revision is None


def test_normalize_hf_source_bare_repo_id_with_marker_word_as_owner() -> None:
    """A repo id whose owner is literally one of the URL marker words
    (``tree``/``blob``/``resolve``) must not be misparsed; ``tree/model`` is
    a valid HF repo id, not a ``/tree/<rev>`` URL."""
    repo_id, revision = normalize_hf_source("tree/model")
    assert repo_id == "tree/model"
    assert revision is None


def test_normalize_hf_source_bare_repo_id_with_marker_word_as_model() -> None:
    """A repo id whose model is literally one of the URL marker words must
    not be misparsed."""
    repo_id, revision = normalize_hf_source("org/blob")
    assert repo_id == "org/blob"
    assert revision is None


def test_normalize_hf_source_bare_repo_id_named_resolve() -> None:
    repo_id, revision = normalize_hf_source("org/resolve")
    assert repo_id == "org/resolve"
    assert revision is None


def test_normalize_hf_source_url_with_marker_word_owner_no_revision() -> None:
    """``https://huggingface.co/tree/model`` — owner is literally ``tree``."""
    repo_id, revision = normalize_hf_source("https://huggingface.co/tree/model")
    assert repo_id == "tree/model"
    assert revision is None


def test_normalize_hf_source_url_with_marker_word_owner_and_real_revision() -> None:
    """``https://huggingface.co/tree/model/tree/main`` — the first ``tree`` is
    the owner, the second introduces revision ``main``."""
    repo_id, revision = normalize_hf_source("https://huggingface.co/tree/model/tree/main")
    assert repo_id == "tree/model"
    assert revision == "main"


def test_normalize_hf_source_url_with_marker_word_model_and_real_revision() -> None:
    """``https://huggingface.co/org/blob/resolve/main/file`` — ``blob`` is the
    model name, ``resolve`` introduces the revision, trailing path is dropped."""
    repo_id, revision = normalize_hf_source("https://huggingface.co/org/blob/resolve/main/file.safetensors")
    assert repo_id == "org/blob"
    assert revision == "main"


def test_normalize_hf_source_invalid_no_slash() -> None:
    with pytest.raises(ValidationException, match="Invalid Hugging Face source"):
        normalize_hf_source("justmodel")


def test_normalize_hf_source_invalid_empty_owner() -> None:
    with pytest.raises(ValidationException, match="Invalid Hugging Face source"):
        normalize_hf_source("/model")


def test_normalize_hf_source_invalid_empty_string() -> None:
    with pytest.raises(ValidationException, match="Invalid Hugging Face source"):
        normalize_hf_source("")


def test_normalize_hf_source_invalid_with_extra_path_segments() -> None:
    with pytest.raises(ValidationException, match="Invalid Hugging Face source"):
        normalize_hf_source("org/model/extra/path")


def test_validate_hf_repo_id_accepts_canonical_bare_id() -> None:
    """The canonical 'owner/model' form returned by preview must pass."""
    validate_hf_repo_id("meta-llama/Meta-Llama-3-8B-Instruct")


def test_validate_hf_repo_id_accepts_dotted_and_underscored_parts() -> None:
    """HF allows '.', '_', '-' in repo parts; the validator must permit them."""
    validate_hf_repo_id("org.name/model_name-v2.0")


def test_validate_hf_repo_id_rejects_missing_slash() -> None:
    with pytest.raises(ValidationException, match="not a valid Hugging Face repo id"):
        validate_hf_repo_id("justmodel")


def test_validate_hf_repo_id_rejects_extra_segments() -> None:
    with pytest.raises(ValidationException, match="not a valid Hugging Face repo id"):
        validate_hf_repo_id("owner/model/extra")


def test_validate_hf_repo_id_rejects_empty_segment() -> None:
    with pytest.raises(ValidationException, match="not a valid Hugging Face repo id"):
        validate_hf_repo_id("owner/")


def test_validate_hf_repo_id_rejects_disallowed_characters() -> None:
    """Slash already split the parts; spaces and '@' must fail the per-part pattern."""
    with pytest.raises(ValidationException, match="not a valid Hugging Face repo id"):
        validate_hf_repo_id("owner/model name")
    with pytest.raises(ValidationException, match="not a valid Hugging Face repo id"):
        validate_hf_repo_id("own@er/model")


def test_validate_hf_repo_id_rejects_empty_string() -> None:
    with pytest.raises(ValidationException, match="not a valid Hugging Face repo id"):
        validate_hf_repo_id("")


def test_validate_hf_repo_id_trims_surrounding_whitespace() -> None:
    """Whitespace-padded repo ids must validate just like preview accepts them
    via ``normalize_hf_source``'s ``strip()`` — otherwise minor UI/transport
    whitespace produces a surprising 400 at the onboard boundary."""
    validate_hf_repo_id("  meta-llama/Meta-Llama-3-8B-Instruct  ")
    validate_hf_repo_id("\tmeta-llama/Meta-Llama-3-8B-Instruct\n")


def test_normalize_hf_source_invalid_non_hf_host() -> None:
    with pytest.raises(ValidationException, match="Only huggingface.co URLs"):
        normalize_hf_source("https://example.com/org/model")


def test_normalize_hf_source_invalid_file_scheme() -> None:
    with pytest.raises(ValidationException, match="http\\(s\\)://huggingface.co"):
        normalize_hf_source("file:///org/model")


def test_normalize_hf_source_invalid_mailto_scheme() -> None:
    with pytest.raises(ValidationException, match="http\\(s\\)://huggingface.co"):
        normalize_hf_source("mailto:org/model")


def test_normalize_hf_source_invalid_ftp_scheme_even_with_hf_host() -> None:
    with pytest.raises(ValidationException, match="http\\(s\\)://huggingface.co"):
        normalize_hf_source("ftp://huggingface.co/org/model")


def test_normalize_hf_source_invalid_http_without_netloc() -> None:
    with pytest.raises(ValidationException, match="must include 'huggingface.co'"):
        normalize_hf_source("http:///org/model")


def test_normalize_hf_source_invalid_protocol_relative_wrong_host() -> None:
    """Protocol-relative URLs are out of contract regardless of host; the
    short-circuit on ``//host/...`` fires before the host allowlist."""
    with pytest.raises(ValidationException, match="http\\(s\\)://huggingface.co"):
        normalize_hf_source("//example.com/org/model")


def test_normalize_hf_source_invalid_protocol_relative_even_with_hf_host() -> None:
    """``//huggingface.co/org/model`` parses with a non-empty netloc but no
    scheme. The contract is "bare repo id" or "http(s)://huggingface.co/..."
    so this form must be rejected, not silently accepted as a URL."""
    with pytest.raises(ValidationException, match="http\\(s\\)://huggingface.co"):
        normalize_hf_source("//huggingface.co/org/model")


def test_normalize_hf_source_invalid_disallowed_chars_in_repo_id() -> None:
    with pytest.raises(ValidationException, match="may only contain"):
        normalize_hf_source("org/mo del")


def test_normalize_hf_source_invalid_path_traversal_segments() -> None:
    """Multi-segment ``..`` paths are blocked by the segment-count check."""
    with pytest.raises(ValidationException, match="Invalid Hugging Face source"):
        normalize_hf_source("../etc/passwd")


def test_normalize_hf_source_invalid_dot_dot_part() -> None:
    """``org/..`` has the right shape but the regex blocks pure-dot parts."""
    with pytest.raises(ValidationException, match="may only contain"):
        normalize_hf_source("org/..")


def test_get_file_extension_simple_safetensors() -> None:
    assert _get_file_extension("model.safetensors") == ".safetensors"


def test_get_file_extension_compound_returns_only_final_extension() -> None:
    """Function returns only the trailing dot-extension. Compound suffixes
    such as ``.safetensors.index.json`` must be matched via the full filename
    (see ``_INDEX_PATTERN``), not via this helper."""
    assert _get_file_extension("model.safetensors.index.json") == ".json"


def test_get_file_extension_uppercase_is_normalized_to_lowercase() -> None:
    assert _get_file_extension("MODEL.GGUF") == ".gguf"


def test_get_file_extension_no_dot_returns_empty_string() -> None:
    assert _get_file_extension("README") == ""


def test_get_file_extension_empty_string_returns_empty() -> None:
    assert _get_file_extension("") == ""


def test_get_file_extension_nested_path_uses_last_segment_extension() -> None:
    assert _get_file_extension("subdir/nested/file.bin") == ".bin"


def test_get_file_extension_dotfile_returns_full_name() -> None:
    """A leading-dot filename (no other dots) returns the entire name; this is
    fine because dotfiles never have weight or config extensions and so fall
    through to the unknown-file path in ``classify_siblings``."""
    assert _get_file_extension(".gitignore") == ".gitignore"


_SAFETENSORS_SIBLINGS = [
    {"rfilename": "model-00001-of-00002.safetensors", "lfs": {"size": 4_000_000_000}},
    {"rfilename": "model-00002-of-00002.safetensors", "lfs": {"size": 4_000_000_000}},
    {"rfilename": "model.safetensors.index.json", "size": 1024},
    {"rfilename": "config.json", "size": 820},
    {"rfilename": "tokenizer.json", "size": 2048},
    {"rfilename": "tokenizer_config.json", "size": 512},
]

_GGUF_SIBLINGS = [
    {"rfilename": "model.Q4_K_M.gguf", "lfs": {"size": 4_200_000_000}},
    {"rfilename": "model.Q8_0.gguf", "lfs": {"size": 8_100_000_000}},
    {"rfilename": "README.md", "size": 3000},
]

_SINGLE_SAFETENSORS_SIBLINGS = [
    {"rfilename": "model.safetensors", "lfs": {"size": 500_000_000}},
    {"rfilename": "config.json", "size": 512},
]

_BIN_AND_SAFETENSORS_SIBLINGS = [
    {"rfilename": "pytorch_model-00001-of-00002.bin", "lfs": {"size": 4_000_000_000}},
    {"rfilename": "pytorch_model-00002-of-00002.bin", "lfs": {"size": 4_000_000_000}},
    {"rfilename": "model-00001-of-00002.safetensors", "lfs": {"size": 4_000_000_000}},
    {"rfilename": "model-00002-of-00002.safetensors", "lfs": {"size": 4_000_000_000}},
    {"rfilename": "config.json", "size": 512},
]


def test_classify_siblings_multiple_safetensors_are_shards() -> None:
    files = classify_siblings(_SAFETENSORS_SIBLINGS)
    weight_files = [f for f in files if f.role != "config"]
    assert len(weight_files) == 2
    assert all(f.role == "shard" for f in weight_files)


def test_classify_siblings_safetensors_index_json_is_skipped() -> None:
    """The HF safetensors shard manifest (``<basename>.safetensors.index.json``)
    is metadata about the shards, not a weight file, and must not appear in
    the classified output."""
    files = classify_siblings(_SAFETENSORS_SIBLINGS)
    paths = [f.path for f in files]
    assert "model.safetensors.index.json" not in paths


def test_classify_siblings_generic_index_json_is_not_skipped() -> None:
    """A generic ``*.index.json`` file (not ``.safetensors.index.json``) is
    metadata to the model author and must fall through to the config-files
    path rather than being silently dropped."""
    files = classify_siblings(
        [
            {"rfilename": "model.safetensors", "lfs": {"size": 1}},
            {"rfilename": "something.index.json", "size": 42},
        ]
    )
    paths = {f.path: f.role for f in files}
    assert paths["something.index.json"] == "config"


def test_classify_siblings_config_files_get_config_role() -> None:
    files = classify_siblings(_SAFETENSORS_SIBLINGS)
    config_files = [f for f in files if f.role == "config"]
    config_paths = {f.path for f in config_files}
    assert "config.json" in config_paths
    assert "tokenizer.json" in config_paths


def test_classify_siblings_markdown_files_get_config_role() -> None:
    files = classify_siblings([{"rfilename": "README.md", "size": 3000}])
    assert len(files) == 1
    assert files[0].path == "README.md"
    assert files[0].role == "config"


def test_classify_siblings_single_safetensors_is_primary() -> None:
    files = classify_siblings(_SINGLE_SAFETENSORS_SIBLINGS)
    weight_files = [f for f in files if f.role != "config"]
    assert len(weight_files) == 1
    assert weight_files[0].role == "primary"


def test_classify_siblings_multiple_gguf_are_shards() -> None:
    files = classify_siblings(_GGUF_SIBLINGS)
    weight_files = [f for f in files if f.role != "config"]
    assert len(weight_files) == 2
    assert all(f.role == "shard" for f in weight_files)


def test_classify_siblings_size_bytes_from_lfs() -> None:
    files = classify_siblings([{"rfilename": "model.safetensors", "lfs": {"size": 1234}}])
    assert files[0].size_bytes == 1234


def test_classify_siblings_size_bytes_fallback_to_toplevel() -> None:
    files = classify_siblings([{"rfilename": "config.json", "size": 512}])
    assert files[0].size_bytes == 512


def test_classify_siblings_size_zero_is_preserved_at_lfs() -> None:
    """A legitimate size of 0 in ``lfs.size`` must be preserved, not treated
    as missing."""
    files = classify_siblings([{"rfilename": "model.safetensors", "lfs": {"size": 0}, "size": 99}])
    assert files[0].size_bytes == 0


def test_classify_siblings_size_zero_is_preserved_at_top_level() -> None:
    """Top-level ``size=0`` must be preserved when ``lfs.size`` is absent."""
    files = classify_siblings([{"rfilename": "config.json", "size": 0}])
    assert files[0].size_bytes == 0


def test_classify_siblings_size_bytes_missing_returns_none() -> None:
    """Neither ``lfs.size`` nor top-level ``size`` present → ``size_bytes`` is None."""
    files = classify_siblings([{"rfilename": "config.json"}])
    assert files[0].size_bytes is None


def test_classify_siblings_prefers_lfs_size_over_top_level_size() -> None:
    """When both fields are present ``lfs.size`` wins — top-level ``size`` on
    LFS-tracked files is the pointer-file size, not the real blob size."""
    files = classify_siblings([{"rfilename": "model.safetensors", "lfs": {"size": 4_000_000_000}, "size": 134}])
    assert files[0].size_bytes == 4_000_000_000


def test_classify_siblings_empty_siblings_returns_empty() -> None:
    assert classify_siblings([]) == []


def test_classify_siblings_bin_files_are_ignored_only_safetensors_classified() -> None:
    files = classify_siblings(_BIN_AND_SAFETENSORS_SIBLINGS)
    weight_files = [f for f in files if f.role != "config"]
    paths = [f.path for f in weight_files]
    assert not any(".bin" in p for p in paths)
    assert any(".safetensors" in p for p in paths)


def test_classify_siblings_sibling_without_rfilename_is_skipped() -> None:
    """A sibling entry lacking ``rfilename`` is silently dropped rather than
    raising — the Hub schema is permissive enough that we tolerate the gap."""
    files = classify_siblings([{"size": 100}, {"rfilename": "config.json", "size": 200}])
    assert len(files) == 1
    assert files[0].path == "config.json"


def test_assign_weight_roles_single_safetensors_is_primary() -> None:
    files = [WeightFile(path="model.safetensors", size_bytes=1, role=None)]
    _assign_weight_roles(files)
    assert files[0].role == "primary"


def test_assign_weight_roles_multiple_safetensors_are_shards() -> None:
    files = [
        WeightFile(path="model-00001-of-00002.safetensors", size_bytes=1, role=None),
        WeightFile(path="model-00002-of-00002.safetensors", size_bytes=1, role=None),
    ]
    _assign_weight_roles(files)
    assert [f.role for f in files] == ["shard", "shard"]


def test_assign_weight_roles_single_gguf_is_primary() -> None:
    files = [WeightFile(path="model.Q4_K_M.gguf", size_bytes=1, role=None)]
    _assign_weight_roles(files)
    assert files[0].role == "primary"


def test_assign_weight_roles_multiple_gguf_are_shards() -> None:
    files = [
        WeightFile(path="model.Q4_K_M.gguf", size_bytes=1, role=None),
        WeightFile(path="model.Q8_0.gguf", size_bytes=1, role=None),
    ]
    _assign_weight_roles(files)
    assert [f.role for f in files] == ["shard", "shard"]


def test_assign_weight_roles_mixed_groups_are_assigned_independently() -> None:
    """A single safetensors with two gguf siblings: safetensors stays
    ``primary`` while both gguf files become ``shard`` — role assignment is
    per-format-group."""
    files = [
        WeightFile(path="model.safetensors", size_bytes=1, role=None),
        WeightFile(path="model.Q4_K_M.gguf", size_bytes=1, role=None),
        WeightFile(path="model.Q8_0.gguf", size_bytes=1, role=None),
    ]
    _assign_weight_roles(files)
    roles = {f.path: f.role for f in files}
    assert roles["model.safetensors"] == "primary"
    assert roles["model.Q4_K_M.gguf"] == "shard"
    assert roles["model.Q8_0.gguf"] == "shard"


def test_assign_weight_roles_empty_list_is_noop() -> None:
    files: list[WeightFile] = []
    _assign_weight_roles(files)
    assert files == []


def test_assign_weight_roles_non_weight_extensions_are_left_untouched() -> None:
    """The function only mutates entries whose extension is in the weight set;
    anything else (callers pre-filter, but be defensive) is left with its
    incoming role value."""
    files = [
        WeightFile(path="config.json", size_bytes=1, role="config"),
        WeightFile(path="model.safetensors", size_bytes=1, role=None),
    ]
    _assign_weight_roles(files)
    assert files[0].role == "config"
    assert files[1].role == "primary"


def test_get_layout_hint_safetensors() -> None:
    files = classify_siblings(_SAFETENSORS_SIBLINGS)
    weight_only = [f for f in files if f.role != "config"]
    assert get_layout_hint(weight_only) == "safetensors"


def test_get_layout_hint_gguf() -> None:
    files = classify_siblings(_GGUF_SIBLINGS)
    weight_only = [f for f in files if f.role != "config"]
    assert get_layout_hint(weight_only) == "gguf"


def test_get_layout_hint_mixed() -> None:
    mixed_siblings = [
        {"rfilename": "model.safetensors", "lfs": {"size": 1}},
        {"rfilename": "model.Q4_K_M.gguf", "lfs": {"size": 1}},
    ]
    files = classify_siblings(mixed_siblings)
    weight_only = [f for f in files if f.role != "config"]
    assert get_layout_hint(weight_only) == "mixed"


def test_get_layout_hint_bin_only_returns_no_hint() -> None:
    files = classify_siblings([{"rfilename": "pytorch_model.bin", "lfs": {"size": 1}}])
    assert get_layout_hint(files) is None


def test_get_layout_hint_no_weights_returns_none() -> None:
    assert get_layout_hint([]) is None


def test_get_layout_hint_ignores_config_entries() -> None:
    """``get_layout_hint`` is expected to be called on the weight-only subset,
    but if a config entry sneaks through it must not influence the hint."""
    files = [
        WeightFile(path="config.json", size_bytes=1, role="config"),
        WeightFile(path="model.safetensors", size_bytes=1, role="primary"),
    ]
    assert get_layout_hint(files) == "safetensors"


def test_hub_request_args_basic_returns_url_and_blobs_param() -> None:
    url, params, headers = hub_request_args("org/model", None, None)
    assert url == f"{HF_API_BASE}/org/model"
    assert params == {"blobs": "true"}
    assert headers == {}


def test_hub_request_args_with_revision_adds_revision_param() -> None:
    _url, params, _headers = hub_request_args("org/model", "v1.0", None)
    assert params == {"blobs": "true", "revision": "v1.0"}


def test_hub_request_args_with_token_sets_bearer_authorization() -> None:
    _url, _params, headers = hub_request_args("org/model", None, "hf_token_value")
    assert headers == {"Authorization": "Bearer hf_token_value"}


def test_hub_request_args_with_token_and_revision_both_applied() -> None:
    _url, params, headers = hub_request_args("org/model", "main", "hf_tok")
    assert params == {"blobs": "true", "revision": "main"}
    assert headers == {"Authorization": "Bearer hf_tok"}


def test_hub_request_args_empty_string_token_omits_authorization() -> None:
    """An empty-string token must not produce a ``Bearer `` header — that
    request would be auth-shaped but valueless and confuse the Hub."""
    _url, _params, headers = hub_request_args("org/model", None, "")
    assert "Authorization" not in headers


def test_raise_for_hub_status_200_is_noop() -> None:
    raise_for_hub_status(200, "org/model", None, None)


def test_raise_for_hub_status_401_with_token_says_invalid_or_expired() -> None:
    with pytest.raises(ForbiddenException) as exc_info:
        raise_for_hub_status(401, "org/model", None, "hf_tok")
    assert "invalid or expired" in str(exc_info.value)


def test_raise_for_hub_status_401_invalid_username_with_token_is_credential_error() -> None:
    """The Hub masks private/nonexistent repos behind "invalid username or
    password". When the caller supplied a token, that is a credential failure
    (403), not a misleading "model not found" (404) — the no-token branch keeps
    the not-found mapping."""
    with pytest.raises(ForbiddenException) as exc_info:
        raise_for_hub_status(401, "org/model", None, "hf_tok", b'{"error":"Invalid username or password."}')
    assert "invalid or expired" in str(exc_info.value)


def test_raise_for_hub_status_401_invalid_username_without_token_is_not_found() -> None:
    with pytest.raises(NotFoundException) as exc_info:
        raise_for_hub_status(401, "org/model", None, None, b'{"error":"Invalid username or password."}')
    assert "was not found on Hugging Face Hub" in str(exc_info.value)


def test_raise_for_hub_status_401_without_token_says_token_required() -> None:
    with pytest.raises(ForbiddenException) as exc_info:
        raise_for_hub_status(401, "org/model", None, None)
    assert "requires a Hugging Face token" in str(exc_info.value)


def test_raise_for_hub_status_403_with_token_says_no_access() -> None:
    with pytest.raises(ForbiddenException) as exc_info:
        raise_for_hub_status(403, "org/gated-model", None, "hf_tok")
    assert "does not have access" in str(exc_info.value)
    assert "org/gated-model" in str(exc_info.value)


def test_raise_for_hub_status_403_without_token_says_token_required() -> None:
    with pytest.raises(ForbiddenException) as exc_info:
        raise_for_hub_status(403, "org/gated-model", None, None)
    assert "requires a Hugging Face token" in str(exc_info.value)


def test_raise_for_hub_status_401_does_not_leak_token_value() -> None:
    with pytest.raises(ForbiddenException) as exc_info:
        raise_for_hub_status(401, "org/model", None, "hf_secret_value_xyz")
    assert "hf_secret_value_xyz" not in str(exc_info.value)


def test_raise_for_hub_status_403_does_not_leak_token_value() -> None:
    with pytest.raises(ForbiddenException) as exc_info:
        raise_for_hub_status(403, "org/model", None, "hf_secret_value_xyz")
    assert "hf_secret_value_xyz" not in str(exc_info.value)


def test_raise_for_hub_status_404_with_revision_mentions_revision() -> None:
    with pytest.raises(NotFoundException) as exc_info:
        raise_for_hub_status(404, "org/model", "v1.0", None)
    message = str(exc_info.value)
    assert "org/model" in message
    assert "v1.0" in message


def test_raise_for_hub_status_404_without_revision_omits_revision() -> None:
    with pytest.raises(NotFoundException) as exc_info:
        raise_for_hub_status(404, "org/model", None, None)
    message = str(exc_info.value)
    assert "org/model" in message
    assert "revision" not in message.lower()


def test_raise_for_hub_status_500_raises_external_service_error_with_status() -> None:
    with pytest.raises(ExternalServiceError) as exc_info:
        raise_for_hub_status(500, "org/model", None, None)
    assert "HTTP 500" in str(exc_info.value)


def test_raise_for_hub_status_503_raises_external_service_error_with_status() -> None:
    with pytest.raises(ExternalServiceError) as exc_info:
        raise_for_hub_status(503, "org/model", None, None)
    assert "HTTP 503" in str(exc_info.value)


def test_raise_for_hub_status_unexpected_status_raises_external_service_error() -> None:
    """Anything outside the explicit 401/403/404/5xx branches is surfaced as
    an ExternalServiceError with the actual status code so operators can
    diagnose unexpected upstream behaviour."""
    with pytest.raises(ExternalServiceError) as exc_info:
        raise_for_hub_status(418, "org/model", None, None)
    message = str(exc_info.value)
    assert "418" in message
    assert "Unexpected" in message


def test_build_display_name_uses_card_data_model_name_when_present() -> None:
    assert build_display_name({"cardData": {"model_name": "Pretty Name"}}, "org/raw-name") == "Pretty Name"


def test_build_display_name_falls_back_to_repo_id_last_segment() -> None:
    assert build_display_name({"cardData": {}}, "org/My-Cool-Model") == "My Cool Model"


def test_build_display_name_replaces_underscores_in_fallback() -> None:
    assert build_display_name({}, "org/my_cool_model") == "my cool model"


def test_build_display_name_handles_missing_card_data_key() -> None:
    """Hub payloads without ``cardData`` at all must still produce a name
    via the repo-id fallback."""
    assert build_display_name({}, "org/some-model") == "some model"


def test_build_display_name_handles_null_card_data() -> None:
    """``cardData: null`` shows up in Hub responses for models with no card;
    treat it like a missing key."""
    assert build_display_name({"cardData": None}, "org/some-model") == "some model"


def test_build_display_name_empty_model_name_falls_back() -> None:
    """An empty-string ``model_name`` is treated as missing and falls back to
    the repo-id derived form."""
    assert build_display_name({"cardData": {"model_name": ""}}, "org/some-model") == "some model"


def test_build_description_uses_card_data_description() -> None:
    assert build_description({"cardData": {"description": "A great model."}}) == "A great model."


def test_build_description_missing_card_data_returns_empty_string() -> None:
    assert build_description({}) == ""


def test_build_description_null_card_data_returns_empty_string() -> None:
    assert build_description({"cardData": None}) == ""


def test_build_description_missing_description_field_returns_empty_string() -> None:
    assert build_description({"cardData": {"model_name": "X"}}) == ""


def test_build_description_null_description_returns_empty_string() -> None:
    assert build_description({"cardData": {"description": None}}) == ""


# ---------------------------------------------------------------------------
# resolve_onboard_phase — state machine
# ---------------------------------------------------------------------------


def test_resolve_onboard_phase_ready_when_aim_ready_and_profile_ready() -> None:
    assert resolve_onboard_phase("Ready", profile_ready=True, artifact_phase=None) == OnboardPhase.READY


def test_resolve_onboard_phase_not_ready_when_aim_ready_but_profile_not_ready() -> None:
    """Profile not yet emitted: Ready AIMModel alone is not sufficient."""
    assert resolve_onboard_phase("Ready", profile_ready=False, artifact_phase=None) == OnboardPhase.PENDING


def test_resolve_onboard_phase_importing_gates_ready_model_and_profile() -> None:
    """An in-flight weight import gates readiness even when the AIMModel is
    Ready and a profile exists. aim-engine derives the profile from the base
    image, not from the presence of weights in S3, so it can mark the model
    Ready before the import finishes — but the model is not deployable until
    the weights land, so the composed state stays Importing."""
    assert resolve_onboard_phase("Ready", profile_ready=True, artifact_phase="Importing") == OnboardPhase.IMPORTING


def test_resolve_onboard_phase_ready_when_import_done_and_profile_ready() -> None:
    """Once the import is done (phase Ready) and the AIMModel is Ready with a
    profile, the composed state is Ready."""
    assert resolve_onboard_phase("Ready", profile_ready=True, artifact_phase="Ready") == OnboardPhase.READY


def test_resolve_onboard_phase_failed_when_aim_status_failed() -> None:
    assert resolve_onboard_phase("Failed", profile_ready=False, artifact_phase=None) == OnboardPhase.FAILED


def test_resolve_onboard_phase_failed_when_aim_status_error() -> None:
    """``Error`` is a second failure variant the engine emits; both must map to FAILED."""
    assert resolve_onboard_phase("Error", profile_ready=False, artifact_phase=None) == OnboardPhase.FAILED


def test_resolve_onboard_phase_failed_when_artifact_phase_failed() -> None:
    """A failed weight import surfaces as FAILED even when the AIMModel is
    still Progressing; the artifact failure is the definitive signal."""
    assert resolve_onboard_phase("Progressing", profile_ready=False, artifact_phase="Failed") == OnboardPhase.FAILED


def test_resolve_onboard_phase_importing_when_artifact_in_progress() -> None:
    assert (
        resolve_onboard_phase("Progressing", profile_ready=False, artifact_phase="Importing") == OnboardPhase.IMPORTING
    )


def test_resolve_onboard_phase_pending_when_no_artifact_and_no_profile() -> None:
    """Default holding state: CR exists, engine has not yet reconciled."""
    assert resolve_onboard_phase("Progressing", profile_ready=False, artifact_phase=None) == OnboardPhase.PENDING


def test_resolve_onboard_phase_pending_when_artifact_ready_but_aim_not_ready() -> None:
    """Artifact completed but AIMModel hasn't reached Ready + profile yet.
    This is the gap between import completion and aim-engine reconciliation."""
    assert resolve_onboard_phase("Progressing", profile_ready=False, artifact_phase="Ready") == OnboardPhase.PENDING


def test_resolve_onboard_phase_pending_when_aim_status_not_available() -> None:
    """NotAvailable is the initial AIMModel status before the engine first sees
    the CR; it should not be confused with a Ready or failure state."""
    assert resolve_onboard_phase("NotAvailable", profile_ready=False, artifact_phase=None) == OnboardPhase.PENDING
