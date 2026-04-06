"""
Experiment concerning vote tallying.
"""

# Python standard library
import csv
import random
import time

# Libraries
from petlib.ec import EcGroup

# Local files
from .common import (
    ensures_csv_exists,
    ensures_dir_exists,
    parse_arg_list_float,
    parse_arg_list_int,
)
from .logging import LOGGER
from .procedures.election_data import election_setup


MEASURE_PERFORMANCES_TALLY_TITLES = (
    "NumberVoters",
    "TallyTime",
    "VotesAgainst",
    "VotesFor",
    "Winner",
)

MEASURE_PERFORMANCES_TALLY_DELEGATION_TITLES = (
    "NumberVoters",
    "VoteDelegationPercent",
    "TallyTime",
    "VotesAgainst",
    "VotesFor",
    "Winner",
)


def measure_performances_tally(namespace):
    """Measure performances of tallying votes."""

    output_dir = namespace.out
    num_voters = parse_arg_list_int(namespace.num_voters)
    repetitions = namespace.repetitions

    ensures_dir_exists(output_dir)

    measurements = tally_execution_times(num_voters, n_repetitions=repetitions)

    filepath = output_dir / "tally.csv"

    ensures_csv_exists(filepath, MEASURE_PERFORMANCES_TALLY_TITLES)

    with filepath.open(mode="a+", newline="") as tally_fd:
        filewriter = csv.writer(
            tally_fd, delimiter=",", quotechar="|", quoting=csv.QUOTE_MINIMAL
        )
        for measurement in measurements:
            filewriter.writerow(measurement)

        tally_fd.flush()


def measure_performances_tally_delegation(namespace):
    """Measure performances of tallying votes with delegation."""

    output_dir = namespace.out
    num_voters = parse_arg_list_int(namespace.num_voters)
    repetitions = namespace.repetitions
    vote_delegation_percents = parse_arg_list_float(namespace.vote_delegation_percent)

    ensures_dir_exists(output_dir)

    measurements = []
    for vote_delegation_percent in vote_delegation_percents:
        measurements.extend(
            tally_delegation_times(
                num_voters,
                vote_delegation_percent,
                n_repetitions=repetitions,
            )
        )

    filepath = output_dir / "tally_delegation.csv"

    ensures_csv_exists(filepath, MEASURE_PERFORMANCES_TALLY_DELEGATION_TITLES)

    with filepath.open(mode="a+", newline="") as tally_fd:
        filewriter = csv.writer(
            tally_fd, delimiter=",", quotechar="|", quoting=csv.QUOTE_MINIMAL
        )
        for measurement in measurements:
            filewriter.writerow(measurement)

        tally_fd.flush()

def tally_execution_times(num_voters_l, curve_nid=415, n_repetitions=1):
    """Measure the execution time for tally operations."""

    group = EcGroup(curve_nid)

    measurements = list()

    for num_voters in num_voters_l:

        LOGGER.info("Running tally with %d voters.", num_voters)
        # Simulate already decrypted votes
        decrypted_votes = [
            random.choice([0, 1]) * group.generator() for _ in range(num_voters)
        ]

        for _ in range(n_repetitions):
            tally_start = time.process_time()

            tally_result = _tally_votes(decrypted_votes, group)

            tally_time = time.process_time() - tally_start

            winner = _determine_winner(tally_result[0], tally_result[1])

            measurements.append(
                [
                    num_voters,
                    tally_time,
                    tally_result[0],
                    tally_result[1],
                    winner,
                ]
            )

    return measurements

def _tally_votes(decrypted_votes, group):
    """
    Tally the decrypted votes

    :param decrypted_votes: List of decrypted vote group elements
    :param group: The elliptic curve group
    :return: Dictionary mapping vote choices to counts
    """
    tally = {0: 0, 1: 0}
    zero_vote = group.infinite()
    one_vote = group.generator()

    for vote in decrypted_votes:
        if vote == zero_vote:
            tally[0] += 1
        elif vote == one_vote:
            tally[1] += 1

    return tally

def tally_delegation_times(
    num_voters_l,
    vote_delegation_percent,
    curve_nid=415,
    security_param=128,
    n_repetitions=1,
):
    """Measure tally with delegation DAG, cycle removal, and election outcome."""

    group = EcGroup(curve_nid)

    measurements = list()

    for num_voters in num_voters_l:
        LOGGER.info(
            "Running delegation tally with %d voters and delegation percent %.2f.",
            num_voters,
            vote_delegation_percent,
        )

        vids, _ = election_setup(group, num_voters, security_param)

        # Generate already-decrypted choices outside timing
        voter_choices = {
            voter_vid: _make_delegated_choice(vote_delegation_percent, vids)
            for voter_vid in vids
        }

        for _ in range(n_repetitions):
            tally_start = time.process_time()

            direct_votes, delegation_edges = _build_delegation_structures(voter_choices)
            cycle_nodes = _find_cycle_nodes(delegation_edges)

            votes_against = 0
            votes_for = 0

            memo = {}
            for voter_vid in vids:
                resolved = _resolve_tallied_vote(
                    voter_vid,
                    direct_votes,
                    delegation_edges,
                    cycle_nodes,
                    memo,
                )

                if resolved == 0:
                    votes_against += 1
                elif resolved == 1:
                    votes_for += 1

            winner = _determine_winner(votes_against, votes_for)
            tally_time = time.process_time() - tally_start

            measurements.append(
                [
                    num_voters,
                    vote_delegation_percent,
                    tally_time,
                    votes_against,
                    votes_for,
                    winner,
                ]
            )

    return measurements

def _make_delegated_choice(vote_delegation_percent, vids):
    """Generate one already-decrypted choice: 0, 1, or delegated vid."""

    if random.random() < vote_delegation_percent:
        return random.choice(vids)

    return random.choice([0, 1])

def _build_delegation_structures(voter_choices):
    """Split choices into direct votes and delegation edges."""

    direct_votes = {}
    delegation_edges = {}

    for voter_vid, choice in voter_choices.items():
        if choice in (0, 1):
            direct_votes[voter_vid] = choice
        else:
            delegation_edges[voter_vid] = choice

    return direct_votes, delegation_edges

def _find_cycle_nodes(delegation_edges):
    """Return all voter vids that belong to a directed cycle."""

    cycle_nodes = set()
    state = {}  # 0=unvisited, 1=visiting, 2=done
    stack = []
    stack_pos = {}

    def depth_first_search(node):
        state[node] = 1
        stack_pos[node] = len(stack)
        stack.append(node)

        nxt = delegation_edges.get(node)
        if nxt is not None:
            nxt_state = state.get(nxt, 0)
            if nxt_state == 0:
                depth_first_search(nxt)
            elif nxt_state == 1:
                cycle_start = stack_pos[nxt]
                cycle_nodes.update(stack[cycle_start:])

        stack.pop()
        stack_pos.pop(node, None)
        state[node] = 2

    for node in delegation_edges:
        if state.get(node, 0) == 0:
            depth_first_search(node)

    return cycle_nodes

def _resolve_tallied_vote(voter_vid, direct_votes, delegation_edges, cycle_nodes, memo):
    """Resolve a voter's final direct vote (0/1), or None if dropped/unresolved."""

    if voter_vid in memo:
        return memo[voter_vid]

    if voter_vid in cycle_nodes:
        memo[voter_vid] = None
        return None

    if voter_vid in direct_votes:
        memo[voter_vid] = direct_votes[voter_vid]
        return memo[voter_vid]

    delegate_vid = delegation_edges.get(voter_vid)
    if delegate_vid is None:
        memo[voter_vid] = None
        return None

    if delegate_vid in cycle_nodes:
        memo[voter_vid] = None
        return None

    memo[voter_vid] = _resolve_tallied_vote(
        delegate_vid, direct_votes, delegation_edges, cycle_nodes, memo
    )
    return memo[voter_vid]

def _determine_winner(votes_against, votes_for):
    """Determine winner: 'for' wins ties."""
    if votes_for > votes_against:
        return "for"
    if votes_against > votes_for:
        return "against"
    return "tie"