#import stats_create_tables as tables
import pandas as pd
import pickle
import os
#import numpy as np


FULL_RELATION_LIST = ['Acknowledgement', 'Alternation', 'Anaphora', 'Background', 'Clarification_question',
                     'Comment', 'Conditional', 'Continuation', 'Contrast', 'Correction', 'Elaboration',
                     'Explanation', 'Narration', 'Parallel', 'Q-Elab', 'Question-answer_pair', 'Result', 'Sequence']

ENDPOINTS_DICT = {'EDU': 'Segment', 'EEU': 'NonplayerSegment', 'CDU': 'Complex_discourse_unit'}

current_dir = os.getcwd()
pickle_path = current_dir + '/stac_data_pickles/'

pkl_file = open(pickle_path + 'turns_situ.pkl', 'rb')
turns_situ = pickle.load(pkl_file)
pkl_file = open(pickle_path + 'dlgs_situ.pkl', 'rb')
dlgs_situ = pickle.load(pkl_file)
pkl_file = open(pickle_path + 'segs_situ.pkl', 'rb')
segs_situ = pickle.load(pkl_file)
pkl_file = open(pickle_path + 'acts_situ.pkl', 'rb')
acts_situ = pickle.load(pkl_file)
pkl_file = open(pickle_path + 'schms_situ.pkl', 'rb')
schms_situ = pickle.load(pkl_file)
pkl_file = open(pickle_path + 'schm_mbrs_situ.pkl', 'rb')
schm_mbrs_situ = pickle.load(pkl_file)
pkl_file = open(pickle_path + 'rels_situ.pkl', 'rb')
rels_situ = pickle.load(pkl_file)
pkl_file = open(pickle_path + 'res_situ.pkl', 'rb')
res_situ = pickle.load(pkl_file)
pkl_file = open(pickle_path + 'pref_situ.pkl', 'rb')
pref_situ = pickle.load(pkl_file)

pkl_file = open(pickle_path + 'turns_spect.pkl', 'rb')
turns_spect = pickle.load(pkl_file)
pkl_file = open(pickle_path + 'dlgs_spect.pkl', 'rb')
dlgs_spect = pickle.load(pkl_file)
pkl_file = open(pickle_path + 'segs_spect.pkl', 'rb')
segs_spect = pickle.load(pkl_file)
pkl_file = open(pickle_path + 'acts_spect.pkl', 'rb')
acts_spect = pickle.load(pkl_file)
pkl_file = open(pickle_path + 'schms_spect.pkl', 'rb')
schms_spect = pickle.load(pkl_file)
pkl_file = open(pickle_path + 'schm_mbrs_spect.pkl', 'rb')
schm_mbrs_spect = pickle.load(pkl_file)
pkl_file = open(pickle_path + 'rels_spect.pkl', 'rb')
rels_spect = pickle.load(pkl_file)
pkl_file = open(pickle_path + 'res_spect.pkl', 'rb')
res_spect = pickle.load(pkl_file)
pkl_file = open(pickle_path + 'pref_spect.pkl', 'rb')
pref_spect = pickle.load(pkl_file)

pkl_file.close()

print("data tables opened...")

GAMES = sorted(list(set(segs_situ['doc'])))

print("Games Available: ")

for g in GAMES:
    print(g)


def edu_helper(game):
    """

    :param game: game string
    :return: a single row of the final edu_count table: for a single game return the frequencies of
    segments by segment/version type
    """
    sit_table = segs_situ.loc[segs_situ['doc'] == game].groupby('type').size()
    spect_table = segs_spect.loc[segs_spect['doc'] == game].groupby('type').size()
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
        for s in GAMES:
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
        tmp_table = rels_situ.loc[(rels_situ['doc'] == game) & (rels_situ['type'].isin(relations))].groupby('type').size()
    elif version == 'spect':
        tmp_table = rels_spect.loc[(rels_spect['doc'] == game) & (rels_spect['type'].isin(relations))].groupby('type').size()
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

        sit_tmp = rels_situ.loc[rels_situ['type'].isin(relations)].groupby('type').size()
        spect_tmp = rels_spect.loc[rels_spect['type'].isin(relations)].groupby('type').size()

        frame = pd.concat([spect_tmp, sit_tmp], axis=1)
        frame.fillna(value=0, inplace=True)
        frame.columns = ['spect', 'situated']
        frame['situated - spect'] = frame['situated'] - frame['spect']
        frame = frame.sort_values(by='situated - spect', ascending=0)
        #print(frame)

    else:

        if game == 'all':
            games = GAMES
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
        games = GAMES

    if version == 'situated':
        tmp_table = rels_situ.loc[(rels_situ['doc'].isin(games)) &
                                  (rels_situ['source_type'] == ENDPOINTS_DICT[endpoints[0]]) &
                                (rels_situ['target_type'] == ENDPOINTS_DICT[endpoints[1]]) &
                                (rels_situ['type'].isin(relations))].groupby('type').size()
    elif version == 'spect':
        tmp_table = rels_spect.loc[(rels_spect['doc'].isin(games)) &
                                          (rels_spect['source_type'] == ENDPOINTS_DICT[endpoints[0]]) &
                                          (rels_spect['target_type'] == ENDPOINTS_DICT[endpoints[1]]) &
                                          (rels_spect['type'].isin(relations))].groupby('type').size()
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
