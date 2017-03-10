#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Automatically adds annotations on non-linguistic events in a STAC game.

When a relation goes from one subdoc to another (e.g.: from pilot02_03
to pilot02_03), it is not added to the files but written to a separate
file `Implicit_Relations.txt`.

This script only uses functions from the standard python library and
re-implements the generation of local and global ids as it is implemented
in educe.

Usage :
python nonling_annotations.py <path to the game> <version of the game>

Example :
python nonling_annotations.py ../../data/pilot_nonling/test/pilot14/ SILVER

NB : it would be wise to not use this script twice on the same files,
since it would add the same annotations twice.
"""

from __future__ import print_function

import argparse
import codecs
import os
import re
import xml.etree.ElementTree as ET

from csvtoglozz import append_unit, init_mk_id, mk_id
from educe.stac.util.prettifyxml import prettify


_AUTHOR = 'stacnl'

# ---------------------------------------------------------------------
# "Units" annotations
# ---------------------------------------------------------------------

# trade offer with another player
OFFER_RE = r'(?P<X>.+) made an offer to trade (?P<V>(\d+) (clay|ore|sheep|wheat|wood)(, (\d+) (clay|ore|sheep|wheat|wood))*)? for (?P<W>(\d+) (clay|ore|sheep|wheat|wood)(, (\d+) (clay|ore|sheep|wheat|wood))*)?\.'
OFFER_PROG = re.compile(OFFER_RE)
# [...] [from Y]
FROM_PROG = re.compile(r'from (.+)')

# trade offer with the bank or a port
BANK_OFFER_RE = r'(?P<X>.+) made an offer to trade (?P<V>(\d+) (clay|ore|sheep|wheat|wood)(, (\d+) (clay|ore|sheep|wheat|wood))*)? for (?P<W>(\d+) (clay|ore|sheep|wheat|wood)(, (\d+) (clay|ore|sheep|wheat|wood))*)? from (?P<Y>the bank or a port)\.'
BANK_OFFER_PROG = re.compile(BANK_OFFER_RE)

# trade done
TRADE_RE = r'(?P<X>.+) traded (?P<V>(\d+) (clay|ore|sheep|wheat|wood)(, (\d+) (clay|ore|sheep|wheat|wood))*)? for (?P<W>(\d+) (clay|ore|sheep|wheat|wood)(, (\d+) (clay|ore|sheep|wheat|wood))*)? from (?P<Y>.+)\.'
TRADE_PROG = re.compile(TRADE_RE)


def add_units_annotations(tree, text):
    """Add units annotations on non-linguistic events.

    Parameters
    ----------
    tree :
        XML tree extracted from the .aa file to modify
    text : string
        raw text extracted from the .ac file

    Returns
    -------
    root :
        modified XML tree with additional units annotations on
        non-linguistic events


    NOTE: 1.1-surfaceact-1 and 1.1-addressee-3 from the annotation manual are checked for each unit
    """
    root = tree

    #That's the moment I hope I didn't make any typo...

    RejectRegEx = re.compile(r'(.+) rejected trade offer\.')

    GetRegEx = re.compile(r'(.+) gets (\d+) (clay|ore|sheep|wheat|wood)\.')
    Get2RegEx = re.compile(r'(.+) gets (\d+) (clay|ore|sheep|wheat|wood), (\d+) (clay|ore|sheep|wheat|wood)\.')
    #It is impossible in "Settlers of Catan" to get more than 2 different types of resources with one roll dice.
    #That's why we actually don't need to bother with complex regular expression since there are in fact just two cases to consider. :)

    MonopolyRegEx = re.compile(r'(.+) monopolized (clay|ore|sheep|wheat|wood)\.')


    Trader = ''

    def parse_offer(m, start, end, unit, root):
        """Reimplementation of parseOffer.

        Parameters
        ----------
        m: TODO
            Match object for the offer.
        start: int
            Start of the offer.
        end: int
            End of the offer.
        unit: TODO
            XML element for this unit annotation.
        root: TODO
            Root of the XML tree.
        """
        X = m.group('X')
        # 1. update the unit annotation:
        # * type = 'Offer'
        unit.find('characterisation/type').text = 'Offer'

        feats = unit.find('characterisation/featureSet')
        # * surface act = 'Assertion'
        f_elm1 = ET.SubElement(feats, 'feature', {'name': 'Surface_act'})
        f_elm1.text = 'Assertion'
        # * addressee = '?'
        f_elm2 = ET.SubElement(feats, 'feature', {'name': 'Addressee'})
        f_elm2.text = '?'
        # 2. add 'Resource' annotations for both offered and asked resources
        # * resources offered
        # expected position of the leftmost character of the first one
        left = start + len(X) + 24
        right = left  # useful when m.group('V') is None
        if m.group('V') is not None:
            resources_offered = m.group('V').split(', ')
            for resource in resources_offered:
                right = left + len(resource)  # end of span
                qty, kind = resource.split(' ')
                append_unit(root, 'Resource', [('Status', 'Givable'),
                                               ('Quantity', qty),
                                               ('Correctness', 'True'),
                                               ('Kind', kind)],
                            left, right, author=_AUTHOR)
                # expected position of the leftmost character of the next
                # offered resource (if any)
                left = right + 2
        # * resources asked
        left = right + 5
        right = left
        if m.group('W') is not None:
            resources_asked = m.group('W').split(', ')
            for resource in resources_asked:
                right = left + len(resource)  # end of span
                qty, kind = resource.split(' ')
                append_unit(root, 'Resource', [('Status', 'Receivable'),
                                               ('Quantity', qty),
                                               ('Correctness', 'True'),
                                               ('Kind', kind)],
                            left, right, author=_AUTHOR)
                # expected position of the leftmost character of the next
                # asked resource (if any)
                left = right + 2
        # the eventual Y (if m comes from BANK_OFFER_PROG) is currently unused

    def parse_trade(m, start, end, unit, root):
        """Reimplementation of parseTrade.

        Parameters
        ----------
        m: TODO
            Match object for the offer.
        start: int
            Start of the offer.
        end: int
            End of the offer.
        unit: TODO
            XML element for this unit annotation.
        root: TODO
            Root of the XML tree.
        """
        X = m.group('X')
        Y = m.group('Y')
        # 1. update the unit annotation:
        # * type = 'Offer'
        unit.find('characterisation/type').text = 'Accept'
        feats = unit.find('characterisation/featureSet')
        # * surface act = 'Assertion'
        f_elm1 = ET.SubElement(feats, 'feature', {'name': 'Surface_act'})
        f_elm1.text = 'Assertion'
        # * addressee = Y or 'All' if Y = 'the bank' or 'a port'
        f_elm2 = ET.SubElement(feats, 'feature', {'name': 'Addressee'})
        if Y == 'the bank' or Y == 'a port':
            f_elm2.text = 'All'
        else:
            f_elm2.text = Y
        # 2. add 'Resource' annotations for both offered and asked resources
        # * resources offered
        # expected position of the leftmost character of the first one
        left = start + len(X) + 8
        right = left  # not sure it's useful here, but harmless anyway
        if m.group('V') is not None:
            resources_offered = m.group('V').split(', ')
            for resource in resources_offered:
                right = left + len(resource)  # end of span
                qty, kind = resource.split(' ')
                append_unit(root, 'Resource', [('Status', '?'),
                                               ('Quantity', qty),
                                               ('Correctness', 'True'),
                                               ('Kind', kind)],
                            left, right, author=_AUTHOR)
                left = right + 2
        # * resources asked
        left = right + 5  # ' for '
        right = left
        if m.group('W') is not None:
            resources_asked = m.group('W').split(', ')
            for resource in resources_asked:
                right = left + len(resource)
                qty, kind = resource.split(' ')
                append_unit(root, 'Resource', [('Status', 'Possessed'),
                                               ('Quantity', qty),
                                               ('Correctness', 'True'),
                                               ('Kind', kind)],
                            left, right, author=_AUTHOR)
                left = right + 2

    last_trade_offer_unitid = ''
    ellipse = 0
    trade_offer_addressees = []
    for unit in root:
        if unit.findtext('characterisation/type') == 'NonplayerSegment':
            start = int(unit.find('positioning/start/singlePosition').get(
                'index'))
            end = int(unit.find('positioning/end/singlePosition').get(
                'index'))
            event = text[start:end]

            # WIP 2016-07-11
            if OFFER_PROG.search(event) is not None:
                """1.2 - resources - offer, 1.1-type-1, 1.1-addressee-1"""
                # <X> made an offer to trade <N1> <R1> for <N2> <R2>.
                m = OFFER_PROG.search(event)
                parse_offer(m, start, end, unit, root)
                Trader = m.group('X')
                last_trade_offer_unitid = unit.get("id")
                print(last_trade_offer_unitid)
                continue
            if BANK_OFFER_PROG.search(event) is not None:
                """1.2 - resources - offer, 1.1-type-2, 1.1-addressee-1"""
                # <X> made an offer to trade <N1> <R1> for <N2> <R2> with
                # the bank or a port.
                m = BANK_OFFER_PROG.search(event)
                parse_offer(m, start, end, unit, root)
                Trader = m.group('X')
                continue
            if TRADE_PROG.search(event) is not None:
                """1.2 - resources - trade, 1.1-type-2, 1.1-addresse-2"""
                m = TRADE_PROG.search(event)
                parse_trade(m, start, end, unit, root)
                continue
            # end WIP 2016-07-11

            if RejectRegEx.search(event) != None:
                """1.1.-type-3"""
                # <Y> rejected trade offer.
                mo = RejectRegEx.search(event)
                Y = mo.group(1)

                unit.find('characterisation/type').text = 'Refusal'
                feats = unit.find('characterisation/featureSet')
                f_elm1 = ET.SubElement(feats, 'feature',
                                       {'name': 'Surface_act'})
                f_elm1.text = 'Assertion'
                f_elm2 = ET.SubElement(feats, 'feature',
                                       {'name': 'Addressee'})
                if Trader != '':
                    f_elm2.text = Trader
                else:
                    f_elm2.text = 'All'
                continue

            if event == "You can't make that trade.":
                """1.1-type-4"""
                unit.find('characterisation/type').text = 'Other'
                feats = unit.find('characterisation/featureSet')
                f_elm1 = ET.SubElement(feats, 'feature',
                                       {'name': 'Surface_act'})
                f_elm1.text = 'Assertion'
                f_elm2 = ET.SubElement(feats, 'feature',
                                       {'name': 'Addressee'})
                if Trader != '':
                    f_elm2.text = Trader
                else:
                    f_elm2.text = 'All'
                continue

            if GetRegEx.search(event) != None:
                """1.2-resources-gets"""
                # <Y> gets <N> <R>.
                mo = GetRegEx.search(event)
                Y = mo.group(1)
                N = mo.group(2)
                R = mo.group(3)

                unit.find('characterisation/type').text = 'Other'
                feats = unit.find('characterisation/featureSet')
                f_elm1 = ET.SubElement(feats, 'feature',
                                       {'name': 'Surface_act'})
                f_elm1.text = 'Assertion'
                f_elm2 = ET.SubElement(feats, 'feature',
                                       {'name': 'Addressee'})
                f_elm2.text = 'All'

                left = start + len(Y) + 6
                right = end - 1
                append_unit(root, 'Resource', [('Status', 'Possessed'),
                                               ('Quantity', N),
                                               ('Correctness', 'True'),
                                               ('Kind', R)],
                            left, right, author=_AUTHOR)
                continue

            if Get2RegEx.search(event) != None:
                """1.2-resources-gets"""
                # <Y> gets <N1> <R1>, <N2> <R2>.
                mo = Get2RegEx.search(event)
                Y = mo.group(1)
                N1 = mo.group(2)
                R1 = mo.group(3)
                N2 = mo.group(2)
                R2 = mo.group(3)

                unit.find('characterisation/type').text = 'Other'
                feats = unit.find('characterisation/featureSet')
                f_elm1 = ET.SubElement(feats, 'feature',
                                       {'name': 'Surface_act'})
                f_elm1.text = 'Assertion'
                f_elm2 = ET.SubElement(feats, 'feature',
                                       {'name': 'Addressee'})
                f_elm2.text = 'All'

                left1 = start + len(Y) + 6
                right1 = left1 + len(N1) + 1 + len(R1)
                append_unit(root, 'Resource', [('Status', 'Possessed'),
                                               ('Quantity', N1),
                                               ('Correctness', 'True'),
                                               ('Kind', R1)],
                            left1, right1, author=_AUTHOR)
                left2 = right1 + 2
                right2 = left2 + len(N2) + 1 + len(R2)
                append_unit(root, 'Resource', [('Status', 'Possessed'),
                                               ('Quantity', N2),
                                               ('Correctness', 'True'),
                                               ('Kind', R2)],
                            left2, right2, author=_AUTHOR)
                continue

            if MonopolyRegEx.search(event) != None:
                """1.2-resources-monopolized"""
                # <X> monopolized <R>.
                mo = MonopolyRegEx.search(event)
                X = mo.group(1)
                R = mo.group(2)

                unit.find('characterisation/type').text = 'Other'
                feats = unit.find('characterisation/featureSet')
                f_elm1 = ET.SubElement(feats, 'feature',
                                       {'name': 'Surface_act'})
                f_elm1.text = 'Assertion'
                f_elm2 = ET.SubElement(feats, 'feature',
                                       {'name': 'Addressee'})
                f_elm2.text = 'All'

                right = end - 1
                left = right - len(R)
                append_unit(root, 'Resource', [('Status', 'Possessed'),
                                               ('Quantity', '?'),
                                               ('Correctness', 'True'),
                                               ('Kind', R)],
                            left, right, author=_AUTHOR)
                continue

            else:
                """1.1-addressee-3, 1.1-type-4"""
                unit.find('characterisation/type').text = 'Other'
                feats = unit.find('characterisation/featureSet')
                f_elm1 = ET.SubElement(feats, 'feature',
                                       {'name': 'Surface_act'})
                f_elm1.text = 'Assertion'
                f_elm2 = ET.SubElement(feats, 'feature',
                                       {'name': 'Addressee'})
                f_elm2.text = 'All'
                if event == '...' and last_trade_offer_unitid != '':
                    ellipse = 1
                elif event.split(' ')[0] == 'from':
                    if ellipse:
                        trade_offer_addressees.append((last_trade_offer_unitid, event.split(' ')[1]))
                        ellipse = 0
                        last_trade_offer_unitid == ''

    """Go through list of units '1.2 - resources - offer' and add addressee"""
    for unit in root:
        if len(trade_offer_addressees) > 0:
            for i, t in enumerate(trade_offer_addressees):
                if unit.get("id") == t[0]:
                    unit.find('characterisation/featureSet/feature[2]').text = t[1]
                    trade_offer_addressees.pop(i)
                    break
    return root


# ---------------------------------------------------------------------
# "Discourse" annotations
# ---------------------------------------------------------------------


def append_relation(root, utype, global_id1, global_id2, place):
    """
    Append a new relation level annotation to the given root element.
    Note that this generates a new identifier behind the scenes.

    Parameters
    ----------
    root :
        node of the XML tree to which we want to add a "relation" child
    utype : string
        type of the relation we want to create (sequence, continuation,
        QAP...)
    global_id1 : string
        global id of the first element (EDU or CDU) of the relation
    global_id2 : string
        global id of the second element (EDU or CDU) of the relation
    """
    unit_id, date = mk_id(author=_AUTHOR)

    id1 = global_id1.split('_')
    id2 = global_id2.split('_')

    subdoc1 = id1[1]
    subdoc2 = id2[1]

    if subdoc1 == subdoc2:

        rel1 = "Implicit relation from subdoc %s to subdoc %s for %s :" % (
            subdoc1, subdoc2, place)
        rel2 = "%s ------ %s -----> %s" % (global_id1, utype, global_id2)


        local_id1 = '_'.join([id1[-2], id1[-1]])
        local_id2 = '_'.join([id2[-2], id2[-1]])

        metadata = [('author', _AUTHOR),
                    ('creation-date', str(date)),
                    ('lastModifier', 'n/a'),
                    ('lastModificationDate', '0')]
        elm_relation = ET.SubElement(root, 'relation', {'id': unit_id})
        elm_metadata = ET.SubElement(elm_relation, 'metadata')
        for key, val in metadata:
            ET.SubElement(elm_metadata, key).text = val
        elm_charact = ET.SubElement(elm_relation, 'characterisation')
        ET.SubElement(elm_charact, 'type').text = utype

        elm_features = ET.SubElement(elm_charact, 'featureSet')
        comments = ET.SubElement(elm_features, 'feature',
                                 {'name': 'Comments'})
        comments.text = 'Please write in remarks...'
        argument_scope = ET.SubElement(elm_features, 'feature',
                                       {'name': 'Argument_scope'})
        argument_scope.text = 'Please choose...'

        positioning = ET.SubElement(elm_relation, 'positioning')
        edu1 = ET.SubElement(positioning, 'term', {'id': local_id1})
        edu2 = ET.SubElement(positioning, 'term', {'id': local_id2})

        return []

    else:
        err1 = "Implicit relation from subdoc %s to subdoc %s for %s :" % (
            subdoc1, subdoc2, place)
        err2 = "%s ------ %s -----> %s" % (global_id1, utype, global_id2)
        return [err1, err2]


class Events:
    def __init__(self):
        self.Join = ("", "")
        self.Sat = ("", "")
        self.Start = "NONE"
        self.Building = dict()
        self.Roll = ""
        self.Dice = []
        self.Robber = []
        self.Trade = []
        self.Monopoly = ""
        self.Road = []


def append_schema(root, utype, edus):
    """
    Append a new schema level annotation to the given root element.
    Note that this generates a new identifier behind the scenes.

    Parameters
    ----------
    root :
        node of the XML tree to which we want to add a "schema" child
    utype : string
        type of the schema we want to create. Usually, a
        "Complex_discourse_unit".
    edus :
        list of the global ids of the EDUs that compose the CDU

    Returns
    -------
    cdu_id : string
        local id of the CDU created (used later to create a relation
        between this CDU and another element)
    """
    cdu_id, date = mk_id(author=_AUTHOR)

    metadata = [('author', _AUTHOR),
                ('creation-date', str(date)),
                ('lastModifier', 'n/a'),
                ('lastModificationDate', '0')]
    elm_schema = ET.SubElement(root, 'schema', {'id': cdu_id})
    elm_metadata = ET.SubElement(elm_schema, 'metadata')
    for key, val in metadata:
        ET.SubElement(elm_metadata, key).text = val
    elm_charact = ET.SubElement(elm_schema, 'characterisation')
    # utype = 'Complex_discourse_unit'
    ET.SubElement(elm_charact, 'type').text = utype
    elm_features = ET.SubElement(elm_charact, 'featureSet')

    positioning = ET.SubElement(elm_schema, 'positioning')
    for edu in edus:
        edusplit = edu.split('_')
        local_id = '_'.join([edusplit[-2], edusplit[-1]])
        ET.SubElement(positioning, 'embedded-unit', {'id': local_id})

    return cdu_id


def add_discourse_annotations(tree, text, e, subdoc):
    """
    For each non-linguistic unit in the discourse tree object, check the text using a set
    of RegEx patterns. Event object attributes are used to determine whether criteria are
    met for the addition of a particular relation between two events. If they are, the two
    events are given to the append_relation function to add relations and the append_schema
    function to create CDUs. If the events involved in a relation span two subdocs, the
    functions return an 'error' list, which will be added to the final implicit relation
    .txt file (see main() function)

    Parameters
    ----------
    tree :
        XML tree extracted from the .aa file to modify
    text : string
        raw text extracted from the .ac file
    e : Events
        set of global ids for events currently happenning
    subdoc : string
        name of the subdoc currently annotated : GameName_XX (ex:
        pilot02_09)

    Returns
    -------
    root :
        modified XML tree with discourse annotations for non-linguistical
        events
    events : Events
        set of global ids for events currently happenning
    errors : string list
        list of error messages
    """

    root = tree
    events = e
    errors = []

    JoinRegEx = re.compile(r'(.+) joined the game\.')
    SitDownRegEx = re.compile(r'(.+) sat down at seat (\d)\.')

    # TurnToBuildRegEx = re.compile(r"It's (.+)'s turn to build a (road|settlement)\.")
    BuiltRegEx = re.compile(r'(.+) built a (road|settlement)\.')

    TurnToRollRegEx = re.compile(r"It's (.+)'s turn to roll the dice\.")
    DiceRegEx = re.compile(r'(.+) rolled a (\d) and a (\d)\.')
    GetRegEx = re.compile(r'(.+) gets (\d+) (clay|ore|sheep|wheat|wood)\.')
    Get2RegEx = re.compile(r'(.+) gets (\d+) (clay|ore|sheep|wheat|wood), (\d+) (clay|ore|sheep|wheat|wood)\.')
    #It is impossible in "Settlers of Catan" to get more than 2 different types of resources with one roll dice.
    #That's why we actually don't need to bother with complex regular expression since there are in fact just two cases to consider. :)
    NoGetRegEx = re.compile(r'No player gets anything\.')
    PlayedCardRegEx = re.compile(r'(.+) played a (.{,20}) card')

    SoldierRegEx = re.compile(r'(.+) played a Soldier card\.')
    Discard1RegEx = re.compile(r'(.+) needs to discard\.')
    Discard2RegEx = re.compile(r'(.+) discarded (\d+) resources\.')
    Robber1RegEx = re.compile(r'(.+) will move the robber\.')
    Robber2RegEx = re.compile(r'(.+) moved the robber\.')
    Robber3RegEx = re.compile(r'(.+) moved the robber, must choose a victim\.')
    StoleRegEx = re.compile(r'(.+) stole a resource from (.+)')

    CantRegEx = re.compile(r"You can't make that trade\.")
    RejectRegEx = re.compile(r'(.+) rejected trade offer\.')

    CardRegEx = re.compile(r'(.+) played a Monopoly card\.')
    MonopolyRegEx = re.compile(r'(.+) monopolized (clay|ore|sheep|wheat|wood)\.')

    RoadBuildRegEx = re.compile(r'(.+) played a Road Building card\.')
    consecutive = 0

    for unit in root:
        if unit.findtext('characterisation/type') == 'NonplayerSegment':

            start = int(unit.find('positioning/start/singlePosition').get(
                'index'))
            end = int(unit.find('positioning/end/singlePosition').get(
                'index'))
            event = text[start:end]
            global_id = '_'.join([subdoc, unit.get('id')])

            """
            The "place" variable reflects the section of the situated annotation
            manual describing the relation.

            The "consecutive" variable is initialized outside the loop and is used
            to determine whether or not <X's turn to roll> is followed by
            <X played a P card> without any other intervening non-linguistic events.

            A Sequence relation is only added between two consecutive non-linguistic
            events. Here "consecutive" means "with no intervening non-linguistic events".
            If two non-linguistic events are either right next to each other, or separated
            by linguistic events only, they are considered consecutive.
            """

            if JoinRegEx.search(event) is not None:
                mo = JoinRegEx.search(event)
                events.Join = (mo.group(1), global_id)
                continue

            if SitDownRegEx.search(event) is not None:
                mo = SitDownRegEx.search(event)
                events.Sat = (mo.group(1), global_id)

                if events.Sat[0] == events.Join[0]:
                    """
                    <X joined the game> --Sequence--> <X sat down at seat N>
                    !!!ASSUMPTION: no other non-linguistic events can take place
                    between X joining the game and X sitting down, so there is no
                    need to keep track using a 'consecutive' variable
                    """
                    place = "2.2.1-1, join & sit"
                    errors.extend(append_relation(
                        root, 'Sequence', events.Join[1], events.Sat[1], place))
                    events.Join = ("", "")
                else:
                    events.Join = ("", "")
                continue

            if event == "Game state 0.":
                """<X sat down at seat N> --Sequence--> <Game State 0.>"""
                place = "2.2.1-2 game state 0"
                if events.Sat[1]:
                    errors.extend(append_relation(
                        root, 'Result', events.Sat[1], global_id, place))
                continue

            if event == "Game started.":
                events.Start = global_id
                continue

            if TurnToRollRegEx.search(event) is not None:
                if events.Start != "NONE":
                    """(see 2.2.1-3) Adds Result between all game setup moves, terminating at
                    first player turn to roll: <X's turn to roll the dice.>"""
                    # place = "NUMBER 3"
                    # errors.extend(append_relation(
                    #     root, 'Result', events.Start, global_id, place))
                    events.Start = "NONE"
                events.Roll = global_id
                consecutive = 1
                continue

            if events.Start != "NONE":
                """Adds Result between all game setup moves, terminating at
                first player turn to roll: <X's turn to roll the dice.>"""
                place = "2.2.1-3 game setup"
                errors.extend(append_relation(
                    root, 'Result', events.Start, global_id, place))
                events.Start = global_id
                continue

            # Resource distribution events
            #

            if PlayedCardRegEx.search(event) is not None:
                """<X's turn to roll the dice.> --Sequence--> <X played a P card.>"""
                place = '2.2.2-2 turn to roll & played card'
                if consecutive == 1:
                    errors.extend(append_relation(
                        root, 'Sequence', events.Roll, global_id, place))

            if DiceRegEx.search(event) is not None:
                consecutive = 0
                mo = DiceRegEx.search(event)
                M1 = int(mo.group(2))
                M2 = int(mo.group(3))
                if M1 + M2 != 7:
                    # Resource distribution event
                    # Since we don't know when finishes a resource
                    # distribution, the trick is to compute a resource
                    # distribution when the next one starts.
                    # So here we first need to compute the preceding
                    # resource distribution.
                    if len(events.Dice) > 0:
                        if len(events.Dice) == 2:
                            # Resource distribution: 1 player
                            """<X rolled an M1 and M2> --Result--> <Y gets N R's>"""
                            place = '2.2.3-1 roll and distribution'
                            errors.extend(append_relation(
                                root, 'Result', events.Dice[0], events.Dice[1], place))
                        else:
                            # Resource Distribution : 2 or more players
                            """
                            <X rolled an M1 and M2> --CDU Result-->
                            [<Y gets N1 R1s> -- Continuation --> <Z gets N2 R2s>]
                            """
                            cdu_dice = append_schema(
                                root, 'Complex_discourse_unit', events.Dice[1:])
                            global_cdu_dice = '_'.join([subdoc, cdu_dice])
                            place = '2.2.3-2 roll and distribution'
                            errors.extend(append_relation(
                                root, 'Result', events.Dice[0], global_cdu_dice, place))
                            for i in range(1, len(events.Dice) - 1):
                                errors.extend(append_relation(
                                    root, 'Continuation', events.Dice[i], events.Dice[i+1], place))
                        events.Dice[:] = []
                    events.Dice.append(global_id)
                else:
                    # M1 + M2 == 7 : Robber event
                    if events.Robber != []:
                        raise Exception("add_discourse_annotations : la liste RobberEvent n'a pas été vidée!")
                    events.Robber.append(global_id)
                if events.Roll != '':
                    """<X's turn to roll.> --Result--> <X rolled an M1 and M2>"""
                    place = '2.2.2-1 what was rolled'
                    errors.extend(append_relation(
                        root, 'Result', events.Roll, global_id, place))
                    events.Roll = ''
                continue

            if GetRegEx.search(event) is not None:
                consecutive = 0
                # <Y> gets <N> <R>.
                events.Dice.append(global_id)
                continue

            if Get2RegEx.search(event) is not None:
                consecutive = 0
                # <Y> gets <N1> <R1>, <N2> <R2>.
                events.Dice.append(global_id)
                continue

            if NoGetRegEx.search(event) is not None:
                """<X rolled an M1 and M2> --Result--> No player gets anything."""
                consecutive = 0
                place = '2.2.3-1 no player gets anything'
                errors.extend(append_relation(
                    root, 'Result', events.Dice[0], global_id, place))
                events.Dice[:] = []
                continue

            # Robber events
            if SoldierRegEx.search(event) is not None:
                consecutive = 0
                # <X> played a Soldier card.
                if events.Robber != []:
                    raise Exception("add_discourse_annotations : la liste RobberEvent n'a pas été vidée!")
                events.Robber.append(global_id)
                continue

            if Discard1RegEx.search(event) is not None:
                consecutive = 0
                # <Y> needs to discard.
                events.Robber.append(global_id)
                continue

            if Discard2RegEx.search(event) is not None:
                consecutive = 0
                # <Y> discarded <N> resources.
                events.Robber.append(global_id)
                continue

            if Robber1RegEx.search(event) is not None:
                consecutive = 0
                # <X> will move the robber.
                events.Robber.append(global_id)
                continue

            if Robber2RegEx.search(event) is not None:
                consecutive = 0
                # <X> moved the robber.
                events.Robber.append(global_id)
                place = '2.2.6-1 robber event'
                cdu_robber = append_schema(
                    root, 'Complex_discourse_unit', events.Robber[1:])
                global_cdu_robber = '_'.join([subdoc, cdu_robber])
                errors.extend(append_relation(
                    root, 'Result', events.Robber[0], global_cdu_robber, place))
                for i in range(1, len(events.Robber) - 1):
                    errors.extend(append_relation(
                        root, 'Result', events.Robber[i], events.Robber[i+1], place))
                events.Robber[:] = []
                continue

            if Robber3RegEx.search(event) is not None:
                consecutive = 0
                # <X> moved the robber, must choose a victim.
                events.Robber.append(global_id)
                continue

            if StoleRegEx.search(event) is not None:
                consecutive = 0
                # <X> stole a resource from <Z>.
                events.Robber.append(global_id)
                place = '2.2.6-1 stolen resource'
                cdu_robber = append_schema(
                    root, 'Complex_discourse_unit', events.Robber[1:])
                global_cdu_robber = '_'.join([subdoc, cdu_robber])
                errors.extend(append_relation(
                    root, 'Result', events.Robber[0], global_cdu_robber, place))
                for i in range(1, len(events.Robber) - 1):
                    errors.extend(append_relation(
                        root, 'Result', events.Robber[i], events.Robber[i+1], place))
                events.Robber[:] = []
                continue

            # Trade events

            if OFFER_PROG.search(event) is not None:
                consecutive = 0
                # <X> made an offer to trade <M> <R1> for <N> <R2>.
                events.Trade[:] = []
                events.Trade.append(global_id)
                continue
            if event == '...':
                consecutive = 0
                # ...
                events.Trade.append(global_id)
                continue
            if (FROM_PROG.search(event) is not None
                  and TRADE_PROG.search(event) is None
                  and BANK_OFFER_PROG.search(event) is None):
                consecutive = 0
                """
                [CDU] — [X made an offer to trade M R1 for N R2—[elaboration]— … —[continuation]— from Y]
                """
                place = 'NUMBER 8 2.2.4-2 trades offers'
                events.Trade.append(global_id)
                errors.extend(append_relation(
                    root, 'Elaboration', events.Trade[0], events.Trade[1], place))
                errors.extend(append_relation(
                    root, 'Continuation', events.Trade[1], global_id, place))
                cdu_offer = append_schema(
                    root, 'Complex_discourse_unit', events.Trade)
                global_cdu_offer = '_'.join([subdoc, cdu_offer])
                events.Trade[0] = global_cdu_offer
                continue

            if BANK_OFFER_PROG.search(event) is not None:
                consecutive = 0
                # <X> made an offer to trade <M> <R1> for <N> <R2> from
                # the bank or a port.
                events.Trade[:] = []
                events.Trade.append(global_id)
                continue

            if CantRegEx.search(event) is not None:
                consecutive = 0
                # You can't make that trade.
                place = 'CANNOT TRADE'
                errors.extend(append_relation(
                    root, 'Question-answer_pair', events.Trade[0], global_id, place))
                # this message does not clear the pending trade offer,
                # it just means that the trade can't be made right now
                # for example, if the offering player is in a building phase,
                # the addressee needs to wait until the offering player is
                # done, but the trade offer is accepted afterwards
                # ex: s1-league2-game1, turns 423..425
                # events.Trade[:] = []
                continue

            if TRADE_PROG.search(event) is not None:
                """<X made an offer to trade M R1 for N R2>--QAP--><X traded M R1 for N R2>"""
                consecutive = 0
                place = '2.2.4-3 trade accept'
                errors.extend(append_relation(
                    root, 'Question-answer_pair', events.Trade[0], global_id, place))
                events.Trade[:] = []
                continue

            if RejectRegEx.search(event) is not None:
                """<X made an offer to trade M R1 for N R2>--QAP--><Y rejected trade offer>"""
                consecutive = 0
                place = '2.2.4-4 trade reject'
                errors.extend(append_relation(
                    root, 'Question-answer_pair', events.Trade[0], global_id, place))
                events.Trade[:] = []
                continue

            # Monopoly events

            if CardRegEx.search(event) is not None:
                consecutive = 0
                # <X> played a Monopoly card.
                if events.Monopoly != "":
                    raise Exception("add_discourse_annotations : la chaîne MonopolyEvent n'a pas été vidée!")
                events.Monopoly = global_id
                continue

            if MonopolyRegEx.search(event) is not None:
                """<X played a monopoly card>--Result--><X monopolized R>"""
                consecutive = 0
                place = '2.2.6-3 monopoly'
                errors.extend(append_relation(
                    root, 'Result', events.Monopoly, global_id, place))
                events.Monopoly = ""
                continue

            # Road Building events

            if RoadBuildRegEx.search(event) is not None:
                consecutive = 0
                # <X> played a Road Building Card.
                events.Road.append(global_id)
                continue

            if BuiltRegEx.search(event) is not None:
                consecutive = 0
                # <X> built a road.
                if len(events.Road) == 1:
                    events.Road.append(global_id)
                elif len(events.Road) == 2:
                    """
                    <X played a Road Building Card --CDU Result-->
                    [<X built a road>--Sequence--><X built a road>]
                    !!!ASSUMPTION: the two following road building events will
                    always be consecutive.
                    """
                    place = '2.2.6-5 road building event'
                    events.Road.append(global_id)
                    cdu_road = append_schema(root, 'Complex_discourse_unit', events.Road[1:])
                    global_cdu_road = '_'.join([subdoc, cdu_road])
                    errors.extend(append_relation(
                        root, 'Result', events.Road[0], global_cdu_road, place))
                    errors.extend(append_relation(
                        root, 'Sequence', events.Road[1], events.Road[2], place))
                    events.Road = []
                continue

    """
    For resources distributions, we complete the XML tree and empty the
    list at the next dice roll.
    So for the last turn we may have forgotten to annotate some events.
    """
    if len(events.Dice) > 0:
        if len(events.Dice) == 2:
            # Resource distribution : 1 player
            place = '2.2.3-1 roll adn distribution'
            errors.extend(append_relation(
                root, 'Result', events.Dice[0], events.Dice[1], place))
        else:
            # Resource Distribution : 2 or more players
            place = '2.2.3-2 roll and distribution'
            cdu_dice = append_schema(
                root, 'Complex_discourse_unit', events.Dice[1:])
            global_cdu_dice = '_'.join([subdoc, cdu_dice])
            errors.extend(append_relation(
                root, 'Result', events.Dice[0], global_cdu_dice, place))
            for i in range(1, len(events.Dice) - 1):
                errors.extend(append_relation(
                    root, 'Continuation', events.Dice[i], events.Dice[i+1], place))
        events.Dice[:] = []

    return root, events, errors


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    """
    -For each subdoc in a game/document which has added non-linguistic events/nonNonPlayerSegments,
    open three files: text .ac file, units .aa file and discourse .aa file.
    -Convert each of the .aa (XML)files into tree objects.
    -Call add_units_annotations function on units tree object, call add_discourse_annotations
    function on discourse tree object.
    -Initialize an Event object which will be used to keep a record over all subdocs of the
    sequence of events necessary for each relation
    -Functions return amended tree objects plus a .txt file of implicit relations
    which could not be added because they would span two different subdocs.
    **For now, these must be corrected by hand**
    -Save the tree objects as files, overwriting old files.
    :return: units .aa files and discourse .aa files with added automatic relations
    """

    #ligne de commande : python nonling_annotations.py ../../data/pilot_nonling/test/pilot14/ SILVER

    init_mk_id()

    parser = argparse.ArgumentParser()

    parser.add_argument('folder', help='folder where the files to annotate are')
    parser.add_argument('metal', help=('version of the game you want to '
                                       'annotate (ex: GOLD)'))

    args = parser.parse_args()
    folder = os.path.abspath(args.folder)
    metal = args.metal
    name = os.path.basename(folder)

    unitsfolder = os.path.join(folder, 'units', metal)
    discoursefolder = os.path.join(folder, 'discourse', metal)

    N = len(os.listdir(unitsfolder)) / 2

    Implicit_Relations = []
    events = Events()

    for i in range(1, N+1):
        e = events

        subdoc = name + '_%02d' % i
        print(subdoc)

        textname = os.path.join(folder, 'unannotated', subdoc + '.ac')
        unitsname = os.path.join(unitsfolder, subdoc + '.aa')
        discoursename = os.path.join(discoursefolder, subdoc + '.aa')

        textfile = codecs.open(textname, 'r', 'utf-8')
        unitsfile = codecs.open(unitsname, 'r', 'ascii')
        discoursefile = codecs.open(discoursename, 'r', 'ascii')

        text = textfile.read()
        stringtree_units = unitsfile.read()
        units_tree = ET.fromstring(stringtree_units)
        stringtree_discourse = discoursefile.read()
        discourse_tree = ET.fromstring(stringtree_discourse)

        units_root = add_units_annotations(units_tree, text)

        discourse_root, events, errors = add_discourse_annotations(
            discourse_tree, text, e, subdoc)

        Implicit_Relations.extend(errors)

        with codecs.open(unitsname, 'w', 'ascii') as out:
            out.write(prettify(units_root))
        with codecs.open(discoursename, 'w', 'ascii') as out:
            out.write(prettify(discourse_root))

        textfile.close()
        unitsfile.close()
        discoursefile.close()

    if Implicit_Relations != []:

        error_report = '\n'.join(Implicit_Relations)
        filename = os.path.join(folder, 'Implicit_Relations.txt')
        with codecs.open(filename, 'w', 'ascii') as out:
            out.write(error_report)


if __name__ == '__main__':
    main()
