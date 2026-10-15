
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class TopicWeight(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    weight: float = Field(ge=0, le=100)


class PaperConfig(BaseModel):
    subject: Literal["maths", "science"]
    total_marks: int = Field(ge=1, le=500)

    difficulty: dict[str, float]
    question_types: dict[str, float]
    topics: list[TopicWeight] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_percentages(self):
        if set(self.difficulty) != {"easy", "medium", "hard"}:
            raise ValueError(
                "Difficulty must contain easy, medium and hard."
            )

        expected_types = {"mcq", "short_answer", "long_answer"}
        if set(self.question_types) != expected_types:
            raise ValueError(
                "Question types must contain mcq, short_answer and long_answer."
            )

        for label, values in [
            ("Difficulty", self.difficulty.values()),
            ("Question types", self.question_types.values()),
        ]:
            values = list(values)
            if any(not 0 <= value <= 100 for value in values):
                raise ValueError(f"{label} values must be between 0 and 100.")

            if abs(sum(values) - 100) > 1e-6:
                raise ValueError(f"{label} percentages must total 100.")

        names = [topic.name.strip().casefold() for topic in self.topics]

        if any(not name for name in names):
            raise ValueError("Topic names cannot be blank.")

        if len(names) != len(set(names)):
            raise ValueError("Topic names must be unique.")

        if abs(sum(t.weight for t in self.topics) - 100) > 1e-6:
            raise ValueError("Topic weights must total 100.")

        return self


class SwapRequest(BaseModel):
    subject: Literal["maths", "science"]
    question_id: str
    config: PaperConfig
    paper: dict
