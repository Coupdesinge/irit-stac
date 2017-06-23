import stats_create_tables as tables
import pandas as pd
#import numpy as np

FULL_RELATION_LIST = ['Acknowledgement', 'Alternation', 'Anaphora', 'Background', 'Clarification_question',
                     'Comment', 'Conditional', 'Continuation', 'Contrast', 'Correction', 'Elaboration',
                     'Explanation', 'Narration', 'Parallel', 'Q-Elab', 'Question-answer_pair', 'Result', 'Sequence']

ENDPOINTS_DICT = {'EDU': 'Segment', 'EEU': 'NonplayerSegment', 'CDU': 'Complex_discourse_unit'}

"""
to do:
CREATE PICKLES OF ALL THE TABLES TO DECREASE LOAD TIME
"""


def edu_helper(game):
    """

    :param game: game string
    :return: a single row of the final edu_count table: for a single game return the frequencies of
    segments by segment/version type
    """
    sit_table = tables.segs_situ.loc[tables.segs_situ['doc'] == game].groupby('type').size()
    spect_table = tables.segs_spect.loc[tables.segs_spect['doc'] == game].groupby('type').size()
    frame = pd.concat([spect_table, sit_table], axis=0)
    new_frame = frame.to_frame()
    new_frame.columns = [game]
    new_frame = new_frame.T
    new_frame.columns = ['spect EDUs', 'situated EEUs', 'situated EDUs']
    return new_frame


def edu_count(game='all'):
    """
    TO DO: ADD TOTALS COLUMN AT THE BOTTOM -- ADD AGGREGATE NUMBERS FOR SITUATED/SPECT SEGMENTS

    :param game: game string or list of game strings or 'all'
    :return: a table displaying frequencies different types of segments + versions
        ROWS == game
        COLUMNS == segment type + version
    """
    if game == 'all':
        all_tables = []
        for s in tables.sel_games:
            all_tables.append(edu_helper(s))
        frame = pd.concat(all_tables, axis=0)

    elif type(game) == list:
        all_tables = []
        for s in game:
            all_tables.append(edu_helper(s))
        frame = pd.concat(all_tables, axis=0)

    else:
        frame = edu_helper(game)

    return frame


def relation_helper(game, version, relations):
    """

    :param game: a game string
    :param version: a string specifiying 'spect', 'situated' or 'both'
    :param relations: a list of relations types (strings)
    :return: a single row of the final relation_count table: for a single game/version and set of relations the
    frequencies of the types of relations
    """
    tmp_table = None
    if version == 'situated':
        tmp_table = tables.rels_situ.loc[(tables.rels_situ['doc'] == game) & (tables.rels_situ['type'].isin(relations))].groupby('type').size()
    elif version == 'spect':
        tmp_table = tables.rels_spect.loc[(tables.rels_spect['doc'] == game) & (tables.rels_spect['type'].isin(relations))].groupby('type').size()
    tmp_table = tmp_table.to_frame()
    tmp_table.columns = [game + '_' + version]
    tmp_table = tmp_table.T
    return tmp_table


def relation_count(game='all', version='both', relations='all'):
    """

    :param game: a list of games (strings) or 'aggregate'
    :param version: a string specifiying 'spect', 'situated' or 'both'
    :param relations: a list of relation types (strings)
    :return: a table displaying frequencies of relations for each game/version
        ROWS == game/version
        COLUMNS == relation types
    ** if game= 'aggregate'
        ROWS == relation types
        COLUMNS == spect totals, situated totals, situated-spect
        -->rows ordered by situated-spect
    """

    if game == 'aggregate':

        if relations == 'all':
            relations = FULL_RELATION_LIST

        sit_tmp = tables.rels_situ.loc[tables.rels_situ['type'].isin(relations)].groupby('type').size()
        spect_tmp = tables.rels_spect.loc[tables.rels_spect['type'].isin(relations)].groupby('type').size()

        frame = pd.concat([spect_tmp, sit_tmp], axis=1)
        frame.fillna(value=0, inplace=True)
        frame.columns = ['spect', 'situated']
        frame['situated - spect'] = frame['situated'] - frame['spect']
        frame = frame.sort_values(by='situated - spect', ascending=0)
        #print(frame)

    else:

        if game == 'all':
            games = tables.sel_games
        else:
            games = game
        if relations == 'all':
            relations = FULL_RELATION_LIST

        if version == 'both':
            all_tables = []
            for s in games:
                all_tables.append(relation_helper(s, 'situated', relations))
                all_tables.append(relation_helper(s, 'spect', relations))
            frame = pd.concat(all_tables, axis=0)
            frame.fillna(value=0, inplace=True)

        else:
            all_tables = []
            for s in games:
                all_tables.append(relation_helper(s, version, relations))
            frame = pd.concat(all_tables, axis=0)
            frame.fillna(value=0, inplace=True)

    return frame


def endpoint_helper(games, version, endpoints, relations):
    """

    :param games: a list of games or 'all' to see whole corpus --> passed on from relation_endpoints()
    :param version: string 'spect' or 'situated'
    :param endpoints: tuple of endpoints, e.g. ('eeu', 'edu')
    :param relations: a list of relations
    :return: a single row of the final relation_endpoints table: for a single set of endpoints, the frequencies of
    the types of relations between them for a a given set of games and a version
    """

    tmp_table = None

    if games == 'all':
        games = tables.sel_games

    if version == 'situated':
        tmp_table = tables.rels_situ.loc[(tables.rels_situ['doc'].isin(games)) &
                                     (tables.rels_situ['source_type'] == ENDPOINTS_DICT[endpoints[0]]) &
                                         (tables.rels_situ['target_type'] == ENDPOINTS_DICT[endpoints[1]]) &
                                         (tables.rels_situ['type'].isin(relations))].groupby('type').size()
    elif version == 'spect':
        tmp_table = tables.rels_spect.loc[(tables.rels_spect['doc'].isin(games)) &
                                          (tables.rels_spect['source_type'] == ENDPOINTS_DICT[endpoints[0]]) &
                                          (tables.rels_spect['target_type'] == ENDPOINTS_DICT[endpoints[1]]) &
                                          (tables.rels_spect['type'].isin(relations))].groupby('type').size()
    tmp_table = tmp_table.to_frame()
    tmp_table.columns = [version + '__' + endpoints[0] + '-' + endpoints[1]]
    tmp_table = tmp_table.T

    return tmp_table


def relation_endpoints(games='all', version='both', endpoints='all', relations='all'):
    """

    :param games: a list of games or 'all' to see whole corpus
    :param version: a string indicating the version: 'situated', 'spect', or 'both'
    :param endpoints: a list of endpoint tuples, e.g. [(eeu, edu), (eeu, eeu)], or 'all'
    :param relations: a list of relation strings, e.g. ['Contrast', 'Parallel'], or 'all'
    :return: a table displaying frequencies of relations between segments of each kind
        ROWS == endpoint combinations
        COLUMNS == relation types
        -->columns ordered by Column Total
        -->rows ordered by Row Total
    """

    all_tables = []

    if relations == 'all':
        relations = FULL_RELATION_LIST

    if endpoints == 'all':
        endpoints = [('eeu', 'eeu'), ('eeu', 'edu'), ('eeu', 'cdu'),
                     ('edu', 'eeu'), ('edu', 'edu'), ('edu', 'cdu'),
                     ('cdu', 'eeu'), ('cdu', 'edu'), ('cdu', 'cdu')]

    if version == 'both':
        for e in endpoints:
            all_tables.append(endpoint_helper(games, 'spect', (e[0].upper(), e[1].upper()), relations))
            all_tables.append(endpoint_helper(games, 'situated', (e[0].upper(), e[1].upper()), relations))
    else:
        for e in endpoints:
            all_tables.append(endpoint_helper(games, version, (e[0].upper(), e[1].upper()), relations))

    frame = pd.concat(all_tables, axis=0)
    frame.fillna(value=0, inplace=True)
    frame.insert(0, 'Row Total', frame.sum(axis=1))
    frame.loc['Column Total'] = frame.sum()
    frame = frame.sort_values(by='Row Total')
    frame = frame.sort_values(by='Column Total', axis=1, ascending=False)

    return frame


def create_relation_span_table():
    #create a table with columns 'doc', 'subdoc', 'relation', 'endpoint1', 'endpoint2', distance
    return None


def game_size():

    return None


def orphan_count():
    #need to use the flattened versions of the game
    return None


def cdu_count():

    return None
