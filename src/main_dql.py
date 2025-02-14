#!/usr/bin/env python3

#####################################################################
# This script presents how to use the most basic features of the environment.
# It configures the engine, and makes the agent perform random actions.
# It also gets current state and reward earned with the action.
# <episodes> number of episodes are played.
# Random combination of buttons is chosen for every action.
# Game variables from state and last reward are printed.
#
# To see the scenario description go to "../../scenarios/README.md"
#####################################################################

from __future__ import print_function

from random import choice
import traceback
import datetime
from collections import deque
import argparse
import tensorflow as tf
print(f'Running TensorFlow v{tf.__version__}')
import os
from random import random, randint
import time
from time import sleep
from matplotlib import pyplot as plt
from shutil import rmtree

USE_GPU = True
DEVICES = None
os.environ['CUDA_VISIBLE_DEVICES'] = '0'

if USE_GPU:
    DEVICES = tf.config.experimental.list_physical_devices('GPU')
    for gpu in DEVICES:
        tf.config.experimental.set_memory_growth(gpu, True)
else:
    DEVICES = tf.config.list_physical_devices('CPU')
    tf.config.experimental.set_visible_devices(devices=DEVICES, device_type='CPU')
    tf.config.experimental.set_visible_devices(devices=[], device_type='GPU')

# tf.compat.v1.disable_eager_execution()
from algorithms.DeepQNetwork import DeepQNetwork
import numpy as np
from vizdoom import vizdoom as vzd

# print(gpus)
import numpy as np

def build_action(n_actions, index):
    return [True if i == index else False for i in range(0, n_actions)]

def build_all_actions(n_actions):
    return [build_action(n_actions, index) for index in range(0, n_actions)]

def setup_tensorboard(path):
    current_time = datetime.datetime.now().strftime('%d%m%Y-%H%M%S')
    
    train_log_dir = f'{path}/{current_time}/train'
    print(train_log_dir)
    os.makedirs(train_log_dir, exist_ok=True)
    train_summary_writer = tf.summary.create_file_writer(train_log_dir)
    return train_summary_writer

def write_tensorboard_data(writer, episode, avg_q, episode_reward, episode_loss):
    with writer.as_default():
        tf.summary.scalar('Average Q', avg_q, step=episode)
        tf.summary.scalar('Episode Reward', episode_reward, step=episode)
        tf.summary.scalar('Average Episode Loss', episode_loss, step=episode)
    writer.flush()

def build_memory_state(state, action, reward, new_state, is_terminal):
    state_array = np.array(state)
    # state_array = state_array.reshape(sa_shape[1:3] + (4,))
    state_array = np.squeeze(np.rollaxis(state_array, 0, 3))
    new_state_array = np.array(new_state)
    # new_state_array = new_state_array.reshape(nsa_shape[1:3] + (4,))
    new_state_array = np.squeeze(np.rollaxis(new_state_array, 0, 3))
    return {
        'state': state_array,
        'action': action,
        'reward': reward,
        'next_state': new_state_array,
        'terminal': is_terminal
    }

def dry_run(game, n_states, actions, available_maps):
    visited_states = []
    state_buffer = deque(maxlen=4)
    game.new_episode()
    for i in range(n_states):
        #TODO: refactor state collection and preprocessing into a single function
        state = game.get_state()
        frame = state.screen_buffer
        processed_frame = dql.preprocess(frame)
        if len(state_buffer) == 0:
            [state_buffer.append(processed_frame) for _ in range(4)]
        else:
            state_buffer.append(processed_frame)
        state_buffer_array = np.array(state_buffer)

        state_buffer_array = np.rollaxis(np.expand_dims(state_buffer_array, axis=-1), 0, 3)
        visited_states.append(np.squeeze(state_buffer_array))
        #TODO: plot visited stated, just to ensure that they actually make sense
        game.make_action(choice(actions), 4)
        if game.is_episode_finished():
            state_buffer.clear()
            game.close()
            setup_game(game, choice(available_maps))
            game.new_episode()
    return np.array(visited_states)

def eval_average_q(states, network):
    q_vals = network.get_actions(states)
    print(q_vals[500:520])
    # argmax = np.argmax(q_vals, axis=1)
    # max_values = np.array([q_vals[i][argmax[i]] for i in range(len(argmax))])
    max_values = np.max(q_vals, axis=1)
    return np.mean(max_values)

def limit_gpu_usage():
    gpus = tf.config.experimental.list_physical_devices('GPU')
    for gpu in gpus:
        tf.config.experimental.set_memory_growth(gpu, True)

def select_random_map(available_maps):
    chosen_map = choice(available_maps)

def setup_game(game, wad):

    print(f'Setting up map {wad["name"]}')

    game.load_config(f"../scenarios/configs/{wad['cfg']}")
    game.set_doom_scenario_path(f"../scenarios/{wad['name']}")
    game.set_doom_map(wad['map'])
    game.init()

def create_parser():
    pass

if __name__ == "__main__":
    train_name = 'doom_E1M1_time'
    # Create DoomGame instance. It will run the game and communicate with you.

    # #TODO: remove every ViZDoom configuration code and create a cfg file containing them
    available_maps = [
        # {'name': 'fork_corridor.wad', 'map': 'MAP01'},
        # {'name': 'simple_corridor.wad', 'map': 'MAP01', 'cfg': 'training.cfg'},
        # {'name': 'simple_corridor_distance.wad', 'map': 'MAP01', 'cfg': 'training.cfg'},
        # {'name': 'my_way_home.wad', 'map': 'MAP01', 'cfg': 'my_way_home.cfg'},
        # {'name': 'deadly_corridor.wad', 'map': 'MAP01', 'cfg': 'deadly_corridor.cfg'},
        {'name': 'basic.wad', 'map': 'map01', 'cfg': 'basic.cfg'},
        # {'name': 't_corridor.wad', 'map': 'MAP01'},
        # {'name': 'doom1_converted.wad', 'map': 'E1M1', 'cfg': 'training_fullmap.cfg'},
    ]
    game = vzd.DoomGame()
    setup_game(game, choice(available_maps))
    n_actions = game.get_available_buttons_size()

    actions = build_all_actions(n_actions)

    tf.config.experimental_run_functions_eagerly(False)
    # Run this many episodes
    episodes = 10000
    resolution = (320, 240)
    dims = (resolution[1]//4, resolution[0]//4)
    frames_per_state = 4
    account_time_reward = True
    account_dist_reward = False
    last_avg_q = -np.inf

    dql = DeepQNetwork(dims, n_actions, training=True, dueling=False)
    tb_writer = setup_tensorboard(f'../logs/{train_name}')
    state_buffer = deque(maxlen=4)

    #TODO: simplify game loop: collect state -> perform action -> collect next state -> train
    #TODO: check each and every line of this code. something MUST be off, it's impossible dude

    try:
        eval_states = dry_run(game, 300, actions, available_maps)
        setup_game(game, choice(available_maps))
        frame_number = 0
        t = datetime.datetime.now()
        for i in range(episodes):
            game.new_episode()
            timeout = game.get_episode_timeout() // 4
            tic = 0
            cumulative_reward = 0.
            loss = 0.
            initial_distance = vzd.doom_fixed_to_double(game.get_game_variable(vzd.GameVariable.USER2))
            start = time.time()
            train_steps = 0
            while not game.is_episode_finished():
                frame_number += 1
                train_steps += 1
                tic += 1.
                t = datetime.datetime.now()
                state = game.get_state()
                frame = state.screen_buffer
                processed_frame = dql.preprocess(frame)
                if len(state_buffer) == 0:
                    [state_buffer.append(processed_frame) for _ in range(frames_per_state)]
                else:
                    state_buffer.append(processed_frame)
                rand = random()
                epsilon = dql.next_eps(frame_number)
                if rand <= epsilon:
                    best_action = randint(0, n_actions-1)
                else:
                    state_array = np.array(state_buffer)
                    state_array = np.expand_dims(np.squeeze(np.rollaxis(state_array, 0, 3)), axis=0)
                    q_vals = dql.get_actions(state_array)
                    best_action = np.argmax(q_vals, axis=1)

                a = build_action(n_actions, best_action)
                r = game.make_action(a, 4)
                if account_time_reward:
                    tic_reward = tic / timeout
                    r -= tic_reward
                if account_dist_reward:
                    dist = vzd.doom_fixed_to_double(game.get_game_variable(vzd.GameVariable.USER1))
                    dist = dist / initial_distance
                    r -= dist
                if r > 1.:
                    print("Agent found some positive reward:", r)
                cumulative_reward += r
                isterminal = game.is_episode_finished()
                if isterminal:
                    print("Terminal state. Current tic:", tic)
                    new_state_buffer = state_buffer.copy()
                else:
                    new_state = game.get_state()
                    new_frame = new_state.screen_buffer
                    processed_new_frame = dql.preprocess(new_frame)
                    new_state_buffer = state_buffer.copy()
                    new_state_buffer.append(processed_new_frame)
                memory_state = build_memory_state(state_buffer, best_action, r, new_state_buffer, isterminal)
                dql.add_transition(memory_state)
                history = dql.train()
                if history is not None:
                    loss += history.history['loss'][0]
                # print(f'Time to complete one training cycle: {time.time() - start}')
            episode_loss = loss / train_steps
            diff = time.time() - start
            state_buffer.clear()
            game.close()
            setup_game(game, choice(available_maps))

            # METRICS

            print(f'End of episode {i}. Episode reward: {cumulative_reward}. Episode loss: {episode_loss}. Time to finish episode: {str(diff)}')
            print(f'Collecting Average Q for weights of episode {i}...')
            avg_q = eval_average_q(eval_states, dql)
            print(f'Episode {i}: Average Q: {avg_q}')
            write_tensorboard_data(tb_writer, i, avg_q, cumulative_reward, episode_loss)
            if avg_q > last_avg_q:
                print(f'Average Q {avg_q} greater than last average Q {last_avg_q}.')
                last_avg_q = avg_q

            else:
                print(f'Average Q {avg_q} lower than last average Q {last_avg_q}.')
            dql.save_weights(f'../weights/{train_name}')


    except Exception as e:
        traceback.print_exc()
        print(e)
        game.close()
        exit(1)
    # It will be done automatically anyway but sometimes you need to do it in the middle of the program...
    game.close()
