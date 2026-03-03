from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService

# Global Configuration
config.background_color = "#0F172A"
TEXT_COLOR = "#F8FAFC"
PX_COLOR = "#FDE047"
GX_COLOR = "#22D3EE"
MU_COLOR = "#FB923C"
SUCCESS_COLOR = "#4ADE80"
AXES_COLOR = "#94A3B8"

class MyScene(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GTTSService(lang="en"))

        # --- Scene 1: Lecture Overview & Roadmap ---
        
        # Block 1
        with self.voiceover(text="Today we solve first-order linear differential equations using the Integrating Factor method.") as tracker:
            title = Text("Integrating Factor Method", color=TEXT_COLOR).to_edge(UP)
            
            term1 = MathTex(r"a_1(x)y'", color=TEXT_COLOR)
            plus = MathTex("+", color=TEXT_COLOR)
            term2 = MathTex(r"a_0(x)y", color=TEXT_COLOR)
            equals = MathTex("=", color=TEXT_COLOR)
            rhs = MathTex(r"f(x)", color=TEXT_COLOR)
            gen_eq = VGroup(term1, plus, term2, equals, rhs).arrange(RIGHT).next_to(title, DOWN, buff=0.5)
            
            self.play(FadeIn(title))
            self.play(FadeIn(gen_eq))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 2
        with self.voiceover(text="Before we calculate anything, we need a roadmap.") as tracker:
            vocab_box = Rectangle(width=4.5, height=3, color=AXES_COLOR).to_edge(LEFT, buff=0.5).shift(DOWN*1)
            vocab_title = Text("Vocabulary", font_size=24, color=AXES_COLOR).next_to(vocab_box, UP, buff=0.1)
            
            v1 = Text("Linear", font_size=24, color=TEXT_COLOR)
            v2 = Text("Standard Form", font_size=24, color=TEXT_COLOR)
            v3 = Text("Integrating Factor", font_size=24, color=TEXT_COLOR)
            v4 = Text("Interval of Validity", font_size=24, color=TEXT_COLOR)
            vocab_list = VGroup(v1, v2, v3, v4).arrange(DOWN, aligned_edge=LEFT, buff=0.3).move_to(vocab_box.get_center())
            
            self.play(FadeIn(vocab_box), FadeIn(vocab_title))
            self.play(FadeIn(vocab_list))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 3
        with self.voiceover(text="Our process follows five strict steps.") as tracker:
            steps_text = [
                r"1. \ y' + p(x)y = g(x)",
                "2. Check Continuity",
                r"3. \ \mu(x) = e^{\int p(x)dx}",
                r"4. \ \frac{d}{dx}[\mu y] = \mu g",
                "5. Select Interval"
            ]
            flowchart = VGroup()
            for i, text in enumerate(steps_text):
                content = MathTex(text, font_size=24) if "\\" in text or "y'" in text else Text(text, font_size=18)
                box = SurroundingRectangle(content, buff=0.2, color=AXES_COLOR)
                step_box = VGroup(box, content)
                flowchart.add(step_box)
            
            flowchart.arrange(DOWN, buff=0.3).to_edge(RIGHT, buff=0.5).shift(DOWN*0.5)
            flowchart[2][1].set_color(MU_COLOR)
            
            self.play(LaggedStart(*[FadeIn(s) for s in flowchart], lag_ratio=0.5))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 4
        with self.voiceover(text="This method works as long as the functions are continuous near our starting point.") as tracker:
            self.play(Indicate(v4, color=SUCCESS_COLOR))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # --- Scene 2: Standard Form & Continuity Analysis ---
        
        # Block 5
        self.play(FadeOut(vocab_box, vocab_title, vocab_list, flowchart, gen_eq, title))
        
        with self.voiceover(text="Step 1: Normalize. We must have a leading coefficient of 1 for the y-prime term.") as tracker:
            prob_title = MathTex(r"(x^2 - 9)y' + 2xy = \frac{1}{x-5}, \quad y(4)=2", color=TEXT_COLOR).to_edge(UP)
            
            coeff = MathTex(r"(x^2 - 9)", color=SUCCESS_COLOR)
            y_prime = MathTex(r"y'")
            middle = MathTex(r"+ 2xy")
            equals_sign = MathTex("=")
            source_rhs = MathTex(r"\frac{1}{x-5}")
            
            working_eq = VGroup(coeff, y_prime, middle, equals_sign, source_rhs).arrange(RIGHT).shift(UP*1)
            norm_rect = SurroundingRectangle(coeff, color=SUCCESS_COLOR)
            
            self.play(FadeIn(prob_title))
            self.play(FadeIn(working_eq))
            self.play(FadeIn(norm_rect))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 6
        with self.voiceover(text="To do this, we divide every term in the equation by the coefficient of y-prime.") as tracker:
            standard_form = VGroup(
                MathTex(r"y'"),
                MathTex(r"+"),
                MathTex(r"\frac{2x}{x^2-9}"),
                MathTex(r"y"),
                MathTex(r"="),
                MathTex(r"\frac{1}{(x-5)(x^2-9)}")
            ).arrange(RIGHT).next_to(working_eq, DOWN, buff=1)
            
            self.play(ReplacementTransform(working_eq.copy(), standard_form))
            self.play(FadeOut(norm_rect), FadeOut(working_eq), FadeOut(prob_title))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 7
        with self.voiceover(text="Now we identify p of x and g of x.") as tracker:
            # Highlight parts manually by rebuilding standard form
            p_part = MathTex(r"\frac{2x}{x^2-9}", color=PX_COLOR)
            g_part = MathTex(r"\frac{1}{(x-5)(x^2-9)}", color=GX_COLOR)
            
            final_std_form = VGroup(
                MathTex(r"y'"),
                MathTex(r"+"),
                p_part,
                MathTex(r"y"),
                MathTex(r"="),
                g_part
            ).arrange(RIGHT).move_to(standard_form)
            
            self.play(ReplacementTransform(standard_form, final_std_form))
            self.play(Indicate(p_part), Indicate(g_part))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 8
        with self.voiceover(text="Step 2: Check for discontinuities. Where do these functions blow up?") as tracker:
            exclusion = MathTex(r"x \neq \pm 3, 5", color=PX_COLOR).next_to(final_std_form, DOWN, buff=0.4)
            self.play(FadeIn(exclusion))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 9
        with self.voiceover(text="Visualizing this on a number line, we see four potential intervals.") as tracker:
            number_line = NumberLine(
                x_range=[-6, 8, 1],
                length=10,
                color=AXES_COLOR,
                include_numbers=True,
                label_direction=DOWN
            ).shift(DOWN*2.8)
            
            m1 = Dot(number_line.n2p(-3), color=TEXT_COLOR)
            m2 = Dot(number_line.n2p(3), color=TEXT_COLOR)
            m3 = Dot(number_line.n2p(5), color=TEXT_COLOR)
            
            self.play(FadeIn(number_line))
            self.play(FadeIn(m1, m2, m3))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # --- Scene 3: Constructing the Integrating Factor ---
        
        # Block 10
        self.play(FadeOut(exclusion, number_line, m1, m2, m3))
        # Move normalized equation to top for workspace
        self.play(final_std_form.animate.to_edge(UP, buff=1.5))
        
        with self.voiceover(text="Step 3: The Integrating Factor, mu of x.") as tracker:
            mu_label = MathTex(r"\mu(x)", color=MU_COLOR)
            equals_mu = MathTex("=")
            formula = MathTex(r"e^{\int p(x) dx}", color=MU_COLOR)
            mu_eq = VGroup(mu_label, equals_mu, formula).arrange(RIGHT).shift(UP*0.5)
            
            self.play(FadeIn(mu_eq))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 11
        with self.voiceover(text="We plug in our Yellow p(x) term.") as tracker:
            mu_step2 = MathTex(r"\mu(x) = e^{\int", r"\frac{2x}{x^2-9}", "dx}", color=TEXT_COLOR).move_to(mu_eq)
            mu_step2[1].set_color(PX_COLOR)
            self.play(Transform(mu_eq, mu_step2))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 12
        with self.voiceover(text="Using a simple u-substitution, the integral becomes the natural log of x-squared minus nine.") as tracker:
            side_math = VGroup(
                MathTex(r"u = x^2-9", font_size=28),
                MathTex(r"du = 2x dx", font_size=28),
                MathTex(r"\int \frac{1}{u} du = \ln|x^2-9|", font_size=28)
            ).arrange(DOWN, aligned_edge=LEFT).to_edge(RIGHT, buff=0.5).shift(UP*0.5)
            
            box = SurroundingRectangle(side_math, color=AXES_COLOR)
            self.play(FadeIn(box), FadeIn(side_math))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 13
        with self.voiceover(text="The exponential and the log cancel out, leaving us with our multiplier.") as tracker:
            mu_cancel = MathTex(r"\mu(x) =", "e", r"^{\ln", "|x^2-9|}", color=TEXT_COLOR).move_to(mu_eq)
            mu_final = MathTex(r"\mu(x) = x^2-9", color=MU_COLOR).move_to(mu_eq)
            
            self.play(Transform(mu_eq, mu_cancel))
            strike = Cross(mu_cancel[1:3], color=RED)
            self.play(Create(strike))
            self.play(FadeOut(strike), Transform(mu_eq, mu_final))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # --- Scene 4: General Solution Integration ---
        
        # Block 14
        self.play(FadeOut(side_math, box, final_std_form, mu_eq))
        
        with self.voiceover(text="Step 4: Multiply the standard form by mu of x.") as tracker:
            mult_eq = MathTex(r"(x^2-9) \left[ y' + \frac{2x}{x^2-9}y \right] = (x^2-9) \left[ \frac{1}{(x-5)(x^2-9)} \right]", font_size=32).to_edge(UP, buff=1.2)
            self.play(FadeIn(mult_eq))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 15
        with self.voiceover(text="The left side is now the perfect derivative of mu times y.") as tracker:
            lhs_deriv = MathTex(r"\frac{d}{dx} [ (x^2-9) y ]", color=SUCCESS_COLOR, font_size=36).move_to(mult_eq.get_left(), aligned_edge=LEFT).shift(DOWN*1.5 + RIGHT*0.5)
            self.play(FadeIn(lhs_deriv))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 16
        with self.voiceover(text="On the right, terms cancel out beautifully, leaving just a simple fraction.") as tracker:
            rhs_simp = MathTex(r"= \frac{1}{x-5}", color=TEXT_COLOR, font_size=36).next_to(lhs_deriv, RIGHT)
            self.play(FadeIn(rhs_simp))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 17
        with self.voiceover(text="Now, we integrate both sides.") as tracker:
            int_eq = MathTex(r"\int \frac{d}{dx}[(x^2-9)y] dx = \int \frac{1}{x-5} dx").move_to(VGroup(lhs_deriv, rhs_simp))
            self.play(FadeOut(lhs_deriv, rhs_simp), FadeIn(int_eq))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 18
        with self.voiceover(text="Don't forget the constant of integration, C.") as tracker:
            sol_step = MathTex(r"(x^2-9)y = \ln|x-5| + ", "C", color=TEXT_COLOR).move_to(int_eq)
            sol_step[1].set_color(PX_COLOR)
            
            self.play(FadeOut(int_eq), FadeIn(sol_step))
            int_eq = sol_step
            self.play(Indicate(sol_step[1]))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # --- Scene 5: Interval of Validity & Initial Value ---
        
        # Block 19
        self.play(FadeOut(mult_eq, sol_step))
        
        with self.voiceover(text="To find C, we use our initial condition y of 4 equals 2.") as tracker:
            plug_in = MathTex(r"2 = \frac{\ln|4-5|+C}{4^2-9}", color=TEXT_COLOR).shift(UP*2)
            self.play(FadeIn(plug_in))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 20
        with self.voiceover(text="Since the natural log of 1 is zero, C equals 14.") as tracker:
            c_val = MathTex(r"C = 14", color=SUCCESS_COLOR).next_to(plug_in, DOWN)
            final_sol = MathTex(r"y = \frac{\ln|x-5| + 14}{x^2-9}", color=SUCCESS_COLOR).next_to(c_val, DOWN, buff=0.5)
            self.play(FadeIn(c_val))
            self.play(FadeIn(final_sol))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 21
        self.play(FadeOut(plug_in, c_val, int_eq))
        
        with self.voiceover(text="Finally: Step 5. What is the Interval of Validity?") as tracker:
            final_sol.generate_target()
            final_sol.target.to_edge(UP).shift(LEFT*3)
            
            number_line_final = NumberLine(
                x_range=[-6, 8, 1],
                length=10,
                color=AXES_COLOR,
                include_numbers=True
            ).shift(DOWN*1)
            
            dots = VGroup(
                Dot(number_line_final.n2p(-3), color=RED),
                Dot(number_line_final.n2p(3), color=RED),
                Dot(number_line_final.n2p(5), color=RED)
            )
            
            self.play(MoveToTarget(final_sol))
            self.play(FadeIn(number_line_final))
            self.play(FadeIn(dots))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 22
        with self.voiceover(text="Our initial x is 4. We look for the largest continuous interval containing 4.") as tracker:
            init_dot = Dot(number_line_final.n2p(4), color=SUCCESS_COLOR)
            init_label = MathTex("x_0=4", font_size=24, color=SUCCESS_COLOR).next_to(init_dot, UP)
            self.play(FadeIn(init_dot), FadeIn(init_label))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 23
        with self.voiceover(text="The solution is only valid between the discontinuities at x equals 3 and x equals 5.") as tracker:
            valid_segment = Line(
                number_line_final.n2p(3), 
                number_line_final.n2p(5), 
                color=SUCCESS_COLOR, 
                stroke_width=8
            )
            interval_text = MathTex(r"3 < x < 5", color=SUCCESS_COLOR).next_to(valid_segment, DOWN, buff=0.5)
            
            self.play(FadeIn(valid_segment))
            self.play(FadeIn(interval_text))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Block 24
        with self.voiceover(text="Follow these five steps: Normalize, find discontinuities, calculate mu, integrate, and pick your interval based on x-nought.") as tracker:
            self.play(FadeOut(number_line_final, dots, init_dot, init_label, valid_segment))
            
            final_group = VGroup(final_sol, interval_text).arrange(DOWN)
            summary_box = SurroundingRectangle(final_group, color=SUCCESS_COLOR, buff=0.3)
            res_display = VGroup(summary_box, final_group).scale(0.8).to_edge(RIGHT, buff=1)
            
            roadmap_end = flowchart.copy().scale(0.8).to_edge(LEFT, buff=1)
            roadmap_end.set_color(SUCCESS_COLOR)
            
            self.play(
                FadeIn(roadmap_end),
                final_sol.animate.set_color(SUCCESS_COLOR).move_to(final_group[0]),
                interval_text.animate.set_color(SUCCESS_COLOR).move_to(final_group[1]),
                Create(summary_box)
            )
            self.wait(max(0.01, tracker.get_remaining_duration()))