"""DFA Visual Simulator - Main game loop with animated execution."""

import pygame
import math
from typing import Dict, Tuple, Optional

from dfa_engine import DFA, SimulationState, create_binary_dfa
from animator import Animator, AnimationState
from renderer import Renderer
from ui import UIManager, ExecutionMode


# Screen configuration
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 650
FPS = 60


def calculate_state_positions(dfa: DFA,
                              center_x: float, center_y: float,
                              radius: float = 150) -> Dict[str, Tuple[float, float]]:
    """
    Calculate positions for states arranged in a circle.
    For 2 states, arrange horizontally.
    """
    positions = {}
    states = list(dfa.states)
    n = len(states)

    if n == 0:
        return positions

    if n == 1:
        positions[states[0]] = (center_x, center_y)
        return positions

    if n == 2:
        # Place two states horizontally
        positions[states[0]] = (center_x - 100, center_y)
        positions[states[1]] = (center_x + 100, center_y)
        return positions

    # Arrange in a circle
    for i, state in enumerate(states):
        angle = 2 * math.pi * i / n - math.pi / 2  # Start from top
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        positions[state] = (x, y)

    return positions


class DFASimulator:
    """Main simulator class that coordinates all components."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("DFA Visual Simulator")
        self.clock = pygame.time.Clock()

        # Initialize components
        self.dfa = create_binary_dfa()  # DFA for strings ending with '01'
        self.simulation = SimulationState(self.dfa)
        self.renderer = Renderer(self.screen)
        self.animator = Animator()
        self.ui = UIManager(SCREEN_WIDTH, SCREEN_HEIGHT)

        # Calculate state positions (shifted down to make room for top status)
        self.state_positions = calculate_state_positions(
            self.dfa, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30
        )
        self.renderer.set_state_positions(self.state_positions)
        self.ui.set_alphabet(self.dfa.alphabet)

        # Simulation control
        self.pending_transition = False
        self.pending_from_state: Optional[str] = None
        self.pending_symbol: Optional[str] = None

        # Running state
        self.running = True

    def run(self):
        """Main game loop."""
        while self.running:
            dt = self.clock.tick(FPS)
            self.handle_events()
            self.update(dt)
            self.render()
            pygame.display.flip()

        pygame.quit()

    def handle_events(self):
        """Handle pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            action = self.ui.handle_event(event)
            if action == "start":
                self.start_simulation()
            elif action == "reset":
                self.reset_simulation()
            elif action == "step":
                self.step_simulation()
            elif action == "mode":
                self.reset_simulation()

    def start_simulation(self):
        """Start the simulation with current input."""
        input_text = self.ui.get_input_text()
        if not input_text:
            return

        if self.simulation.start(input_text):
            self.ui.set_buttons_disabled(True)
            self.animator.reset()

            if self.ui.execution_mode == ExecutionMode.AUTO:
                self.do_next_step()

    def reset_simulation(self):
        """Reset the simulation to initial state."""
        self.simulation.reset()
        self.animator.reset()
        self.pending_transition = False
        self.ui.set_buttons_disabled(False)
        self.ui.update_step_button_state()

    def step_simulation(self):
        """Execute one step in step mode."""
        if self.ui.execution_mode == ExecutionMode.STEP and not self.animator.is_moving():
            self.do_next_step()

    def do_next_step(self):
        """Execute the next simulation step."""
        if not self.simulation.is_running:
            return

        result = self.simulation.step()

        if result is None:
            # Simulation finished
            self.animator.finish_simulation()
            self.ui.set_buttons_disabled(False)
        else:
            from_state, symbol, to_state = result
            self.pending_from_state = from_state
            self.pending_symbol = symbol

            # Start animation
            start_pos = self.renderer.get_state_position(from_state)
            end_pos = self.renderer.get_state_position(to_state)
            self.animator.set_active_edge((from_state, to_state, symbol))
            self.animator.start_transition(start_pos, end_pos)

    def update(self, dt: float):
        """Update game state."""
        self.animator.update(dt)

        # Handle animation state transitions
        if self.animator.state == AnimationState.MOVING:
            pass  # Token is moving
        elif self.animator.state == AnimationState.IDLE and self.simulation.is_running:
            # Check if we just finished a transition
            if self.animator.token.progress >= 1.0 and self.pending_transition:
                self.pending_transition = False
                if self.ui.execution_mode == ExecutionMode.AUTO:
                    self.animator.start_pause(200)
            elif not self.animator.is_paused():
                # Ready for next step in auto mode
                if self.ui.execution_mode == ExecutionMode.AUTO and self.simulation.is_running:
                    self.do_next_step()
        elif self.animator.state == AnimationState.PAUSE:
            pass  # Waiting before next step
        elif self.animator.state == AnimationState.FINISHED:
            pass  # Show result

        # Update step button state
        if self.ui.execution_mode == ExecutionMode.STEP:
            self.ui.set_step_enabled(self.simulation.is_running and not self.animator.is_moving())

    def render(self):
        """Render the current frame."""
        self.renderer.clear()

        # Draw status at top first (background layer)
        if self.simulation.is_finished:
            status = "Simulation Complete"
        elif self.simulation.is_running:
            status = f"Processing: {self.simulation.input_string}"
        else:
            status = "Enter input string (0s and 1s)"
        self.renderer.draw_status(status)

        # Draw DFA graph
        self.renderer.draw_all_transitions(self.dfa, self.animator.active_edge)

        # Draw states
        for state in self.dfa.states:
            is_final = state in self.dfa.final_states
            is_current = state == self.simulation.current_state
            is_start = state == self.dfa.start_state

            # Determine status color
            status_color = None
            pulse_radius = None

            if is_current:
                if self.simulation.is_finished:
                    if self.simulation.accepted:
                        status_color = self.renderer.COLOR_ACCEPTED
                    else:
                        status_color = self.renderer.COLOR_REJECTED
                else:
                    status_color = self.renderer.COLOR_ACTIVE
                    pulse_radius = self.animator.current_pulse.current_radius

            self.renderer.draw_state(
                state,
                is_final=is_final,
                is_current=is_current,
                is_start=is_start,
                pulse_radius=pulse_radius,
                status_color=status_color
            )

        # Draw token if moving
        if self.animator.state == AnimationState.MOVING:
            self.renderer.draw_token(self.animator.token.current_pos)

        # Draw current symbol info
        if self.simulation.is_running and self.simulation.input_string:
            idx = min(self.simulation.current_index, len(self.simulation.input_string) - 1)
            symbol = self.simulation.input_string[idx]
            self.renderer.draw_current_symbol(symbol, idx, len(self.simulation.input_string))

        # Draw result if finished
        if self.animator.state == AnimationState.FINISHED:
            self.renderer.draw_result(
                self.simulation.accepted,
                alpha=self.animator.result_fade.alpha
            )

        # Draw UI
        self.renderer.draw_input_box(
            self.ui.input_box.rect,
            self.ui.get_input_text(),
            self.ui.input_box.is_active
        )

        self.renderer.draw_button(
            self.ui.start_button.rect,
            self.ui.start_button.label,
            self.ui.is_start_hovered(),
            self.ui.start_button.is_disabled
        )

        self.renderer.draw_button(
            self.ui.reset_button.rect,
            self.ui.reset_button.label,
            self.ui.is_reset_hovered()
        )

        self.renderer.draw_button(
            self.ui.mode_button.rect,
            self.ui.mode_button.label,
            self.ui.is_mode_hovered()
        )

        # Draw step button in step mode
        if self.ui.execution_mode == ExecutionMode.STEP:
            self.renderer.draw_button(
                self.ui.step_button.rect,
                self.ui.step_button.label,
                self.ui.is_step_hovered(),
                self.ui.step_button.is_disabled
            )


def main():
    """Entry point."""
    sim = DFASimulator()
    sim.run()


if __name__ == "__main__":
    main()
