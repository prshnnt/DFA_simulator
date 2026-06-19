# Usage guide

This guide walks through the bundled example DFA and shows how to swap in
your own.

## The bundled DFA

`create_binary_dfa` builds a three-state DFA over the alphabet `{0, 1}`
that accepts exactly the binary strings whose length is divisible by 3.

```
states:    q0, q1, q2
start:     q0
final:     {q0}
alphabet:  {0, 1}

transitions:
  q0 --0--> q1
  q0 --1--> q0
  q1 --0--> q1
  q1 --1--> q2
  q2 --0--> q1
  q2 --1--> q0
```

Intuitively, each transition advances a counter modulo 3: the only way back
to the accepting start state `q0` is to consume a total of 3, 6, 9, … symbols.

### Try these inputs

| Input   | Result   | Reason                              |
|---------|----------|-------------------------------------|
| `""`    | ACCEPTED | Empty string has length 0 (≡ 0 mod 3) |
| `0`     | REJECTED | Length 1                            |
| `11`    | REJECTED | Length 2                            |
| `111`   | ACCEPTED | Length 3                            |
| `0101`  | REJECTED | Length 4                            |
| `111111`| ACCEPTED | Length 6                            |
| `1110`  | REJECTED | Length 4                            |

### Step mode vs Auto mode

- **Auto**: the simulator queues the next step as soon as the current
  token animation finishes. Sit back and watch.
- **Step**: each click of **Step** advances one transition. Useful for
  teaching or for verifying that a particular edge is taken.

## Building your own DFA

The `DFA` class is the only piece you need to touch. Example: a DFA that
accepts binary strings containing the substring `01`.

```python
from main import DFA, DFASimulator

def create_contains_01() -> DFA:
    dfa = DFA()
    dfa.start_state = "q0"
    dfa.final_states = {"q2"}
    # q0: nothing useful seen yet
    dfa.add("q0", "0", "q0")
    dfa.add("q0", "1", "q1")
    # q1: just saw a 1
    dfa.add("q1", "0", "q2")
    dfa.add("q1", "1", "q1")
    # q2: already saw 01 — stay here forever
    dfa.add("q2", "0", "q2")
    dfa.add("q2", "1", "q2")
    return dfa
```

Then in `DFASimulator.__init__`, swap the factory call:

```python
self.dfa = create_contains_01()
```

The input box automatically restricts typed characters to whatever symbols
appear in `dfa.alphabet`, so you do not need to do anything else.

### Layout limits

`calc_positions` arranges states evenly around a circle. With more than
about eight states the labels start to overlap; for larger DFAs, replace the
layout function with your own coordinate computation.

## Keyboard shortcuts

| Key          | Effect                       |
|--------------|------------------------------|
| `0` / `1`    | Add a symbol to the input    |
| `Backspace`  | Delete the last symbol       |
| `Enter`      | Start the simulation         |

The close-window button is the only way to quit.