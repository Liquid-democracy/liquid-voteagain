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
from .common import ensures_csv_exists, ensures_dir_exists, parse_arg_list_int
from .logging import LOGGER
from .primitives import elgamal
from .procedures.election_data import election_setup, make_vote


MEASURE_PERFORMANCES_TALLY_TITLES = (
    "NumberVoters",
    "TallyTime",
)

MEASURE_PERFORMANCES_TALLY_DELEGATION_TITLES = (
    "NumberVoters",
    "VoteDelegationPercent",
    "NumberVotesCreated",
    "VoteVectorLength",
    "SetupTime",
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
    vote_delegation_percent = float(namespace.vote_delegation_percent)

    if vote_delegation_percent <= 0.0 or vote_delegation_percent > 1.0:
        raise ValueError("vote_delegation_percent must be in (0.0, 1.0].")

    ensures_dir_exists(output_dir)

    measurements = tally_delegation_times(
        num_voters,
        vote_delegation_percent,
        n_repetitions=repetitions,
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


def build_delegated_votes_setup(pk, vids, group, vote_delegation_percent):
    """Build one vote per voter using delegation-aware vote creation."""

    return [make_vote(vote_delegation_percent, pk, vids, group) for _ in vids]


def tally_delegation_times():
    measurements = list()

    return measurements


def tally_execution_times(num_voters_l, curve_nid=415, n_repetitions=1):
    """Measure the execution time for tally operations."""

    group = EcGroup(curve_nid)

    measurements = list()

    for num_voters in num_voters_l:

        LOGGER.info("Running tally with %d voters.", num_voters)
        '''
        For testing purposes, we simulate decrypted votes as random group elements correspondingto votes 0 or 1
        In a real scenario, these would be the result of decrypting the encrypted votes
        '''
        decrypted_votes = [random.choice([0, 1]) * group.generator() for _ in range(num_voters)]
        
        for _ in range(n_repetitions):
            tally_start = time.process_time()
            
            tally_result = _tally_votes(decrypted_votes, group)
            
            tally_time = time.process_time() - tally_start
            
            measurements.append([num_voters, tally_time])

    return measurements


def _tally_votes(decrypted_votes, group):
    """
    Tally the decrypted votes.
    
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
        else:
            raise ValueError("Unexpected vote encoding in tally input.")

    return tally
