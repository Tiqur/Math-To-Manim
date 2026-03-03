from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService

# Set background color
config.background_color = "#111827"

class ExactDiffEq(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GTTSService(lang="en"))

        # --- Scene 1: Lecture Overview ---
        title = Title("Exact Differential Equations: Overview").to_edge(UP, buff=0.5)
        
        # Prerequisites
        prereq_title = Text("Prerequisites", font_size=32).to_edge(LEFT, buff=1.0).shift(UP * 0.5)
        item1 = Text("1. Partial Derivatives", font_size=24)
        item2 = Text("2. Integration", font_size=24)
        item3 = Text("3. The Chain Rule", font_size=24)
        prereqs = VGroup(item1, item2, item3).arrange(DOWN, aligned_edge=LEFT, buff=0.3).next_to(prereq_title, DOWN, aligned_edge=LEFT)
        
        # Standard Form
        m_part = MathTex(r"M(x,y)", color="#60A5FA")
        dx = MathTex(r"\,dx")
        plus = MathTex(r" + ")
        n_part = MathTex(r"N(x,y)", color="#FDE047")
        dy = MathTex(r"\,dy")
        eq_zero = MathTex(r" = 0")
        std_form = VGroup(m_part, dx, plus, n_part, dy, eq_zero).arrange(RIGHT, buff=0.1)
        std_form_group = VGroup(Text("Standard Form", font_size=32), std_form).arrange(DOWN, buff=0.5).to_edge(RIGHT, buff=1.0).shift(UP * 0.5)

        # Milestone Map
        def create_milestone(label):
            txt = Text(label, font_size=18)
            # Increased width buffer to 0.8 to prevent text touching edges
            rect = RoundedRectangle(height=0.7, width=max(1.8, txt.width + 0.8), corner_radius=0.35, color=WHITE)
            txt.move_to(rect.get_center())
            return VGroup(rect, txt)

        m1 = create_milestone("Test")
        m2 = create_milestone("Integrate")
        m3 = create_milestone("Differentiate")
        m4 = create_milestone("Solve g(y)")
        m5 = create_milestone("Assemble")
        milestones = VGroup(m1, m2, m3, m4, m5).arrange(RIGHT, buff=0.6).to_edge(DOWN, buff=0.5)
        
        # Blocks
        with self.voiceover(text="To solve an exact differential equation, we follow a rigorous 5-step process to find a hidden potential function.") as tracker:
            self.play(FadeIn(title))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        with self.voiceover(text="Before we dive in, make sure you're comfortable with partial derivatives and basic integration.") as tracker:
            self.play(FadeIn(prereq_title), FadeIn(prereqs))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        with self.voiceover(text="We start with an equation in this specific form, where M and N are functions of both x and y.") as tracker:
            self.play(FadeIn(std_form_group))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        with self.voiceover(text="Think of M as the part attached to dx, and N as the part attached to dy.") as tracker:
            self.play(Indicate(m_part), Indicate(n_part))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        with self.voiceover(text="Let's look at our roadmap. We'll start by testing for exactness, then work our way toward the general solution.") as tracker:
            self.play(FadeIn(milestones))
            self.play(m1[0].animate.set_stroke(width=8), run_time=0.5)
            self.play(m1[0].animate.set_stroke(width=4), run_time=0.5)
            self.wait(max(0.01, tracker.get_remaining_duration()))

        self.play(FadeOut(prereqs), FadeOut(prereq_title), FadeOut(std_form_group))

        # --- Scene 2: Step 1 - The Exactness Test ---
        step1_title = Title("Step 1: The Exactness Test").to_edge(UP, buff=0.5)
        rule = MathTex(r"\frac{\partial M}{\partial y} = \frac{\partial N}{\partial x}")
        rule_box = SurroundingRectangle(rule, buff=0.5, color=BLUE)
        rule_group = VGroup(rule, rule_box).to_edge(LEFT, buff=1.0)

        # Example - Shifted left to provide horizontal buffer for wide derivations
        ex_M = MathTex(r"(2xy + y^2)", color="#60A5FA")
        ex_dx = MathTex(r"dx")
        ex_plus = MathTex(r"+")
        ex_N = MathTex(r"(x^2 + 2xy)", color="#FDE047")
        ex_dy = MathTex(r"dy")
        ex_zero = MathTex(r"= 0")
        example_eq = VGroup(ex_M, ex_dx, ex_plus, ex_N, ex_dy, ex_zero).arrange(RIGHT, buff=0.1).to_edge(RIGHT, buff=1.5).shift(UP * 1.5)

        with self.voiceover(text="First, we check if the equation is actually 'exact.' This happens if the partial of M with respect to y equals the partial of N with respect to x.") as tracker:
            self.play(FadeOut(title), FadeIn(step1_title))
            self.play(FadeIn(rule_box), FadeIn(rule))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        with self.voiceover(text="Let's try this with an example. Here's our equation. Can you spot our M and N functions?") as tracker:
            self.play(FadeIn(example_eq))
            self.wait(2.0)
            self.play(ex_M.animate.scale(1.1), run_time=0.5)
            self.play(ex_M.animate.scale(1/1.1), run_time=0.5)
            self.play(ex_N.animate.scale(1.1), run_time=0.5)
            self.play(ex_N.animate.scale(1/1.1), run_time=0.5)
            self.wait(max(0.01, tracker.get_remaining_duration()))

        with self.voiceover(text="Exactly! M is our dx-term, and N is our dy-term.") as tracker:
            line_m = Underline(ex_M, color="#60A5FA")
            line_n = Underline(ex_N, color="#FDE047")
            self.play(FadeIn(line_m), FadeIn(line_n))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        with self.voiceover(text="Now, let's cross-differentiate. We take the derivative of M with respect to y.") as tracker:
            # Aligning derivatives for better comparison
            my_calc = MathTex(r"M_y", r"=", r"\frac{\partial}{\partial y}(2xy + y^2)", r"=", r"2x + 2y")
            nx_calc = MathTex(r"N_x", r"=", r"\frac{\partial}{\partial x}(x^2 + 2xy)", r"=", r"2x + 2y")
            
            # Positioned to the right of the rule box with tighter buff to ensure right-side safety
            derivs = VGroup(my_calc, nx_calc).arrange(DOWN, buff=0.5, aligned_edge=LEFT).next_to(rule_group, RIGHT, buff=0.6).shift(DOWN * 0.5)
            
            # Hide results initially
            my_calc[3:].set_opacity(0)
            nx_calc.set_opacity(0)
            
            self.play(FadeIn(my_calc[:3]))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        with self.voiceover(text="When we differentiate with respect to y, we treat x as a constant.") as tracker:
            self.play(my_calc[3:].animate.set_opacity(1))
            self.play(Indicate(my_calc[4]))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        with self.voiceover(text="We do the same for N, but with respect to x. Notice we get the exact same result: 2x plus 2y.") as tracker:
            self.play(FadeIn(nx_calc))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        with self.voiceover(text="Since they match, our equation is exact! We're cleared to move to the next step.") as tracker:
            # Checkmark positioned with reduced buff to prevent edge clipping
            checkmark = MathTex(r"\checkmark", color="#4ADE80").scale(2).next_to(derivs, RIGHT, buff=0.6)
            self.play(FadeIn(checkmark))
            self.play(m1[0].animate.set_color("#4ADE80"), m1[1].animate.set_color("#4ADE80"))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        self.play(FadeOut(rule_group), FadeOut(example_eq), FadeOut(derivs), FadeOut(checkmark), FadeOut(line_m), FadeOut(line_n))

        # --- Scene 3: Pitfall Alert ---
        pitfall_title = Title("What if it isn't Exact?").to_edge(UP, buff=0.5)
        with self.voiceover(text="But wait—what if those two partial derivatives don't match?") as tracker:
            self.play(FadeOut(step1_title), FadeIn(pitfall_title))
            bad_eq = MathTex(r"y", r"dx", r"-", r"x", r"dy", r"= 0").move_to(UP * 1.5)
            self.play(FadeIn(bad_eq))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        with self.voiceover(text="In this case, M-y is 1 and N-x is negative 1. They aren't equal, so the equation is NOT exact.") as tracker:
            comparison = MathTex(r"M_y = 1 \neq N_x = -1", color="#F87171").next_to(bad_eq, DOWN, buff=0.5)
            comp_box = SurroundingRectangle(comparison, color="#F87171")
            self.play(FadeIn(comp_box), FadeIn(comparison))
            self.play(Indicate(comparison))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        with self.voiceover(text="Don't panic! You'd usually need to find an 'integrating factor' to fix this.") as tracker:
            # Repositioned to prevent overlap with the comparison box and progress bar
            pro_tip = RoundedRectangle(corner_radius=0.1, color=PURPLE, height=1.5, width=6).move_to(DOWN * 1.5)
            pro_tip_text = Text("Pro-Tip: Integrating Factor", font_size=24, color=PURPLE).move_to(pro_tip.get_top() + DOWN * 0.3)
            mu_formula = MathTex(r"\mu(x) = e^{\int \frac{M_y - N_x}{N} dx}").move_to(pro_tip.get_center() + DOWN * 0.1)
            self.play(FadeIn(pro_tip), FadeIn(pro_tip_text), FadeIn(mu_formula))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        self.play(FadeOut(bad_eq), FadeOut(comparison), FadeOut(comp_box), FadeOut(pro_tip), FadeOut(pro_tip_text), FadeOut(mu_formula))

        # --- Scene 4: Step 2 - Partial Integration ---
        step2_title = Title("Step 2: Partial Integration").to_edge(UP, buff=0.5)
        
        # Checklist as per layout intent
        cl_item1 = MathTex(r"1. \text{ Test } \checkmark", color="#4ADE80", font_size=28)
        cl_item2 = MathTex(r"2. \text{ Integrate } M", color=WHITE, font_size=28)
        checklist = VGroup(cl_item1, cl_item2).arrange(DOWN, aligned_edge=LEFT, buff=0.4).to_edge(LEFT, buff=1.0).shift(UP * 0.5)
        cl_box = SurroundingRectangle(cl_item2, color=YELLOW, buff=0.15)

        with self.voiceover(text="Step 2 is to integrate M with respect to x to find our potential function, which we call Psi.") as tracker:
            self.play(FadeOut(pitfall_title), FadeIn(step2_title))
            self.play(FadeIn(checklist), FadeIn(cl_box))
            
            psi_lhs = MathTex(r"\Psi(x,y) =")
            psi_int = MathTex(r"\int (2xy + y^2) dx")
            psi_g = MathTex(r"+ g(y)", color=PURPLE)
            # Positioned on the RIGHT as per layout intent
            psi_setup = VGroup(psi_lhs, psi_int, psi_g).arrange(RIGHT).to_edge(RIGHT, buff=1.0).shift(UP * 1.5)
            self.play(FadeIn(psi_setup))
            self.play(m2[0].animate.set_stroke(width=8), run_time=0.5)
            self.play(m2[0].animate.set_stroke(width=4), run_time=0.5)
            self.wait(max(0.01, tracker.get_remaining_duration()))

        with self.voiceover(text="Integrating with respect to x gives us x-squared-y plus x-y-squared. We include g-of-y because any function of y would have vanished during our x-derivative.") as tracker:
            res_terms = MathTex(r"x^2y + xy^2").move_to(psi_int.get_center(), aligned_edge=LEFT)
            # Animate the transition without re-grouping to avoid jumps
            self.play(
                ReplacementTransform(psi_int, res_terms),
                psi_g.animate.next_to(res_terms, RIGHT, buff=0.2)
            )
            self.play(Indicate(psi_g))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        with self.voiceover(text="Our goal now is to figure out what that unknown function g-of-y actually is.") as tracker:
            brace = Brace(psi_g, DOWN)
            brace_text = Text("Unknown function of y", font_size=24).next_to(brace, DOWN)
            self.play(FadeIn(brace), FadeIn(brace_text))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        # Cleanup checklist and prep for split screen in Scene 5
        self.play(FadeOut(brace), FadeOut(brace_text), FadeOut(checklist), FadeOut(cl_box))
        self.play(VGroup(psi_lhs, res_terms, psi_g).animate.to_edge(LEFT, buff=1.0).shift(UP * 1))

        # --- Scene 5: Step 3 & 4 - Match & Solve ---
        step3_title = Title(r"Step 3 \& 4: Finding the Unknown").to_edge(UP, buff=0.5)
        with self.voiceover(text="To find g-of-y, we'll differentiate our current result with respect to y and compare it to our original N function.") as tracker:
            self.play(FadeOut(step2_title), FadeIn(step3_title))
            # Following split-screen intent: Target on the right
            target_box = SurroundingRectangle(MathTex(r"\Psi_y = x^2 + 2xy"), color=YELLOW, buff=0.3)
            psi_y_target = VGroup(Text("Target (N):", font_size=24), MathTex(r"x^2 + 2xy")).arrange(DOWN).to_edge(RIGHT, buff=1.0).shift(UP * 1.0)
            self.play(FadeIn(psi_y_target))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        with self.voiceover(text="Differentiating with respect to y, x-squared-y becomes x-squared, x-y-squared becomes 2xy, and g-of-y becomes g-prime.") as tracker:
            diff_label = MathTex(r"\Psi_y =")
            diff_term1 = MathTex(r"x^2")
            diff_term2 = MathTex(r"+ 2xy")
            diff_term3 = MathTex(r"+ g'(y)")
            # Clear layout on the left
            diff_result = VGroup(diff_label, diff_term1, diff_term2, diff_term3).arrange(RIGHT).next_to(psi_lhs, DOWN, buff=1.2, aligned_edge=LEFT)
            self.play(FadeIn(diff_result))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        with self.voiceover(text="Now, we set this equal to our original N. Take a look at both sides—do you see anything that might cancel out?") as tracker:
            # Single MathTex for perfect spacing and alignment - moved lower to avoid overlap
            full_match = MathTex(r"x^2", r"+ 2xy", r"+ g'(y)", r"=", r"x^2", r"+ 2xy").move_to(ORIGIN).shift(DOWN * 1.5)
            
            self.play(FadeIn(full_match))
            self.wait(2.0)
            # Alignment check: 0 and 4 are x^2, 1 and 5 are 2xy
            self.play(Circumscribe(full_match[0]), Circumscribe(full_match[4]))
            self.play(Circumscribe(full_match[1]), Circumscribe(full_match[5]))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        with self.voiceover(text="That's right! The x-squared and 2xy terms appear on both sides, so they cancel out completely.") as tracker:
            # Using Coral Red hex code as per blueprint, targeting the correct indices in full_match
            cross1 = Line(full_match[0].get_corner(DL), full_match[0].get_corner(UR), color="#F87171")
            cross2 = Line(full_match[4].get_corner(DL), full_match[4].get_corner(UR), color="#F87171")
            cross3 = Line(full_match[1].get_corner(DL), full_match[1].get_corner(UR), color="#F87171")
            cross4 = Line(full_match[5].get_corner(DL), full_match[5].get_corner(UR), color="#F87171")
            self.play(FadeIn(cross1), FadeIn(cross2), FadeIn(cross3), FadeIn(cross4))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        with self.voiceover(text="This leaves us with g-prime equals zero. Integrating that gives us a simple constant, which we'll call C-1.") as tracker:
            # Use Mint Green hex to match Scene 2 consistency
            g_final = MathTex(r"g(y) = C_1", color="#4ADE80").next_to(full_match, DOWN, buff=0.5)
            self.play(FadeIn(g_final))
            self.play(
                m2[0].animate.set_color("#4ADE80"), m2[1].animate.set_color("#4ADE80"),
                m3[0].animate.set_color("#4ADE80"), m3[1].animate.set_color("#4ADE80"),
                m4[0].animate.set_color("#4ADE80"), m4[1].animate.set_color("#4ADE80"),
            )
            self.wait(max(0.01, tracker.get_remaining_duration()))

        self.play(FadeOut(step2_title), FadeOut(psi_y_target), FadeOut(diff_result), FadeOut(full_match), FadeOut(cross1), FadeOut(cross2), FadeOut(cross3), FadeOut(cross4), FadeOut(g_final))

        # --- Scene 6: Final Assembly ---
        step5_title = Title(r"Step 5: The General Solution").to_edge(UP, buff=0.5)
        with self.voiceover(text="We assemble our terms into the full potential function. But we aren't quite finished with the standard form.") as tracker:
            self.play(FadeOut(step3_title), FadeIn(step5_title))
            final_psi = MathTex(r"\Psi(x,y) = x^2y + xy^2 + C_1").next_to(step5_title, DOWN, buff=0.5)
            self.play(FadeIn(final_psi))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        with self.voiceover(text="The general solution to an exact equation is usually written implicitly as Psi equals a constant C.") as tracker:
            implicit_sol = MathTex(r"x^2y + xy^2 = C").scale(1.2).move_to(ORIGIN)
            box = SurroundingRectangle(implicit_sol, color=GREEN, buff=0.3)
            self.play(FadeOut(final_psi), FadeIn(implicit_sol))
            self.play(FadeIn(box))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        with self.voiceover(text="Visually, these are level curves. Each curve represents a different value for our constant C.") as tracker:
            self.play(VGroup(implicit_sol, box).animate.to_edge(RIGHT, buff=1.0).scale(0.8))
            # Increased scale and adjusted ranges to ensure curves stay within visual boundaries
            axes = Axes(x_range=[0, 5, 1], y_range=[0, 5, 1], axis_config={"include_tip": False}).scale(0.7).to_edge(LEFT, buff=0.8).shift(UP * 0.5)
            
            # y = C / (x^2 + x) simplified curves with adjusted constants to prevent geometry clipping
            curves = VGroup()
            colors = [BLUE, GREEN, YELLOW, ORANGE, RED]
            for i, c_val in enumerate([0.5, 1.5, 3, 5, 8]):
                # x_range start adjusted per C to keep y <= 5
                x_start = max(0.4, (np.sqrt(1 + 4*c_val/5) - 1)/2)
                curve = axes.plot(lambda x: c_val / (x**2 + x), x_range=[x_start, 5], color=colors[i])
                curves.add(curve)
            
            self.play(FadeIn(axes), FadeIn(curves))
            self.wait(max(0.01, tracker.get_remaining_duration()))

        with self.voiceover(text="Great work! Just remember: Test, Integrate, Differentiate, Match, and Assemble.") as tracker:
            self.play(m5[0].animate.set_color(GREEN), m5[1].animate.set_color(GREEN))
            self.play(LaggedStart(*[Indicate(m) for m in milestones], lag_ratio=0.1))
            self.play(FadeOut(axes), FadeOut(curves), FadeOut(milestones))
            self.play(VGroup(implicit_sol, box).animate.move_to(ORIGIN).scale(1.5))
            self.wait(max(0.01, tracker.get_remaining_duration()))