from dataclasses import dataclass


@dataclass
class Usage:
    input_tokens: int  # all input, cached included
    cached_tokens: int
    output_tokens: int  # reasoning included
    cache_write_tokens: int = 0  # input written to the cache, for APIs that bill it separately


@dataclass
class Reply:
    """One model call's result, the same for every API. `output` holds Responses-API items for history."""

    model: str
    output: list[dict]
    usage: Usage

    @property
    def text(self) -> str:
        return "".join(
            part.get("text", "") for item in self.output if item.get("type") == "message" for part in item["content"]
        )
