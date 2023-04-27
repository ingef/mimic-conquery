import argparse
from typing import Dict, Any, Set, List

from actions.actions_def import Action, get_actions, get_action


def configure_arg_parser_for_actions(arg_parser: argparse.ArgumentParser, default: Set[str], exclude_tag: str):
    """
    Configures arg_parser to accept either a subset (--action) or a range (--from/--to) of actions.
    The range option can be defined with either --from action or --to action.
    The subset option can exclude actions by prepending an exclude-tag to each action.
    It is an error when a subset contains both requested and excluded actions.
    Specifying neither a subset nor a range executes all actions.
    Using --action without arguments executes all actions.
    --do is an alias of --action.
    """
    # available choices for argParse
    choices = {exclude_tag + name for name in default}
    choices |= default

    default_text = ", ".join(default)

    group = arg_parser.add_mutually_exclusive_group()
    group.add_argument('--actions', '--do', nargs='*', choices=choices, metavar='Action',
                       help=f'Import actions out of: {default_text}. ' + "\n" +
                            f'Exclude actions by prepending `{exclude_tag}`: e.g. `{exclude_tag}cqpp`')

    group.add_argument('--from', choices=choices, metavar='Action',
                       help=f'Select the starting action out of: {default_text}.')

    group.add_argument('--to', choices=choices, metavar='Action',
                       help=f'Select the final action out of: {default_text}.')


def get_request(args: Dict[str, Any], all_actions: List[Action], exclude_tag: str) -> Set[Action]:
    """Retrieves the set of requested actions from the arg_dict."""
    actions = args.get('actions') or []
    subset = {action for action in actions if not action.startswith(exclude_tag)}
    excluded_subset = {action[len(exclude_tag):] for action in actions if action.startswith(exclude_tag)}

    if subset and excluded_subset:
        raise argparse.ArgumentError(
            None, message=f'Actions should only be either selected or excluded.\n '
                          f'Selected: {subset}\n '
                          f'Excluded: {excluded_subset}')

    if excluded_subset:
        subset = {action.name for action in all_actions} - excluded_subset

    if subset:
        return get_actions(subset, set(all_actions))

    index = {act: index for act, index in zip(all_actions, range(0, len(all_actions)))}

    start = args['from']
    end = args['to']

    if start:
        start_index = index[get_action(start, set(all_actions))]
        return {action for action in all_actions if start_index <= index[action]}

    if end:
        end_index = index[get_action(end, set(all_actions))]
        return {action for action in all_actions if end_index >= index[action]}

    return set(all_actions)
