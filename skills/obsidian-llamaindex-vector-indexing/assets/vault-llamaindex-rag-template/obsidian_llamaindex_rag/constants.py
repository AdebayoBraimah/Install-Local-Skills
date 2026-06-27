from __future__ import annotations

RAG_DIR_NAME = ".vault-llamaindex-rag"
GRAPH_RAG_DIR_NAME = ".vault-graphrag"
CONDA_ENV_NAME = "obsidian-rag"
COLLECTION_NAME = "obsidian_llamaindex_vault"
MANIFEST_NAME = "llama_index_manifest.json"
CONFIG_NAME = "config.yaml"

FRONTMATTER_SCALAR_KEYS = (
    "Title",
    "Medium",
    "Category",
    "Date Created",
    "Time Created",
)
FRONTMATTER_LIST_KEYS = ("tags", "Keywords")

DEFAULT_INCLUDE_GLOBS = ["**/*.md"]

DEFAULT_EXCLUDE_GLOBS = [
    ".obsidian/**",
    ".git/**",
    f"{RAG_DIR_NAME}/**",
    f"{GRAPH_RAG_DIR_NAME}/**",
    ".trash/**",
    "**/.trash/**",
    "**/attachments/**",
    "Files/Images/**",
    "Files/Presentations/**",
    "**/*_exports/**",
    "**/*exports*/**",
    "**/node_modules/**",
    "**/.cache/**",
    "**/__pycache__/**",
    "**/*.pdf",
    "**/*.png",
    "**/*.jpg",
    "**/*.jpeg",
    "**/*.gif",
    "**/*.webp",
    "**/*.tif",
    "**/*.tiff",
    "**/*.bmp",
    "**/*.svg",
    "**/*.drawio",
    "**/*.excalidraw",
    "**/*.ppt",
    "**/*.pptx",
    "**/*.doc",
    "**/*.docx",
    "**/*.xls",
    "**/*.xlsx",
    "**/*.zip",
    "**/*.tar",
    "**/*.gz",
    "**/*.7z",
]

