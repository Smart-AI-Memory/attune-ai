"""Document generation pipeline.

Three-stage pipeline for generating documentation from source
code: outline, write, review. Requires the ``[ai]`` extra
(``pip install 'attune-author[ai]'``).

Usage:

    from attune_author.doc_gen import generate_docs

    result = generate_docs("src/mymodule.py")
    print(result.content)
"""

from attune_author.doc_gen.config import DocGenConfig
from attune_author.doc_gen.pipeline import DocGenResult, generate_docs

__all__ = [
    "DocGenConfig",
    "DocGenResult",
    "generate_docs",
]
