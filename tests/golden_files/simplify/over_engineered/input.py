"""Over-engineered code sample for simplification testing.

This file deliberately contains patterns that Claude tends
to produce when over-engineering: unnecessary abstraction,
deep nesting, trivial helpers, dead code, and a factory
pattern for a single use case.
"""

# --- Unnecessary base class for a single implementation ---


class BaseProcessor:
    """Abstract base for processors (only one subclass exists)."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self._initialized = False

    def initialize(self) -> None:
        self._initialized = True

    def process(self, data: list) -> list:
        raise NotImplementedError


class DataProcessor(BaseProcessor):
    """The only processor. Base class is unnecessary."""

    def process(self, data: list) -> list:
        if not self._initialized:
            self.initialize()
        return [self._transform(item) for item in data]

    def _transform(self, item: dict) -> dict:
        return {**item, "processed": True}


# --- Deeply nested conditional logic ---


def validate_and_process(data, options, context):
    """Validate input with 6 levels of nesting."""
    result = None
    if data is not None:
        if isinstance(data, dict):
            if "items" in data:
                if len(data["items"]) > 0:
                    if options is not None:
                        if options.get("validate", False) == True:  # noqa: E712
                            items = data["items"]
                            validated = []
                            for item in items:
                                if item is not None:
                                    if isinstance(item, dict):
                                        if "id" in item:
                                            validated.append(item)
                            result = validated
    return result


# --- Trivial helpers that should be inlined ---


def _is_not_none(value):
    """Check if value is not None."""
    return value is not None


def _is_positive(number):
    """Check if number is positive."""
    return number > 0


def _get_or_default(dictionary, key, default=None):
    """Get value from dict with default."""
    return dictionary.get(key, default)


def compute_score(data):
    """Uses trivial helpers that should be inlined."""
    if _is_not_none(data):
        value = _get_or_default(data, "score", 0)
        if _is_positive(value):
            return value * 2
    return 0


# --- Dead code ---


def _unused_helper():
    """This function is never called anywhere."""
    return "dead code"


def _also_unused(x, y):
    """Another dead function."""
    return x + y


# --- Factory pattern for a single type ---


class ItemFactory:
    """Factory that only creates one type of item."""

    _registry = {}

    @classmethod
    def register(cls, item_type, creator):
        cls._registry[item_type] = creator

    @classmethod
    def create(cls, item_type, **kwargs):
        creator = cls._registry.get(item_type)
        if creator is None:
            raise ValueError(f"Unknown type: {item_type}")
        return creator(**kwargs)


def _create_basic_item(**kwargs):
    return {"type": "basic", **kwargs}


# Only one type is ever registered
ItemFactory.register("basic", _create_basic_item)
