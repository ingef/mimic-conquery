"""defined actions and a list of actions arranged in the order of execution"""
from attr import define
from typing import Callable, Optional, Set


# action names starting with this tag are excluded
exclude_tag = "^"


# define actions here
@define
class Action:
    name: str
    callable: Callable

    def __hash__(self):
        return hash(repr(self))

    def __eq__(self, other):
        return self.name == other.name


def get_action(name: Optional[str], all_actions: Set[Action]) -> Action:
    """Returns the action with this name."""
    avail = [action for action in all_actions if action.name == name]
    if not avail:
        raise ValueError(f"Did not find an action with name {name}")

    return avail[0]


def get_actions(subset: Set[str], all_actions: Set[Action]) -> Set[Action]:
    """Returns the actions with these names."""
    return {action for action in all_actions if action.name in subset}
