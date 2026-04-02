"""UI Module - Input handling and UI controls."""

import pygame
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum, auto


class ExecutionMode(Enum):
    """Simulation execution mode."""
    AUTO = auto()
    STEP = auto()


@dataclass
class Button:
    """Represents a clickable button."""
    rect: pygame.Rect
    label: str
    is_disabled: bool = False

    def contains_point(self, pos: Tuple[int, int]) -> bool:
        """Check if point is inside button."""
        return self.rect.collidepoint(pos)

    def is_hovered(self, mouse_pos: Tuple[int, int]) -> bool:
        """Check if mouse is hovering over button."""
        return not self.is_disabled and self.rect.collidepoint(mouse_pos)


@dataclass
class InputBox:
    """Represents a text input box."""
    rect: pygame.Rect
    text: str = ""
    is_active: bool = False
    alphabet: set[str] = None

    def __post_init__(self):
        if self.alphabet is None:
            self.alphabet = set()

    def contains_point(self, pos: Tuple[int, int]) -> bool:
        """Check if point is inside input box."""
        return self.rect.collidepoint(pos)

    def handle_click(self, pos: Tuple[int, int]) -> bool:
        """Handle click event, return True if clicked."""
        if self.rect.collidepoint(pos):
            self.is_active = True
            return True
        self.is_active = False
        return False

    def handle_text(self, char: str) -> bool:
        """Handle text input, return True if text changed."""
        if not self.is_active:
            return False

        # Only allow valid alphabet characters
        if char.lower() in self.alphabet or char in self.alphabet:
            self.text += char
            return True
        return False

    def handle_backspace(self) -> bool:
        """Handle backspace, return True if text changed."""
        if not self.is_active:
            return False
        if self.text:
            self.text = self.text[:-1]
            return True
        return False

    def set_alphabet(self, alphabet: set[str]) -> None:
        """Set the allowed alphabet for input validation."""
        self.alphabet = alphabet

    def clear(self) -> None:
        """Clear the input text."""
        self.text = ""
        self.is_active = False


class UIManager:
    """Manages all UI elements and input handling."""

    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Input box
        input_width = 300
        input_height = 40
        input_x = (screen_width - input_width) // 2
        input_y = screen_height - 120
        self.input_box = InputBox(
            pygame.Rect(input_x, input_y, input_width, input_height)
        )

        # Buttons
        button_width = 100
        button_height = 40
        button_y = screen_height - 60

        # Start button
        self.start_button = Button(
            pygame.Rect(screen_width // 2 - button_width - 10, button_y,
                       button_width, button_height),
            "Start"
        )

        # Reset button
        self.reset_button = Button(
            pygame.Rect(screen_width // 2 + 10, button_y,
                       button_width, button_height),
            "Reset"
        )

        # Mode toggle button
        self.mode_button = Button(
            pygame.Rect(20, button_y, 120, button_height),
            "Mode: Auto"
        )

        # Step button (for step mode)
        self.step_button = Button(
            pygame.Rect(screen_width // 2 - 50, button_y + 50, 100, 35),
            "Step"
        )

        self.execution_mode = ExecutionMode.AUTO

    def set_alphabet(self, alphabet: set[str]) -> None:
        """Set the allowed alphabet for input validation."""
        self.input_box.set_alphabet(alphabet)

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """
        Handle pygame event.
        Returns action string if an action was triggered.
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                pos = pygame.mouse.get_pos()

                # Check input box click
                if self.input_box.handle_click(pos):
                    return None

                # Check button clicks
                if self.start_button.contains_point(pos) and not self.start_button.is_disabled:
                    return "start"

                if self.reset_button.contains_point(pos):
                    return "reset"

                if self.mode_button.contains_point(pos):
                    self.toggle_mode()
                    return "mode"

                if self.step_button.contains_point(pos) and not self.step_button.is_disabled:
                    return "step"

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.input_box.handle_backspace()
            elif event.key == pygame.K_RETURN:
                if not self.start_button.is_disabled:
                    return "start"
            elif event.unicode and self.input_box.is_active:
                self.input_box.handle_text(event.unicode)

        return None

    def toggle_mode(self) -> None:
        """Toggle between Auto and Step mode."""
        if self.execution_mode == ExecutionMode.AUTO:
            self.execution_mode = ExecutionMode.STEP
            self.mode_button.label = "Mode: Step"
        else:
            self.execution_mode = ExecutionMode.AUTO
            self.mode_button.label = "Mode: Auto"

    def get_mouse_pos(self) -> Tuple[int, int]:
        """Get current mouse position."""
        return pygame.mouse.get_pos()

    def is_start_hovered(self) -> bool:
        """Check if start button is hovered."""
        return self.start_button.is_hovered(self.get_mouse_pos())

    def is_reset_hovered(self) -> bool:
        """Check if reset button is hovered."""
        return self.reset_button.is_hovered(self.get_mouse_pos())

    def is_mode_hovered(self) -> bool:
        """Check if mode button is hovered."""
        return self.mode_button.is_hovered(self.get_mouse_pos())

    def is_step_hovered(self) -> bool:
        """Check if step button is hovered."""
        return self.step_button.is_hovered(self.get_mouse_pos())

    def set_buttons_disabled(self, disabled: bool) -> None:
        """Enable or disable the start button."""
        self.start_button.is_disabled = disabled
        if disabled:
            self.step_button.is_disabled = True
        else:
            self.step_button.is_disabled = (self.execution_mode == ExecutionMode.AUTO)

    def set_step_enabled(self, enabled: bool) -> None:
        """Enable or disable the step button."""
        self.step_button.is_disabled = not enabled

    def get_input_text(self) -> str:
        """Get current input text."""
        return self.input_box.text

    def clear_input(self) -> None:
        """Clear the input box."""
        self.input_box.clear()

    def update_step_button_state(self) -> None:
        """Update step button enabled state based on mode."""
        if self.execution_mode == ExecutionMode.STEP:
            self.step_button.is_disabled = False
        else:
            self.step_button.is_disabled = True
