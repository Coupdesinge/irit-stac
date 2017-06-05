import stats_create_tables as tables
import pandas as pd
import numpy as np


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
        print(frame)
    elif type(game) == list:
        all_tables = []
        for s in game:
            all_tables.append(edu_helper(s))
        frame = pd.concat(all_tables, axis=0)
        print(frame)
    else:
        print(edu_helper(game))
    return None


def cdu_count():

    return None


def relation_count():
    #endpoints specified?
    return None


def game_size():

    return None


def orphan_count():
    #need to use the flattened versions of the game
    return None

