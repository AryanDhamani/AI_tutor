from manim import *

class SimpleTest(Scene):
    def construct(self):
        title = Text("Simple Test").scale(1.2).to_edge(UP)
        self.play(Write(title))
        self.wait(1)
        
        circle = Circle(radius=1, color=BLUE)
        self.play(Create(circle))
        self.wait(1)
        
        square = Square(side_length=2, color=RED)
        self.play(Transform(circle, square))
        self.wait(2)