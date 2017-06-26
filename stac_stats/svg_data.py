from collections import defaultdict, OrderedDict
import os
import shutil
import pydot
import re
import glob
import pandas as pd


GLOZZ_COLORS = {'Acknowledgement': '#12FFFF',
              'Alternation': '#1C931A',
              'Background': '#FF8200',
              'Clarification_question': '#FF40D1',
              'Contrast':'#FF7ECF',
              'Correction':'#FF174E',
              'Comment': '#FF8200',
              'Conditional': '#1C931A',
              'Continuation': '#1C931A',
              'Elaboration': '#FF8200',
              'Explanation': '#FF8200',
              'Narration': '#1C931A',
              'Parallel': '#1C931A',
              'Q-Elab':'#0D20FF',
              'Question-answer_pair': '#12FFFF',
              'Result': '#10FF0F',
              'Sequence': '#0D20FF'}


def create_dialogue_dict(dialogues_table):

    """
    dialogues_dict --> dict of dicts of dicts
    {game :
        {subdoc :
            {(beg_index, end_index): dialogue_id
            }}}

    :param dialogues_table: pandas DF containing all STAC game dialogues data
    :return: dict which organizes dialogue_ids by game, subdoc and text indicies
    """

    subset = dialogues_table[['global_id', 'doc', 'subdoc', 'span_beg', 'span_end']]
    tuples = [list(x) for x in subset.values]

    dialogue_dict = {}
    for t in tuples:
        t[0] = re.sub('-', '_', t[0])
        t[1] = re.sub('-', '_', t[1])
        if t[1] in dialogue_dict.keys():
            if t[2] in dialogue_dict[t[1]].keys():
                dialogue_dict[t[1]][t[2]][(t[3], t[4])] = t[0]
            else:
                dialogue_dict[t[1]][t[2]] = {}
                dialogue_dict[t[1]][t[2]][(t[3], t[4])] = t[0]
        else:
            dialogue_dict[t[1]] = {}
            dialogue_dict[t[1]][t[2]] = {}
            dialogue_dict[t[1]][t[2]][(t[3], t[4])] = t[0]

    return dialogue_dict


def add_superdoc(spect_segs, situ_segs):
    """
    change situated segs and spect segs into dataframes and merge into a dataframe showing the
    last linguistic segment in each dialogue. Compute the new superdoc numbers for each dialogue in
    seg and in spect and add to their respective segs.
    :param situated_segs:
    :param spect_segs:
    :return:
    """

    segs_df = pd.DataFrame([[s[0], s[1], s[3], s[6], s[7]] for s in spect_segs], columns=['seg_id', 'game', 'type', 'span', 'dialogue'])
    spect_max = segs_df['dialogue'].max()
    segs_df = segs_df[segs_df['type'] == 'Segment'].groupby(['dialogue'])['seg_id']
    segs_df = segs_df.max()
    spect_table = segs_df.reset_index()

    segs_df = pd.DataFrame([[s[0], s[1], s[3], s[6], s[7]] for s in situ_segs], columns=['seg_id', 'game', 'type', 'span', 'dialogue_situ'])
    situ_max = segs_df['dialogue_situ'].max()
    segs_df = segs_df[segs_df['type'] == 'Segment'].groupby(['dialogue_situ'])[['seg_id']]
    segs_df = segs_df.max()
    situ_table = segs_df.reset_index()

    merged = pd.merge(situ_table, spect_table, on='seg_id', how='outer')
    merged.fillna(0, inplace=True)
    merged = [[x[0], x[2]] for x in merged.values]

    #go through merged list of lists and create dicts which assign superdoc values to all dialogues

    superdoc = 1
    spect_dict = {}
    situ_dict = {}
    spect_last = 1
    situ_last = 1

    for m in merged:
        if m[0] != 0 and m[1] != 0:
            for n in range(situ_last, int(m[0]) + 1):
                situ_dict[n] = superdoc
            situ_last = int(m[0]) + 1
            for n in range(spect_last, int(m[1]) + 1):
                spect_dict[n] = superdoc
            spect_last = int(m[1]) + 1
            superdoc += 1

    for n in range(situ_last, situ_max + 1):
        situ_dict[n] = superdoc - 1

    for n in range(spect_last, spect_max + 1):
        spect_dict[n] = superdoc - 1

    #add superdoc values to segs lists

    for s in situ_segs:
        s.append(situ_dict[s[7]])

    for s in spect_segs:
        s.append(spect_dict[s[7]])

    return spect_segs, situ_segs


def create_nodes_dict(segs_tuples):
    """
    nodes dict --> a dict of dicts of dicts of ordered dicts
    {game :
        {subdoc :
            {dialogue :
               [ superdoc_num, { turn: [(segment_id, segment_type, text), ...]
                }]
                }}}

    :param segs_table: pandas DF containing all STAC game segments data
    :param dialogue_dict: output of dialogue data from create_dialogue_dict()
    :return: dict of segment data (id, type, text) organized by game, subdoc, dialogue, turn
    """

    #create nodes dict
    nodes_dict = {}
    for t in segs_tuples:
        # check if game in dict
        if t[1] in nodes_dict.keys():
            # check if subdoc in dict
            if t[2] in nodes_dict[t[1]].keys():
                if t[7] in nodes_dict[t[1]][t[2]].keys():
                    nodes_dict[t[1]][t[2]][t[7]][1][t[5]].append((t[0], t[3], t[4]))
                else:
                    nodes_dict[t[1]][t[2]][t[7]] = [t[8], defaultdict(list)]
                    nodes_dict[t[1]][t[2]][t[7]][1][t[5]].append((t[0], t[3], t[4]))
            else:
                # add list dict for dialogue
                nodes_dict[t[1]][t[2]] = OrderedDict()
                nodes_dict[t[1]][t[2]][t[7]] = [t[8], defaultdict(list)]
                nodes_dict[t[1]][t[2]][t[7]][1][t[5]].append((t[0], t[3], t[4]))

        else:
            nodes_dict[t[1]] = OrderedDict()
            nodes_dict[t[1]][t[2]] = OrderedDict()

            nodes_dict[t[1]][t[2]][t[7]] = [t[8], defaultdict(list)]
            nodes_dict[t[1]][t[2]][t[7]][1][t[5]].append((t[0], t[3], t[4]))

    return nodes_dict


def get_node_segs(segs_table, dialogue_dict):
    """

    :param segs_table:
    :param dialogue_dict:
    :return: a set of tuples (this is a list!) which will eventually be amended by adding a superdoc number for each
    dialogue.
    """

    # USE dialgoue_dict to add dialogue id  to segs list
    # transform turn numbers into integers 0-N
    # transform dialogue ids into integers 0-N

    subset = segs_table[['global_id', 'doc', 'subdoc', 'type', 'text', 'turn_id', 'span_end']]
    tuples = sorted([list(x) for x in subset.values], key=lambda x: (x[1], x[2], x[6]))
    n = 0
    dialogue_n = 0
    last = None
    di_last = None
    for s in tuples:
        s[0] = re.sub('-', '_', s[0])
        s[1] = re.sub('-', '_', s[1])

        if s[5] == last:
            last = s[5]
            s[5] = n
        else:
            n += 1
            last = s[5]
            s[5] = n
        for pair in dialogue_dict[s[1]][s[2]].keys():
            if pair[0] < s[6] <= pair[1]:
                di_id = dialogue_dict[s[1]][s[2]][pair]
                if di_id == di_last:
                    di_last = di_id
                    s.append(dialogue_n)
                else:
                    dialogue_n += 1
                    di_last = di_id
                    s.append(dialogue_n)

    return tuples


def create_relations_dict(rels_table):
    """
    rels_dict --> a dict of dicts

    {game:
        {subdoc: [(relation_type, source_id, target_id),...]
        }}

    :param rels_table: pandas DF containing all STAC data on relations between segments
    :return: dict which organizes relations data (relation type and endpoint ids) by game, subdoc
    """
    subset = rels_table.loc[(rels_table['source_type'] != 'Complex_discourse_unit') & (
    rels_table['target_type'] != 'Complex_discourse_unit') &
                               (rels_table['stage'] == 'discourse')][['doc', 'subdoc', 'type', 'source', 'target']]
    tuples = [list(x) for x in subset.values]

    rels_dict = {}
    for t in tuples:
        t[0] = re.sub('-', '_', t[0])
        t[3] = re.sub('-', '_', t[3])
        t[4] = re.sub('-', '_', t[4])
        # check if game in dict
        if t[0] in rels_dict.keys():
            rels_dict[t[0]][t[1]].append((t[2], t[3], t[4]))
        else:
            # add list dict for relations
            rels_dict[t[0]] = defaultdict(list)
            # add the relation info
            rels_dict[t[0]][t[1]].append((t[2], t[3], t[4]))

    return rels_dict


def create_cdu_components_dict(schema_table):
    """
    cdu_comps_dict --> a dict of dicts

    {game:
        {subdoc:
            {CDU_id : [ids of component EEUs and EDUs]
        }}}

    :param schema_table: pandas DF containing all STAC data on segments belonging to each CDU
    :return: dict which organizes CDUs by doc and subdoc, and points to their component segments
    """

    subset = schema_table[['member_id', 'schema_id']]
    tuples = [list(x) for x in subset.values]

    cdu_comps_dict = {}
    for t in tuples:
        # get game name and subdoc from schema id
        game, subdoc = t[1].split('_')[:2]
        game = re.sub('-', '_', game)
        t[0] = re.sub('-', '_', t[0])
        t[1] = re.sub('-', '_', t[1])
        # check if game in dict
        if game in cdu_comps_dict.keys():
            if subdoc in cdu_comps_dict[game].keys():
                cdu_comps_dict[game][subdoc][t[1]].append(t[0])
            else:
                cdu_comps_dict[game][subdoc] = defaultdict(list)
                cdu_comps_dict[game][subdoc][t[1]].append(t[0])
        else:
            cdu_comps_dict[game] = {}
            cdu_comps_dict[game][subdoc] = defaultdict(list)
            cdu_comps_dict[game][subdoc][t[1]].append(t[0])

    return cdu_comps_dict


def create_cdu_relations_dict(rels_table):
    """
    cdu_rels_dict -->

    {game:
        {subdoc: [(relation_type, source_id, target_id),...]
        }}

    :param rels_table: pandas DF containing all STAC data on relations between segments
    :return: dict which organizes relations containing at least one CDU by game and subdoc
    """
    subset = rels_table.loc[((rels_table['source_type'] == 'Complex_discourse_unit') |
                             (rels_table['target_type'] == 'Complex_discourse_unit')) & (
                                    rels_table['stage'] == 'discourse')][['doc', 'subdoc', 'type', 'source', 'target']]
    tuples = [list(x) for x in subset.values]

    cdu_rels_dict = {}
    for t in tuples:
        t[0] = re.sub('-', '_', t[0])
        t[1] = re.sub('-', '_', t[1])
        t[3] = re.sub('-', '_', t[3])
        t[4] = re.sub('-', '_', t[4])
        # check if game in dict
        if t[0] in cdu_rels_dict.keys():
            cdu_rels_dict[t[0]][t[1]].append((t[2], t[3], t[4]))
        else:
            # add list dict for relations
            cdu_rels_dict[t[0]] = defaultdict(list)
            # add the relation info
            cdu_rels_dict[t[0]][t[1]].append((t[2], t[3], t[4]))

    return cdu_rels_dict


def get_verticals(game_dict, game, subdoc, dialogue):
    """

    :param game_dict: a nodes dict for the creation of svgs
    :param game: the name of a game
    :param subdoc: a subdoc in the game
    :param dialogue: a dialogue in a game
    :return: the length of the longest turn (in segments) and a list of ids for each turn's first segment
    """
    vertical_list = []
    turn_lengths = []
    for t in sorted(game_dict[game][subdoc][dialogue][1].keys()):
        try:
            turn_lengths.append(len(game_dict[game][subdoc][dialogue][1][t]))
            vertical_list.append(game_dict[game][subdoc][dialogue][1][t][0][0])
        except:
            pass
    return max(turn_lengths), vertical_list


def create_svg_folders(nodes, relations, cdu_relations, cdu_components, version):
    """

    :param nodes:
    :param relations:
    :param cdu_relations:
    :param cdu_components:
    :param version:
    :return: a folder of folders
    """

    #check if game folder exists, if not make it, if so, delete it to start over

    current_dir = os.getcwd()
    if not os.path.exists(current_dir + '/stac_game_graphs/'):
        os.makedirs(current_dir + '/stac_game_graphs/')
    # else:
    #     shutil.rmtree(current_dir + '/stac_game_graphs/')

    for game in nodes.keys():

        #create game folder
        game_folder = current_dir + '/stac_game_graphs/' + game + '/'
        if not os.path.exists(game_folder):
            os.makedirs(game_folder)

        for subdoc in sorted(nodes[game].keys()):

            dialogue_num = 1
            for dialogue in nodes[game][subdoc].keys():

                superdoc = str(nodes[game][subdoc][dialogue][0])

                dot_object = pydot.Dot(graph_name=game, rankdir="TB",
                                       ranksep=0.25)
                dot_object.set_node_defaults(shape='circle', fixedsize='true', style='filled', fillcolor='black',
                                             height=.1, width=.1, fontsize=10)
                dot_object.set_edge_defaults(style='solid', arrowsize=0.5, color='grey', splines='line')

                cluster_main = pydot.Cluster(str(dialogue), label='subdoc ' + subdoc + ', dialogue ' + str(dialogue_num),
                                             labeljust='l')

                dialogue_num += 1
                # keep track of nodes:
                node_list = []
                max_turns, verticals = get_verticals(nodes, game, subdoc, dialogue)

                for turn in sorted(nodes[game][subdoc][dialogue][1].keys()):
                    seg_num = len(nodes[game][subdoc][dialogue][1][turn])
                    add_segs = max_turns - seg_num

                    S = pydot.Subgraph(rank='same')
                    last_seg = None
                    for seg in nodes[game][subdoc][dialogue][1][turn]:

                        text = re.sub('[^A-Za-z0-9?!\s]', '', seg[2])

                        if seg[1] == 'NonplayerSegment':
                            node_eta = pydot.Node(name=seg[0], label='', fillcolor='#FFF834', tooltip=text)
                        else:
                            node_eta = pydot.Node(name=seg[0], label='', tooltip=text)
                        S.add_node(node_eta)
                        node_list.append(seg[0])

                        if last_seg:
                            dot_object.add_edge(pydot.Edge(last_seg, seg[0], style='invis'))
                        last_seg = seg[0]

                    # add blank nodes for structure
                    if add_segs > 0:
                        for n in range(0, add_segs):
                            turn_name = str(turn) + '_' + str(n)

                            node_blank = pydot.Node(name=turn_name, label='', style='invis')
                            S.add_node(node_blank)
                            dot_object.add_edge(pydot.Edge(last_seg, turn_name, style='invis'))
                            last_seg = turn_name

                    cluster_main.add_subgraph(S)

                dot_object.add_subgraph(cluster_main)

                # add invis vertical relations between all verticals
                k = 0
                while k < len(verticals) - 1:
                    dot_object.add_edge(pydot.Edge(verticals[k], verticals[k + 1], style='invis'))
                    k += 1

                # add edges from edge_dict

                for rel in relations[game][subdoc]:
                    # check if there is a relation between the nodes
                    # if yes, change color, add tooltipo
                    # if no, add relation
                    if dot_object.get_edge(rel[1], rel[2]):
                        # print("already a relation")
                        dot_object.del_edge(rel[1], rel[2])
                        rel_text = re.sub('-', '', rel[0])
                        dot_object.add_edge(pydot.Edge(rel[1], rel[2], color=GLOZZ_COLORS[rel[0]], tooltip=rel_text))

                    else:
                        # pass
                        if rel[1] in node_list:
                            rel_text = re.sub('-', '', rel[0])
                            dot_object.add_edge(
                                pydot.Edge(rel[1], rel[2], color=GLOZZ_COLORS[rel[0]], tooltip=rel_text))

                # add cdus -- outside of cluster in another cluster

                C = pydot.Subgraph()
                #print(cdu_components[game])
                try:
                    for c in cdu_components[game][subdoc]:
                        components = cdu_components[game][subdoc][c]
                        if components[0] in node_list:
                            # add CDU id to node list
                            node_list.append(c)
                            node_cdu = pydot.Node(name=c, label='', fillcolor='red', tooltip=c)
                            C.add_node(node_cdu)

                            for component in components:
                                dot_object.add_edge(
                                    pydot.Edge(component, c, color='grey', style='dashed', dir='none'))
                    dot_object.add_subgraph(C)

                except(KeyError):
                    pass

                # add relations to cdus

                try:
                    for c in cdu_relations[game][subdoc]:
                        if c[1] in node_list:
                            rel_text = re.sub('-', '', c[0])
                            dot_object.add_edge(pydot.Edge(c[1], c[2], color=GLOZZ_COLORS[c[0]], tooltip=rel_text))

                except(KeyError):
                    pass

                #save to an svg in the folder

                dot_object.write_svg(game_folder + game + '_' + subdoc + '_' + superdoc + '_' + str(dialogue_num) + '_' + version + '.svg')

    return None


def sort_svg_files(svg_list):
    sorted_list = [svg.split('_') for svg in svg_list]
    sorted_list = sorted(sorted_list, key=lambda x: int(x[-2]))
    sorted_list = ['_'.join([s for s in svg]) for svg in sorted_list]
    return sorted_list


def create_html():
    current_dir = os.getcwd()
    if not os.path.exists(current_dir + '/stac_game_graphs/'):
        print("svg folder not found")
    else:
        # make main game menu/ index.html
        index_html_file = open(current_dir + '/stac_game_graphs/index.html', 'w')
        index_html_file.write('<html><h2>STAC games</h2><ul>')
        filesDepth1 = glob.glob('*/*')
        dirsDepth1 = filter(lambda f: os.path.isdir(current_dir + '/stac_game_graphs/'), filesDepth1)
        #print(dirsDepth1)

        for dir in dirsDepth1:
            dirname = dir.split('/')[-1]
            if dirname != 'index.html':
                #print(dir + '/subdocs.html')
                index_html_file.write('<li> <a href=\"./' + dirname + '/subdocs.html\"</a>' + dirname + '</a></li>')

                # make individual game menus/ subdocs.html
                subdoc_paths = [x for x in os.walk(current_dir + '/stac_game_graphs/' + dirname + '/')][0]

                subdoc_file = open(current_dir + '/stac_game_graphs/' + dirname + '/subdocs.html', 'w')
                subdoc_file.write('<html><h2>' + dirname + ' superdocs</h2><ul>')
                #collect all of the superdoc numbers into a list
                superdoc_dict = defaultdict(list)
                for superdoc in subdoc_paths[2]:
                    if superdoc != 'subdocs.html':
                        superdoc_dict[int(superdoc.split('_')[-3])].append(superdoc)
                #sort all keys
                #re-number so they start at '1' for each game
                new_superdoc_number = 1
                for k in sorted(superdoc_dict.keys()):
                    #make folder for superdocs

                    if not os.path.exists(current_dir + '/stac_game_graphs/' + dirname + '/' + 'superdoc_' + str(new_superdoc_number) + '/'):
                        os.makedirs(current_dir + '/stac_game_graphs/' + dirname + '/' + 'superdoc_' + str(new_superdoc_number) + '/')

                    subdoc_file.write('<li> <a href=\"./' + 'superdoc_' + str(new_superdoc_number) + '/dialogues.html\"</a>' + 'superdoc ' + str(new_superdoc_number) + '</a></li>')

                    #make dialogue comparison files
                    dialogues_file = open(current_dir + '/stac_game_graphs/' + dirname + '/' + 'superdoc_' + str(new_superdoc_number) + '/dialogues.html', 'w')
                    dialogues_file.write(
                        '<html><div id =\"wrapper\"style=\"width:100%;\"><div id=\"header\"'
                        'style=\"width:100%;background:grey;z-index: 10;\"><h2>'
                        + dirname + ' superdoc ' + str(k) + ' comparisons</h2></div>')

                    spect_svgs = []
                    situated_svgs = []
                    for svg in superdoc_dict[k]:
                        #move the file to the new superdocs folder
                        shutil.move(current_dir + '/stac_game_graphs/' + dirname + '/' + svg,
                                    current_dir + '/stac_game_graphs/' + dirname + '/' + 'superdoc_' + str(new_superdoc_number) + '/' + svg)

                        #organize svgs by version and order them
                        if 'situated' in svg:
                            situated_svgs.append(svg)
                        else:
                            spect_svgs.append(svg)
                    new_superdoc_number += 1
                    #dialogues_file.write('<div id = \"spect" style=\"display:inline-block;vertical-align:top;\">')
                    dialogues_file.write('<div id = \"spect" style=\"display:inline-block;vertical-align:top;height:100vh;overflow:auto;margin:0 40px 0 20px;padding:0 20px 0 20px;\">')
                    for svg in sort_svg_files(spect_svgs):
                        dialogues_file.write('<div style=\"display:block\"><object data=\"' + svg + '\" type =\"image/svg+xml\"></object></div>')
                    dialogues_file.write('</div>')

                    dialogues_file.write('<div id = \"situated" style=\"display:inline-block;vertical-align:top;height:100vh;overflow:auto;padding:0 20px 0 20px;\">')
                    for svg in sort_svg_files(situated_svgs):
                        dialogues_file.write('<div style=\"display:block\"><object data=\"' + svg + '\" type =\"image/svg+xml\"></object></div>')
                    dialogues_file.write('</div>')

                    dialogues_file.write('</html>')
                    dialogues_file.close()

                subdoc_file.write('</ul></html>')
                subdoc_file.close()

        index_html_file.write('</ul></html>')
        index_html_file.close()

    return None