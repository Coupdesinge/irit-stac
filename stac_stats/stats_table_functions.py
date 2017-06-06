import stats_create_tables as tables
import pandas as pd
import numpy as np

FULL_RELATION_LIST = ['Acknowledgement', 'Alternation', 'Anaphora', 'Background', 'Clarification_question',
                     'Comment', 'Conditional', 'Continuation', 'Contrast', 'Correction', 'Elaboration',
                     'Explanation', 'Narration', 'Parallel', 'Q-Elab', 'Question-answer_pair', 'Result', 'Sequence']


def edu_helper(game):
    sit_table = tables.segs_situ.loc[tables.segs_situ['doc'] == game].groupby('type').size()
    spect_table = tables.segs_spect.loc[tables.segs_spect['doc'] == game].groupby('type').size()
    frame = pd.concat([spect_table, sit_table], axis=0)
    new_frame = frame.to_frame()
    new_frame.columns = [game]
    new_frame = new_frame.T
    new_frame.columns = ['spect EDUs', 'situated EEUs', 'situated EDUs']
    return new_frame


def edu_count(game):
    if game == 'all':
        all_tables = []
        for s in tables.sel_games:
            all_tables.append(edu_helper(s))
        frame = pd.concat(all_tables, axis=0)
        #print(frame)
    elif type(game) == list:
        all_tables = []
        for s in game:
            all_tables.append(edu_helper(s))
        frame = pd.concat(all_tables, axis=0)
        #print(frame)
    else:
        frame = edu_helper(game)
        #print(edu_helper(game))
    return frame


def cdu_count():

    return None


def relation_helper(game, version, relations):
    tmp_table = None
    if version == 'situated':
        tmp_table = tables.rels_situ.loc[(tables.rels_situ['doc'] == game) & (tables.rels_situ['type'].isin(relations))].groupby('type').size()
    elif version == 'spect':
        tmp_table = tables.rels_spect.loc[(tables.rels_spect['doc'] == game) & (tables.rels_spect['type'].isin(relations))].groupby('type').size()
    tmp_table = tmp_table.to_frame()
    tmp_table.columns = [game + '_' + version]
    tmp_table = tmp_table.T
    return tmp_table


def relation_count(game, version, relations):

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
            #print(frame)
        else:
            all_tables = []
            for s in games:
                all_tables.append(relation_helper(s, version, relations))
            frame = pd.concat(all_tables, axis=0)
            frame.fillna(value=0, inplace=True)
            #print(frame)

    return frame


def game_size():

    return None


def orphan_count():
    #need to use the flattened versions of the game
    return None

