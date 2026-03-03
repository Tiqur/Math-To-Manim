from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService

# Set configuration
config.background_color = "#111827"

class MyScene(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GTTSService(lang="en"))

        # --- Scene 1: Lecture Overview & Roadmap ---
        
        # Block 1
        with self.voiceover(text="To solve a first-order differential equation using exactness, we first look for this standard form.") as tracker:
            title1 = Text("Exact Differential Equations: Overview", font_size=40).to_edge(UP)
            std_form = MathTex(r"M(x,y)dx + N(x,y)dy = 0").shift(UP*1.5)
            box = SurroundingRectangle(std_form, color=BLUE, buff=0.4, corner_radius=0.1)
            
            self.play(FadeIn(title1), FadeIn(box), FadeIn(std_form))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 2
        with self.voiceover(text="Before we dive into the math, you need to be comfortable with partial derivatives and the concept of a total differential.") as tracker:
            # Move equation to top to clear space for the 3-column layout
            self.play(
                VGroup(std_form, box).animate.scale(0.7).to_edge(UP, buff=0.8),
                title1.animate.scale(0.8).to_edge(UP, buff=0.2)
            )
            
            vocab_title = Text("Prerequisites:", font_size=26).to_edge(LEFT, buff=0.5).shift(UP*0.5)
            v1 = MathTex(r"1. \text{ Partial Derivative } (\partial)", font_size=24)
            v2 = MathTex(r"2. \text{ Exactness } (M_y = N_x)", font_size=24)
            v3 = MathTex(r"3. \text{ Potential Function } (\Psi)", font_size=24)
            v4 = MathTex(r"4. \text{ Integrating Factor } (\mu)", font_size=24)
            vocab = VGroup(v1, v2, v3, v4).arrange(DOWN, aligned_edge=LEFT).next_to(vocab_title, DOWN, aligned_edge=LEFT)
            
            self.play(FadeIn(vocab_title))
            for item in vocab:
                self.play(FadeIn(item, shift=RIGHT*0.2), run_time=0.3)
            
            self.play(Indicate(v1, color=YELLOW))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 3
        with self.voiceover(text="Our strategy is a three-step process: identify, test, and reconstruct.") as tracker:
            # Added Start node and adjusted vertical layout to fit blueprint
            n0 = VGroup(RoundedRectangle(height=0.5, width=1.8, color=WHITE), Text("Start", font_size=16)).shift(RIGHT*2.0 + UP*1.8)
            n1 = VGroup(RoundedRectangle(height=0.5, width=2.8, color=WHITE), Text("Identify M & N", font_size=16)).next_to(n0, DOWN, buff=0.6)
            n2 = VGroup(RoundedRectangle(height=0.5, width=2.8, color=WHITE), Text("Test My = Nx", font_size=16)).next_to(n1, DOWN, buff=0.6)
            n3 = VGroup(RoundedRectangle(height=0.7, width=3.0, color=WHITE), Text("Algorithm for Psi", font_size=20)).next_to(n2, DOWN, buff=0.8)
            
            a0 = Arrow(n0.get_bottom(), n1.get_top(), buff=0.1, max_tip_length_to_length_ratio=0.15)
            a1 = Arrow(n1.get_bottom(), n2.get_top(), buff=0.1, max_tip_length_to_length_ratio=0.15)
            
            self.play(FadeIn(n0), FadeIn(n1), FadeIn(n2), Create(a0), Create(a1))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 4
        with self.voiceover(text="Depending on the test result, we either proceed to build the potential function or find an integrating factor.") as tracker:
            a_yes = Arrow(n2.get_bottom(), n3.get_top(), color=GREEN, buff=0.1)
            lab_yes = Text("Yes", font_size=18).next_to(a_yes, LEFT, buff=0.1)
            # Centered positioning for mu branch
            n4 = VGroup(RoundedRectangle(height=0.7, width=2.2, color=ORANGE), Text("Find mu", font_size=20)).next_to(n2, RIGHT, buff=1.5)
            a_no = Arrow(n2.get_right(), n4.get_left(), color=RED, buff=0.1)
            lab_no = Text("No", font_size=18).next_to(a_no, UP, buff=0.1)
            
            self.play(FadeIn(a_yes), FadeIn(lab_yes), FadeIn(n3))
            self.play(FadeIn(a_no), FadeIn(lab_no), FadeIn(n4))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # --- Scene 2: The Exactness Test ---
        
        # Block 5
        with self.voiceover(text="Let's start our first example by following our checklist.") as tracker:
            self.play(FadeOut(vocab, box, std_form, n0, n1, n2, n3, n4, a0, a1, a_yes, a_no, lab_yes, lab_no, vocab_title))
            self.play(self.camera.animate.move_to(ORIGIN))
            title2 = Text("Step 1: The Exactness Test", font_size=35).to_edge(UP)
            self.play(FadeOut(title1), FadeIn(title2))
            
            # Checklist (Rule Box)
            cb1 = Square(side_length=0.3)
            ct1 = MathTex(r"\text{Identify } M(x,y)", font_size=24)
            cb2 = Square(side_length=0.3)
            ct2 = MathTex(r"\text{Identify } N(x,y)", font_size=24)
            cb3 = Square(side_length=0.3)
            ct3 = MathTex(r"\text{Calculate } M_y \text{ and } N_x", font_size=24)
            checklist = VGroup(
                VGroup(cb1, ct1).arrange(RIGHT),
                VGroup(cb2, ct2).arrange(RIGHT),
                VGroup(cb3, ct3).arrange(RIGHT)
            ).arrange(DOWN, aligned_edge=LEFT).to_corner(UR).shift(DOWN*1.2)
            
            self.play(FadeIn(checklist))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 6
        with self.voiceover(text="Let's look at this equation. Our M is the term attached to dx, and N is attached to dy.") as tracker:
            # (3x^2 + 4xy)dx + (2x^2 + 2y)dy = 0
            # Moved equation higher to prevent bottom-edge clipping of multi-line derivatives
            l_paren1 = MathTex("(")
            m_term = MathTex(r"3x^2 + 4xy", color="#38BDF8")
            r_paren1_dx = MathTex(")dx")
            plus_sgn = MathTex("+")
            l_paren2 = MathTex("(")
            n_term = MathTex(r"2x^2 + 2y", color="#4ADE80")
            r_paren2_dy = MathTex(")dy")
            eq_zero = MathTex("= 0")
            
            ex_eq = VGroup(l_paren1, m_term, r_paren1_dx, plus_sgn, l_paren2, n_term, r_paren2_dy, eq_zero).arrange(RIGHT, buff=0.1).shift(UP*1.2)
            
            self.play(FadeIn(ex_eq))
            
            # Added vertical offset to correct glyph descent alignment
            check1 = MathTex(r"\checkmark", color=GREEN).scale(0.7).move_to(cb1).shift(DOWN*0.05)
            check2 = MathTex(r"\checkmark", color=GREEN).scale(0.7).move_to(cb2).shift(DOWN*0.05)
            self.play(FadeIn(check1), FadeIn(check2))
            self.play(Indicate(m_term), Indicate(n_term))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 7
        with self.voiceover(text="The condition for exactness is that the partial of M with respect to y must equal the partial of N with respect to x.") as tracker:
            cond = MathTex(r"M_y = N_x", color=YELLOW).scale(1.5).shift(DOWN*1.2)
            self.play(FadeIn(cond))
            self.play(Indicate(cond, scale_factor=1.2))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 8
        with self.voiceover(text="Differentiating M with respect to y, we treat x as a constant.") as tracker:
            # Consolidated MathTex string to preserve TeX kerning/spacing
            calc_m = MathTex(r"\frac{\partial M}{\partial y}", "=", r"\frac{\partial}{\partial y}", "(", "3x^2", "+", "4x", "y", ")").shift(DOWN*2.0).scale(0.8)
            self.play(FadeIn(calc_m))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 9
        with self.voiceover(text="The 3x-squared term vanishes because it doesn't contain y.") as tracker:
            # Use indexing to access parts of the consolidated MathTex
            self.play(calc_m[4].animate.set_opacity(0.3))
            self.play(Circumscribe(calc_m[7], color=YELLOW))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 10
        with self.voiceover(text="Differentiating N with respect to x yields the same result: 4x.") as tracker:
            res_m = MathTex("= 4x", color=YELLOW).scale(0.8).next_to(calc_m, RIGHT, buff=0.1)
            
            # Decompose to allow underlining the specific result and avoid NameError
            l2_p1 = MathTex(r"\frac{\partial N}{\partial x}")
            l2_p2 = MathTex("=")
            l2_p3 = MathTex(r"\frac{\partial}{\partial x}(2x^2 + 2y) =")
            l2_res = MathTex("4x")
            line2_n = VGroup(l2_p1, l2_p2, l2_p3, l2_res).arrange(RIGHT, buff=0.1).scale(0.8)
            
            # Position line 2 and align its equals sign with the equals sign of calc_m
            line2_n.next_to(calc_m, DOWN, buff=0.8, aligned_edge=LEFT)
            line2_n.shift(RIGHT * (calc_m[1].get_center()[0] - l2_p2.get_center()[0]))
            
            self.play(FadeIn(res_m), FadeIn(line2_n))
            
            u1 = Underline(res_m)
            u2 = Underline(l2_res)
            self.play(FadeIn(u1), FadeIn(u2))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 11
        with self.voiceover(text="Both result in 4x, so the equation is exact.") as tracker:
            final_test = MathTex("4x = 4x", color=GREEN).scale(1.2).move_to(cond)
            # Use FadeOut/FadeIn to avoid broadcast errors
            self.play(
                FadeOut(res_m), FadeOut(line2_n), FadeIn(final_test),
                FadeOut(cond), FadeOut(u1), FadeOut(u2), FadeOut(calc_m)
            )
            
            big_check = MathTex(r"\checkmark", color=GREEN).scale(3).move_to(ORIGIN).shift(LEFT*3.5)
            check3 = MathTex(r"\checkmark", color=GREEN).scale(0.7).move_to(cb3)
            self.play(FadeIn(big_check), FadeIn(check3))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # --- Scene 3: Potential Function Algorithm ---
        
        # Block 12
        with self.voiceover(text="Because it's exact, there exists a potential function Psi. We find it by integrating M with respect to x.") as tracker:
            self.play(FadeOut(ex_eq), FadeOut(big_check), FadeOut(final_test))
            title3 = Text("Step 2: Finding the Potential Function", font_size=35).to_edge(UP)
            self.play(ReplacementTransform(title2, title3))
            
            # New Algorithm Checklist
            self.play(FadeOut(checklist), FadeOut(check1), FadeOut(check2), FadeOut(check3))
            cbs1, cbs2, cbs3 = [Square(side_length=0.3) for _ in range(3)]
            cts1 = MathTex(r"M_y = N_x", font_size=24)
            cts2 = Text("Integrate M w.r.t x", font_size=20)
            cts3 = Text("Solve for g(y)", font_size=20)
            checklist_s3 = VGroup(VGroup(cbs1, cts1).arrange(RIGHT), VGroup(cbs2, cts2).arrange(RIGHT), VGroup(cbs3, cts3).arrange(RIGHT)).arrange(DOWN, aligned_edge=LEFT).to_corner(UR).shift(DOWN*1.2)
            check_s3_1 = MathTex(r"\checkmark", color=GREEN).scale(0.7).move_to(cbs1)
            self.play(FadeIn(checklist_s3), FadeIn(check_s3_1))
            
            psi_pref = MathTex(r"\Psi(x,y) =")
            psi_int_sgn = MathTex(r"\int")
            psi_rest = MathTex(r"M \, dx + g(y)")
            setup_psi = VGroup(psi_pref, psi_int_sgn, psi_rest).arrange(RIGHT).shift(UP*0.5)
            self.play(FadeIn(setup_psi))
            self.play(Indicate(psi_int_sgn))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 13
        with self.voiceover(text="We plug our expression for M into the integral.") as tracker:
            # Decomposition for Block 13
            psi_label = MathTex(r"\Psi(x,y)")
            eq_label = MathTex("=")
            integral_sgn = MathTex(r"\int")
            content = MathTex(r"(3x^2 + 4xy)", color="#38BDF8")
            dx_label = MathTex("dx")
            plus_g = MathTex("+ g(y)")
            
            psi_int = VGroup(psi_label, eq_label, integral_sgn, content, dx_label, plus_g).arrange(RIGHT, buff=0.1).shift(UP*0.5)
            self.play(FadeOut(setup_psi), FadeIn(psi_int))
            self.play(Indicate(content))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 14
        with self.voiceover(text="Integrating term-by-term, we get x-cubed plus 2-x-squared-y.") as tracker:
            # Result: x^3 + 2x^2y + g(y)
            res1 = MathTex("x^3")
            res2 = MathTex("+")
            res3 = MathTex("2x^2y")
            res4 = MathTex("+ g(y)")
            psi_res = VGroup(psi_label.copy(), eq_label.copy(), res1, res3, res4).arrange(RIGHT).next_to(psi_int, DOWN, buff=0.5)
            
            self.play(FadeIn(psi_res))
            self.play(Indicate(res1))
            self.play(Indicate(res3))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 15
        with self.voiceover(text="Don't forget the constant of integration—since we integrated with respect to x, this constant is a function of y, which we call g of y.") as tracker:
            self.play(Circumscribe(res4, color="#FDE047"))
            check_s3_2 = MathTex(r"\checkmark", color=GREEN).scale(0.7).move_to(cbs2)
            self.play(FadeIn(check_s3_2))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 16
        with self.voiceover(text="To find g of y, we differentiate our new Psi with respect to y and set it equal to N.") as tracker:
            cond_g = MathTex(r"\frac{\partial \Psi}{\partial y} = N").shift(DOWN*2)
            self.play(FadeIn(cond_g))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 17
        with self.voiceover(text="Substituting our expression for Psi on the left and our original N on the right.") as tracker:
            lhs_exp = MathTex(r"\frac{\partial}{\partial y}(x^3 + 2x^2y + g(y))")
            eq_exp = MathTex("=")
            rhs_p1 = MathTex("2x^2")
            rhs_p2 = MathTex("+")
            rhs_p3 = MathTex("2y")
            rhs_exp = VGroup(rhs_p1, rhs_p2, rhs_p3).arrange(RIGHT).set_color("#4ADE80")
            
            full_exp = VGroup(lhs_exp, eq_exp, rhs_exp).arrange(RIGHT).scale(0.8).move_to(cond_g)
            self.play(FadeOut(cond_g), FadeIn(full_exp))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 18
        with self.voiceover(text="Terms involving x should cancel out here. If they don't, check your previous derivative!") as tracker:
            # Preserving math alignment while keeping crossable segments
            eval_lhs = MathTex("2x^2", "+", "g'(y)").scale(0.8).move_to(lhs_exp)
            
            self.play(FadeOut(lhs_exp), FadeIn(eval_lhs))
            
            # Cross indices updated for the new MathTex structure
            cross_l = Cross(eval_lhs[0], color=RED)
            cross_r = Cross(rhs_p1, color=RED)
            self.play(Create(cross_l), Create(cross_r))
            
            self.play(Wiggle(rhs_p3))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 19
        with self.voiceover(text="This leaves us with g-prime of y equals 2y, which integrates easily to y-squared.") as tracker:
            gp_eq = MathTex("g'(y) = 2y").move_to(full_exp)
            g_sol = MathTex("g(y) = y^2", color=YELLOW).next_to(gp_eq, DOWN)
            self.play(FadeOut(eval_lhs), FadeOut(eq_exp), FadeOut(rhs_exp), FadeIn(gp_eq), FadeOut(cross_l), FadeOut(cross_r))
            self.play(FadeIn(g_sol))
            check_s3_3 = MathTex(r"\checkmark", color=GREEN).scale(0.7).move_to(cbs3)
            self.play(FadeIn(check_s3_3))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # --- Scene 4: Non-Exact Case (Integrating Factors) ---
        
        # Block 20
        with self.voiceover(text="What if M-sub-y doesn't equal N-sub-x? Let's check this new equation.") as tracker:
            self.play(FadeOut(VGroup(psi_int, psi_res, gp_eq, g_sol, checklist_s3, check_s3_1, check_s3_2, check_s3_3)))
            title4 = Text("When Exactness Fails", font_size=35).to_edge(UP)
            self.play(FadeOut(title3), FadeIn(title4))
            
            # Moved equation higher to avoid collision with the formula box at bottom
            eq_non = MathTex(r"y \, dx + (2x - ye^y) \, dy = 0").shift(UP*2.0)
            self.play(FadeIn(eq_non))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 21
        with self.voiceover(text="Here, the partial of M with respect to y is 1, but the partial of N with respect to x is 2. 1 does not equal 2.") as tracker:
            my_val = MathTex("M_y = 1")
            nx_val = MathTex("N_x = 2")
            vals = VGroup(my_val, nx_val).arrange(RIGHT, buff=1).next_to(eq_non, DOWN, buff=0.4)
            neq = MathTex(r"1 \neq 2", color=RED).next_to(vals, DOWN, buff=0.4)
            
            self.play(FadeIn(vals))
            self.play(FadeIn(neq))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 22
        with self.voiceover(text="We need an integrating factor, mu, to force exactness.") as tracker:
            f_box = RoundedRectangle(height=2, width=8, color=BLUE_A)
            mu1 = MathTex(r"\mu(x) = e^{\int \frac{M_y - N_x}{N} dx}")
            mu2 = MathTex(r"\mu(y) = e^{\int \frac{N_x - M_y}{M} dy}")
            formulas = VGroup(mu1, mu2).arrange(RIGHT, buff=0.5).move_to(f_box)
            formula_box = VGroup(f_box, formulas).to_edge(DOWN, buff=0.5)
            
            self.play(FadeIn(formula_box))
            self.play(f_box.animate.scale(1.05), run_time=0.5, rate_func=there_and_back)
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 23
        with self.voiceover(text="We test the residuals. In this case, the second formula gives us 1 over y, which depends only on y.") as tracker:
            # Reduced buffer to lift calculation away from formula box
            calc_res = MathTex(r"\frac{N_x - M_y}{M} = \frac{2 - 1}{y} = \frac{1}{y}", color=YELLOW).next_to(vals, DOWN, buff=0.8)
            self.play(FadeOut(neq), FadeIn(calc_res))
            self.play(Indicate(calc_res)) 
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 24
        with self.voiceover(text="This gives us an integrating factor of y.") as tracker:
            # Decompose to avoid character indexing which causes crashes in OpenGL
            mu_p1 = MathTex(r"\mu(y) = e^{\int \frac{1}{y} dy} = e^{\ln y} =")
            mu_p2 = MathTex("y", color=YELLOW)
            mu_final = VGroup(mu_p1, mu_p2).arrange(RIGHT).next_to(calc_res, DOWN)
            self.play(FadeIn(mu_final))
            self.play(Indicate(mu_p2))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # --- Scene 5: IVP Finalization ---
        
        # Block 25
        with self.voiceover(text="Finally, if you're given an initial condition, like y of 1 equals 2, we solve for the constant C.") as tracker:
            self.play(FadeOut(VGroup(eq_non, vals, calc_res, mu_final, formula_box)))
            title5 = Text("Initial Value Problems (IVP)", font_size=35).to_edge(UP)
            self.play(FadeOut(title4), FadeIn(title5))
            
            # Back to Example 1 results: Psi = x^3 + 2x^2y + y^2 = C
            gen_sol_lhs = MathTex(r"x^3 + 2x^2y + y^2 =")
            gen_sol_rhs = MathTex("C")
            gen_sol = VGroup(gen_sol_lhs, gen_sol_rhs).arrange(RIGHT).shift(UP*0.5)
            iv = MathTex(r"y(1) = 2").to_corner(UL).shift(DOWN*1.2)
            
            self.play(FadeIn(gen_sol))
            self.play(FadeIn(iv))
            self.play(Indicate(gen_sol_rhs)) 
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 26
        with self.voiceover(text="Substitute 1 for every x and 2 for every y.") as tracker:
            # Consolidated MathTex for correct spacing with substring coloring
            sub_eq = MathTex("(1)^3", "+", "2", "(1)^2", "(2)", "+", "(2)^2", "=", "C").shift(DOWN*1)
            sub_eq[0].set_color(YELLOW)
            sub_eq[3].set_color(YELLOW)
            sub_eq[4].set_color("#4ADE80")
            sub_eq[6].set_color("#4ADE80")
            
            self.play(FadeIn(sub_eq))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 27
        with self.voiceover(text="Calculating the left side gives us 9, so C equals 9.") as tracker:
            steps = MathTex("1 + 4 + 4 = 9").next_to(sub_eq, DOWN)
            c_val = MathTex("C = 9", color=YELLOW).next_to(steps, DOWN)
            self.play(FadeIn(steps))
            self.play(FadeIn(c_val))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 28
        with self.voiceover(text="The final solution is the implicit equation set to that specific constant. This result connects back to our original differential equation by satisfying all conditions.") as tracker:
            final_ans = MathTex(r"x^3 + 2x^2y + y^2 = 9").scale(1.2).move_to(ORIGIN)
            g_box = SurroundingRectangle(final_ans, color="#FDE047", buff=0.4, stroke_width=4)
            
            self.play(FadeOut(VGroup(gen_sol, iv, sub_eq, steps, c_val)))
            self.play(FadeIn(final_ans))
            self.play(FadeIn(g_box))
            self.play(Flash(g_box.get_center(), color=YELLOW, line_length=0.5))
            self.wait(max(0.01, tracker.get_remaining_duration()))