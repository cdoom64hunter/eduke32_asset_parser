#!/bin/python3
# Author: Dino Bollinger
# Licensed under BSD 3-Clause License, see included LICENSE file
"""
This (more or less primitive) script is used to find which tilenums are part of an actors animations.
It relies on the output of get_con_instances.sh for defined names and variables.
It outputs a single pickle file containing a numpy array of size MAXTILES, and reports unused actions, ai, etc.
"""
import os
import re
import sys
import nltk
import numpy as np
import pickle
#nltk.download('punkt')

CODE_DIR:str = ""
MAXTILES:int = -1

if len(sys.argv) >= 2:
    MAXTILES = int(sys.argv[1])
else:
    print("Must specify maxtiles!", file=sys.stderr)
    exit(1)

if len(sys.argv) >= 3:
    CODE_DIR = sys.argv[2]
else:
    print("Must specify code directory!", file=sys.stderr)
    exit(2)


actor_frame_array = np.zeros(MAXTILES)
outfile = "./actor_frame_array.pkl"

action_defs = dict()
ai_defs = dict()

state_actions = dict()
actor_actions = dict()

state_ai = dict()
actor_ai = dict()

states_in_actor = dict()
states_in_state = dict()

initial_actions = dict()

ai_pattern = re.compile("^ai\s+([A-Za-z0-9_]+)\s+(-?[A-Z0-9_]+)")
action_pattern = re.compile("^action\s+([A-Za-z0-9_]+)\s+(-?[0-9]+)")
useractor_pattern = re.compile("^useractor\s+([A-Za-z0-9_]+)\s+[A-Za-z0-9_]+\s+[A-Z0-9_]+\s+[A-Z0-9_]+")
actor_pattern = re.compile("^actor\s+([A-Za-z0-9_]+)\s+[A-Z0-9_]+\s+[A-Z0-9_]+")


# Load name definitions
defined_names = dict()
with open("./statistics/defs.txt", "r") as fd:
    for line in fd:
        tokens = (line.strip()).split()
        try:
            new_value = 0
            if (tokens[2] == "YES"): new_value = 1
            elif tokens[2] == "NO": new_value = 0
            elif tokens[2].startswith("0x"): new_value = int(tokens[2],16)
            else: new_value = int(tokens[2])

            defined_names[tokens[1]] = new_value
        except ValueError:
            print(f"Non integer define: {line.strip()}")




def clean_line(line):
    cleaned_line = line.strip()
    cleaned_line = re.sub("//.*$", "", cleaned_line)
    cleaned_line = re.sub("qputs.*$", "", cleaned_line)
    return cleaned_line

def get_tilenum_for_name(line, name):
    tilenum = None
    try:
        if name.startswith("0x"): tilenum = int(name, 16)
        else: tilenum = int(name)
    except ValueError:
        try:
            tilenum = defined_names[name]
        except KeyError:
            print(f"Name '{name}' is unknown:: {line.strip()}")

    return tilenum


def main():
    # traverse root directory, and list directories as dirs and files as files
    for root, dirs, files in os.walk(CODE_DIR):
        for f in files:
            with open(os.path.join(root, f), 'r') as fd:
                all_file_tokens = []
                commented = False
                for line in fd:
                    if "/*" in line:
                        commented = True

                    if not commented:
                        cleaned_line = clean_line(line)
                        if action_pattern.match(cleaned_line):
                            tokens = cleaned_line.split()
                            action_name = tokens[1]
                            startframe = tokens[2]
                            if len(tokens) > 3:
                                framecount = tokens[3]
                            else:
                                framecount = "1"

                            if len(tokens) > 4:
                                viewtype = tokens[4]
                            else:
                                viewtype = "1"
                            action_defs[action_name] = {"startframe": startframe, "framecount": framecount, "viewtype": viewtype}
                        else:
                            if ai_pattern.match(cleaned_line):
                                tokens = cleaned_line.split()
                                ai_name = tokens[1]
                                action_name = tokens[2]
                                ai_defs[ai_name] = action_name
                            elif useractor_pattern.match(cleaned_line):
                                tokens = cleaned_line.split()
                                if len(tokens) >= 5:
                                    nactor_name = tokens[2]
                                    ninit_action = tokens[4]
                                    #print(tokens)
                                    initial_actions[nactor_name] = ninit_action
                            elif actor_pattern.match(cleaned_line):
                                tokens = cleaned_line.split()
                                if len(tokens) >= 4:
                                    initial_actions[tokens[1]] = tokens[3]
                            tokens = nltk.word_tokenize(cleaned_line)
                            all_file_tokens.extend(tokens)

                    elif "*/" in line:
                        commented = False

                in_actor = False
                in_state = False
                in_event = False

                token_iterator = iter(all_file_tokens)
                try:
                    ctoken = next(token_iterator)
                    while True:
                        #print(ctoken)
                        if ctoken == "defstate":
                            assert(not in_state)
                            state_name = next(token_iterator)
                            in_state = True
                        elif ctoken == "state" and not (in_actor or in_state or in_event):
                            state_name = next(token_iterator)
                            in_state = True
                        elif ctoken == "ends":
                            assert(in_state)
                            state_name = None
                            in_state = False
                        elif ctoken == "actor" or ctoken == "eventloadactor":
                            assert(not in_actor)
                            actor_name = next(token_iterator)
                            in_actor = True
                        elif ctoken == "useractor":
                            assert(not in_actor)
                            actor_type = next(token_iterator)
                            actor_name = next(token_iterator)
                            in_actor = True
                        elif ctoken == "enda":
                            assert(in_actor)
                            actor_type = None
                            actor_name = None
                            in_actor = False
                        elif ctoken == "onevent" or ctoken == "appendevent":
                            assert(not in_event)
                            event_name = next(token_iterator)
                            in_event = True
                        elif ctoken == "endevent":
                            assert(in_event)
                            event_name = None
                            in_event = False


                        elif ctoken == "ai":
                            new_ai_name = next(token_iterator)
                            if in_actor:
                                if actor_name in actor_ai:
                                    actor_ai[actor_name].append(new_ai_name)
                                else:
                                    actor_ai[actor_name] = [new_ai_name]
                            elif in_state:
                                if state_name in state_ai:
                                    state_ai[state_name].append(new_ai_name)
                                else:
                                    state_ai[state_name] = [new_ai_name]

                            else: #definition
                                pass


                        elif ctoken == "action":
                            new_action = next(token_iterator)
                            if in_actor:
                                if actor_name in actor_actions:
                                    actor_actions[actor_name].append(new_action)
                                else:
                                    actor_actions[actor_name] = [new_action]
                            elif in_state:
                                if state_name in state_actions:
                                    state_actions[state_name].append(new_action)
                                else:
                                    state_actions[state_name] = [new_action]
                            else: # definition
                                if new_action not in action_defs:
                                    action_defs[new_action] = {"startframe": "0", "framecount": "1", "viewtype": "1"}

                        elif ctoken == "state" and in_actor:
                            new_state = next(token_iterator)
                            if actor_name in states_in_actor:
                                states_in_actor[actor_name].append(new_state)
                            else:
                                states_in_actor[actor_name] = [new_state]
                        elif ctoken == "state" and in_state:
                            new_state = next(token_iterator)
                            if state_name in states_in_state:
                                states_in_state[state_name].append(new_state)
                            else:
                                states_in_state[state_name] = [new_state]

                        ctoken = next(token_iterator)
                except StopIteration:
                    print(f"Parsed file {root + '/' +  f}")

    print(f"Number of actors with initial actions: {len(initial_actions)}")
    print(f"Number of defined actions: {len(action_defs)}")
    print(f"Number of defined ai routines: {len(ai_defs)}")
    print(f"Number of states that use actions: {len(state_actions)}")
    print(f"Number of states that use ai: {len(state_ai)}")
    print(f"Number of actors that use actions: {len(actor_actions)}")
    print(f"Number of actors that call states: {len(states_in_actor)}")
    print(f"Number of actors that use ai: {len(actor_ai)}")
    print(f"Number of states that call states: {len(states_in_state)}")


    total_actions_per_actor = dict()
    unused_actions = set(action_defs)

    aggr_actions_in_states = dict()
    aggr_ai_in_states = dict()

    for state in states_in_state.keys():
        todo_set = set(states_in_state[state])
        seen_set = set(state)

        if state in state_actions: new_actions = set(state_actions[state])
        else: new_actions = set()

        if state in state_ai: new_ai = set(state_ai[state])
        else: new_ai = set()

        while len(todo_set) > 0:
            next_state = todo_set.pop()
            seen_set.add(next_state)
            if next_state in state_actions: new_actions = new_actions.union(state_actions[next_state])
            if next_state in state_ai: new_ai = new_ai.union(state_ai[next_state])
            if next_state in states_in_state: todo_set = todo_set.union([s for s in states_in_state[next_state] if (s not in seen_set)])

        aggr_actions_in_states[state] = new_actions
        aggr_ai_in_states[state] = new_ai



    for state in state_actions.keys():
        if state in aggr_actions_in_states:
           aggr_actions_in_states[state] = aggr_actions_in_states[state].union(state_actions[state])
        else:
            aggr_actions_in_states[state] = set(state_actions[state])



    for state in state_ai.keys():
        if state in aggr_ai_in_states:
            aggr_ai_in_states[state] = aggr_ai_in_states[state].union(state_ai[state])
        else:
            aggr_ai_in_states[state] = set(state_ai[state])



    for actor in list(actor_actions.keys()) + list(states_in_actor.keys()):
        if actor in states_in_actor:
            states = states_in_actor[actor]
        else:
            states = []

        if actor in actor_actions:
            total_actions = set(actor_actions[actor])
        else:
            total_actions = set()

        for s in states:
            if s in aggr_actions_in_states:
                total_actions = total_actions.union(aggr_actions_in_states[s])

        total_actions_per_actor[actor] = total_actions


    for actor in list(actor_ai.keys()) + list(states_in_actor.keys()):
        states = []
        if actor in states_in_actor:
            states = states_in_actor[actor]

        if actor in total_actions_per_actor:
            total_actions = total_actions_per_actor[actor]
        else:
            total_actions = set()

        if actor in actor_ai:
            for ai in actor_ai[actor]:
                if ai not in ai_defs:
                    print(f"Undefined ai '{ai}' in actor '{actor}'")
                else:
                    total_actions.add(ai_defs[ai])

        for s in states:
            if s in aggr_ai_in_states:
                for ai in aggr_ai_in_states[s]:
                    if ai not in ai_defs:
                        print(f"Undefined ai '{ai}' in state '{s}'")
                    else:
                        total_actions.add(ai_defs[ai])

        total_actions_per_actor[actor] = total_actions

    for actor in initial_actions.keys():
        if actor in total_actions_per_actor:
            total_actions_per_actor[actor].add(initial_actions[actor])
        else:
            total_actions_per_actor[actor] = {initial_actions[actor]}

    for actor, total_actions in total_actions_per_actor.items():
        for a in total_actions:
            if a in unused_actions:
                unused_actions.remove(a)

            if a not in action_defs:
                print(f"Undefined action '{a}' in actor '{actor}'")
            else:
                act_dict = action_defs[a]
                tilenum = get_tilenum_for_name("", str(actor))
                startframe = get_tilenum_for_name("", act_dict["startframe"])
                framecount = get_tilenum_for_name("", act_dict["framecount"])
                viewtype = get_tilenum_for_name("", act_dict["viewtype"])
                if tilenum and startframe and framecount and viewtype:
                    startpoint = tilenum + startframe
                    endpoint = tilenum + startframe + framecount * viewtype
                    #print(f"actor: {actor} -- action: {a} -- range: {startpoint} - {endpoint - 1}")
                    actor_frame_array[startpoint:endpoint] = 1



    print(f"Unused Actions: {unused_actions}")
    print(f"Number of Unused Actions: {len(unused_actions)}")
    print(f"Number of tiles that are part of actor frames: {np.count_nonzero(actor_frame_array)}")
    with open(outfile, "wb") as fd:
        pickle.dump(actor_frame_array, fd, pickle.HIGHEST_PROTOCOL)
        print(f"Actor frame array written to: '{outfile}'")

if __name__ == "__main__":
    main()