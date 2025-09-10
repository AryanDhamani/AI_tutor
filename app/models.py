"""
Pydantic models for API request/response contracts.
These mirror the frontend Zod types for exact 1:1 compatibility.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# Response Models (what backend sends to frontend)

class ExplanationData(BaseModel):
    """Lesson explanation data structure."""
    title: str = Field(..., description="Lesson title")
    bullets: List[str] = Field(..., description="List of 4-7 concise bullet points")


class LessonResponse(BaseModel):
    """Response for lesson generation endpoint."""
    explanation: ExplanationData


class ExampleData(BaseModel):
    """Example problem data structure."""
    prompt: str = Field(..., description="The problem statement")
    walkthrough: List[str] = Field(..., description="3-7 step-by-step solution steps")
    answer: Optional[str] = Field(None, description="Final answer (optional)")


class ExampleResponse(BaseModel):
    """Response for example generation endpoint."""
    example: ExampleData


class ManimData(BaseModel):
    """Manim code data structure."""
    language: Literal["python"] = Field(default="python", description="Programming language")
    filename: str = Field(..., description="Safe filename for the animation")
    code: str = Field(..., description="Manim animation code (~40-80 lines)")
    notes: Optional[List[str]] = Field(None, description="Optional implementation notes")


class ManimResponse(BaseModel):
    """Response for manim code generation endpoint."""
    manim: ManimData


class RenderJob(BaseModel):
    """Render job status and information."""
    jobId: str = Field(..., description="Unique job identifier")
    status: Literal["queued", "rendering", "ready", "error"] = Field(..., description="Current job status")
    videoUrl: Optional[str] = Field(None, description="URL to rendered video (when ready)")
    error: Optional[str] = Field(None, description="Error message (if status is error)")


# Request Models (what frontend sends to backend)

class LessonRequest(BaseModel):
    """Request for lesson generation."""
    topic: str = Field(..., min_length=3, max_length=120, description="Educational topic")
    plan: Optional[str] = Field(None, description="Optional lesson plan guidance")


class ExampleRequest(BaseModel):
    """Request for example generation."""
    topic: str = Field(..., min_length=3, max_length=120, description="Educational topic")
    explanation: ExplanationData = Field(..., description="Previous lesson explanation for context")


class ManimRequest(BaseModel):
    """Request for manim code generation."""
    topic: str = Field(..., min_length=3, max_length=120, description="Educational topic")
    example: ExampleData = Field(..., description="Previous example for animation context")


class RenderRequest(BaseModel):
    """Request to render animation."""
    filename: str = Field(..., min_length=1, max_length=50, description="Safe filename for output")
    code: str = Field(..., min_length=10, max_length=5000, description="Manim code to render")


# Error Response Models

class ErrorDetail(BaseModel):
    """Individual error detail."""
    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")


class ErrorResponse(BaseModel):
    """Standard error response format."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[List[ErrorDetail]] = Field(None, description="Detailed error information")
    timestamp: str = Field(..., description="ISO timestamp of error")


# Utility Models for Internal Use

class JobStore(BaseModel):
    """Internal job storage model."""
    id: str
    status: Literal["queued", "rendering", "ready", "error"]
    filename: str
    code: str
    created_at: str
    updated_at: str
    video_path: Optional[str] = None
    error_message: Optional[str] = None


# Example instances for documentation
EXAMPLE_LESSON_RESPONSE = LessonResponse(
    explanation=ExplanationData(
        title="Pythagorean Theorem",
        bullets=[
            "States that in a right triangle, a² + b² = c²",
            "c is the hypotenuse (longest side opposite the right angle)",
            "a and b are the two shorter sides (legs)",
            "Used to find unknown side lengths in right triangles",
            "Fundamental principle in geometry and trigonometry"
        ]
    )
)

EXAMPLE_EXAMPLE_RESPONSE = ExampleResponse(
    example=ExampleData(
        prompt="Find the length of the hypotenuse in a right triangle with legs of 3 and 4 units.",
        walkthrough=[
            "Identify the given information: legs a = 3, b = 4",
            "Apply Pythagorean theorem: a² + b² = c²",
            "Substitute values: 3² + 4² = c²",
            "Calculate: 9 + 16 = c²",
            "Simplify: 25 = c²",
            "Take square root: c = √25 = 5"
        ],
        answer="5 units"
    )
)

EXAMPLE_MANIM_RESPONSE = ManimResponse(
    manim=ManimData(
        language="python",
        filename="pythagorean_theorem",
        code="""from manim import *

class PythagoreanTheorem(Scene):
    def construct(self):
        # Create right triangle
        triangle = Polygon(
            [0, 0, 0], [3, 0, 0], [3, 4, 0],
            stroke_color=WHITE, fill_opacity=0.1
        )
        
        # Labels for sides
        a_label = MathTex("a = 3").next_to(triangle, DOWN)
        b_label = MathTex("b = 4").next_to(triangle, RIGHT)
        c_label = MathTex("c = ?").next_to(triangle, UP + LEFT)
        
        self.play(Create(triangle))
        self.play(Write(a_label), Write(b_label), Write(c_label))
        self.wait(1)
        
        # Show theorem
        theorem = MathTex("a^2 + b^2 = c^2").to_edge(UP)
        self.play(Write(theorem))
        self.wait(2)""",
        notes=["Uses simple geometric shapes", "Includes clear labeling", "Demonstrates the relationship visually"]
    )
)

