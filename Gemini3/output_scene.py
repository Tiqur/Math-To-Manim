from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService

# Configuration for high-quality output
config.background_color = "#111111"

class MyScene(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GTTSService(lang="en"))

        # --- Scene 1: Concept Roadmap ---
        # Block 1: Title and Triangle
        title = Title(r"\text{The Pythagorean Theorem}", color=WHITE).to_edge(UP, buff=0.3)
        
        # Right Triangle Setup
        v_a = np.array([-1, -1, 0])
        v_b = np.array([2, -1, 0])
        v_c = np.array([2, 1, 0])
        
        tri = Polygon(v_a, v_b, v_c, color=WHITE)
        sq_marker = Rectangle(width=0.3, height=0.3, color="#94A3B8", stroke_width=2).move_to(v_b + LEFT*0.15 + UP*0.15)
        triangle_group = VGroup(tri, sq_marker).to_edge(RIGHT, buff=1.5).shift(UP*0.5)

        with self.voiceover(text="The Pythagorean Theorem is the foundation of geometry, relating the sides of a right triangle.") as tracker:
            self.play(Write(title))
            self.play(Create(tri), Create(sq_marker))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 2: Mastery Path Checklist
        checklist_box = RoundedRectangle(corner_radius=0.1, height=4, width=5, color=GREY_A).to_edge(LEFT, buff=1.0).shift(DOWN*0.5)
        item1 = Text("1. Identify the Right Angle", font_size=24).move_to(checklist_box.get_top() + DOWN*0.6)
        item2 = Text("2. Map the Sides", font_size=24, fill_opacity=0.3).next_to(item1, DOWN, buff=0.4, aligned_edge=LEFT)
        item3 = Text("3. Understanding Area", font_size=24, fill_opacity=0.3).next_to(item2, DOWN, buff=0.4, aligned_edge=LEFT)
        item4 = Text("4. Final Calculation", font_size=24, fill_opacity=0.3).next_to(item3, DOWN, buff=0.4, aligned_edge=LEFT)
        checklist = VGroup(item1, item2, item3, item4)

        with self.voiceover(text="To master it, we follow four steps: Identifying the angle, mapping sides, understanding area, and final calculation.") as tracker:
            self.play(FadeIn(checklist_box), FadeIn(checklist))
            self.play(item1.animate.scale(1.1).set_color(WHITE), rate_func=there_and_back)
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 3: Central Equation
        part_a = MathTex(r"a^2")
        plus = MathTex(r"+")
        part_b = MathTex(r"b^2")
        equals = MathTex(r"=")
        part_c = MathTex(r"c^2")
        main_eq = VGroup(part_a, plus, part_b, equals, part_c).arrange(RIGHT, buff=0.2).to_edge(DOWN, buff=1.0)

        with self.voiceover(text="This simple relationship allows us to solve for missing lengths in any right-angled space.") as tracker:
            self.play(Write(main_eq))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # --- Scene 2: Step 1 – The Right Angle ---
        # Block 4: Step 1 Title and Vectors
        new_title = Title(r"\text{Step 1: The Right Angle}", color=WHITE).to_edge(UP, buff=0.3)
        
        vec_u = Arrow(ORIGIN, RIGHT * 2, color=BLUE_B, buff=0)
        vec_v = Arrow(ORIGIN, rotate_vector(RIGHT * 2, 45 * DEGREES), color=GREEN_B, buff=0)
        vector_group = VGroup(vec_u, vec_v).move_to(triangle_group.get_center())

        with self.voiceover(text="First, the theorem only applies to right triangles.") as tracker:
            self.play(FadeOut(title), FadeIn(new_title), FadeOut(triangle_group), FadeOut(main_eq))
            self.play(Create(vector_group))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 5: Orthogonality
        with self.voiceover(text="This means two sides must be orthogonal, forming a 90-degree angle.") as tracker:
            self.play(Rotate(vec_v, angle=45 * DEGREES, about_point=vec_v.get_start()))
            new_sq_marker = Rectangle(width=0.3, height=0.3, color="#94A3B8", stroke_width=2).move_to(vec_u.get_start() + RIGHT*0.15 + UP*0.15)
            self.play(Create(new_sq_marker))
            self.play(Indicate(new_sq_marker))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 6: Dot Product Equation
        dot_box = RoundedRectangle(height=1.5, width=4, color=WHITE).next_to(checklist_box, RIGHT, buff=0.5).shift(UP*1.5)
        lhs = MathTex(r"\vec{u} \cdot \vec{v}")
        eq_sign = MathTex(r"=")
        rhs = MathTex(r"0")
        dot_eq = VGroup(lhs, eq_sign, rhs).arrange(RIGHT).move_to(dot_box.get_center())

        with self.voiceover(text="Mathematically, their dot product equals zero.") as tracker:
            self.play(FadeIn(dot_box), Write(dot_eq))
            self.play(Indicate(rhs))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 7: Step 1 Complete
        check1 = Tex(r"\checkmark", color=GREEN).next_to(item1, LEFT, buff=0.2)
        
        with self.voiceover(text="With the right angle confirmed, we can now name the components of the triangle.") as tracker:
            self.play(FadeIn(check1), item2.animate.set_opacity(1.0).set_color(WHITE))
            self.play(self.camera.animate.scale(0.8).move_to(vector_group.get_center()))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # --- Scene 3: Step 2 – Hypotenuse vs. Legs ---
        # Block 8: Side Labels a and b
        # Reset camera
        self.play(self.camera.animate.scale(1.25).move_to(ORIGIN))
        self.play(FadeOut(dot_box), FadeOut(dot_eq), FadeOut(vector_group), FadeOut(new_sq_marker))
        
        # New Triangle for naming
        t_v_a = np.array([-0.5, -1, 0])
        t_v_b = np.array([2, -1, 0])
        t_v_c = np.array([2, 1, 0])
        
        side_a = Line(t_v_a, t_v_b, color=BLUE_B)
        side_b = Line(t_v_b, t_v_c, color=GREEN_B)
        side_c = Line(t_v_c, t_v_a, color=WHITE)
        label_a = MathTex("a").next_to(side_a, DOWN)
        label_b = MathTex("b").next_to(side_b, RIGHT)
        named_tri = VGroup(side_a, side_b, side_c, label_a, label_b)
        sq_m = Rectangle(width=0.2, height=0.2, color="#94A3B8").move_to(t_v_b + LEFT*0.1 + UP*0.1)

        with self.voiceover(text="Next, we map the sides. The two sides forming the L-shape are the legs.") as tracker:
            self.play(Create(side_a), Create(side_b), Create(side_c), Create(sq_m))
            self.play(Write(label_a), Write(label_b))
            self.play(Indicate(side_a), Indicate(side_b))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 9: Hypotenuse Arrow
        hyp_arrow = Arrow(sq_m.get_center(), side_c.get_center(), color=GOLD_B)
        
        with self.voiceover(text="Directly across from the right angle is the Hypotenuse.") as tracker:
            self.play(GrowArrow(hyp_arrow))
            self.play(Indicate(side_c))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 10: Side c and Inequality
        label_c = MathTex("c", color=GOLD_B).next_to(side_c, UP + LEFT, buff=-0.5)
        inequality = MathTex(r"c > a, b", font_size=30).next_to(named_tri, DOWN, buff=0.5)

        with self.voiceover(text="This is always the longest side of the triangle.") as tracker:
            self.play(Write(label_c), FadeOut(hyp_arrow))
            self.play(Wiggle(side_c))
            self.play(Write(inequality))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # --- Scene 4: Step 3 – Area Logic ---
        # Block 11: Grow Squares a and b
        sq_a = Square(side_length=2.5, fill_opacity=0.4, fill_color=BLUE_B, stroke_color=BLUE_B).next_to(side_a, DOWN, buff=0)
        sq_b = Square(side_length=2, fill_opacity=0.4, fill_color=GREEN_B, stroke_color=GREEN_B).next_to(side_b, RIGHT, buff=0)
        
        with self.voiceover(text="The theorem states that if we treat each side as the edge of a square...") as tracker:
            self.play(item3.animate.set_opacity(1.0).set_color(WHITE))
            self.play(FadeIn(sq_a), FadeIn(sq_b), run_time=2)
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 12: Pulse and Equation
        area_a = MathTex(r"\text{Area}_a")
        plus_sym = MathTex("+")
        area_b = MathTex(r"\text{Area}_b")
        area_eq_start = VGroup(area_a, plus_sym, area_b).arrange(RIGHT).to_edge(DOWN, buff=0.5)

        with self.voiceover(text="...the combined area of the two smaller squares...") as tracker:
            self.play(sq_a.animate.scale(1.1), sq_b.animate.scale(1.1), rate_func=there_and_back)
            self.play(Write(area_eq_start))
            self.play(Indicate(area_a), Indicate(area_b))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 13: Square c and complete Equation
        # Manual positioning for rotated square on hypotenuse
        sq_c = Polygon(t_v_c, t_v_a, t_v_a + np.array([-2, 2.5, 0]), t_v_c + np.array([-2, 2.5, 0]), 
                      fill_opacity=0.4, fill_color=GOLD_B, stroke_color=GOLD_B)
        
        area_equals = MathTex("=")
        area_c_term = MathTex(r"\text{Area}_c")
        area_eq_full = VGroup(area_eq_start, area_equals, area_c_term).arrange(RIGHT).to_edge(DOWN, buff=0.5)

        with self.voiceover(text="...perfectly equals the area of the square on the hypotenuse.") as tracker:
            self.play(FadeIn(sq_c), run_time=2)
            self.play(Write(area_equals), Write(area_c_term))
            self.play(Indicate(area_c_term))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # --- Scene 5: Step 4 – Calculating Lengths ---
        # Block 14: 3-4-5 Triangle Intro
        self.play(FadeOut(sq_a), FadeOut(sq_b), FadeOut(sq_c), FadeOut(named_tri), FadeOut(sq_m), 
                  FadeOut(label_a), FadeOut(label_b), FadeOut(label_c), FadeOut(inequality), FadeOut(area_eq_full))
        
        calc_v1 = MathTex("3^2")
        calc_p1 = MathTex("+")
        calc_v2 = MathTex("4^2")
        calc_e1 = MathTex("=")
        calc_t1 = MathTex("c^2")
        calc_line1 = VGroup(calc_v1, calc_p1, calc_v2, calc_e1, calc_t1).arrange(RIGHT).move_to(UP * 0.5)

        with self.voiceover(text="Let's solve for c using a 3-4-5 triangle.") as tracker:
            self.play(item4.animate.set_opacity(1.0).set_color(WHITE))
            self.play(Write(calc_line1))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 15: Square calculations
        res1 = MathTex("9")
        res2 = MathTex("16")
        calc_line2 = VGroup(res1, calc_p1.copy(), res2, calc_e1.copy(), calc_t1.copy()).arrange(RIGHT).next_to(calc_line1, DOWN, buff=0.5)

        with self.voiceover(text="First, square the legs. Three squared is nine, and four squared is sixteen.") as tracker:
            self.play(FadeIn(res1), 
                      FadeIn(res2),
                      Write(calc_line2[1]), Write(calc_line2[3]), Write(calc_line2[4]))
            self.play(Indicate(res1), Indicate(res2))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 16: Summing
        sum_res = MathTex("25")
        calc_line3 = VGroup(sum_res, calc_e1.copy(), calc_t1.copy()).arrange(RIGHT).next_to(calc_line2, DOWN, buff=0.5)

        with self.voiceover(text="Summing these gives us twenty-five.") as tracker:
            self.play(FadeOut(res1), FadeOut(res2), FadeIn(sum_res),
                      Write(calc_line3[1]), Write(calc_line3[2]))
            self.play(Indicate(sum_res))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 17: Square root
        sqrt_val = MathTex(r"\sqrt{25}")
        calc_e2 = MathTex("=")
        final_c_sym = MathTex("c")
        calc_line4 = VGroup(sqrt_val, calc_e2, final_c_sym).arrange(RIGHT).next_to(calc_line3, DOWN, buff=0.5)

        with self.voiceover(text="Finally, to find the side length c, we take the square root of both sides.") as tracker:
            self.play(Write(calc_line4))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 18: Final Result
        final_5 = MathTex("5")
        final_eq = VGroup(final_5, MathTex("="), MathTex("c")).arrange(RIGHT).move_to(calc_line4)
        surr_rect = SurroundingRectangle(final_5, color=GOLD_B)

        with self.voiceover(text="Resulting in a hypotenuse of five.") as tracker:
            self.play(FadeOut(sqrt_val), FadeIn(final_5))
            self.play(Create(surr_rect))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # --- Scene 6: Generalization (Law of Cosines) ---
        # Block 19: Obtuse Triangle and Formula
        self.play(FadeOut(VGroup(calc_line1, calc_line2, calc_line3, calc_line4, final_5, final_eq[1:], surr_rect, checklist_box, checklist, check1)))
        
        obtuse_tri = Polygon(np.array([-1.5, -1, 0]), np.array([2, -1, 0]), np.array([3, 1.5, 0]), color=WHITE)
        loc_base = MathTex("c^2 = a^2 + b^2")
        loc_mod = MathTex(r"- 2ab \cos(\theta)")
        loc_full = VGroup(loc_base, loc_mod).arrange(RIGHT).to_edge(DOWN, buff=1.0)

        with self.voiceover(text="What if the angle isn't 90 degrees? We use the Law of Cosines.") as tracker:
            self.play(Create(obtuse_tri))
            self.play(Write(loc_full))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 20: Modifier Highlight
        with self.voiceover(text="Notice this extra term here.") as tracker:
            self.play(loc_mod.animate.set_color(RED_B))
            self.play(Indicate(loc_mod))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 21: Back to 90 degrees
        right_tri_final = Polygon(np.array([-0.5, -1, 0]), np.array([2, -1, 0]), np.array([2, 1, 0]), color=WHITE)
        cos_text = MathTex(r"\cos(90^\circ) = 0").next_to(loc_full, UP, buff=0.5)
        cross = Cross(loc_mod)

        with self.voiceover(text="When the angle is exactly 90 degrees, the cosine becomes zero...") as tracker:
            self.play(FadeOut(obtuse_tri), FadeIn(right_tri_final))
            self.play(Write(cos_text))
            self.play(Create(cross))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 22: Fade out modifier
        final_pyth = MathTex("a^2 + b^2 = c^2").move_to(DOWN * 2).scale(1.2)
        
        with self.voiceover(text="...and we return to the familiar Pythagorean Theorem.") as tracker:
            self.play(FadeOut(loc_mod), FadeOut(cross), FadeOut(cos_text), FadeOut(loc_base))
            self.play(Write(final_pyth))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # --- Scene 7: Final Overview ---
        # Block 23: Grid Display
        self.play(FadeOut(right_tri_final), FadeOut(final_pyth))
        
        g1 = VGroup(Triangle(), Square().scale(0.5)).arrange(RIGHT)
        g2 = MathTex("a^2+b^2=c^2")
        g3 = Text("Hypotenuse", color=GOLD_B)
        g4 = Text("Distance/Geometry", font_size=24)
        grid = VGroup(g1, g2, g3, g4).arrange_in_grid(rows=2, cols=2, buff=1.5)

        with self.voiceover(text="Whether you are calculating distances in a coordinate plane or building a house...") as tracker:
            self.play(FadeIn(grid))
            self.play(self.camera.animate.scale(1.2))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 24: Fade grid, Scale formula
        final_formula = MathTex("a^2 + b^2 = c^2").scale(2.5)

        with self.voiceover(text="...this relationship between sides remains one of the most powerful tools in mathematics.") as tracker:
            self.play(FadeOut(g1), FadeOut(g3), FadeOut(g4))
            self.play(FadeOut(g2), FadeIn(final_formula))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 25: Final Highlight
        final_box = SurroundingRectangle(final_formula, color=GOLD_B, buff=0.4)

        with self.voiceover(text="Remember: a squared plus b squared always equals c squared for a right triangle.") as tracker:
            self.play(Create(final_box))
            self.play(Indicate(final_formula))
            self.wait(max(0.01, tracker.get_remaining_duration()))