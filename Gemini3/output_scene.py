from manim import *
from manim_voiceover import VoiceoverScene
from gemini_tts_service import GeminiTTSService

# Global Style Settings
config.background_color = "#0F172A"
PRIMARY_COLOR = "#F8FAFC"
HIGHLIGHT_PARTICULAR = "#FACC15"  # Yellow
HIGHLIGHT_HOMOGENEOUS = "#60A5FA" # Blue
HIGHLIGHT_DISCONTINUITY = "#F87171" # Red

class MyScene(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GeminiTTSService(
            model="gemini-2.5-flash-preview-tts",
            voice="Kore",
            style_context="You are narrating an educational math animation. Adapt your tone and pacing to match this description: This verbose anim",
        ))

        # --- Scene 1: Lecture Overview ---
        with self.voiceover(text="In this lecture, we will explore solving second order linear differential equations with piecewise forcing functions.") as tracker:
            title = MathTex(r"\text{Solving 2nd Order Linear ODEs}", color=PRIMARY_COLOR).to_edge(UP)
            eq_box = MathTex(r"a y'' + b y' + c y = g(t)", color=PRIMARY_COLOR).scale(1.2).shift(UP * 0.5)
            self.play(FadeIn(title))
            eq_rect = SurroundingRectangle(eq_box, color=PRIMARY_COLOR)
            self.play(FadeIn(eq_rect), FadeIn(eq_box))

        with self.voiceover(text="Note the difference between homogeneous and non-homogeneous cases, and how step functions require C1 continuity.") as tracker:
            sidebar = VGroup(
                MathTex(r"\text{Homogeneous: } g(t) = 0", font_size=30),
                MathTex(r"\text{Non-Homogeneous: } g(t) \neq 0", font_size=30),
                MathTex(r"\text{Step Function: } u(t-c)", font_size=30),
                MathTex(r"C^1 \text{ Continuity: } y, y' \text{ smooth}", font_size=30)
            ).arrange(DOWN, aligned_edge=LEFT).to_edge(LEFT).shift(DOWN * 1)
            self.play(FadeIn(sidebar))

        with self.voiceover(text="We follow a systematic flowchart: identify the forcing function, solve for the homogeneous solution, find the particular solution, and finally stitch the solutions at the jumps.") as tracker:
            box1 = MathTex(r"\text{Identify } g(t)", font_size=28)
            box2 = MathTex(r"\text{Solve Homogeneous } y_h", font_size=28)
            box3 = MathTex(r"\text{Find Particular } y_p", font_size=28)
            box4 = MathTex(r"\text{Stitch at Jumps}", font_size=28, color=HIGHLIGHT_DISCONTINUITY)
            
            flowchart = VGroup(box1, box2, box3, box4).arrange(DOWN, buff=0.6).to_edge(RIGHT).shift(DOWN * 1)
            arrows = VGroup(*[Arrow(flowchart[i].get_bottom(), flowchart[i+1].get_top(), buff=0.1) for i in range(len(flowchart)-1)])
            
            self.play(LaggedStart(FadeIn(flowchart), FadeIn(arrows), lag_ratio=0.5))
            self.play(Indicate(box4))
        
        self.wait(1)
        self.play(FadeOut(title, eq_box, eq_rect, sidebar, flowchart, arrows))

        # --- Scene 2: The Continuous Case ---
        with self.voiceover(text="Let's look at a continuous example: y double prime plus 3y prime plus 2y equals 4e to the t, with specific initial conditions.") as tracker:
            problem = MathTex(r"y'' + 3y' + 2y = 4e^t", color=PRIMARY_COLOR).to_corner(UL)
            ics = MathTex(r"y(0)=1, y'(0)=0", font_size=30).next_to(problem, DOWN, aligned_edge=LEFT)
            self.play(FadeIn(problem), FadeIn(ics))

        with self.voiceover(text="First, we find the homogeneous solution using the characteristic equation.") as tracker:
            char_eq = MathTex(r"r^2 + 3r + 2 = 0").shift(UP * 0.5)
            char_eq_fact = MathTex(r"(r+1)(r+2)=0").move_to(char_eq)
            roots = MathTex(r"r = -1, -2").next_to(char_eq_fact, DOWN)
            yh = MathTex(r"y_h(t) = c_1e^{-t} + c_2e^{-2t}", color=HIGHLIGHT_HOMOGENEOUS).next_to(roots, DOWN)
            
            self.play(FadeIn(char_eq))
            self.wait(0.5)
            self.play(ReplacementTransform(char_eq, char_eq_fact))
            self.play(FadeIn(roots), FadeIn(yh))

        with self.voiceover(text="For the particular solution, we guess y sub p equals A e to the t. Substituting this back gives 6A equals 4, so A is two thirds.") as tracker:
            particular_group = VGroup(
                MathTex(r"\text{Guess: } y_p = Ae^t"),
                MathTex(r"(A + 3A + 2A)e^t = 4e^t"),
                MathTex(r"6A = 4 \Rightarrow A = 2/3", color=HIGHLIGHT_PARTICULAR)
            ).arrange(DOWN).scale(0.85).next_to(yh, DOWN, buff=0.4)
            
            self.play(FadeIn(particular_group[0]))
            self.play(FadeIn(particular_group[1]))
            self.play(Indicate(particular_group[2]), FadeIn(particular_group[2]))

        with self.voiceover(text="The general solution combines both parts. Here is the plot for our specific initial conditions.") as tracker:
            gen_sol = MathTex(r"y(t) = c_1e^{-t} + c_2e^{-2t} + \frac{2}{3}e^t").to_edge(DOWN).shift(UP * 0.5)
            # Clear derivation steps to prevent overlap with gen_sol at bottom
            self.play(FadeOut(char_eq_fact, roots, yh, particular_group))
            self.play(FadeIn(gen_sol))
            self.wait(1)
            self.play(FadeOut(gen_sol))

            axes = Axes(x_range=[0, 3, 1], y_range=[0, 15, 5], axis_config={"color": PRIMARY_COLOR}).scale(0.7).shift(DOWN * 0.5)
            labels = axes.get_axis_labels()
            # Plot 1.66*exp(-2*x) - 1.33*exp(-x) + 0.66*exp(x)
            graph = axes.plot(lambda x: 1.66*np.exp(-2*x) - 1.33*np.exp(-x) + 0.66*np.exp(x), x_range=[0, 3], color=HIGHLIGHT_HOMOGENEOUS)
            self.play(FadeIn(axes), FadeIn(labels))
            self.play(FadeIn(graph))
        self.wait(1)
        self.play(FadeOut(problem, ics, axes, labels, graph))

        # --- Scene 3: Handling Discontinuity ---
        with self.voiceover(text="Now consider a discontinuous forcing function g of t. It jumps from five down to zero at t equals 2.") as tracker:
            axes3 = Axes(x_range=[0, 4, 1], y_range=[0, 6, 1]).scale(0.7).to_edge(UP)
            g1 = Line(axes3.c2p(0, 5), axes3.c2p(2, 5), color=HIGHLIGHT_PARTICULAR)
            g2 = Line(axes3.c2p(2, 0), axes3.c2p(4, 0), color=HIGHLIGHT_PARTICULAR)
            open_circle = Circle(radius=0.1, color=HIGHLIGHT_PARTICULAR).move_to(axes3.c2p(2, 5))
            closed_circle = Dot(axes3.c2p(2, 0), color=HIGHLIGHT_PARTICULAR)
            
            discon_line = DashedLine(axes3.c2p(2, 0), axes3.c2p(2, 6), color=HIGHLIGHT_DISCONTINUITY)
            self.play(FadeIn(axes3), FadeIn(g1), FadeIn(g2), FadeIn(open_circle), FadeIn(closed_circle))
            self.play(FadeIn(discon_line))

        with self.voiceover(text="At the discontinuity, the solution y of t must remain smooth, meaning both the function and its first derivative must be continuous.") as tracker:
            text_discon = Text("At t=2, g(t) is discontinuous. y(t) must be C1.", font_size=24, color=PRIMARY_COLOR).next_to(axes3, DOWN)
            logic = VGroup(
                MathTex(r"\lim_{t \to 2^-} y_1(t) = \lim_{t \to 2^+} y_2(t)"),
                MathTex(r"\lim_{t \to 2^-} y'_1(t) = \lim_{t \to 2^+} y'_2(t)")
            ).arrange(DOWN, buff=0.3).next_to(text_discon, DOWN)
            
            self.play(FadeIn(text_discon))
            self.play(FadeIn(logic))
            self.play(Indicate(closed_circle))

        self.wait(1)
        self.play(FadeOut(axes3, g1, g2, open_circle, closed_circle, discon_line, text_discon, logic))

        # --- Scene 4: Piecewise Example (Part 1) ---
        with self.voiceover(text="Let's solve a specific piecewise problem where the forcing function is 1 until pi, and 0 afterwards.") as tracker:
            main_eq = MathTex(r"y'' + y = \begin{cases} 1 & 0 \le t < \pi \\ 0 & t \ge \pi \end{cases}").to_edge(UP)
            label1 = Text("Interval 1: 0 <= t < pi", font_size=24).next_to(main_eq, DOWN)
            eq1 = MathTex(r"y'' + y = 1, \quad y(0)=0, y'(0)=0").next_to(label1, DOWN)
            self.play(FadeIn(main_eq))
            self.play(FadeIn(label1), FadeIn(eq1))

        with self.voiceover(text="In the first interval, the homogeneous solution is cosine plus sine, and the particular solution is 1. Solving for initial conditions gives y1 equals 1 minus cosine t.") as tracker:
            sol_comp = VGroup(
                MathTex(r"y_h = c_1\cos(t) + c_2\sin(t)"),
                MathTex(r"y_p = 1")
            ).arrange(DOWN).next_to(eq1, DOWN)
            
            solving_c = VGroup(
                MathTex(r"y(0) = c_1(1) + c_2(0) + 1 = 0 \Rightarrow c_1 = -1"),
                MathTex(r"y'(0) = -c_1(0) + c_2(1) = 0 \Rightarrow c_2 = 0")
            ).arrange(DOWN).next_to(sol_comp, DOWN)
            
            res1 = MathTex(r"y_1(t) = 1 - \cos(t)", color=HIGHLIGHT_HOMOGENEOUS).move_to(sol_comp)
            
            self.play(FadeIn(sol_comp))
            self.play(FadeIn(solving_c))
            self.wait(0.5)
            self.play(FadeOut(sol_comp, solving_c), FadeIn(res1))

        with self.voiceover(text="At the hand-off point pi, we calculate the values of y and y prime to use as initial conditions for the next interval.") as tracker:
            handoff_label = Text("At t = pi:", font_size=24).to_edge(LEFT).shift(DOWN * 1)
            handoff_vals = VGroup(
                MathTex(r"y_1(\pi) = 1 - (-1) = 2"),
                MathTex(r"y'_1(\pi) = \sin(\pi) = 0")
            ).arrange(DOWN).next_to(handoff_label, DOWN).set_color(HIGHLIGHT_DISCONTINUITY)
            
            self.play(FadeIn(handoff_label))
            self.play(FadeIn(handoff_vals))
            self.play(AnimationGroup(Indicate(handoff_vals[0]), Indicate(handoff_vals[1])))
        
        self.wait(1)
        saved_vals = handoff_vals.copy().to_corner(UR).scale(0.8)
        self.play(FadeOut(label1, eq1, res1, handoff_label, handoff_vals), FadeIn(saved_vals))

        # --- Scene 5: Piecewise Example (Part 2) ---
        with self.voiceover(text="Now for the second interval where t is greater than pi, the equation becomes homogeneous. We use our previous hand-off values as the new initial conditions.") as tracker:
            label2 = Text("Interval 2: t >= pi", font_size=24).next_to(main_eq, DOWN)
            eq2 = MathTex(r"y'' + y = 0").next_to(label2, DOWN)
            ics2 = MathTex(r"y_2(\pi) = 2, \quad y'_2(\pi) = 0").next_to(eq2, DOWN)
            self.play(FadeIn(label2), FadeIn(eq2))
            self.play(FadeIn(ics2))

        with self.voiceover(text="Solving the homogeneous equation with these conditions, we find that A is negative two and B is zero.") as tracker:
            y2_gen = MathTex(r"y_2(t) = A\cos(t) + B\sin(t)").next_to(ics2, DOWN)
            y2_solve1 = MathTex(r"A\cos(\pi) + B\sin(\pi) = 2 \Rightarrow -A = 2 \Rightarrow A = -2").next_to(y2_gen, DOWN, buff=0.4)
            y2_solve2 = MathTex(r"-A\sin(\pi) + B\cos(\pi) = 0 \Rightarrow -B = 0 \Rightarrow B = 0").next_to(y2_solve1, DOWN)
            
            self.play(FadeIn(y2_gen))
            self.play(FadeIn(y2_solve1))
            self.play(FadeIn(y2_solve2))
        
        with self.voiceover(text="This gives us y2 equals negative 2 cosine t. The final piecewise solution is shown here.") as tracker:
            res2 = MathTex(r"y_2(t) = -2\cos(t)", color=HIGHLIGHT_PARTICULAR).move_to(y2_gen)
            final_piecewise = MathTex(r"y(t) = \begin{cases} 1 - \cos(t) & 0 \le t < \pi \\ -2\cos(t) & t \ge \pi \end{cases}").scale(0.85).to_edge(DOWN).shift(UP * 0.5)
            
            self.play(FadeOut(y2_gen, y2_solve1, y2_solve2), FadeIn(res2))
            self.play(FadeIn(final_piecewise))
            
        self.wait(1)
        # Keep final_piecewise for Scene 6 as per blueprint
        self.play(FadeOut(main_eq, label2, eq2, ics2, res2, saved_vals))

        # --- Scene 6: Final Visualization ---
        with self.voiceover(text="Finally, let's visualize the complete stitched solution. Notice the smooth transition at pi.") as tracker:
            axes6 = Axes(x_range=[0, 2*PI, PI], y_range=[-2.5, 2.5, 1], x_length=6, y_length=4).to_edge(LEFT).shift(UP * 0.5)
            pi_label = MathTex(r"\pi").move_to(axes6.c2p(PI, -0.4))
            twopi_label = MathTex(r"2\pi").move_to(axes6.c2p(2*PI, -0.4))
            
            # Plot y1 = 1 - cos(t) [0, PI]
            graph1 = axes6.plot(lambda x: 1 - np.cos(x), x_range=[0, PI], color=HIGHLIGHT_HOMOGENEOUS)
            # Plot y2 = -2*cos(t) [PI, 2*PI]
            graph2 = axes6.plot(lambda x: -2 * np.cos(x), x_range=[PI, 2*PI], color=HIGHLIGHT_PARTICULAR)
            
            v_line = DashedLine(axes6.c2p(PI, -2.5), axes6.c2p(PI, 2.5), color=HIGHLIGHT_DISCONTINUITY)
            
            self.play(FadeIn(axes6), FadeIn(pi_label), FadeIn(twopi_label))
            self.play(FadeIn(graph1))
            self.play(FadeIn(v_line))
            self.play(FadeIn(graph2))

        with self.voiceover(text="To recap: solve the first phase, calculate boundary values, use them as initial conditions for the second phase, and state the final piecewise form.") as tracker:
            checklist = VGroup(
                MathTex(r"1. \text{ Solve Phase 1 } \checkmark"),
                MathTex(r"2. \text{ Boundary values } y, y' \checkmark"),
                MathTex(r"3. \text{ Use as ICs for Phase 2 } \checkmark"),
                MathTex(r"4. \text{ Final Piecewise Form } \checkmark")
            ).arrange(DOWN, aligned_edge=LEFT).scale(0.8).to_edge(RIGHT)
            
            for item in checklist:
                self.play(FadeIn(item))
                self.wait(0.2)
        
        self.wait(3)