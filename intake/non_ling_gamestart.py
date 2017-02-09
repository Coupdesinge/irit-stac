import re


def main(root, text, subdoc):
    """
    For the first subdoc of every doc, add the relations between non linguistic
    turns.
    Assumptions:
    -These relations are only found in the first doc
    -They terminate with the first player roll turn
    -The Result relations can be added between each turn from 'Game Started.' to
    'It's <x's> turn to roll the dice.' without checking the text of each turn, as these
    will all be 'NonplayerSegment'.

    :param root: XML tree extracted from the .aa file to modify
    :param text: (string) raw text extracted from the .ac file
    :param subdoc: (string)
        name of the subdoc currently annotated : GameName_XX
        (ex: pilot02_09)
    :return: a list of tuples to give to nonling_annotations.append_relation, which will then add
    the relations in the root element
    """

    JoinRegEx = re.compile(r'(.+) joined the game\.')
    SitDownRegEx = re.compile(r'(.+) sat down at seat (\d)\.')
    TurnToRollRegEx = re.compile(r"It's (.+)'s turn to roll the dice\.")

    """
    the various regexes that are checked can be sorted into those that come
    before the server says 'Game Started.' and those that come after. Hence
    the before_game_start state
    """
    before_game_start = 1

    relations_list = []

    joined = ("", "")
    sat = ("", "")
    game_start = ""

    for unit in [u for u in root if u.findtext('characterisation/type') == 'NonplayerSegment']:
        start = int(unit.find('positioning/start/singlePosition').get(
            'index'))
        end = int(unit.find('positioning/end/singlePosition').get(
            'index'))
        event = text[start:end]
        global_id = '_'.join([subdoc, unit.get('id')])

        if before_game_start:
            if JoinRegEx.search(event) is not None:
                mo = JoinRegEx.search(event)
                joined = (mo.group(1), global_id)
            elif SitDownRegEx.search(event) is not None:
                mo = SitDownRegEx.search(event)
                sat = (mo.group(1), global_id)
                if sat[0] == joined[0]:
                    relations_list.append(('Sequence', joined[1], sat[1]))
                    joined = ("", "")
            elif event == "Game state 0.":
                if sat[1]:
                    relations_list.append(('Result', sat[1], global_id))
            elif event == "Game started.":
                game_start = global_id
                before_game_start = 0
        else:
            if TurnToRollRegEx.search(event) is not None:
                relations_list.append(('Result', game_start, global_id))
                break
            else:
                relations_list.append(('Result', game_start, global_id))
                game_start = global_id

    return relations_list



