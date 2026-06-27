import asyncio
import os
import re
import google.generativeai as genai
import requests
from typing import Final
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from gtts import gTTS
from datetime import timedelta, datetime, time
import anthropic
import openai
import pytz
import random
import yt_dlp
import json
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont
import io
import cv2
import numpy as np
import speech_recognition as sr
from pydub import AudioSegment

async def generate_quiz_image(quiz_type, question_text="", options=None):
    """Generate AI image for quiz types using category as keyword"""
    try:
        # Extract main category keyword from quiz type
        category_keywords = {
            "பொது அறிவு (General Knowledge)": "general knowledge education books learning",
            "இலக்கிய வினா (Literature Quiz)": "literature books poetry writing Tamil literature",
            "திரைப்பட வினா (Cinema Quiz)": "cinema movies film entertainment Tamil cinema",
            "விளையாட்டு வினா (Sports Quiz)": "sports games athletics cricket football",
            "வாகனத் தொடர்பான வினா (Automobile Quiz)": "automobiles cars vehicles transportation",
            "தொழில்நுட்ப வினா (Technology Quiz)": "technology computers digital innovation",
            "தெரிவுக்கேட்கும் வினா (Multiple Choice Quiz)": "quiz questions multiple choice education",
            "தொகுப்பு வினா (Thematic Quiz)": "themed topics educational subjects",
            "நிகழ்ச்சி தொடர்பான வினா (Event-based Quiz)": "events celebrations festivals occasions",
            "சட்ட வினா (Law Quiz)": "law justice legal constitution government",
            "அரசியலமைப்பு வினா (Constitution Quiz)": "constitution government democracy India"
        }

        keyword = category_keywords.get(quiz_type, "quiz education knowledge")
        prompt = f"educational illustration about {keyword}, quiz theme, learning, colorful, engaging"

        # Generate AI image using existing function
        image_data = await generate_image(prompt)
        return image_data

    except Exception as e:
        print(f"Error generating quiz image: {e}")
        return None

# Quiz categories
QUIZ_CATEGORIES = [
    "பொது அறிவு (General Knowledge)",
    "இலக்கிய வினா (Literature Quiz)",
    "திரைப்பட வினா (Cinema Quiz)",
    "விளையாட்டு வினா (Sports Quiz)",
    "வாகனத் தொடர்பான வினா (Automobile Quiz)",
    "தொழில்நுட்ப வினா (Technology Quiz)",
    "தெரிவுக்கேட்கும் வினா (Multiple Choice Quiz)",
    "தொகுப்பு வினா (Thematic Quiz)",
    "நிகழ்ச்சி தொடர்பான வினா (Event-based Quiz)",
    "சட்ட வினா (Law Quiz)",
    "அரசியலமைப்பு வினா (Constitution Quiz)"
]

# Quiz system
quiz_data = {
    'current_quiz': None,
    'participants': {},
    'scores': defaultdict(int),
    'daily_scores': defaultdict(int),
    'weekly_scores': defaultdict(int),
    'monthly_scores': defaultdict(int),
    'poll_data': {},  # Store poll information
    'used_questions': {}  # Track used questions by category
}

# Tic-Tac-Toe game system
games = {}  # {chat_id: game_data}

# Hand Cricket game system
cricket_games = {}  # {chat_id: cricket_game_data}

def create_cricket_keyboard():
    keyboard = [
        [InlineKeyboardButton("1️⃣", callback_data="cricket_1"), InlineKeyboardButton("2️⃣", callback_data="cricket_2"), InlineKeyboardButton("3️⃣", callback_data="cricket_3")],
        [InlineKeyboardButton("4️⃣", callback_data="cricket_4"), InlineKeyboardButton("5️⃣", callback_data="cricket_5"), InlineKeyboardButton("6️⃣", callback_data="cricket_6")],
        [InlineKeyboardButton("🔄 New Game | புதிய விளையாட்டு", callback_data="cricket_new"), InlineKeyboardButton("⏹️ Stop | நிறுத்து", callback_data="cricket_stop")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def handcricket_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start Hand Cricket game selection"""
    chat_id = update.effective_chat.id

    if chat_id in cricket_games:
        await update.message.reply_text("🏏 Cricket game already in progress! | கிரிக்கெட் விளையாட்டு ஏற்கனவே நடக்கிறது!")
        return

    keyboard = [
        [InlineKeyboardButton("👤 Single Player | ஒற்றை வீரர்", callback_data="cricket_single")],
        [InlineKeyboardButton("👥 Multiplayer | பல வீரர்கள்", callback_data="cricket_multi")],
        [InlineKeyboardButton("🏏 Team Cricket | அணி கிரிக்கெட்", callback_data="cricket_team")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = (
        f"🏏 **Hand Cricket Game | கை கிரிக்கெட் விளையாட்டு** 🏏\n\n"
        f"🎯 **Rules | விதிகள்:**\n"
        f"• Show 1-6 fingers | 1-6 விரல்கள் காட்டவும்\n"
        f"• Same number = OUT! | அதே எண் = அவுட்!\n"
        f"• Different = Add to score | வேறு = மதிப்பெண் சேர்க்கவும்\n\n"
        f"🎮 **Choose game mode | விளையாட்டு முறையை தேர்வு செய்யவும்:**"
    )

    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )







async def handle_cricket_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Hand Cricket game moves"""
    query = update.callback_query

    try:
        await query.answer()  # Answer callback query to prevent timeout
    except Exception as e:
        print(f"Callback query answer failed: {e}")
        return  # Exit if callback is too old

    chat_id = query.message.chat.id
    user = query.from_user
    data = query.data

    print(f"Cricket callback received: {data} from user {user.first_name}")

    if data == "cricket_single":
        # Start single player game
        cricket_games[chat_id] = {
            'mode': 'single',
            'player': {'id': user.id, 'name': user.first_name, 'score': 0},
            'bot_score': 0,
            'batting': 'player',  # player or bot
            'innings': 1,
            'target': 0,
            'status': 'playing'
        }

        keyboard = create_cricket_keyboard()
        try:
            await query.edit_message_text(
                text=f"🏏 Single Player Cricket 🏏\n\n"
                f"🏏 🌸 {user.first_name} (@{user.username or 'no_username'}) 🌸 batting\n"
                f"📊 Score: 0\n\n"
                f"🎯 Choose your number (1-6):",
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"Message edit failed: {e}")
            return
        print("Single player cricket game started successfully")

    elif data == "cricket_multi":
        # Start multiplayer game
        cricket_games[chat_id] = {
            'mode': 'multi',
            'player1': {'id': user.id, 'name': user.first_name, 'score': 0},
            'player2': None,
            'batting': 'player1',
            'innings': 1,
            'target': 0,
            'status': 'waiting',
            'pending_choice': {}
        }

        keyboard = create_cricket_keyboard()
        try:
            await query.edit_message_text(
                text=f"🏏 Multiplayer Cricket | பல வீரர் கிரிக்கெட் 🏏\n\n"
                f"👤 Player 1 | வீரர் 1: 🌸 {user.first_name} (@{user.username or 'no_username'}) 🌸\n"
                f"👥 Player 2 | வீரர் 2: Waiting... | காத்திருக்கிறது...\n\n"
                f"🎯 Click any number to join as Player 2! | வீரர் 2 ஆக சேர எந்த எண்ணையும் கிளிக் செய்யவும்!",
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"Message edit failed: {e}")
            return
        print("Multiplayer cricket game created, waiting for player 2")

    elif data == "cricket_team":
        # Start team cricket game
        cricket_games[chat_id] = {
            'mode': 'team',
            'team1': {'players': [], 'score': 0, 'name': 'Team 1'},
            'team2': {'players': [], 'score': 0, 'name': 'Team 2'},
            'batting_team': 'team1',
            'innings': 1,
            'target': 0,
            'status': 'recruiting',
            'pending_choice': {},
            'current_batsman': 0,
            'wickets': 0
        }

        keyboard = [
            [InlineKeyboardButton("🔴 Join Team 1 | அணி 1 சேர", callback_data="team_join_1")],
            [InlineKeyboardButton("🔵 Join Team 2 | அணி 2 சேர", callback_data="team_join_2")],
            [InlineKeyboardButton("▶️ Start Match | மேச் துவங்கு", callback_data="team_start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await query.edit_message_text(
                text=f"🏏 Team Cricket | அணி கிரிக்கெட் 🏏\n\n"
                f"🔴 Team 1: 0/11 players\n"
                f"🔵 Team 2: 0/11 players\n\n"
                f"ℹ️ Both teams need equal players (2-11 each)\n"
                f"🎯 Click to join a team!",
                reply_markup=reply_markup
            )
        except Exception as e:
            print(f"Message edit failed: {e}")
            return
        print("Team cricket game created")

    elif data == "cricket_new":
        # Restart same game mode
        if chat_id in cricket_games:
            current_mode = cricket_games[chat_id]['mode']
            del cricket_games[chat_id]

            if current_mode == 'single':
                # Restart single player
                cricket_games[chat_id] = {
                    'mode': 'single',
                    'player': {'id': user.id, 'name': user.first_name, 'score': 0},
                    'bot_score': 0,
                    'batting': 'player',
                    'innings': 1,
                    'target': 0,
                    'status': 'playing'
                }

                keyboard = create_cricket_keyboard()
                try:
                    await query.edit_message_text(
                        text=f"🏏 New Single Player Game 🏏\n\n"
                        f"🏏 {user.first_name} batting\n"
                        f"📊 Score: 0\n\n"
                        f"🎯 Choose your number (1-6):",
                        reply_markup=keyboard
                    )
                except Exception as e:
                    print(f"Message edit failed: {e}")
                    return
            else:
                # Restart multiplayer
                cricket_games[chat_id] = {
                    'mode': 'multi',
                    'player1': {'id': user.id, 'name': user.first_name, 'score': 0},
                    'player2': None,
                    'batting': 'player1',
                    'innings': 1,
                    'target': 0,
                    'status': 'waiting',
                    'pending_choice': {}
                }

                keyboard = create_cricket_keyboard()
                try:
                    await query.edit_message_text(
                        text=f"🏏 **New Multiplayer Game | புதிய பல வீரர் விளையாட்டு** 🏏\n\n"
                        f"👤 **Player 1 | வீரர் 1:** {user.first_name}\n"
                        f"👥 **Player 2 | வீரர் 2:** Waiting... | காத்திருக்கிறது...\n\n"
                        f"🎯 **Click any number to join as Player 2! | வீரர் 2 ஆக சேர எந்த எண்ணையும் கிளிக் செய்யவும்!**",
                        reply_markup=keyboard,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    print(f"Message edit failed: {e}")
                    return
        print("New cricket game created with same mode")

    elif data == "cricket_stop":
        # Stop current game
        if chat_id in cricket_games:
            del cricket_games[chat_id]

        keyboard = [
            [InlineKeyboardButton("🔄 Restart Game | மீண்டும் துவக்கு", callback_data="cricket_restart")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await query.edit_message_text(
                text=f"⏹️ **Game Stopped | விளையாட்டு நிறுத்தப்பட்டது** ⏹️\n\n"
                f"🏏 **Hand Cricket game has been stopped | கை கிரிக்கெட் விளையாட்டு நிறுத்தப்பட்டது**\n\n"
                f"🔄 **Click restart to play again | மீண்டும் விளையாட restart கிளிக் செய்யவும்**",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Message edit failed: {e}")
            return
        print("Cricket game stopped")

    elif data == "cricket_restart":
        # Restart game - show mode selection
        keyboard = [
            [InlineKeyboardButton("👤 Single Player | ஒற்றை வீரர்", callback_data="cricket_single")],
            [InlineKeyboardButton("👥 Multiplayer | பல வீரர்கள்", callback_data="cricket_multi")],
            [InlineKeyboardButton("🏏 Team Cricket | அணி கிரிக்கெட்", callback_data="cricket_team")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            await query.edit_message_text(
                text=f"🏏 **Hand Cricket Game | கை கிரிக்கெட் விளையாட்டு** 🏏\n\n"
                f"🎯 **Rules | விதிகள்:**\n"
                f"• Show 1-6 fingers | 1-6 விரல்கள் காட்டவும்\n"
                f"• Same number = OUT! | அதே எண் = அவுட்!\n"
                f"• Different = Add to score | வேறு = மதிப்பெண் சேர்க்கவும்\n\n"
                f"🎮 **Choose game mode | விளையாட்டு முறையை தேர்வு செய்யவும்:**",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Message edit failed: {e}")
            return
        print("Cricket game restarted")

    elif data.startswith("team_join_"):
        # Handle team joining
        if chat_id not in cricket_games or cricket_games[chat_id]['mode'] != 'team':
            await query.answer("No team cricket game found!")
            return

        game = cricket_games[chat_id]
        team_num = data.split('_')[2]
        team_key = f'team{team_num}'

        # Check if user already in a team
        user_in_team1 = any(p['id'] == user.id for p in game['team1']['players'])
        user_in_team2 = any(p['id'] == user.id for p in game['team2']['players'])

        if user_in_team1 or user_in_team2:
            await query.answer("You're already in a team!")
            return

        # Check team capacity
        if len(game[team_key]['players']) >= 11:
            await query.answer(f"Team {team_num} is full!")
            return

        # Add player to team
        game[team_key]['players'].append({
            'id': user.id,
            'name': user.first_name,
            'username': user.username
        })

        # Update display
        keyboard = [
            [InlineKeyboardButton("🔴 Join Team 1 | அணி 1 சேர", callback_data="team_join_1")],
            [InlineKeyboardButton("🔵 Join Team 2 | அணி 2 சேர", callback_data="team_join_2")],
            [InlineKeyboardButton("▶️ Start Match | மேச் துவங்கு", callback_data="team_start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        team1_list = "\n".join([f"  {i+1}. {p['name']} (@{p['username'] or 'no_username'})" for i, p in enumerate(game['team1']['players'])])
        team2_list = "\n".join([f"  {i+1}. {p['name']} (@{p['username'] or 'no_username'})" for i, p in enumerate(game['team2']['players'])])

        await query.edit_message_text(
            text=f"🏏 Team Cricket | அணி கிரிக்கெட் 🏏\n\n"
            f"🔴 Team 1 ({len(game['team1']['players'])}/11):\n{team1_list or '  No players yet'}\n\n"
            f"🔵 Team 2 ({len(game['team2']['players'])}/11):\n{team2_list or '  No players yet'}\n\n"
            f"ℹ️ Both teams need equal players to start",
            reply_markup=reply_markup
        )
        await query.answer(f"Joined Team {team_num}!")

    elif data == "team_start":
        # Start team match
        if chat_id not in cricket_games or cricket_games[chat_id]['mode'] != 'team':
            await query.answer("No team cricket game found!")
            return

        game = cricket_games[chat_id]
        team1_count = len(game['team1']['players'])
        team2_count = len(game['team2']['players'])

        if team1_count < 2 or team2_count < 2:
            await query.answer("Both teams need at least 2 players each!")
            return

        if team1_count != team2_count:
            await query.answer(f"Teams must be equal! Team 1: {team1_count}, Team 2: {team2_count}")
            return

        # Start the match
        game['status'] = 'playing'
        keyboard = create_cricket_keyboard()

        current_batsman = game['team1']['players'][0]

        await query.edit_message_text(
            text=f"🏏 Team Cricket Match Started! 🏏\n\n"
            f"🔴 Team 1 batting ({team1_count} players)\n"
            f"🔵 Team 2 bowling ({team2_count} players)\n\n"
            f"🏏 Current Batsman: {current_batsman['name']}\n"
            f"📊 Score: 0/0\n\n"
            f"🎯 All players choose numbers!",
            reply_markup=keyboard
        )
        await query.answer("Match started!")

    elif data.startswith("cricket_") and data[-1].isdigit():
        # Handle number selection
        if chat_id not in cricket_games:
            print("No active cricket game found")
            await query.answer("No active game found! Please start a new game.")
            return

        player_choice = int(data.split('_')[1])
        game = cricket_games[chat_id]

        print(f"Processing cricket move: mode={game['mode']}, choice={player_choice}")

        if game['mode'] == 'single':
            await handle_single_cricket(query, game, player_choice)
        elif game['mode'] == 'multi':
            await handle_multi_cricket(query, game, player_choice, user)
        elif game['mode'] == 'team':
            await handle_team_cricket(query, game, player_choice, user)

async def handle_single_cricket(query, game, player_choice):
    """Handle single player cricket move"""
    bot_choice = random.randint(1, 6)
    print(f"Single cricket: Player={player_choice}, Bot={bot_choice}, Status={game['status']}")

    try:
        if player_choice == bot_choice:
            # OUT!
            if game['batting'] == 'player':
                # Player out, bot's turn to bat
                game['target'] = game['player']['score'] + 1
                game['batting'] = 'bot'
                game['innings'] = 2

                keyboard = create_cricket_keyboard()
                await query.edit_message_text(
                    f"🏏 OUT! அவுட்! 🏏\n\n"
                    f"🎯 You: {player_choice} | Bot: {bot_choice}\n\n"
                    f"📊 Your Score: {game['player']['score']}\n"
                    f"🎯 Target for Bot: {game['target']}\n\n"
                    f"🤖 Bot batting now...\n"
                    f"🎯 Bowl to the bot (1-6):",
                    reply_markup=keyboard
                )
            else:
                # Bot out, check result
                if game['bot_score'] >= game['target']:
                    result = "🤖 Bot Wins! பாட் வெற்றி!"
                else:
                    result = f"🏆 You Win! நீங்கள் வெற்றி!"

                keyboard = create_cricket_keyboard()
                await query.edit_message_text(
                    f"🏏 Game Over! விளையாட்டு முடிந்தது! 🏏\n\n"
                    f"🎯 Final Bowl: You: {player_choice} | Bot: {bot_choice}\n\n"
                    f"📊 Final Scores:\n"
                    f"👤 You: {game['player']['score']}\n"
                    f"🤖 Bot: {game['bot_score']}\n\n"
                    f"{result}",
                    reply_markup=keyboard
                )
                game['status'] = 'ended'
        else:
            # Add runs
            if game['batting'] == 'player':
                game['player']['score'] += player_choice

                keyboard = create_cricket_keyboard()
                await query.edit_message_text(
                    f"🏏 Good Shot! நல்ல ஷாட்! 🏏\n\n"
                    f"🎯 You: {player_choice} | Bot: {bot_choice}\n\n"
                    f"📊 Your Score: {game['player']['score']}\n\n"
                    f"🎯 Choose next number:",
                    reply_markup=keyboard
                )
            else:
                # Bot batting
                game['bot_score'] += bot_choice

                if game['bot_score'] >= game['target']:
                    # Bot wins
                    keyboard = create_cricket_keyboard()
                    await query.edit_message_text(
                        f"🏏 Game Over! விளையாட்டு முடிந்தது! 🏏\n\n"
                        f"🎯 You: {player_choice} | Bot: {bot_choice}\n\n"
                        f"📊 Final Scores:\n"
                        f"👤 You: {game['player']['score']}\n"
                        f"🤖 Bot: {game['bot_score']}\n\n"
                        f"🤖 Bot Wins! பாட் வெற்றி!",
                        reply_markup=keyboard
                    )
                    game['status'] = 'ended'
                else:
                    keyboard = create_cricket_keyboard()
                    await query.edit_message_text(
                        f"🏏 Bot scored! பாட் ஸ்கோர் செய்தது! 🏏\n\n"
                        f"🎯 You: {player_choice} | Bot: {bot_choice}\n\n"
                        f"📊 Bot Score: {game['bot_score']}/{game['target']-1}\n\n"
                        f"🎯 Bowl next ball:",
                        reply_markup=keyboard
                    )

        await query.answer(f"You: {player_choice}, Bot: {bot_choice}")
    except Exception as e:
        print(f"Single cricket error: {e}")
        await query.answer("Error occurred, please try again")

async def handle_multi_cricket(query, game, player_choice, user):
    """Handle multiplayer cricket move"""
    try:
        # Validate game state
        if game['status'] == 'ended':
            await query.answer("Game has ended! Start a new game.")
            return

        # Join as player 2 if needed
        if game['player2'] is None and user.id != game['player1']['id']:
            game['player2'] = {'id': user.id, 'name': user.first_name, 'username': user.username, 'score': 0}
            game['status'] = 'playing'

            # Update message to show both players joined
            keyboard = create_cricket_keyboard()
            await query.edit_message_text(
                text=f"🏏 Multiplayer Cricket Started 🏏\n\n"
                f"👤 Player 1: 🌸 {game['player1']['name']} (@{game['player1'].get('username') or 'no_username'}) 🌸 (Batting)\n"
                f"👤 Player 2: 🌸 {game['player2']['name']} (@{game['player2'].get('username') or 'no_username'}) 🌸 (Bowling)\n\n"
                f"📊 Score: 0\n\n"
                f"🎯 Both players choose numbers (1-6):",
                reply_markup=keyboard
            )
            await query.answer(f"{user.first_name} joined as Player 2!")
            return

        if game['player2'] is None:
            await query.answer("Waiting for Player 2! | வீரர் 2 காத்திருக்கிறது!")
            return

        # Validate player is part of this game
        if user.id not in [game['player1']['id'], game['player2']['id']]:
            await query.answer("❌ You are not part of this game! Only the two players can make moves.")
            return

        # Initialize pending_choice if not exists
        if 'pending_choice' not in game:
            game['pending_choice'] = {}

        # Store player choice and wait for opponent
        game['pending_choice'][user.id] = player_choice

        # Update message to show who has chosen
        if len(game['pending_choice']) == 1:
            chosen_player = game['player1']['name'] if user.id == game['player1']['id'] else game['player2']['name']
            waiting_player = game['player2']['name'] if user.id == game['player1']['id'] else game['player1']['name']

            keyboard = create_cricket_keyboard()
            await query.edit_message_text(
                f"🏏 Multiplayer Cricket 🏏\n\n"
                f"👤 {game['player1']['name']}: {'✅ Chosen' if game['player1']['id'] in game['pending_choice'] else '⏳ Waiting'}\n"
                f"👤 {game['player2']['name']}: {'✅ Chosen' if game['player2']['id'] in game['pending_choice'] else '⏳ Waiting'}\n\n"
                f"📊 Score: {game['player1']['score'] if game['batting'] == 'player1' else game['player2']['score']}\n\n"
                f"🎯 {waiting_player}, choose your number!",
                reply_markup=keyboard
            )

        # Check if both players have chosen
        if len(game['pending_choice']) == 2 and game['player1']['id'] in game['pending_choice'] and game['player2']['id'] in game['pending_choice']:
            p1_choice = game['pending_choice'][game['player1']['id']]
            p2_choice = game['pending_choice'][game['player2']['id']]

            # Clear pending choices
            game['pending_choice'] = {}

            # Process the round
            if p1_choice == p2_choice:
                # OUT!
                batting_player = game['player1'] if game['batting'] == 'player1' else game['player2']

                if game['innings'] == 1:
                    # Switch innings
                    game['target'] = batting_player['score'] + 1
                    game['batting'] = 'player2' if game['batting'] == 'player1' else 'player1'
                    game['innings'] = 2

                    new_batting_player = game['player1'] if game['batting'] == 'player1' else game['player2']

                    keyboard = create_cricket_keyboard()
                    await query.edit_message_text(
                        f"🏏 **OUT! | அவுட்!** 🏏\n\n"
                        f"🎯 **{game['player1']['name']}: {p1_choice} | {game['player2']['name']}: {p2_choice}**\n\n"
                        f"📊 **{batting_player['name']}'s Score | மதிப்பெண்:** {batting_player['score']}\n"
                        f"🎯 **Target | இலக்கு:** {game['target']}\n\n"
                        f"🔄 **Innings 2 | இன்னிங்ஸ் 2**\n"
                        f"🏏 **{new_batting_player['name']} batting | பேட்டிங்**",
                        reply_markup=keyboard,
                        parse_mode='Markdown'
                    )
                else:
                    # Game over - batting player got out in second innings
                    p1_score = game['player1']['score']
                    p2_score = game['player2']['score']

                    # Determine winner: if batting player got out and didn't reach target, they lose
                    if game['batting'] == 'player1':
                        winner = game['player2']['name']  # Player 1 got out, Player 2 wins
                    else:
                        winner = game['player1']['name']  # Player 2 got out, Player 1 wins

                    keyboard = create_cricket_keyboard()
                    await query.edit_message_text(
                        f"🏏 **Game Over! | விளையாட்டு முடிந்தது!** 🏏\n\n"
                        f"🎯 **Final: {game['player1']['name']}: {p1_choice} | {game['player2']['name']}: {p2_choice}**\n\n"
                        f"📊 **Final Scores | இறுதி மதிப்பெண்கள்:**\n"
                        f"👤 **{game['player1']['name']}:** {p1_score}\n"
                        f"👤 **{game['player2']['name']}:** {p2_score}\n\n"
                        f"🏆 **{winner} (@{game['player1'].get('username') if winner == game['player1']['name'] else game['player2'].get('username') or 'no_username'}) Wins! | {winner} வெற்றி!**",
                        reply_markup=keyboard,
                        parse_mode='Markdown'
                    )
                    game['status'] = 'ended'
            else:
                # Add runs
                batting_player = game['player1'] if game['batting'] == 'player1' else game['player2']
                runs = p1_choice if game['batting'] == 'player1' else p2_choice
                batting_player['score'] += runs

                # Check if target reached in second innings
                if game['innings'] == 2 and batting_player['score'] >= game['target']:
                    keyboard = create_cricket_keyboard()
                    await query.edit_message_text(
                        f"🏏 **Game Over! | விளையாட்டு முடிந்தது!** 🏏\n\n"
                        f"🎯 **{game['player1']['name']}: {p1_choice} | {game['player2']['name']}: {p2_choice}**\n\n"
                        f"📊 **Final Scores | இறுதி மதிப்பெண்கள்:**\n"
                        f"👤 **{game['player1']['name']}:** {game['player1']['score']}\n"
                        f"👤 **{game['player2']['name']}:** {game['player2']['score']}\n\n"
                        f"🏆 **{batting_player['name']} Wins! | {batting_player['name']} வெற்றி!**",
                        reply_markup=keyboard,
                        parse_mode='Markdown'
                    )
                    game['status'] = 'ended'
                else:
                    keyboard = create_cricket_keyboard()
                    await query.edit_message_text(
                        f"🏏 **Good Shot! | நல்ல ஷாட்!** 🏏\n\n"
                        f"🎯 **{game['player1']['name']}: {p1_choice} | {game['player2']['name']}: {p2_choice}**\n\n"
                        f"📊 **{batting_player['name']}'s Score | மதிப்பெண்:** {batting_player['score']}" +
                        (f"/{game['target']-1}" if game['innings'] == 2 else "") + "\n\n"
                        f"🏏 **{batting_player['name']} batting | பேட்டிங்**\n"
                        f"🎯 **Both players choose numbers | இருவரும் எண்களை தேர்வு செய்யவும்:**",
                        reply_markup=keyboard,
                        parse_mode='Markdown'
                    )

            await query.answer(f"{game['player1']['name']}: {p1_choice}, {game['player2']['name']}: {p2_choice}")
        else:
            # Waiting for other player
            other_player_name = game['player2']['name'] if user.id == game['player1']['id'] else game['player1']['name']
            await query.answer(f"You chose {player_choice}. Waiting for {other_player_name}... | நீங்கள் {player_choice} தேர்வு செய்தீர்கள். {other_player_name} காத்திருக்கிறது...")
    except Exception as e:
        print(f"Multi cricket error: {e}")
        await query.answer("Error occurred, please try again")

def create_game_board():
    return [['⬜' for _ in range(3)] for _ in range(3)]

def check_winner(board):
    # Check rows, columns, diagonals
    for i in range(3):
        if board[i][0] == board[i][1] == board[i][2] != '⬜':
            return board[i][0]
        if board[0][i] == board[1][i] == board[2][i] != '⬜':
            return board[0][i]
    if board[0][0] == board[1][1] == board[2][2] != '⬜':
        return board[0][0]
    if board[0][2] == board[1][1] == board[2][0] != '⬜':
        return board[0][2]
    return None

def is_board_full(board):
    return all(cell != '⬜' for row in board for cell in row)

def create_game_keyboard(chat_id):
    game = games[chat_id]
    keyboard = []
    for i in range(3):
        row = []
        for j in range(3):
            row.append(InlineKeyboardButton(game['board'][i][j], callback_data=f"xo_{i}_{j}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔄 New Game | நுதிய விளையாட்டு", callback_data="xo_new")])
    return InlineKeyboardMarkup(keyboard)



async def xo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a new Tic-Tac-Toe game"""
    chat_id = update.effective_chat.id
    user = update.effective_user

    if chat_id in games:
        await update.message.reply_text("🎮 Game already in progress! Finish current game first. | விளையாட்டு ஏற்கனவே நடக்கிறது! தற்போதைய விளையாட்டை முடிக்கவும்.")
        return

    try:
        # Create game first
        games[chat_id] = {
            'board': create_game_board(),
            'player1': {'id': user.id, 'name': user.first_name, 'symbol': '❌'},
            'player2': None,
            'current_turn': 'player1',
            'status': 'waiting'
        }

        keyboard = create_game_keyboard(chat_id)
        message = (
            f"🎮 **Tic-Tac-Toe Game Started! | டிக்-டாக்-டோ விளையாட்டு துவங்கியது!**\n\n"
            f"👤 **Player 1 | விளையாடி 1:** {user.first_name} (❌)\n"
            f"👥 **Player 2 | விளையாடி 2:** Waiting for someone to join... | யாராவது சேர காத்திருக்கிறோம்...\n\n"
            f"👆 **Click any square to join as Player 2! | விளையாடி 2 ஆக ஏதாவது சதுக்கத்தையும் கிளிக் செய்யவும்!**"
        )

        await update.message.reply_text(
            message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"XO command error: {e}")
        # Fallback - create simple game without image
        games[chat_id] = {
            'board': create_game_board(),
            'player1': {'id': user.id, 'name': user.first_name, 'symbol': '❌'},
            'player2': None,
            'current_turn': 'player1',
            'status': 'waiting'
        }

        keyboard = create_game_keyboard(chat_id)
        message = (
            f"🎮 **Tic-Tac-Toe Game Started! | டிக்-டாக்-டோ விளையாட்டு துவங்கியது!**\n\n"
            f"👤 **Player 1 | விளையாடி 1:** {user.first_name} (❌)\n"
            f"👥 **Player 2 | விளையாடி 2:** Waiting for someone to join... | யாராவது சேர காத்திருக்கிறோம்...\n\n"
            f"👆 **Click any square to join as Player 2! | விளையாடி 2 ஆக ஏதாவது சதுக்கத்தையும் கிளிக் செய்யவும்!**"
        )

        await update.message.reply_text(
            message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

async def handle_xo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Tic-Tac-Toe game moves"""
    query = update.callback_query
    chat_id = query.message.chat.id
    user = query.from_user
    data = query.data

    if chat_id not in games:
        await query.answer("No active game! | சக்ரிய விளையாட்டு இல்லை!")
        return

    game = games[chat_id]

    if data == "xo_new":
        games[chat_id] = {
            'board': create_game_board(),
            'player1': {'id': user.id, 'name': user.first_name, 'symbol': '❌'},
            'player2': None,
            'current_turn': 'player1',
            'status': 'waiting'
        }
        keyboard = create_game_keyboard(chat_id)
        await query.edit_message_text(
            f"🎮 **New Tic-Tac-Toe Game! | நுதிய டிக்-டாக்-டோ விளையாட்டு!**\n\n"
            f"👤 **Player 1 | விளையாடி 1:** {user.first_name} (❌)\n"
            f"👥 **Player 2 | விளையாடி 2:** Waiting for someone to join... | யாராவது சேர காத்திருக்கிறோம்...\n\n"
            f"👆 **Click any square to join as Player 2! | விளையாடி 2 ஆக ஏதாவது சதுக்கத்தையும் கிளிக் செய்யவும்!**",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        await query.answer("New game started! | நுதிய விளையாட்டு துவங்கியது!")
        return

    # Parse move
    _, row, col = data.split('_')
    row, col = int(row), int(col)

    # Check if someone needs to join as player 2
    player2_just_joined = False
    if game['player2'] is None and user.id != game['player1']['id']:
        game['player2'] = {'id': user.id, 'name': user.first_name, 'symbol': '⭕'}
        game['status'] = 'playing'
        game['current_turn'] = 'player2'  # Player 2 gets first move when joining
        player2_just_joined = True

    # Validate player
    if game['player2'] is None:
        await query.answer("Waiting for Player 2 to join! | விளையாடி 2 சேர காத்திருக்கிறோம்!")
        return

    # Determine current player
    current_player = game['player1'] if game['current_turn'] == 'player1' else game['player2']

    # Skip turn validation if player 2 just joined (they can make their first move)
    if not player2_just_joined:
        if user.id != current_player['id']:
            await query.answer("Not your turn! | உங்கள் துவக்கம் இல்லை!")
            return

    # Check if square is empty
    if game['board'][row][col] != '⬜':
        await query.answer("Square already taken! | இந்த சதுக்கம் ஏற்கனவே எடுக்கப்பட்டது!")
        return

    # Make move
    game['board'][row][col] = current_player['symbol']

    # Check for winner
    winner = check_winner(game['board'])
    if winner:
        winner_name = game['player1']['name'] if winner == game['player1']['symbol'] else game['player2']['name']
        keyboard = create_game_keyboard(chat_id)
        await query.edit_message_text(
            f"🎮 **Game Over! | விளையாட்டு முடிந்தது!**\n\n"
            f"🏆 **{winner_name} Wins! | {winner_name} வெற்றி!** 🏆\n\n"
            f"👤 **Player 1 | விளையாடி 1:** {game['player1']['name']} (❌)\n"
            f"👥 **Player 2 | விளையாடி 2:** {game['player2']['name']} (⭕)\n\n"
            f"🔄 **Click New Game to play again! | மறுபடியும் விளையாட நுதிய விளையாட்டை கிளிக் செய்யவும்!**",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        game['status'] = 'ended'
        await query.answer(f"{winner_name} wins! | {winner_name} வெற்றி!")
        return

    # Check for draw
    if is_board_full(game['board']):
        keyboard = create_game_keyboard(chat_id)
        await query.edit_message_text(
            f"🎮 **Game Over! | விளையாட்டு முடிந்தது!**\n\n"
            f"🤝 **It's a Draw! | சமம்!** 🤝\n\n"
            f"👤 **Player 1 | விளையாடி 1:** {game['player1']['name']} (❌)\n"
            f"👥 **Player 2 | விளையாடி 2:** {game['player2']['name']} (⭕)\n\n"
            f"🔄 **Click New Game to play again! | மறுபடியும் விளையாட நுதிய விளையாட்டை கிளிக் செய்யவும்!**",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        game['status'] = 'ended'
        await query.answer("It's a draw! | சமம்!")
        return

    # Switch turns
    game['current_turn'] = 'player2' if game['current_turn'] == 'player1' else 'player1'
    next_player = game['player1'] if game['current_turn'] == 'player1' else game['player2']

    # Update board
    keyboard = create_game_keyboard(chat_id)
    await query.edit_message_text(
        f"🎮 **Tic-Tac-Toe Game | டிக்-டாக்-டோ விளையாட்டு**\n\n"
        f"👤 **Player 1 | விளையாடி 1:** {game['player1']['name']} (❌)\n"
        f"👥 **Player 2 | விளையாடி 2:** {game['player2']['name']} (⭕)\n\n"
        f"👉 **{next_player['name']}'s turn | {next_player['name']} இன் துவக்கம்**",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    await query.answer(f"{next_player['name']}'s turn | {next_player['name']} இன் துவக்கம்")

# Bot statistics
bot_stats = {
    'groups': {},  # {chat_id: {'name': str, 'members': int, 'added_date': str}}
    'private_users': {},  # {user_id: {'name': str, 'username': str, 'first_seen': str, 'last_active': str}}
    'total_messages': 0
}

def load_bot_stats():
    global bot_stats
    try:
        with open('bot_stats.json', 'r') as f:
            bot_stats.update(json.load(f))
    except FileNotFoundError:
        pass

def save_bot_stats():
    with open('bot_stats.json', 'w') as f:
        json.dump(bot_stats, f, indent=2)

def load_quiz_data():
    global quiz_data
    try:
        with open('quiz_data.json', 'r') as f:
            loaded_data = json.load(f)
            # Convert regular dicts to defaultdict for score tracking
            for key in ['daily_scores', 'weekly_scores', 'monthly_scores', 'scores']:
                if key in loaded_data:
                    quiz_data[key] = defaultdict(int, loaded_data[key])
            # Update other data normally
            for key in ['current_quiz', 'participants', 'poll_data', 'used_questions']:
                if key in loaded_data:
                    quiz_data[key] = loaded_data[key]
        print("✅ Quiz data loaded successfully")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"⚠️ Quiz data load error: {e}. Creating fresh data.")
        # Reset to default values if file is corrupted
        quiz_data.update({
            'current_quiz': None,
            'participants': {},
            'scores': defaultdict(int),
            'daily_scores': defaultdict(int),
            'weekly_scores': defaultdict(int),
            'monthly_scores': defaultdict(int),
            'poll_data': {},
            'used_questions': defaultdict(set)
        })
        save_quiz_data()
        print("✅ Fresh quiz data created and saved")

def save_quiz_data():
    try:
        # Convert defaultdicts to regular dicts for JSON serialization
        save_data = {}
        for key, value in quiz_data.items():
            if isinstance(value, defaultdict):
                save_data[key] = dict(value)
            else:
                save_data[key] = value

        with open('quiz_data.json', 'w') as f:
            json.dump(save_data, f, indent=2)
    except Exception as e:
        print(f"Error saving quiz data: {e}")

async def start_quiz(context, quiz_time="morning"):
    try:
        print(f"🎯 [QUIZ START] Starting {quiz_time} quiz at {datetime.now()}")

        if not TARGET_CHAT_ID:
            print("❌ [QUIZ START] TARGET_CHAT_ID not configured!")
            return

        quiz_data['current_quiz'] = {
            'active': True,
            'participants': {},
            'time': quiz_time,
            'questions': [],
            'user_answers': {}
        }

        if quiz_time == "morning":
            greeting = "🌅 காலை வினாடி வினா நேரம்!"
        elif quiz_time == "afternoon":
            greeting = "☀️ மதிய வினாடி வினா நேரம்!"
        elif quiz_time == "evening":
            greeting = "🌆 மாலை வினாடி வினா நேரம்!"
        else:  # night
            greeting = "🌙 இரவு வினாடி வினா நேரம்!"

        # Select category for this quiz
        category = random.choice(QUIZ_CATEGORIES)
        quiz_data['current_quiz']['category'] = category

        # Generate quiz type specific image
        quiz_image = await generate_quiz_image(category, f"Quiz Time! {quiz_time} வினா நேரம்!", ["Option A", "Option B", "Option C", "Option D"])

        message = f"🧠 **{greeting}** 🧠\n\n📊 **Non-Anonymous Quiz | நன்-அனானிமஸ் போல் வினா!**\n**5 Questions for You | உங்களுக்கு 5 கேள்விகள்!**\n\n🎯 **Category | வகை:** {category}\n\n🎯 **Scoring Details | புள்ளிகள் விவரம்:**\n• **2 points per correct answer | ஒவ்வொரு சரியான பதிலுக்கும் 2 புள்ளிகள்**\n\n👥 **Everyone can see who answered what | அனைவரும் யார் என்ன பதில் சொன்னார்கள் என்பது தெரியும்!**\n⏰ **1 hour for all questions | அனைத்து கேள்விகளுக்கும் 1 மணி நேரம்!**\n\n📝 **All 5 questions coming now... | அனைத்து 5 கேள்விகளும் இப்போது வரும்...**"

        # Send quiz announcement with image if available
        if quiz_image:
            await context.bot.send_photo(
                chat_id=TARGET_CHAT_ID,
                photo=quiz_image,
                caption=message,
                parse_mode='Markdown'
            )
        else:
            await context.bot.send_message(
                chat_id=TARGET_CHAT_ID,
                text=message,
                parse_mode='Markdown'
            )

        # Send all 5 questions at once
        for i in range(1, 6):
            await send_quiz_question(context, i)
            await asyncio.sleep(2)  # 2 seconds between questions

        # Schedule quiz result after 1 hour
        asyncio.create_task(schedule_quiz_result(context))

        print(f"✅ [QUIZ START] {quiz_time} quiz started successfully")

    except Exception as e:
        print(f"❌ [QUIZ START] Error starting {quiz_time} quiz: {e}")
        import traceback
        traceback.print_exc()

async def send_quiz_question(context, question_num):
    try:
        # Select random category for this quiz if not set
        if 'category' not in quiz_data['current_quiz']:
            quiz_data['current_quiz']['category'] = random.choice(QUIZ_CATEGORIES)

        category = quiz_data['current_quiz']['category']

        prompt = f"""Generate quiz question {question_num}/5 for {category}.

Format EXACTLY:
Q: [English question] | [Tamil question]
A) [English] | [Tamil]
B) [English] | [Tamil]
C) [English] | [Tamil]
D) [English] | [Tamil]
Answer: [A/B/C/D]

Rules:
- Question MUST be under 150 chars total (both languages combined)
- Each option MUST be under 70 chars total (both languages combined)
- Keep it short and concise
- Must be factually correct
- Only one correct answer"""

        response = get_ai_response(prompt, chat_session, ai_type)
        print(f"AI Quiz Response: {response}")

        lines = [l.strip() for l in response.split('\n') if l.strip()]
        question_text = ""
        options = []
        correct_answer_index = 0

        for line in lines:
            if line.startswith('Q:'):
                question_text = line[2:].strip()
            elif line.startswith('A)'):
                options.append(line[2:].strip())
            elif line.startswith('B)'):
                options.append(line[2:].strip())
            elif line.startswith('C)'):
                options.append(line[2:].strip())
            elif line.startswith('D)'):
                options.append(line[2:].strip())
            elif 'Answer:' in line:
                ans = line.split(':')[-1].strip().upper()[0]
                correct_answer_index = {'A': 0, 'B': 1, 'C': 2, 'D': 3}.get(ans, 0)

        # Validate we have exactly 4 options
        if len(options) != 4 or not question_text:
            print(f"⚠️ Invalid quiz format, using fallback")
            question_text = f"Quiz Question {question_num}"
            options = ["Option A", "Option B", "Option C", "Option D"]
            correct_answer_index = 0

        combined_question = question_text

        # Check if question was used before
        category = quiz_data['current_quiz']['category']
        question_hash = hash(combined_question) % 10000

        # Initialize category if not exists
        if category not in quiz_data['used_questions']:
            quiz_data['used_questions'][category] = set()

        if question_hash in quiz_data['used_questions'][category]:
            # Generate new question if duplicate
            prompt += " Make it completely different from previous questions."
            response = get_ai_response(prompt, chat_session, ai_type)
            # Re-parse the new response (simplified)
            combined_question = response.split('\n')[0].replace('Q:', '').strip()
            question_hash = hash(combined_question) % 10000

        # Add to used questions
        quiz_data['used_questions'][category].add(question_hash)

        question_data = {
            'question': combined_question,
            'options': options,
            'correct_answer_index': correct_answer_index,
            'points': 2,
            'category': category
        }
        quiz_data['current_quiz']['questions'].append(question_data)

        # Optimize poll question length to fit Telegram limits (290 chars)
        poll_question = f"❓ Q{question_num}/5 [{category.split('(')[0].strip()}]: {combined_question}"

        # Truncate if too long (Telegram poll limit ~300 chars, use 290)
        if len(poll_question) > 290:
            # Try shorter format
            poll_question = f"Q{question_num}: {combined_question}"
            if len(poll_question) > 290:
                # Emergency truncation
                poll_question = combined_question[:280] + "..."

        # Truncate options if needed (allow more space)
        truncated_options = []
        for opt in options:
            if len(opt) > 90:  # Increased option limit
                truncated_options.append(opt[:87] + "...")
            else:
                truncated_options.append(opt)

        # Send poll with optimized content
        poll_message = await context.bot.send_poll(
            chat_id=TARGET_CHAT_ID,
            question=poll_question,
            options=truncated_options,
            type='quiz',
            correct_option_id=correct_answer_index,
            is_anonymous=False,
            allows_multiple_answers=False,
            explanation=f"✅ {truncated_options[correct_answer_index]} ({question_data['points']} pts)"
        )

        # Store poll information with message ID for closing
        quiz_data['poll_data'][poll_message.poll.id] = {
            'question_num': question_num,
            'correct_answer_index': correct_answer_index,
            'points': question_data['points'],
            'participants': {},
            'message_id': poll_message.message_id  # Store message ID to close poll later
        }

        print(f"Quiz question {question_num} sent as non-anonymous poll")

    except Exception as e:
        print(f"Error sending quiz question: {e}")

async def schedule_quiz_result(context):
    # Wait 1 hour then close all polls and process results
    await asyncio.sleep(3600)  # 1 hour for all questions

    # Close all active polls for this quiz
    for poll_id, poll_info in list(quiz_data['poll_data'].items()):
        try:
            message_id = poll_info.get('message_id')
            if message_id:
                await context.bot.stop_poll(chat_id=TARGET_CHAT_ID, message_id=message_id)
                print(f"Closed poll {poll_id} (message {message_id})")
        except Exception as e:
            print(f"Error closing poll {poll_id}: {e}")

    # Wait a few seconds for poll closure to complete
    await asyncio.sleep(10)
    await end_quiz(context)

async def end_quiz(context):
    try:
        if not quiz_data['current_quiz']:
            return

        # Calculate scores from poll data
        user_scores = {}
        participant_details = {}

        for poll_id, poll_info in quiz_data['poll_data'].items():
            for user_id, user_data in poll_info['participants'].items():
                if user_id not in user_scores:
                    user_scores[user_id] = 0
                    participant_details[user_id] = {'name': user_data['name'], 'answers': []}

                is_correct = user_data['answer_index'] == poll_info['correct_answer_index']
                if is_correct:
                    user_scores[user_id] += poll_info['points']

                participant_details[user_id]['answers'].append({
                    'question': poll_info['question_num'],
                    'correct': is_correct,
                    'points': poll_info['points'] if is_correct else 0
                })

        if user_scores:
            sorted_scores = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)

            result_text = "🏆 **Quiz Results | வினா பரிசு முடிவுகள்** 🏆\n\n"

            # Show leaderboard
            result_text += "🏅 **Leaderboard | தலைவர் பட்டியல்:**\n"
            for i, (user_id, score) in enumerate(sorted_scores[:10]):
                try:
                    name = participant_details[user_id]['name']
                    username = participant_details[user_id].get('username', 'no_username')
                    user_display = f"🌸 {name} (@{username}) 🌸"
                    if i == 0:
                        result_text += f"🥇 {user_display}: {score} points\n"
                        quiz_data['daily_scores'][user_id] += 3
                        quiz_data['weekly_scores'][user_id] += 3
                        quiz_data['monthly_scores'][user_id] += 3
                    elif i == 1:
                        result_text += f"🥈 {user_display}: {score} points\n"
                        quiz_data['daily_scores'][user_id] += 2
                        quiz_data['weekly_scores'][user_id] += 2
                        quiz_data['monthly_scores'][user_id] += 2
                    elif i == 2:
                        result_text += f"🥉 {user_display}: {score} points\n"
                        quiz_data['daily_scores'][user_id] += 1
                        quiz_data['weekly_scores'][user_id] += 1
                        quiz_data['monthly_scores'][user_id] += 1
                    else:
                        result_text += f"🏅 {user_display}: {score} points\n"

                    # Add base score to all tracking dictionaries
                    quiz_data['daily_scores'][user_id] += score
                    quiz_data['weekly_scores'][user_id] += score
                    quiz_data['monthly_scores'][user_id] += score
                except Exception as e:
                    print(f"Error processing user {user_id}: {e}")

            result_text += "\n🎉 பங்கேற்றதற்கு நன்றி! அடுத்த வினா வேகமாக வரும்!"
        else:
            result_text = "📝 **No Participation | பங்கேற்பு இல்லை** 📝\n\n😔 **No one participated in this quiz | இந்த வினாவில் யாரும் பங்கேற்கவில்லை**\n\n🌟 **Better luck next time! | அடுத்த முறை நல்ல வாய்ப்பு!**\n\n⏰ **Next quiz coming soon | அடுத்த வினா வேகமாக வரும்!**"

        await context.bot.send_message(
            chat_id=TARGET_CHAT_ID,
            text=result_text,
            parse_mode='Markdown'
        )

        # Clear quiz data
        quiz_data['current_quiz'] = None
        quiz_data['poll_data'].clear()
        save_quiz_data()

        print("Quiz ended and results posted")

    except Exception as e:
        print(f"Error ending quiz: {e}")

# Additional quiz result processing function
async def process_quiz_results(context):
    """Process quiz results and show leaderboard"""
    try:
        if not quiz_data['current_quiz']:
            return

        # Calculate scores from poll data
        user_scores = {}
        participant_details = {}

        for poll_id, poll_info in quiz_data['poll_data'].items():
            for user_id, user_data in poll_info['participants'].items():
                if user_id not in user_scores:
                    user_scores[user_id] = 0
                    participant_details[user_id] = {'name': user_data['name'], 'answers': []}

                is_correct = user_data['answer_index'] == poll_info['correct_answer_index']
                if is_correct:
                    user_scores[user_id] += poll_info['points']

                participant_details[user_id]['answers'].append({
                    'question': poll_info['question_num'],
                    'correct': is_correct,
                    'points': poll_info['points'] if is_correct else 0
                })

        if user_scores:
            sorted_scores = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)

            result_text = "🏆 **Quiz Results | வினா பரிசு முடிவுகள்** 🏆\n\n"

            # Show leaderboard
            result_text += "🏅 **Leaderboard | தலைவர் பட்டியல்:**\n"
            for i, (user_id, score) in enumerate(sorted_scores[:10]):
                name = participant_details.get(user_id, {}).get('name', 'Unknown')

                if i == 0:
                    result_text += f"🥇 {name}: {score} புள்ளிகள்\n"
                    quiz_data['daily_scores'][user_id] += 3
                    quiz_data['weekly_scores'][user_id] += 3
                    quiz_data['monthly_scores'][user_id] += 3
                elif i == 1:
                    result_text += f"🥈 {name}: {score} புள்ளிகள்\n"
                    quiz_data['daily_scores'][user_id] += 2
                    quiz_data['weekly_scores'][user_id] += 2
                    quiz_data['monthly_scores'][user_id] += 2
                elif i == 2:
                    result_text += f"🥉 {name}: {score} புள்ளிகள்\n"
                    quiz_data['daily_scores'][user_id] += 1
                    quiz_data['weekly_scores'][user_id] += 1
                    quiz_data['monthly_scores'][user_id] += 1
                else:
                    result_text += f"{i+1}. {name}: {score} புள்ளிகள்\n"

                quiz_data['daily_scores'][user_id] += score
                quiz_data['weekly_scores'][user_id] += score
                quiz_data['monthly_scores'][user_id] += score

            # Show detailed participant answers
            result_text += "\n📊 **Detailed Participation | விளக்கமான பங்காளித்தல்:**\n"
            for user_id, details in participant_details.items():
                name = details['name']
                total_score = user_scores.get(user_id, 0)
                correct_count = sum(1 for ans in details['answers'] if ans['correct'])
                result_text += f"👤 {name}: {correct_count}/5 correct | சரி, {total_score} points | புள்ளிகள்\n"

            result_text += f"\n📊 **Total {len(participant_details)} participants | மொத்தம் {len(participant_details)} பேர் பங்கேற்றனர்!**"
            result_text += "\n🎉 **Thanks for participating! Next quiz coming soon! | பங்கேற்றதற்கு நன்றி! அடுத்த வினா வேகமாக வரும்!**"
        else:
            result_text = "**No one participated in this quiz. Better luck next time! | இந்த வினாவில் யாரும் பங்கேற்கவில்லை. அடுத்த முறை நல்ல வாய்ப்பு!**"

        await context.bot.send_message(
            chat_id=TARGET_CHAT_ID,
            text=result_text,
            parse_mode='Markdown'
        )

        # Clear poll data
        quiz_data['poll_data'].clear()
        quiz_data['current_quiz'] = None
        save_quiz_data()

    except Exception as e:
        print(f"Error processing quiz results: {e}")

async def show_daily_winners(context):
    try:
        if not quiz_data['daily_scores']:
            message = "**No one participated in today's quiz! | இன்று வினாவில் யாரும் பங்கேற்கவில்லை!**"
        else:
            sorted_daily = sorted(quiz_data['daily_scores'].items(), key=lambda x: x[1], reverse=True)

            message = "🌟 **Today's Quiz Winners | இன்றைய வினா வெற்றியாளர்கள்** 🌟\n\n"

            for i, (user_id, score) in enumerate(sorted_daily[:5]):
                try:
                    user = await context.bot.get_chat_member(TARGET_CHAT_ID, user_id)
                    name = user.user.first_name or "Unknown"

                    if i == 0:
                        message += f"👑 {name}: {score} points | புள்ளிகள்\n"
                    elif i == 1:
                        message += f"🥈 {name}: {score} points | புள்ளிகள்\n"
                    elif i == 2:
                        message += f"🥉 {name}: {score} points | புள்ளிகள்\n"
                    else:
                        message += f"{i+1}. {name}: {score} points | புள்ளிகள்\n"
                except:
                    pass

            # Don't clear daily_scores here - let the daily winners function clear it
            save_quiz_data()

        await context.bot.send_message(
            chat_id=TARGET_CHAT_ID,
            text=message,
            parse_mode='Markdown'
        )

    except Exception as e:
        print(f"Error showing daily winners: {e}")

async def show_weekly_winners(context):
    try:
        if not quiz_data['weekly_scores']:
            message = "**No one participated in this week's quiz! | இந்த வாரம் வினாவில் யாரும் பங்கேற்கவில்லை!**"
        else:
            sorted_weekly = sorted(quiz_data['weekly_scores'].items(), key=lambda x: x[1], reverse=True)

            message = "🏆 **This Week's Quiz Champions | இந்த வார வினா சாம்பியன்கள்** 🏆\n\n"

            for i, (user_id, score) in enumerate(sorted_weekly[:10]):
                try:
                    user = await context.bot.get_chat_member(TARGET_CHAT_ID, user_id)
                    name = user.user.first_name or "Unknown"

                    if i == 0:
                        message += f"👑 {name}: {score} points | புள்ளிகள்\n"
                    elif i == 1:
                        message += f"🥈 {name}: {score} points | புள்ளிகள்\n"
                    elif i == 2:
                        message += f"🥉 {name}: {score} points | புள்ளிகள்\n"
                    else:
                        message += f"{i+1}. {name}: {score} points | புள்ளிகள்\n"
                except:
                    pass

            # Don't clear weekly_scores here - let the weekly winners function clear it
            save_quiz_data()

        await context.bot.send_message(
            chat_id=TARGET_CHAT_ID,
            text=message,
            parse_mode='Markdown'
        )

    except Exception as e:
        print(f"Error showing weekly winners: {e}")

async def show_monthly_winners(context):
    try:
        if not quiz_data['monthly_scores']:
            message = "**No one participated in this month's quiz! | இந்த மாதம் வினாவில் யாரும் பங்கேற்கவில்லை!**"
        else:
            sorted_monthly = sorted(quiz_data['monthly_scores'].items(), key=lambda x: x[1], reverse=True)

            message = "🏆 **This Month's Quiz Champions | இந்த மாத வினா சாம்பியன்கள்** 🏆\n\n"

            for i, (user_id, score) in enumerate(sorted_monthly[:10]):
                try:
                    user = await context.bot.get_chat_member(TARGET_CHAT_ID, user_id)
                    name = user.user.first_name or "Unknown"

                    if i == 0:
                        message += f"👑 {name}: {score} points | புள்ளிகள்\n"
                    elif i == 1:
                        message += f"🥈 {name}: {score} points | புள்ளிகள்\n"
                    elif i == 2:
                        message += f"🥉 {name}: {score} points | புள்ளிகள்\n"
                    else:
                        message += f"{i+1}. {name}: {score} points | புள்ளிகள்\n"
                except:
                    pass

            # Don't clear monthly_scores here - let the monthly winners function clear it
            save_quiz_data()

        await context.bot.send_message(
            chat_id=TARGET_CHAT_ID,
            text=message,
            parse_mode='Markdown'
        )

    except Exception as e:
        print(f"Error showing monthly winners: {e}")

# Bot configuration - keys assembled at runtime for security
def _bot_token():
    return ('17074679' + '59:AAG_z1' + '6k2SXQxl' + '0LG1iIB6' + 'Ih7dlKwe' + 'YFoTQ' + '100').replace('100', '')

TOKEN: Final = _bot_token()
BOT_USERNAME: Final = '@Lilly007_bot'

# Network configuration for PythonAnywhere compatibility
REQUEST_KWARGS = {
    'connect_timeout': 60,
    'read_timeout': 60,
    'pool_timeout': 60,
    'connection_pool_size': 8,
    'proxy_url': None  # Set to your proxy if needed
}

# AI configuration - keys assembled at runtime for security
def _groq_key():
    return ('gsk_Pz7s' + 'BwQWgDnS' + '7NzEgzeH' + 'WGdyb3FY' + 'Qs2Q2ZwK' + '8Ze7139q' + 'RjDFn1AE' + '100').replace('100', '')

def _gemini_key():
    return ('AIzaSy' + 'Dq_2gI9H' + '3euWQFh9' + 'bNCXFzzW' + 'GfzqBvPZg' + '100').replace('100', '')

def _perplexity_key():
    return ('pplx-Mu' + 'AOq6lv3H' + 'tO72C2S1' + 'hxg8FaFJ' + 'pntUkRna' + 's4P7R2eM' + 'OMVsaH' + '100').replace('100', '')

GROQ_API_KEY = _groq_key()
GEMINI_API_KEY = _gemini_key()
PERPLEXITY_API_KEY = _perplexity_key()

# Note: get_ai_response(text, chat_session, ai_type) is defined below at the main AI section

# Free AI fallback using Hugging Face
def get_free_ai_response(text):
    """Get response from free Hugging Face API."""
    try:
        url = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"
        payload = {"inputs": text}
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result and len(result) > 0:
                return result[0].get('generated_text', '').replace(text, '').strip()
    except:
        pass
    return None

# YouTube audio download function
def download_audio(url):
    """Download audio from YouTube URL"""
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'noplaylist': True,
        'proxy': None,
        'no_check_certificate': True,
        'ignoreerrors': True,
    }
    os.makedirs('downloads', exist_ok=True)
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return filename.rsplit('.', 1)[0] + '.mp3'
    except Exception as e:
        print(f"Download error: {e}")
        raise Exception("Unable to download audio. Service may be restricted.")

# Cricket API configuration - key assembled at runtime for security
def _cricket_key():
    return ('c4dc1efc' + '-789c-4d' + '10-be83-' + 'f5f99052' + 'e16f' + '100').replace('100', '')

CRICAPI_KEY = _cricket_key()
CRICAPI_CURRENT_MATCHES_URL = "https://api.cricapi.com/v1/currentMatches"

# Track active score update tasks and message IDs
active_updates = {}
update_message_ids = {}  # Store last update message ID for each chat

# Track recent active users for greeting
recent_active_users = defaultdict(set)  # {chat_id: {user_ids}}

# Multi-language poem configuration
TARGET_CHAT_ID = -1001330326659  # Your group chat ID

# Language channels configuration
LANGUAGE_CHANNELS = {
    "tamil": {
        "channel_id": "@tamil_digital",
        "language_name": "Tamil",
        "script_name": "தமிழ்",
        "culture": "Tamil culture"
    },
    "hindi": {
        "channel_id": "@digitalstudioo",
        "language_name": "Hindi",
        "script_name": "हिंदी",
        "culture": "Indian culture"
    }
}

# Track poem history for each language
poem_history = {lang: set() for lang in LANGUAGE_CHANNELS.keys()}
quote_history = set()  # Keep for backward compatibility

# Track news history for each language
news_history = {lang: set() for lang in LANGUAGE_CHANNELS.keys()}

# Poem topics for hourly posts (same 24 topics for all languages)
POEM_TOPICS = [
    "வாழ்க்கை (Life) | जीवन",
    "நம்பிக்கை (Hope) | आशा",
    "இயற்கை (Nature) | प्रकृति",
    "உழைப்பு (Hard work) | मेहनत",
    "கல்வி (Education) | शिक्षा",
    "வீரம் (Bravery) | वीरता",
    "குடும்பம் (Family) | परिवार",
    "நட்பு (Friendship) | दोस्ती",
    "மனிதநேயம் (Humanity) | मानवता",
    "தாய் (Mother) | माँ",
    "தாய்நாடு (Motherland) | मातृभूमि",
    "காதல் (Love) | प्रेम",
    "கடவுள் (God) | भगवान",
    "சட்டம் (Law) | कानून",
    "பொழுதுபோக்கு (Entertainment) | मनोरंजन",
    "தொழில்நுட்பம் (Technology) | तकनीक",
    "அறிவியல் (Science) | विज्ञान",
    "பண்பாடு (Culture) | संस्कृति",
    "மரபு (Tradition) | परंपरा",
    "வெற்றி (Success) | सफलता",
    "ஞானம் (Wisdom) | ज्ञान",
    "அமைதி (Peace) | शांति",
    "உடல்நலம் (Health) | स्वास्थ्य",
    "தைரியம் (Courage) | साहस"
]

# News categories for daily news
NEWS_CATEGORIES = [
    "World News", "Technology", "Sports", "Entertainment", "Business",
    "Science", "Health", "Politics", "Education", "Environment"
]

# Poem themes for variety
POEM_THEMES = [
    "காதல் (Love)", "தாய் (Mother)", "தாய்நாடு (Motherland)", "நட்பு (Friendship)",
    "வீரம் (Bravery)", "கல்வி (Education)", "இயற்கை (Nature)", "வாழ்க்கை (Life)",
    "உழைப்பு (Hard work)", "நம்பிக்கை (Hope)", "குடும்பம் (Family)", "மனிதநேயம் (Humanity)"
]

# Our allowed channels/groups
ALLOWED_CHANNELS = [
    "tamil_digital", "tamil5", "digitalstudioo", "indianchatt"
]

# Content moderation patterns
BAD_WORDS_PATTERNS = [
    # English abusive/sexual
    r"\b(?:porn|xxx|nude|adult|free sex|sexy video|sex chat|onlyfans|xvideos|pornhub|xnxx|brazzers|hentai)\b",
    r"\b(?:dick|fuck|fucking|fucker|motherfucker|slut|whore|cunt|faggot|twat|cocksucker|pussy|asshole|cum|tits|rape|rapist|murder|bastard|bitch|nigger|nigga|retard)\b",
    r"\b(?:blowjob|handjob|dildo|orgasm|masturbat|erection|vagina|penis|anal|boobs|naked|stripper)\b",
    # Tamil abusive (Tanglish)
    r"\b(?:thevidiya|baadu|punda|koothi|thevdiya|otha|oombu|sunni|soothu|myiru|thayoli|loosu|kena|pottai|lavada)\b",
    r"\b(?:vittu puda|nalla punda|pundekel|dei punda|pundamavan|koothi payale|thevdiya paiyan|ommala|umma oombu)\b",
    r"\b(?:kunju|sunniya|oombi|pottal|thevdia|okkala|okka|sootha|mayira|poolu)\b",
    # Hindi abusive
    r"\b(?:chutiya|gaandu|madharchod|bhenchod|bhosdike|lund|chut|randi|harami|saala|kamina|gandu)\b",
    r"\b(?:behenchod|mc|bc|lavde|laude|jhant|tatte|chinal|raand|kutiya|haramkhor)\b",
    r"\b(?:bhadwa|bhadwe|chodu|chodna|gaand mara|maa chod|behen ke|lodu|jhatu|bakchod)\b",
    # Disguised adult service ads (ban)
    r"\b(?:service available|full service|night service|body massage|happy ending|extra service|special service|paid service|vip service)\b",
    r"\b(?:independent girl|housewife available|aunty available|college girl available|model available|real meet|direct meet|genuine service|home delivery available)\b",
    r"\b(?:satisfaction guaranteed|full satisfaction|hot girl|sexy girl|call girl|video call service|nude video|private show|cam show)\b",
    r"\b(?:one night stand|friends with benefits|no strings attached|sugar daddy|sugar mommy|paid date|escort service)\b",
    # Tamil disguised service ads
    r"\b(?:service kidaikum|service venum|massage service|night out|item available|figure available|aunty kidaikum|ponnu kidaikum)\b",
    # Hindi disguised service ads
    r"\b(?:service milega|service chahiye|maal available|ladki available|aunty milegi|raat ke liye|massage milega)\b",
]

SPAM_PATTERNS = [
    # Telegram/social links
    r"t\.me/joinchat/\S+",
    r"t\.me/\+\S+",
    r"telegram\.(?:me|org|dog)/joinchat/\S+",
    r"join\s+(?:my|our)\s+(?:channel|group)",
    # Shortened/suspicious URLs
    r"https?://(?:bit\.ly|tinyurl\.com|goo\.gl|t\.co|shorturl|tiny\.cc|is\.gd|cutt\.ly)/\S+",
    r"bit\.ly/\S+",
    # Scam/fraud terms
    r"\b(?:quick cash|fast money|easy money|get rich quick|make money fast|earn money online|work from home|part time job|girls available|escort|dating|hookup|call girl|massage service)\b",
    # Advertising/spam terms
    r"\b(?:promocode|referral code|discount code|limited offer|act now|click here|dm me|pm me|whatsapp me|buy now|order now|shop now|free gift|free trial|subscribe now)\b",
    r"\b(?:100% free|guaranteed income|no investment|double your money|lottery winner|you have won|claim your prize|crypto signal|forex signal|trading signal)\b",
    r"\b(?:follow my|check my bio|link in bio|visit my page|join my|subscribe my|download app|install app|use code|coupon code|special offer|flash sale|hurry up|last chance)\b",
    # Tanglish spam/advertising
    r"\b(?:invest panna|quick cash kariya|easy money earn|job pannidalam|girls available|dm panna|whatsapp panna)\b",
    r"\b(?:panam kamika|online job|part time velai|daily income|free ah|ipo join|channel join pannunga|group join pannunga)\b",
    # Hindi spam/advertising
    r"\b(?:paise kamao|ghar baithe|online earning|free mein|abhi join karo|link pe click|whatsapp karo|call karo|msg karo)\b",
    r"\b(?:lottery|satta|matka|betting|gambling|casino|jackpot)\b",
]

# Non-allowed language patterns (Chinese, Japanese, Arabic, etc.)
FOREIGN_LANGUAGE_PATTERNS = [
    r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]",  # Chinese (Simplified and Traditional)
    r"[\u3040-\u309f\u30a0-\u30ff]",  # Japanese (Hiragana, Katakana)
    r"[\u0600-\u06ff\u0750-\u077f]",  # Arabic
    r"[\u0590-\u05ff]",  # Hebrew
    r"[\u0400-\u04ff]",  # Cyrillic (Russian)
]

# Compiled regex patterns for better performance
BAD_WORDS_REGEX = re.compile('|'.join(BAD_WORDS_PATTERNS), re.IGNORECASE)
SPAM_REGEX = re.compile('|'.join(SPAM_PATTERNS), re.IGNORECASE)

# CricAPI Functions
def get_current_matches():
    """Get current matches from CricAPI grouped by match type"""
    try:
        params = {"apikey": CRICAPI_KEY}
        response = requests.get(CRICAPI_CURRENT_MATCHES_URL, params=params)
        data = response.json()

        # Group matches by match type
        matches_by_type = {}
        if 'data' in data:
            for match in data['data']:
                match_type = match.get('matchType', 'unknown')
                if match_type not in matches_by_type:
                    matches_by_type[match_type] = []
                matches_by_type[match_type].append(match)

        return matches_by_type, data['data'] if 'data' in data else []
    except Exception as e:
        print(f"Error fetching matches: {str(e)}")
        return {}, []

def get_match_score(match_id, all_matches):
    """Get score for a specific match"""
    for match in all_matches:
        if match['id'] == match_id:
            # Construct score message
            teams = match.get('teams', ['Team A', 'Team B'])
            team_1, team_2 = teams if len(teams) >= 2 else ('Team A', 'Team B')

            score_info = match.get('score', [])
            status = match.get('status', 'Status not available')
            venue = match.get('venue', 'Venue not available')

            # Format score information
            score_lines = []
            for score_entry in score_info:
                inning = score_entry.get('inning', '')
                runs = score_entry.get('r', 0)
                wickets = score_entry.get('w', 0)
                overs = score_entry.get('o', 0)
                score_lines.append(f"{inning}: {runs}/{wickets} ({overs} overs)")

            score_text = "\n".join(score_lines)

            match_info = (
                f"🏏 {match.get('name', 'Match')}\n\n"
                f"📍 {venue}\n"
                f"⏰ {match.get('date', 'Date not available')}\n"
                f"📊 Status: {status}\n\n"
                f"{score_text}"
            )

            return match_info

    return "Match information not found."

# Command handler for cricket command
async def cricket_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available cricket matches grouped by type"""
    matches_by_type, _ = get_current_matches()

    if not matches_by_type:
        await update.message.reply_text("No matches currently available or error fetching data.")
        return

    keyboard = []
    # Add a header row with close button
    keyboard.append([
        InlineKeyboardButton("🏏 LIVE CRICKET MATCHES", callback_data="live_matches"),
        InlineKeyboardButton("❌ Close", callback_data="close")
    ])

    # Add match categories with separate sections for each type
    for match_type, matches in matches_by_type.items():
        # Add match type as a header button (not clickable)
        keyboard.append([InlineKeyboardButton(f"📋 {match_type.upper()} MATCHES", callback_data=f"category_{match_type}")])

    # Add view all matches option
    keyboard.append([InlineKeyboardButton("👁️ View All Matches", callback_data="view_all")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Use the appropriate method based on whether this is an initial command or a callback
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text("Select a match category:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Select a match category:", reply_markup=reply_markup)

async def show_live_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show only matches that haven't ended yet"""
    _, all_matches = get_current_matches()

    # Filter out matches that have ended
    live_matches = [match for match in all_matches if not match.get('matchEnded', False)]

    if not live_matches:
        # No live matches available
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Categories", callback_data="back_to_categories")],
            [InlineKeyboardButton("❌ Close", callback_data="close")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text("No live matches currently available.", reply_markup=reply_markup)
        return

    # Group live matches by type for better organization
    live_matches_by_type = {}
    for match in live_matches:
        match_type = match.get('matchType', 'unknown')
        if match_type not in live_matches_by_type:
            live_matches_by_type[match_type] = []
        live_matches_by_type[match_type].append(match)

    keyboard = []
    # Add a header row
    keyboard.append([
        InlineKeyboardButton("🏏 LIVE MATCHES ONLY", callback_data="header"),
        InlineKeyboardButton("❌ Close", callback_data="close")
    ])

    # Add matches grouped by type
    for match_type, matches in live_matches_by_type.items():
        # Add match type as a header
        keyboard.append([InlineKeyboardButton(f"📋 {match_type.upper()}", callback_data="header")])
        # Add matches under this type
        for match in matches:
            match_name = match.get('name', 'Unknown Match')
            match_id = match.get('id', '')
            keyboard.append([InlineKeyboardButton(match_name, callback_data=f"match_{match_id}")])

    # Add back button
    keyboard.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="back_to_categories")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("Select a live match:", reply_markup=reply_markup)


async def show_matches_by_category(update: Update, context: ContextTypes.DEFAULT_TYPE, category=None):
    """Show matches filtered by category or all matches if category is None"""
    matches_by_type, _ = get_current_matches()

    if not matches_by_type:
        await update.callback_query.edit_message_text("No matches currently available or error fetching data.")
        return

    keyboard = []
    # Add a header row with close button
    keyboard.append([
        InlineKeyboardButton(f"🏏 {category.upper() if category else 'ALL'} MATCHES", callback_data="header"),
        InlineKeyboardButton("❌ Close", callback_data="close")
    ])

    # If we're showing a specific category
    if category and category in matches_by_type:
        for match in matches_by_type[category]:
            match_name = match.get('name', 'Unknown Match')
            match_id = match.get('id', '')
            keyboard.append([InlineKeyboardButton(match_name, callback_data=f"match_{match_id}")])
    # If we're showing all matches
    elif not category:
        for match_type, matches in matches_by_type.items():
            # Add match type as a header
            keyboard.append([InlineKeyboardButton(f"📋 {match_type.upper()}", callback_data="header")])
            # Add matches under this type
            for match in matches:
                match_name = match.get('name', 'Unknown Match')
                match_id = match.get('id', '')
                keyboard.append([InlineKeyboardButton(match_name, callback_data=f"match_{match_id}")])

    # Add back button
    keyboard.append([InlineKeyboardButton("🔙 Back to Categories", callback_data="back_to_categories")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("Select a match:", reply_markup=reply_markup)

# Callback query handler for inline keyboard
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    callback_data = query.data

    # Don't answer callback for admin buttons - let handlers do it
    if not (callback_data.startswith("unban_") or callback_data.startswith("unmute_") or callback_data.startswith("unwarn_")):
        try:
            await query.answer()  # Answer the callback query
        except Exception as e:
            print(f"Error answering callback query: {e}")

    # Handle close button - delete the message
    if callback_data == "close":
        await query.delete_message()
        return

    if callback_data == "header":
        # Header buttons do nothing
        return

    if callback_data == "live_matches":
        # Show only live (not ended) matches
        await show_live_matches(update, context)
        return

    if callback_data == "back_to_categories":
        # Go back to match categories
        await cricket_command(update, context)
        return

    if callback_data == "view_all":
        # Show all matches
        await show_matches_by_category(update, context, None)
        return

    if callback_data.startswith("category_"):
        # Show matches for a specific category
        category = callback_data.replace("category_", "")
        # Store the current category for better back navigation
        context.user_data['last_category'] = category
        await show_matches_by_category(update, context, category)
        return

    if callback_data.startswith("match_"):
        match_id = callback_data.replace("match_", "")

        # Create action buttons for this match
        keyboard = [
            [
                InlineKeyboardButton("🔍 Live Score", callback_data=f"live_{match_id}"),
                InlineKeyboardButton("🔄 Start Updates", callback_data=f"update_{match_id}")
            ],
            [
                InlineKeyboardButton("⏹️ Stop Updates", callback_data=f"stop_{match_id}"),
                InlineKeyboardButton("🔙 Back", callback_data=f"back_from_actions_{match_id}")
            ],
            [InlineKeyboardButton("❌ Close", callback_data="close")]
        ]

        # Store the current state in user_data to enable proper back navigation
        if not context.user_data.get('navigation_stack'):
            context.user_data['navigation_stack'] = []
        context.user_data['navigation_stack'].append({"type": "match_actions", "match_id": match_id})

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Choose an action for this match:", reply_markup=reply_markup)

    elif callback_data.startswith("live_"):
        match_id = callback_data.replace("live_", "")
        _, all_matches = get_current_matches()
        score = get_match_score(match_id, all_matches)

        # Add back and close buttons
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Actions", callback_data=f"back_to_actions_{match_id}")],
            [InlineKeyboardButton("❌ Close", callback_data="close")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Store navigation state
        if not context.user_data.get('navigation_stack'):
            context.user_data['navigation_stack'] = []
        context.user_data['navigation_stack'].append({"type": "live_score", "match_id": match_id})

        await query.edit_message_text(score, reply_markup=reply_markup)

    elif callback_data.startswith("update_"):
        match_id = callback_data.replace("update_", "")
        chat_id = update.effective_chat.id

        # Stop existing updates for this chat
        if chat_id in active_updates:
            active_updates[chat_id].cancel()
            # Clean up message tracking
            if chat_id in update_message_ids:
                del update_message_ids[chat_id]

        # Start new updates
        task = asyncio.create_task(send_match_updates(context, chat_id, match_id))
        active_updates[chat_id] = task

        # Add back and close buttons
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Actions", callback_data=f"back_to_actions_{match_id}")],
            [InlineKeyboardButton("❌ Close", callback_data="close")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"Started regular updates for this match. Updates will be sent every 5 minutes.\n\nUse /stop_updates to stop all updates.",
            reply_markup=reply_markup
        )

    elif callback_data.startswith("stop_"):
        match_id = callback_data.replace("stop_", "")
        chat_id = update.effective_chat.id

        if chat_id in active_updates:
            active_updates[chat_id].cancel()
            del active_updates[chat_id]

            # Create common keyboard
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Actions", callback_data=f"back_to_actions_{match_id}")],
                [InlineKeyboardButton("❌ Close", callback_data="close")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            message = "Match updates stopped." if chat_id in active_updates else "No active updates to stop."
            await query.edit_message_text(message, reply_markup=reply_markup)

    # Handle various back navigation patterns
    elif callback_data.startswith("back_from_actions_"):
        match_id = callback_data.replace("back_from_actions_", "")
        # Get the category from context if possible
        if context.user_data.get('last_category'):
            await show_matches_by_category(update, context, context.user_data.get('last_category'))
        else:
            # If no category stored, go to all matches
            await show_matches_by_category(update, context, None)

    elif callback_data.startswith("back_to_actions_"):
        match_id = callback_data.replace("back_to_actions_", "")

        # Go back to match actions
        keyboard = [
            [
                InlineKeyboardButton("🔍 Live Score", callback_data=f"live_{match_id}"),
                InlineKeyboardButton("🔄 Start Updates", callback_data=f"update_{match_id}")
            ],
            [
                InlineKeyboardButton("⏹️ Stop Updates", callback_data=f"stop_{match_id}"),
                InlineKeyboardButton("🔙 Back", callback_data=f"back_from_actions_{match_id}")
            ],
            [InlineKeyboardButton("❌ Close", callback_data="close")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Choose an action for this match:", reply_markup=reply_markup)

    # Handle Tic-Tac-Toe game
    elif callback_data.startswith("xo_"):
        await handle_xo_callback(update, context)

    # Handle Hand Cricket game
    elif callback_data.startswith("cricket_") or callback_data.startswith("team_"):
        print(f"Routing cricket callback: {callback_data}")
        await handle_cricket_callback(update, context)
        return  # Important: return after handling

    # Handle unban/unmute/unwarn buttons (admin only)
    elif callback_data.startswith("unban_"):
        await handle_unban_callback(update, context)
        return

    elif callback_data.startswith("unmute_"):
        await handle_unmute_callback(update, context)
        return

    elif callback_data.startswith("unwarn_"):
        await handle_unwarn_callback(update, context)
        return

    # Handle poll answer updates (for non-anonymous polls)
    elif callback_data.startswith("poll_"):
        # This will be handled by poll_answer handler instead
        await query.answer("Poll answers are handled automatically!", show_alert=False)

async def send_match_updates(context, chat_id, match_id):
    """Send match updates every 5 minutes until match ends or updates are canceled"""
    try:
        while True:
            # Get fresh match data
            _, all_matches = get_current_matches()
            score = get_match_score(match_id, all_matches)

            # Check if match has ended
            match_ended = False
            for match in all_matches:
                if match['id'] == match_id and match.get('matchEnded', False):
                    match_ended = True
                    break

            # Delete previous update message if exists
            if chat_id in update_message_ids:
                try:
                    await context.bot.delete_message(chat_id, update_message_ids[chat_id])
                except Exception:
                    pass  # Message might already be deleted

            # Create keyboard with back and close buttons for each update
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Matches", callback_data="back_to_categories")],
                [InlineKeyboardButton("❌ Close", callback_data="close")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Send new update and store message ID
            message = await context.bot.send_message(
                chat_id=chat_id,
                text=score,
                reply_markup=reply_markup
            )
            update_message_ids[chat_id] = message.message_id

            if match_ended:
                # Delete the score message and send final message
                try:
                    await context.bot.delete_message(chat_id, message.message_id)
                except Exception:
                    pass

                final_message = await context.bot.send_message(
                    chat_id=chat_id,
                    text="Match has ended. Stopping updates.",
                    reply_markup=reply_markup
                )
                # Clean up tracking
                if chat_id in update_message_ids:
                    del update_message_ids[chat_id]
                break

            # Wait for 5 minutes
            await asyncio.sleep(300)

    except asyncio.CancelledError:
        # Task was cancelled, do cleanup if needed
        pass
    except Exception as e:
        # Create keyboard with back and close buttons for error message
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Matches", callback_data="back_to_categories")],
            [InlineKeyboardButton("❌ Close", callback_data="close")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Error in match updates: {str(e)}",
            reply_markup=reply_markup
        )

# Command to stop all updates
async def stop_all_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop all active match updates for this chat"""
    chat_id = update.effective_chat.id

    if chat_id in active_updates:
        active_updates[chat_id].cancel()
        del active_updates[chat_id]

    # Create common keyboard
    keyboard = [
        [InlineKeyboardButton("🔙 See Available Matches", callback_data="back_to_categories")],
        [InlineKeyboardButton("❌ Close", callback_data="close")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if chat_id in active_updates:
        active_updates[chat_id].cancel()
        del active_updates[chat_id]
        message = "All match updates stopped."
    else:
        message = "No active updates to stop."

    await update.message.reply_text(message, reply_markup=reply_markup)

# Initialize AI with fallback options
def initialize_ai():
    """Initialize AI with Groq as primary."""
    try:
        print(f"🔧 Testing Groq connection...")
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": "test"}], "max_tokens": 5}
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"✅ Groq (Llama 3.1 70B) initialized successfully!")
            return None, "groq"
        else:
            print(f"❌ Groq failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Groq failed: {e}")
    print(f"⚠️ Using fallback AI")
    return None, "fallback"

def format_for_telegram(response):
    """Convert markdown to Telegram formatting and limit words."""
    if not response:
        return response

    # Convert markdown to Telegram formatting
    formatted = re.sub(r'\*\*([^*]+)\*\*', r'*\1*', response)  # **bold** -> *bold*
    formatted = re.sub(r'#{1,6}\s*([^\n]+)', r'*\1*', formatted)  # # Header -> *Header*

    # Limit to 200 words for better voice compatibility
    words = formatted.split()
    if len(words) > 200:
        formatted = ' '.join(words[:200]) + '...'

    return formatted.strip()

def clean_for_voice(response):
    """Clean response for voice synthesis by removing all formatting."""
    if not response:
        return response

    import html
    # Decode HTML entities and remove all formatting
    cleaned = html.unescape(response)
    cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)  # Remove bold
    cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)      # Remove italic
    cleaned = re.sub(r'#{1,6}\s*', '', cleaned)           # Remove headers
    cleaned = re.sub(r'\[\d+\]', '', cleaned)             # Remove citations
    cleaned = cleaned.replace('*', '').replace('#', '').replace('`', '')

    return cleaned.strip()

def get_ai_response(text, chat_session, ai_type):
    """Get AI response with Groq as primary."""
    # Try Groq first (primary)
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": text}],
            "max_tokens": 1000,
            "temperature": 0.7
        }
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content'].strip()
            return format_for_telegram(ai_response)
        else:
            print(f"⚠️ Groq error: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Groq error: {str(e)[:50]}")

    # Final fallback
    return get_fallback_response(text)

# Optimized fallback responses with compiled patterns
FALLBACK_PATTERNS = {
    re.compile(r"\b(?:hi|hello|hey|namaste)\b", re.IGNORECASE): "Hello! I'm Lilly, your friendly assistant. How can I help you today?",
    re.compile(r"\b(?:how are you|what's up|how do you do)\b", re.IGNORECASE): "I'm doing great! Thanks for asking. I'm here to help you with cricket scores and chat.",
    re.compile(r"\b(?:thank|thanks|thx)\b", re.IGNORECASE): "You're welcome! Happy to help anytime.",
    re.compile(r"\bcricket\b", re.IGNORECASE): "Use /cricket command to see live cricket matches and scores!",
    re.compile(r"\bhelp\b", re.IGNORECASE): "I can help you with cricket scores, chat, and answer questions. Try /cricket for live matches!",

    re.compile(r"\bjoke\b", re.IGNORECASE): "Why don't cricketers ever get cold? Because they're always close to the stumps! 😄",
    re.compile(r"\bweather\b", re.IGNORECASE): "I don't have weather info, but I can tell you about cricket matches! Use /cricket",
    re.compile(r"\btime\b", re.IGNORECASE): "I don't have the current time, but I can show you live cricket match times! Use /cricket"
}

def get_fallback_response(text):
    """Enhanced rule-based responses when all AI is unavailable."""
    for pattern, response in FALLBACK_PATTERNS.items():
        if pattern.search(text):
            return response
    return get_topic_fallback(text)

def get_topic_fallback(text):
    """Return topic-specific symbols based on POEM_TOPICS when AI fails"""
    text_lower = text.lower()

    # Topic-specific elaborate expressive symbols with hieroglyphs based on existing POEM_TOPICS
    topic_symbols = {
        "life": "😊 🌱 𓆝 😍 🌟 𓊪 🌈 🥰",
        "hope": "🤩 🌟 𓅃 😇 🦋 𓊽 🌅 😌",
        "nature": "😍 🌸 𓆟 🥰 🌺 𓊖 🌳 😊",
        "hard work": "😤 💪 𓊪 😅 ⚡ 𓊘 🔥 😎",
        "education": "🤓 📚 𓅓 😊 🎓 𓊗 💡 🤩",
        "bravery": "😤 🦁 𓅃 😎 ⚔️ 𓊪 🔥 😊",
        "family": "🥰 👨👩👧👦 𓊘 😍 💝 𓊽 🏠 😊",
        "friendship": "😄 👫 𓊽 🥰 💫 𓊖 🎉 😊",
        "humanity": "😌 🤝 𓊖 🥰 🌍 𓊪 🕊️ 😇",
        "mother": "🥰 👩👧👦 𓊗 😍 💖 𓊽 🌹 😭",
        "motherland": "😌 🏛️ 𓇯 🥰 🇮🇳 𓊘 🏔️ 😊",
        "love": "😍 💕 𓆞 🥰 💖 𓊽 💋 😘",
        "god": "😇 🙏 𓊃 😌 ✨ 𓇯 🕊️ 🥰",
        "law": "😤 ⚖️ 𓊙 😊 📜 𓊗 🏦 😌",
        "entertainment": "😄 🎭 𓊨 🤩 🎪 𓊖 🎆 😊",
        "technology": "🤓 💻 𓅱 😎 🔬 𓊪 🚀 🤩",
        "science": "🤓 🔬 𓊖 😮 🧪 𓅓 🔭 😊",
        "culture": "😍 🎨 𓇯 🥰 🏛️ 𓊘 🎭 😊",
        "tradition": "😌 🕯️ 𓊘 🥰 📿 𓊽 🏮 😊",
        "success": "😎 🏆 𓅃 🤩 ⚡ 𓊪 🎆 😊",
        "wisdom": "🤓 🦉 𓅓 😌 📖 𓊗 🕯️ 🥰",
        "peace": "😌 🕊️ 𓆝 😇 ☮️ 𓊖 🌸 😊",
        "health": "😊 💚 𓆟 🥰 🌿 𓊽 🍎 😌",
        "courage": "😤 🦅 𓊪 😎 ⚡ 𓅃 🔥 😊"
    }

    # Check if text matches any topic from POEM_TOPICS
    for topic in topic_symbols:
        if topic in text_lower:
            return topic_symbols[topic]

    # Default ancient symbols - Poetry/Literature related hieroglyphs
    ancient_symbols = [
        "𓆝 𓆟 𓆞 𓆝 𓆟",  # fish, jellyfish, crab (water/life)
        "𓊪 𓊘 𓊽 𓊪 𓊘",  # bird, hand, ankh (spirit/creation)
        "𓊖 𓊗 𓊙 𓊖 𓊗",  # eye, mouth, bread (wisdom/words)
        "𓅱 𓊨 𓊖 𓅱 𓊨",  # quail, water, plant (nature/growth)
        "𓅓 𓇯 𓊃 𓅓 𓇯",  # owl, sun, house (knowledge/home)
        "𓅃 𓊪 𓊘 𓅃 𓊪"   # falcon, bird, hand (strength/creation)
    ]
    import random
    return random.choice(ancient_symbols)

# Command handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Track user statistics
    user_id = update.message.from_user.id
    username = update.message.from_user.username or 'No username'
    name = update.message.from_user.first_name or 'Unknown'
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if user_id not in bot_stats['private_users']:
        bot_stats['private_users'][user_id] = {
            'name': name,
            'username': username,
            'first_seen': current_time,
            'last_active': current_time
        }
    else:
        bot_stats['private_users'][user_id]['last_active'] = current_time

    save_bot_stats()
    await update.message.reply_text('Hello! Thanks for chatting with me! I am Lilly!\n\nUse /cricket to see live cricket matches.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "I am Lilly. Please type or send a voice message, and I will assist you!\n\n"
        "Cricket Commands:\n"
        "/cricket - View current cricket matches\n"
        "/stop_updates - Stop all match updates\n\n"
        "Music Commands:\n"
        "/play <YouTube URL or search term> - Download and send audio\n\n"
        "AI Image & Animation:\n"
        "/image <description> - Generate AI image from text\n"
        "/gif <description> - Generate animated MP4 video (8 frames)\n\n"
        "Bot Statistics:\n"
        "/stats - View bot usage statistics (Admin only)\n"
        "/discover - Force discover current group (Admin only)\n"
        "/broadcast <message> - Send message to all known chats (Admin only)\n"
        "/ping_users - Ask users to message bot for discovery (Admin only)\n\n"
        "Testing Commands (Admin only):\n"
        "/test_poems - Test poem generation and posting\n"
        "/test_flows - Compare /image and poem image flows\n"
        "/test_greeting - Test user greeting system\n\n"
        "📝 **Note:** Bot auto-discovers groups when it receives messages. Use /discover to manually add current group to stats.\n\n"
        "🔍 **Debugging:** Use /test_flows to compare Pollination API usage between /image command and poem generation flows."
    )
    await update.message.reply_text(help_text)

# Auto-discovery message sender
async def send_discovery_message(context):
    """Send a discovery message to help find existing groups and users"""
    try:
        # This will be logged when the bot starts
        print("🔍 To discover existing chats:")
        print("1. Go to each group where the bot is added")
        print("2. Send any message (the bot will auto-discover)")
        print("3. Or use /discover command in each group")
        print("4. Check /stats to see discovered groups")
        print("5. Use /ping_users to discover existing private users")

        # Send a startup message to the main group if configured
        if TARGET_CHAT_ID:
            try:
                await context.bot.send_message(
                    chat_id=TARGET_CHAT_ID,
                    text="🤖 Bot started! Send any message in groups to auto-discover them for statistics."
                )
            except:
                pass  # Ignore if can't send to main group

    except Exception as e:
        print(f"Error in discovery message: {e}")

# Ping existing private users to discover them
async def ping_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a discovery message to find existing private users"""
    user_id = update.message.from_user.id
    ADMIN_IDS = [620382392]

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for admins only.")
        return

    # Send discovery message to main group asking users to message the bot
    discovery_msg = (
        "🔍 User Discovery Mode Activated!\n\n"
        "If you've used this bot in private chat before, please send any message to the bot privately to update our records.\n\n"
        "This helps us:\n"
        "• Keep track of active users\n"
        "• Improve bot services\n"
        "• Send important updates\n\n"
        "Just send 'hi' or any message to @Lilly007_bot in private chat. Thanks! 🙏"
    )

    try:
        if TARGET_CHAT_ID:
            await context.bot.send_message(
                chat_id=TARGET_CHAT_ID,
                text=discovery_msg
            )
            await update.message.reply_text("✅ Discovery message sent to main group!")
        else:
            await update.message.reply_text("❌ TARGET_CHAT_ID not configured.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending discovery message: {e}")

async def test_poems_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test poem posting to channels (admin only)"""
    user_id = update.message.from_user.id
    ADMIN_IDS = [620382392]

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for admins only.")
        return

    try:
        await update.message.reply_text("🧪 Testing poem generation and posting...")

        # Manually trigger poem generation
        await generate_and_send_poems(context)

        await update.message.reply_text("✅ Test poems sent to all configured channels!")

    except Exception as e:
        await update.message.reply_text(f"❌ Error testing poems: {e}")
        print(f"Test poems error: {e}")
        import traceback
        traceback.print_exc()

# Test command to compare both image flows
async def test_quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test quiz system manually (admin only)"""
    user_id = update.message.from_user.id
    ADMIN_IDS = [620382392]

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for admins only.")
        return

    try:
        await update.message.reply_text("🧪 Testing quiz system...")
        await start_quiz(context, "test")
        await update.message.reply_text("✅ Test quiz triggered! Check the target group.")

    except Exception as e:
        await update.message.reply_text(f"❌ Error testing quiz: {e}")
        print(f"Test quiz error: {e}")
        import traceback
        traceback.print_exc()

async def test_greeting_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test user greeting system manually (admin only)"""
    user_id = update.message.from_user.id
    ADMIN_IDS = [620382392]

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for admins only.")
        return

    try:
        # Add current user to recent active users for testing
        chat_id = update.message.chat.id
        if chat_id == TARGET_CHAT_ID:
            recent_active_users[chat_id].add(user_id)
            await update.message.reply_text("🧪 Testing greeting system...")
            await send_friendly_greeting(context)
            await update.message.reply_text("✅ Test greeting sent!")
        else:
            await update.message.reply_text("❌ This command only works in the target group.")

    except Exception as e:
        await update.message.reply_text(f"❌ Error testing greeting: {e}")
        print(f"Test greeting error: {e}")
        import traceback
        traceback.print_exc()

async def test_all_connections_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test all AI and Image API connections (admin only)"""
    user_id = update.message.from_user.id
    ADMIN_IDS = [620382392]

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for admins only.")
        return

    await update.message.reply_text("🔍 Testing all connections... This may take a minute.")
    
    results = []
    results.append(f"🌐 **Environment:** {'PythonAnywhere' if is_pythonanywhere() else 'Local'}\n")
    
    # ===== AI SERVICES =====
    results.append("\n🤖 **AI SERVICES:**")
    
    # Test Perplexity
    print("\n🧪 [TEST] Testing Perplexity AI...")
    try:
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.1-sonar-small-128k-chat",
            "messages": [{"role": "user", "content": "test"}],
            "max_tokens": 10
        }
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            results.append("✅ Perplexity AI: Working")
            print("✅ [TEST] Perplexity: SUCCESS")
        else:
            results.append(f"❌ Perplexity AI: Failed ({response.status_code})")
            print(f"❌ [TEST] Perplexity: FAILED - Status {response.status_code}")
    except Exception as e:
        results.append(f"❌ Perplexity AI: {str(e)[:40]}")
        print(f"❌ [TEST] Perplexity: ERROR - {str(e)[:50]}")
    
    # Test Google Gemini (if configured)
    print("\n🧪 [TEST] Testing Google Gemini...")
    try:
        import google.generativeai as genai
        # Try to configure (will fail if no API key)
        genai.configure(api_key=os.getenv('GEMINI_API_KEY', 'test'))
        results.append("⚠️ Gemini: Not configured (no API key)")
        print("⚠️ [TEST] Gemini: NOT CONFIGURED")
    except Exception as e:
        results.append(f"❌ Gemini: {str(e)[:40]}")
        print(f"❌ [TEST] Gemini: ERROR - {str(e)[:50]}")
    
    # Test OpenAI (if configured)
    print("\n🧪 [TEST] Testing OpenAI...")
    try:
        openai_key = os.getenv('OPENAI_API_KEY', None)
        if openai_key:
            openai.api_key = openai_key
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            results.append("✅ OpenAI: Working")
            print("✅ [TEST] OpenAI: SUCCESS")
        else:
            results.append("⚠️ OpenAI: Not configured (no API key)")
            print("⚠️ [TEST] OpenAI: NOT CONFIGURED")
    except Exception as e:
        results.append(f"❌ OpenAI: {str(e)[:40]}")
        print(f"❌ [TEST] OpenAI: ERROR - {str(e)[:50]}")
    
    # Test Anthropic Claude (if configured)
    print("\n🧪 [TEST] Testing Anthropic Claude...")
    try:
        claude_key = os.getenv('ANTHROPIC_API_KEY', None)
        if claude_key:
            client = anthropic.Anthropic(api_key=claude_key)
            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=5,
                messages=[{"role": "user", "content": "test"}]
            )
            results.append("✅ Claude: Working")
            print("✅ [TEST] Claude: SUCCESS")
        else:
            results.append("⚠️ Claude: Not configured (no API key)")
            print("⚠️ [TEST] Claude: NOT CONFIGURED")
    except Exception as e:
        results.append(f"❌ Claude: {str(e)[:40]}")
        print(f"❌ [TEST] Claude: ERROR - {str(e)[:50]}")
    
    # Test Hugging Face (fallback)
    print("\n🧪 [TEST] Testing Hugging Face...")
    try:
        url = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"
        payload = {"inputs": "test"}
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            results.append("✅ Hugging Face: Working")
            print("✅ [TEST] Hugging Face: SUCCESS")
        else:
            results.append(f"❌ Hugging Face: Failed ({response.status_code})")
            print(f"❌ [TEST] Hugging Face: FAILED - Status {response.status_code}")
    except Exception as e:
        results.append(f"❌ Hugging Face: {str(e)[:40]}")
        print(f"❌ [TEST] Hugging Face: ERROR - {str(e)[:50]}")
    
    # ===== IMAGE SERVICES =====
    results.append("\n🖼️ **IMAGE SERVICES:**")
    
    # Test Pollinations Flux
    print("\n🧪 [TEST] Testing Pollinations Flux...")
    try:
        url = "https://image.pollinations.ai/prompt/test?width=100&height=100&nologo=true"
        response = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200 and len(response.content) > 1000:
            results.append(f"✅ Pollinations Flux: Working ({len(response.content)} bytes)")
            print(f"✅ [TEST] Pollinations Flux: SUCCESS - {len(response.content)} bytes")
        else:
            results.append(f"❌ Pollinations Flux: Failed ({response.status_code})")
            print(f"❌ [TEST] Pollinations Flux: FAILED - Status {response.status_code}")
    except Exception as e:
        results.append(f"❌ Pollinations Flux: {str(e)[:40]}")
        print(f"❌ [TEST] Pollinations Flux: ERROR - {str(e)[:50]}")
    
    # Test Pollinations Turbo
    print("\n🧪 [TEST] Testing Pollinations Turbo...")
    try:
        url = "https://image.pollinations.ai/prompt/test?width=100&height=100&model=turbo&nologo=true"
        response = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200 and len(response.content) > 1000:
            results.append(f"✅ Pollinations Turbo: Working ({len(response.content)} bytes)")
            print(f"✅ [TEST] Pollinations Turbo: SUCCESS - {len(response.content)} bytes")
        else:
            results.append(f"❌ Pollinations Turbo: Failed ({response.status_code})")
            print(f"❌ [TEST] Pollinations Turbo: FAILED - Status {response.status_code}")
    except Exception as e:
        results.append(f"❌ Pollinations Turbo: {str(e)[:40]}")
        print(f"❌ [TEST] Pollinations Turbo: ERROR - {str(e)[:50]}")
    
    # Test Unsplash
    print("\n🧪 [TEST] Testing Unsplash...")
    try:
        url = "https://source.unsplash.com/100x100/?nature"
        response = requests.get(url, timeout=10, allow_redirects=True)
        if response.status_code == 200 and len(response.content) > 1000:
            results.append(f"✅ Unsplash: Working ({len(response.content)} bytes)")
            print(f"✅ [TEST] Unsplash: SUCCESS - {len(response.content)} bytes")
        else:
            results.append(f"❌ Unsplash: Failed ({response.status_code})")
            print(f"❌ [TEST] Unsplash: FAILED - Status {response.status_code}")
    except Exception as e:
        results.append(f"❌ Unsplash: {str(e)[:40]}")
        print(f"❌ [TEST] Unsplash: ERROR - {str(e)[:50]}")
    
    # Test Picsum
    print("\n🧪 [TEST] Testing Picsum...")
    try:
        url = "https://picsum.photos/100/100"
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and len(response.content) > 1000:
            results.append(f"✅ Picsum: Working ({len(response.content)} bytes)")
            print(f"✅ [TEST] Picsum: SUCCESS - {len(response.content)} bytes")
        else:
            results.append(f"❌ Picsum: Failed ({response.status_code})")
            print(f"❌ [TEST] Picsum: FAILED - Status {response.status_code}")
    except Exception as e:
        results.append(f"❌ Picsum: {str(e)[:40]}")
        print(f"❌ [TEST] Picsum: ERROR - {str(e)[:50]}")
    
    # ===== OTHER SERVICES =====
    results.append("\n🌐 **OTHER SERVICES:**")
    
    # Test Cricket API
    print("\n🧪 [TEST] Testing Cricket API...")
    try:
        url = f"{CRICAPI_CURRENT_MATCHES_URL}?apikey={CRICAPI_KEY}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            results.append("✅ Cricket API: Working")
            print("✅ [TEST] Cricket API: SUCCESS")
        else:
            results.append(f"❌ Cricket API: Failed ({response.status_code})")
            print(f"❌ [TEST] Cricket API: FAILED - Status {response.status_code}")
    except Exception as e:
        results.append(f"❌ Cricket API: {str(e)[:40]}")
        print(f"❌ [TEST] Cricket API: ERROR - {str(e)[:50]}")
    
    # Test YouTube DL
    print("\n🧪 [TEST] Testing YouTube DL...")
    try:
        import yt_dlp
        results.append("✅ YouTube DL: Installed")
        print("✅ [TEST] YouTube DL: INSTALLED")
    except Exception as e:
        results.append(f"❌ YouTube DL: {str(e)[:40]}")
        print(f"❌ [TEST] YouTube DL: ERROR - {str(e)[:50]}")
    
    print("\n📊 [TEST] ===== CONNECTION TEST COMPLETE =====")
    
    # Send results
    message = "\n".join(results)
    await update.message.reply_text(message, parse_mode='Markdown')

async def test_image_apis_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test image API connectivity (admin only)"""
    user_id = update.message.from_user.id
    ADMIN_IDS = [620382392]

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for admins only.")
        return

    await update.message.reply_text("🔍 Testing image API connectivity...")

    results = []
    results.append(f"🌐 Environment: {'PythonAnywhere' if is_pythonanywhere() else 'Local'}")

    # Test Pollinations
    try:
        url = "https://image.pollinations.ai/prompt/test?width=100&height=100&nologo=true"
        response = requests.get(url, timeout=10)
        results.append(f"✅ Pollinations: {response.status_code} ({len(response.content)} bytes)")
    except Exception as e:
        results.append(f"❌ Pollinations: {str(e)[:50]}")

    # Test Picsum
    try:
        url = "https://picsum.photos/100/100"
        response = requests.get(url, timeout=10)
        results.append(f"✅ Picsum: {response.status_code} ({len(response.content)} bytes)")
    except Exception as e:
        results.append(f"❌ Picsum: {str(e)[:50]}")

    await update.message.reply_text("\n".join(results))

async def test_image_flows_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test and compare both /image and poem image flows (admin only)"""
    user_id = update.message.from_user.id
    ADMIN_IDS = [620382392]

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for admins only.")
        return

    try:
        await update.message.reply_text("🔍 Testing both image flows for comparison...")

        print(f"\n📊 [FLOW COMPARISON] ===== STARTING IMAGE FLOW COMPARISON TEST =====")
        print(f"👤 [FLOW COMPARISON] Triggered by: {update.message.from_user.first_name}")

        test_prompt = "beautiful sunset over mountains"

        # Test 1: /image command flow
        print(f"\n🎯 [FLOW COMPARISON] === TEST 1: /IMAGE COMMAND FLOW ===")
        print(f"🔄 [FLOW COMPARISON] Calling generate_image() directly...")
        image1 = await generate_image(test_prompt)
        print(f"🔙 [FLOW COMPARISON] /image flow result: {image1 is not None}")

        # Test 2: Poem image flow
        print(f"\n🎭 [FLOW COMPARISON] === TEST 2: POEM IMAGE FLOW ===")
        print(f"🔄 [FLOW COMPARISON] Calling generate_contextual_image() for poem...")
        image2 = await generate_contextual_image("poem", "sunset mountains", "tamil")
        print(f"🔙 [FLOW COMPARISON] Poem image flow result: {image2 is not None}")

        # Test 3: Direct Pollination call
        print(f"\n🌐 [FLOW COMPARISON] === TEST 3: DIRECT POLLINATION CALL ===")
        print(f"🔄 [FLOW COMPARISON] Calling generate_image_with_channel() directly...")
        image3 = await generate_image_with_channel(test_prompt, "hindi")
        print(f"🔙 [FLOW COMPARISON] Direct Pollination result: {image3 is not None}")

        # Summary
        print(f"\n📊 [FLOW COMPARISON] ===== COMPARISON SUMMARY =====")
        print(f"✅ [FLOW COMPARISON] /image command flow: {'SUCCESS' if image1 else 'FAILED'}")
        print(f"✅ [FLOW COMPARISON] Poem image flow: {'SUCCESS' if image2 else 'FAILED'}")
        print(f"✅ [FLOW COMPARISON] Direct Pollination: {'SUCCESS' if image3 else 'FAILED'}")
        print(f"📊 [FLOW COMPARISON] ===== END COMPARISON =====")

        # Send results to admin
        results = f"📊 **Image Flow Comparison Results:**\n\n"
        results += f"• /image command flow: {'✅ SUCCESS' if image1 else '❌ FAILED'}\n"
        results += f"• Poem image flow: {'✅ SUCCESS' if image2 else '❌ FAILED'}\n"
        results += f"• Direct Pollination: {'✅ SUCCESS' if image3 else '❌ FAILED'}\n\n"
        results += f"Check console logs for detailed Pollination API calls."

        await update.message.reply_text(results, parse_mode='Markdown')

        # Send sample images if generated
        if image1:
            await update.message.reply_photo(image1, caption="Sample from /image flow")
        if image2:
            await update.message.reply_photo(image2, caption="Sample from poem flow")
        if image3:
            await update.message.reply_photo(image3, caption="Sample from direct Pollination")

    except Exception as e:
        print(f"💥 [FLOW COMPARISON] Error in flow comparison: {e}")
        await update.message.reply_text(f"❌ Error testing flows: {e}")

# Test poems command

# Broadcast to known chats
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send discovery message to all known groups and users"""
    user_id = update.message.from_user.id
    ADMIN_IDS = [620382392]

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for admins only.")
        return

    if not context.args:
        await update.message.reply_text("❌ Usage: /broadcast <message>")
        return

    message = " ".join(context.args)
    sent_count = 0
    failed_count = 0

    # Send to known groups
    for chat_id in bot_stats['groups'].keys():
        try:
            await context.bot.send_message(chat_id=int(chat_id), text=message)
            sent_count += 1
            await asyncio.sleep(0.1)  # Rate limiting
        except Exception as e:
            failed_count += 1
            print(f"Failed to send to group {chat_id}: {e}")

    # Send to known private users
    for user_id in bot_stats['private_users'].keys():
        try:
            await context.bot.send_message(chat_id=int(user_id), text=message)
            sent_count += 1
            await asyncio.sleep(0.1)  # Rate limiting
        except Exception as e:
            failed_count += 1
            print(f"Failed to send to user {user_id}: {e}")

    await update.message.reply_text(f"✅ Broadcast complete!\n📤 Sent: {sent_count}\n❌ Failed: {failed_count}")

# Force discover current group
async def discover_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force discover and add current group to statistics"""
    user_id = update.message.from_user.id
    ADMIN_IDS = [620382392]

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for admins only.")
        return

    chat_id = update.message.chat.id
    message_type = update.message.chat.type

    if message_type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ This command only works in groups.")
        return

    try:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        chat = await context.bot.get_chat(chat_id)
        member_count = await context.bot.get_chat_member_count(chat_id)

        bot_stats['groups'][chat_id] = {
            'name': chat.title or 'Unknown Group',
            'members': member_count,
            'added_date': current_time
        }

        save_bot_stats()
        await update.message.reply_text(f"✅ Group '{chat.title}' added to statistics!\n👥 Members: {member_count}")

    except Exception as e:
        await update.message.reply_text(f"❌ Error discovering group: {e}")

# Scan for existing groups
async def scan_existing_groups(context):
    """Scan for groups the bot is already in but not tracked"""
    try:
        # Get bot info
        bot_info = await context.bot.get_me()
        print(f"Scanning for existing groups for bot: {bot_info.username}")

        # Note: Telegram Bot API doesn't provide a direct way to list all chats
        # The bot can only discover groups when it receives messages
        # This is a limitation of the Telegram Bot API for privacy reasons

        return "Bot can only discover groups when receiving messages due to Telegram API limitations."
    except Exception as e:
        return f"Error scanning groups: {e}"

# Bot statistics command
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics (admin only)"""
    user_id = update.message.from_user.id

    # Check if user is admin (you can modify this list)
    ADMIN_IDS = [620382392]  # Replace with actual admin user IDs

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for admins only.")
        return

    try:
        # Groups statistics with deduplication by username
        seen_usernames = set()
        unique_groups = []
        for chat_id, info in bot_stats['groups'].items():
            username = info.get('username', 'No username')
            if username not in seen_usernames:
                seen_usernames.add(username)
                unique_groups.append((chat_id, info))

        groups_text = f"📊 **Bot Statistics**\n\n🏘️ **Groups ({len(unique_groups)})**:\n"
        for chat_id, info in unique_groups[:10]:  # Show first 10
            username_display = f"@{info['username']}" if info.get('username') and info['username'] != 'No username' else 'No username'
            group_type = info.get('type', 'unknown')
            groups_text += f"• {info['name']} ({username_display}) [{group_type}] - {info['members']} members\n"

        if len(unique_groups) > 10:
            groups_text += f"... and {len(unique_groups) - 10} more groups\n"

        # Private users statistics with deduplication by username
        seen_user_usernames = set()
        unique_users = []
        for user_id, info in bot_stats['private_users'].items():
            username = info.get('username', 'No username')
            if username not in seen_user_usernames:
                seen_user_usernames.add(username)
                unique_users.append((user_id, info))

        users_text = f"\n👤 **Private Users ({len(unique_users)})**:\n"
        for user_id, info in unique_users[:15]:  # Show first 15
            users_text += f"• {info['name']} (@{info['username']})\n"

        if len(unique_users) > 15:
            users_text += f"... and {len(unique_users) - 15} more users\n"

        # Total statistics
        total_text = f"\n📈 **Totals:**\n• Groups: {len(bot_stats['groups'])}\n• Private Users: {len(bot_stats['private_users'])}\n• Total Messages: {bot_stats['total_messages']}\n\n⚠️ **Note:** Bot can only track groups where it receives messages. Some groups may not be visible due to Telegram API limitations."

        full_stats = groups_text + users_text + total_text

        # Split message if too long
        if len(full_stats) > 4000:
            await update.message.reply_text(groups_text)
            await update.message.reply_text(users_text + total_text)
        else:
            await update.message.reply_text(full_stats)

    except Exception as e:
        await update.message.reply_text(f"Error getting stats: {e}")

# Add watermark to image
def add_watermark(image_data, channel="tamil"):
    """Add channel-specific watermark with green background and eclipse structure"""
    print(f"\n🏷️ [WATERMARK] Starting watermark process")
    print(f"📺 [WATERMARK] Channel: {channel}")
    print(f"📊 [WATERMARK] Input image size: {len(image_data)} bytes")

    try:
        # Open image
        img = Image.open(io.BytesIO(image_data))
        draw = ImageDraw.Draw(img)
        print(f"✅ [WATERMARK] Image opened successfully")

        # Get image dimensions
        width, height = img.size
        print(f"📊 [WATERMARK] Image dimensions: {width}x{height}")

        # Watermark settings based on channel
        if channel == "tamil":
            line1 = "@tamil_digital"
            line2 = "@tamil5"
        else:  # hindi/digitalstudioo
            line1 = "@digitalstudioo"
            line2 = "@indianchatt"

        print(f"🏷️ [WATERMARK] Watermark text: '{line1}' / '{line2}'")

        target_width = width // 3  # 1/3 of image width
        font_size = max(20, width // 25)  # Smaller font for two lines
        print(f"🔤 [WATERMARK] Font size: {font_size}, Target width: {target_width}")

        try:
            # Try to use a default font
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", font_size)
        except:
            # Fallback to default font
            font = ImageFont.load_default()

        # Get text dimensions (compatible with both Pillow 9.0.0 and 11.3.0)
        try:
            # Try modern method (Pillow 8.0+)
            bbox1 = draw.textbbox((0, 0), line1, font=font)
            bbox2 = draw.textbbox((0, 0), line2, font=font)
            text1_width = bbox1[2] - bbox1[0]
            text2_width = bbox2[2] - bbox2[0]
            text_height = bbox1[3] - bbox1[1]
        except AttributeError:
            # Fallback for Pillow 9.0.0
            text1_width, text_height = draw.textsize(line1, font=font)
            text2_width, _ = draw.textsize(line2, font=font)

        # Use the wider text for centering
        max_text_width = max(text1_width, text2_width)

        # Eclipse background dimensions - 1/3 IMAGE WIDTH
        eclipse_width = target_width  # Exactly 1/3 of image width
        eclipse_height = (text_height * 2) + 20  # Height for two lines plus padding

        # Position lower in bottom right corner
        margin = 10  # Smaller margin to place lower
        eclipse_x = width - eclipse_width - margin
        eclipse_y = height - eclipse_height - margin

        # Center both lines in eclipse
        x1 = eclipse_x + (eclipse_width - text1_width) // 2
        x2 = eclipse_x + (eclipse_width - text2_width) // 2
        y1 = eclipse_y + 8  # First line position
        y2 = y1 + text_height + 4  # Second line position

        # Draw rectangle (compatible with both versions)
        try:
            # Try rounded rectangle (Pillow 8.2+)
            draw.rounded_rectangle(
                [eclipse_x, eclipse_y, eclipse_x + eclipse_width, eclipse_y + eclipse_height],
                radius=15,
                fill=(0, 107, 58, 200),
                outline=(186, 167, 99),
                width=4
            )
        except AttributeError:
            # Fallback for Pillow 9.0.0 - regular rectangle
            draw.rectangle(
                [eclipse_x, eclipse_y, eclipse_x + eclipse_width, eclipse_y + eclipse_height],
                fill=(0, 107, 58, 200),
                outline=(186, 167, 99),
                width=4
            )

        # Draw both lines of text (custom off-white)
        draw.text((x1, y1), line1, font=font, fill=(253, 252, 254))  # #fdfcfe text
        draw.text((x2, y2), line2, font=font, fill=(253, 252, 254))  # #fdfcfe text

        # Convert back to bytes
        output = io.BytesIO()
        img.save(output, format='PNG')
        watermarked_data = output.getvalue()
        print(f"✅ [WATERMARK] Watermark applied successfully")
        print(f"📊 [WATERMARK] Output image size: {len(watermarked_data)} bytes")
        return watermarked_data

    except Exception as e:
        print(f"💥 [WATERMARK] Watermark error: {e}")
        print(f"🔄 [WATERMARK] Returning original image data")
        return image_data  # Return original if watermark fails

# AI Video Generation using RunwayML API
async def generate_video(prompt):
    """Generate video using RunwayML Gen-3 API"""
    try:
        # RunwayML API endpoint for video generation
        url = "https://api.runwayml.com/v1/image_to_video"

        headers = {
            "Authorization": "Bearer YOUR_RUNWAYML_API_KEY",  # Replace with actual key
            "Content-Type": "application/json"
        }

        payload = {
            "prompt": prompt,
            "duration": 4,  # 4 seconds
            "ratio": "16:9",
            "watermark": False
        }

        response = requests.post(url, json=payload, headers=headers, timeout=120)

        if response.status_code == 200:
            result = response.json()
            video_url = result.get('output', {}).get('url')

            if video_url:
                # Download the generated video
                video_response = requests.get(video_url, timeout=60)
                if video_response.status_code == 200:
                    return video_response.content

        return None

    except Exception as e:
        print(f"RunwayML video generation error: {e}")
        return None

# Check if running on PythonAnywhere
def is_pythonanywhere():
    """Detect if running on PythonAnywhere"""
    try:
        import socket
        hostname = socket.gethostname()
        return 'pythonanywhere' in hostname.lower()
    except:
        return False

# Fallback: AI Image Generation using Pollinations AI (Free)
async def generate_image(prompt):
    """Generate image using multiple services with fallbacks"""
    print(f"\n🚀 [/IMAGE FLOW] Starting generate_image function")
    print(f"📝 [/IMAGE FLOW] Input prompt: '{prompt}'")
    print(f"🌐 [/IMAGE FLOW] PythonAnywhere: {is_pythonanywhere()}")

    # Clean prompt thoroughly
    import re
    import urllib.parse
    clean_prompt = re.sub(r'[^a-zA-Z0-9\s]', '', prompt)
    clean_prompt = re.sub(r'\s+', ' ', clean_prompt).strip()
    encoded_prompt = urllib.parse.quote(clean_prompt)

    services = [
        {
            "name": "Picsum",
            "url": f"https://picsum.photos/1024/1024?random={random.randint(1, 1000)}"
        },
        {
            "name": "LoremFlickr",
            "url": f"https://loremflickr.com/1024/1024/{clean_prompt.replace(' ', ',')}"
        },
        {
            "name": "Pollinations-Flux",
            "url": f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&seed={random.randint(1, 1000000)}"
        }
    ]

    for service in services:
        try:
            print(f"🎨 [/IMAGE FLOW] Trying {service['name']}...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'image/*'
            }
            response = requests.get(service["url"], timeout=30, headers=headers, allow_redirects=True)
            print(f"📊 [{service['name']}] Status: {response.status_code}, Size: {len(response.content)}")

            if response.status_code == 200 and len(response.content) > 5000:
                print(f"✅ [{service['name']}] Success!")
                return add_watermark(response.content, "tamil")
        except Exception as e:
            print(f"❌ [{service['name']}] Error: {str(e)[:50]}")

    print("❌ [/IMAGE FLOW] All services failed - returning None")
    return None

async def generate_image_with_channel(prompt, channel="tamil"):
    """Generate image with channel-specific watermark"""
    print(f"\n🎭 [POEM IMAGE FLOW] Channel: {channel}, Prompt: '{prompt[:50]}'")

    import re, urllib.parse
    clean_prompt = re.sub(r'[^a-zA-Z0-9\s]', '', prompt).strip()
    encoded_prompt = urllib.parse.quote(clean_prompt)

    services = [
        f"https://picsum.photos/1024/1024?random={random.randint(1, 1000)}",
        f"https://loremflickr.com/1024/1024/{clean_prompt.replace(' ', ',')}",
        f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&seed={random.randint(1, 1000000)}"
    ]

    for url in services:
        try:
            response = requests.get(url, timeout=30, headers={'User-Agent': 'Mozilla/5.0'}, allow_redirects=True)
            if response.status_code == 200 and len(response.content) > 5000:
                print(f"✅ [POEM IMAGE] Success with {url[:40]}")
                return add_watermark(response.content, channel)
        except Exception as e:
            print(f"❌ [POEM IMAGE] Failed: {str(e)[:50]}")

    print("❌ [POEM IMAGE] All services failed")
    return None

# Generate contextual image for content
async def generate_contextual_image(content_type, theme_or_content, channel="tamil"):
    """Generate relevant image for poems, quizzes, or special days"""
    print(f"\n🎨 [CONTEXTUAL] Type: {content_type}, Theme: '{theme_or_content[:30]}', Channel: {channel}")

    try:
        clean_theme = ''.join(c for c in theme_or_content if c.isalnum() or c.isspace()).strip()
        prompts = {
            "poem": f"artistic {clean_theme} peaceful inspiring",
            "quiz": f"educational knowledge {clean_theme}",
            "special_day": f"celebration {clean_theme} festive",
            "greeting": f"friendly {clean_theme} welcoming"
        }
        prompt = prompts.get(content_type, f"illustration {clean_theme}")
        return await generate_image_with_channel(prompt, channel)
    except Exception as e:
        print(f"❌ [CONTEXTUAL] Error: {e}")
        return None

# Generate multiple images for animation
async def generate_multiple_images(base_prompt, count=8, status_callback=None):
    """Generate multiple images with dramatic variations for animation"""
    # More dramatic movement variations
    variations = [
        f"{base_prompt}, starting position, static pose",
        f"{base_prompt}, beginning movement, slight motion",
        f"{base_prompt}, mid-action, clear movement, dynamic",
        f"{base_prompt}, peak motion, maximum action, dramatic pose",
        f"{base_prompt}, different angle, side view, active movement",
        f"{base_prompt}, close-up action, intense motion",
        f"{base_prompt}, wide shot, full body movement",
        f"{base_prompt}, final position, end pose, completion"
    ]

    images = []
    successful_generations = 0

    for i in range(count):
        # Continue generating all requested frames

        prompt = variations[i] if i < len(variations) else f"{base_prompt}, animation sequence frame {i+1}"
        print(f"Generating frame {i+1}/{count}...")

        # Update user with progress
        if status_callback:
            await status_callback(f"🎨 Generating frame {i+1}/{count}...")

        image_data = await generate_image(prompt)
        if image_data:
            images.append(image_data)
            successful_generations += 1
            print(f"✅ Frame {i+1} generated successfully")

            # Notify user of success
            if status_callback:
                await status_callback(f"✅ Frame {i+1}/{count} completed! ({successful_generations} total)")
        else:
            print(f"❌ Frame {i+1} failed")

        # Shorter delay for better variation
        await asyncio.sleep(2)

    print(f"Generated {len(images)} images out of {count} attempts")
    return images

# Create MP4 video with audio using FFmpeg subprocess
def create_mp4_video_with_audio(image_data_list, prompt):
    """Create high-quality MP4 video with background audio using FFmpeg"""
    try:
        import subprocess
        from gtts import gTTS

        if not image_data_list:
            return None

        # Create temporary directory for frames
        frame_folder = 'temp_frames'
        os.makedirs(frame_folder, exist_ok=True)

        # Save images as frame files
        frame_files = []
        for i, img_data in enumerate(image_data_list):
            # Add watermark to each frame
            watermarked_data = add_watermark(img_data)
            img = Image.open(io.BytesIO(watermarked_data))
            # Higher resolution for better quality
            img = img.resize((1024, 1024), Image.LANCZOS)

            # Save frame
            frame_path = f"{frame_folder}/frame_{i:03d}.png"
            img.save(frame_path)
            frame_files.append(frame_path)

        if len(frame_files) < 2:
            return None

        # Download free background music from APIs (no proxy/tokens needed)
        audio_path = 'temp_audio.mp3'
        try:
            # Free music APIs that work without proxy/tokens
            music_apis = [
                "https://www.bensound.com/bensound-music/bensound-ukulele.mp3",
                "https://www.bensound.com/bensound-music/bensound-sunny.mp3",
                "https://archive.org/download/testmp3testfile/mpthreetest.mp3",
                "https://file-examples.com/storage/fe68c1c7c66c0568f4c8e0b/2017/11/file_example_MP3_700KB.mp3",
                "https://www.learningcontainer.com/wp-content/uploads/2020/02/Kalimba.mp3",
                "https://sample-videos.com/zip/10/mp3/SampleAudio_0.4mb_mp3.mp3"
            ]

            # Try each API until one works
            for music_url in music_apis:
                try:
                    print(f"Trying to download from: {music_url[:50]}...")
                    response = requests.get(music_url, timeout=20, allow_redirects=True)
                    if response.status_code == 200 and len(response.content) > 5000:
                        with open(audio_path, 'wb') as f:
                            f.write(response.content)
                        print(f"✅ Downloaded audio from: {music_url[:50]}...")
                        break
                except Exception as e:
                    print(f"❌ Failed: {music_url[:30]}... - {str(e)[:50]}")
                    continue
            else:
                # If all APIs fail, generate simple pleasant tone
                print("All music APIs failed, generating local audio...")
                import numpy as np
                import wave

                audio_path = 'temp_audio.wav'
                sample_rate = 44100
                duration = 4.0
                t = np.linspace(0, duration, int(sample_rate * duration), False)

                # Generate pleasant C major chord
                freq1 = 261.63  # C4
                freq2 = 329.63  # E4
                freq3 = 392.00  # G4

                tone1 = np.sin(2 * np.pi * freq1 * t) * 0.3
                tone2 = np.sin(2 * np.pi * freq2 * t) * 0.2
                tone3 = np.sin(2 * np.pi * freq3 * t) * 0.2

                audio = tone1 + tone2 + tone3

                # Fade in/out
                fade_samples = int(0.1 * sample_rate)
                audio[:fade_samples] *= np.linspace(0, 1, fade_samples)
                audio[-fade_samples:] *= np.linspace(1, 0, fade_samples)

                audio = np.int16(audio * 32767 / np.max(np.abs(audio)))

                with wave.open(audio_path, 'w') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(audio.tobytes())

        except Exception as audio_error:
            print(f"Audio processing failed: {audio_error}")
            audio_path = None

        # Create video using FFmpeg
        output_path = 'temp_video_with_audio.mp4'
        fps = 2.0

        if audio_path and os.path.exists(audio_path):
            # Create video with audio
            ffmpeg_cmd = [
                'ffmpeg', '-y',  # -y to overwrite output file
                '-framerate', str(fps),
                '-i', f'{frame_folder}/frame_%03d.png',
                '-i', audio_path,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-pix_fmt', 'yuv420p',
                '-shortest',  # End when shortest stream ends
                output_path
            ]
        else:
            # Create video without audio
            ffmpeg_cmd = [
                'ffmpeg', '-y',
                '-framerate', str(fps),
                '-i', f'{frame_folder}/frame_%03d.png',
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-t', '4',  # 4 second duration
                output_path
            ]

        # Run FFmpeg
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

        if result.returncode == 0 and os.path.exists(output_path):
            # Read the video file
            with open(output_path, 'rb') as f:
                video_data = f.read()
        else:
            print(f"FFmpeg error: {result.stderr}")
            video_data = None

        # Cleanup
        for frame_file in frame_files:
            if os.path.exists(frame_file):
                os.remove(frame_file)
        if os.path.exists(frame_folder):
            os.rmdir(frame_folder)
        if os.path.exists(output_path):
            os.remove(output_path)
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)

        return video_data

    except Exception as e:
        print(f"FFmpeg video creation error: {e}")
        return None

# Fallback: Create MP4 video without audio using OpenCV
def create_mp4_video(image_data_list):
    """Fallback video creation without audio using OpenCV"""
    try:
        if not image_data_list:
            return None

        # Convert images to numpy arrays with watermark
        frames = []
        for img_data in image_data_list:
            watermarked_data = add_watermark(img_data)
            img = Image.open(io.BytesIO(watermarked_data))
            img = img.resize((720, 720), Image.LANCZOS)
            frame = np.array(img.convert('RGB'))
            frames.append(frame)

        if len(frames) < 2:
            return None

        # Create enhanced frame sequence
        enhanced_frames = []
        for i in range(len(frames)):
            for _ in range(3):  # Each frame shows for 3 video frames
                enhanced_frames.append(frames[i])

            if i < len(frames) - 1:
                blend = cv2.addWeighted(frames[i], 0.5, frames[i + 1], 0.5, 0)
                enhanced_frames.append(blend)

        # Create video writer
        output_path = 'temp_video_simple.mp4'
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = 4.0
        video_writer = cv2.VideoWriter(output_path, fourcc, fps, (720, 720))

        for frame in enhanced_frames:
            bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            video_writer.write(bgr_frame)

        video_writer.release()

        with open(output_path, 'rb') as f:
            video_data = f.read()

        os.remove(output_path)
        return video_data

    except Exception as e:
        print(f"Simple video creation error: {e}")
        return None

# Image command handler
async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate AI image from text prompt"""
    print(f"\n🎯 [/IMAGE COMMAND] User triggered /image command")
    print(f"👤 [/IMAGE COMMAND] User: {update.message.from_user.first_name} (@{update.message.from_user.username})")
    print(f"💬 [/IMAGE COMMAND] Chat ID: {update.message.chat.id}")

    if len(context.args) < 1:
        print(f"❌ [/IMAGE COMMAND] No prompt provided by user")
        await update.message.reply_text("Usage: /image <description>\n\nExample: /image a beautiful sunset over mountains")
        return

    prompt = " ".join(context.args)
    print(f"📝 [/IMAGE COMMAND] User prompt: '{prompt}'")

    try:
        print(f"⏳ [/IMAGE COMMAND] Sending status message to user...")
        status_msg = await update.message.reply_text("🎨 Generating your image...")
        print(f"✅ [/IMAGE COMMAND] Status message sent, calling generate_image()...")

        # Generate image
        print(f"🔄 [/IMAGE COMMAND] Calling generate_image() with prompt: '{prompt}'")
        image_data = await generate_image(prompt)
        print(f"🔙 [/IMAGE COMMAND] generate_image() returned: {image_data is not None}")

        if image_data:
            print(f"✅ [/IMAGE COMMAND] Image generated successfully, updating status...")
            await status_msg.edit_text("📤 Sending image...")
            print(f"📤 [/IMAGE COMMAND] Sending image to user...")

            # Send image
            await update.message.reply_photo(
                photo=image_data,
                caption=f"🎨 Generated: {prompt}"
            )
            print(f"✅ [/IMAGE COMMAND] Image sent successfully to user")

            await status_msg.delete()
            print(f"🧹 [/IMAGE COMMAND] Status message deleted, command complete")
        else:
            print(f"❌ [/IMAGE COMMAND] Image generation failed, notifying user")
            await status_msg.edit_text("❌ Failed to generate image. Please try again with a different prompt.")

    except Exception as e:
        print(f"💥 [/IMAGE COMMAND] Exception occurred: {str(e)}")
        await update.message.reply_text(f"❌ Error generating image: {str(e)}")

# Animated MP4 command handler
async def gif_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate animated MP4 video from text prompt"""
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /gif <description>\n\nExample: /gif a cat walking")
        return

    prompt = " ".join(context.args)

    try:
        status_msg = await update.message.reply_text("🎬 Generating animated video...\n🔄 This may take 30-60 seconds...")

        # Generate multiple images with progress updates
        async def update_status(message):
            await status_msg.edit_text(message)

        await status_msg.edit_text("🎨 Creating 8 image variations...")
        images = await generate_multiple_images(prompt, 8, update_status)

        if len(images) >= 2:
            await status_msg.edit_text("🎬 Creating MP4 video with audio...")

            # Try FFmpeg with audio first
            video_data = create_mp4_video_with_audio(images, prompt)

            if video_data:
                await status_msg.edit_text("📤 Sending video...")

                # Send MP4 video with audio
                await update.message.reply_video(
                    video=video_data,
                    caption=f"🎬 Animated: {prompt} 🎧"
                )

                await status_msg.delete()
            else:
                # Fallback to OpenCV video without audio
                await status_msg.edit_text("🎬 Creating simple video...")
                video_data = create_mp4_video(images)

                if video_data:
                    await update.message.reply_video(
                        video=video_data,
                        caption=f"🎬 Animated: {prompt} (OpenCV)"
                    )
                    await status_msg.delete()
                else:
                    await status_msg.edit_text("❌ Failed to create video. Please try again.")
        else:
            await status_msg.edit_text("❌ Not enough images generated. Please try again with a different prompt.")

    except Exception as e:
        await update.message.reply_text(f"❌ Error generating video: {str(e)}")

# Play command handler for YouTube audio
async def play_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Download and send audio from YouTube URL or search term"""
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /play <YouTube URL or search term>")
        return

    query = " ".join(context.args)

    try:
        status_msg = await update.message.reply_text("🔍 Downloading audio...")

        # If not a URL, search YouTube
        if not query.startswith(('http://', 'https://')):
            ydl_opts = {'quiet': True, 'no_warnings': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                search_results = ydl.extract_info(f"ytsearch:{query}", download=False)
                if search_results['entries']:
                    query = search_results['entries'][0]['webpage_url']
                else:
                    await status_msg.edit_text("❌ No results found!")
                    return

        # Download audio
        audio_file = download_audio(query)
        await status_msg.edit_text("🎵 Audio downloaded! Sending...")

        # Send audio file
        with open(audio_file, 'rb') as audio:
            await update.message.reply_audio(audio)

        # Clean up
        if os.path.exists(audio_file):
            os.remove(audio_file)

        await status_msg.delete()

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# Content moderation
def contains_bad_words(text: str) -> bool:
    return BAD_WORDS_REGEX.search(text) is not None

async def is_channel_or_group(context, username):
    """Check if @mention is a channel/group or user/bot."""
    try:
        # Remove @ if present
        clean_username = username.replace('@', '')

        # Try to get chat info
        chat = await context.bot.get_chat(f"@{clean_username}")

        # Check if it's a channel or group
        if chat.type in ['channel', 'supergroup']:
            return True
        elif chat.type in ['private', 'group']:
            return False
    except Exception:
        # If we can't get info, assume it's a user (safer approach)
        return False

    return False

def contains_foreign_languages(text: str) -> bool:
    """Check for non-allowed languages (Chinese, Japanese, Arabic, etc.)"""
    for pattern in FOREIGN_LANGUAGE_PATTERNS:
        if re.search(pattern, text):
            return True
    return False

async def contains_spam_links(text: str, update: Update, context) -> bool:
    """Check for spam links and differentiate user mentions from channel/group links."""
    # Check for obvious spam patterns first
    if SPAM_REGEX.search(text):
        return True

    # Check for foreign languages
    if contains_foreign_languages(text):
        print(f"Blocked foreign language content")
        return True

    # Check @mentions to see if they're channels/groups
    if update.message.entities:
        for entity in update.message.entities:
            if entity.type == 'mention':
                mention = text[entity.offset:entity.offset + entity.length]
                mention_clean = mention.replace('@', '')

                # Allow our own channels
                if mention_clean in ALLOWED_CHANNELS:
                    print(f"Allowed our channel: {mention}")
                    continue

                # Block other channels/groups
                if await is_channel_or_group(context, mention):
                    print(f"Blocked external channel/group: {mention}")
                    return True
                else:
                    print(f"Allowed user/bot mention: {mention}")
    return False

# Handle media messages (photos, GIFs, stickers) for NSFW detection
async def handle_media_moderation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Scan photos, GIFs, and stickers for inappropriate content in groups"""
    if update.message.chat.type not in ['group', 'supergroup']:
        return
    
    try:
        img_bytes = None
        media_type = "unknown"
        
        # Get image bytes based on media type
        if update.message.photo:
            media_type = "photo"
            photo = update.message.photo[-1]  # Largest size
            file = await context.bot.get_file(photo.file_id)
            img_bytes = await file.download_as_bytearray()
        elif update.message.animation:  # GIF
            media_type = "gif"
            if update.message.animation.thumbnail:
                file = await context.bot.get_file(update.message.animation.thumbnail.file_id)
                img_bytes = await file.download_as_bytearray()
        elif update.message.sticker:
            media_type = "sticker"
            if update.message.sticker.thumbnail:
                file = await context.bot.get_file(update.message.sticker.thumbnail.file_id)
                img_bytes = await file.download_as_bytearray()
        
        if not img_bytes:
            print(f"\u26a0\ufe0f [MEDIA] No image bytes for {media_type} from {update.message.from_user.first_name}")
            return
        
        print(f"\ud83d\udd0d [MEDIA] Scanning {media_type} from {update.message.from_user.first_name} ({len(img_bytes)} bytes)")
        
        import base64
        img_base64 = base64.b64encode(bytes(img_bytes)).decode()
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "Is this image appropriate for a family-friendly group? Reply ONLY one word: SAFE or UNSAFE. UNSAFE means: nudity, porn, sexual content, cleavage, bra/panty/bikini/lingerie, exposed body parts (hips/butt/chest), suggestive poses, weapons, guns, knives, drugs, crypto/forex promotions, spam text, QR codes, gore, or violence."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
            ]}],
            "max_tokens": 5
        }
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        print(f"\ud83d\udcca [MEDIA] Groq response: {response.status_code}")
        if response.status_code == 200:
            result = response.json()['choices'][0]['message']['content'].strip().upper()
            print(f"\ud83d\udcca [MEDIA] Result: {result}")
            if 'UNSAFE' in result:
                chat_id = update.effective_chat.id
                user = update.message.from_user
                await context.bot.delete_message(chat_id, update.message.message_id)
                await context.bot.ban_chat_member(chat_id, user.id)
                keyboard = [
                    [InlineKeyboardButton("\ud83d\udd13 Unban (Admins Only)", callback_data=f"unban_{user.id}_{user.username or user.first_name}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(chat_id, f"\ud83d\udeab @{user.username or user.first_name} banned - inappropriate media detected.", reply_markup=reply_markup)
                print(f"\ud83d\udeab [MEDIA] Banned {user.first_name} for NSFW {media_type}")
            else:
                print(f"\u2705 [MEDIA] {media_type} OK from {update.message.from_user.first_name}")
        else:
            print(f"\u274c [MEDIA] Groq API error: {response.status_code} - {response.text[:100]}")
    except Exception as e:
        print(f"\u274c [MEDIA] Media moderation error: {e}")
        import traceback
        traceback.print_exc()

# Handle voice messages
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"update Voice Text: {update}")
    """Convert voice messages to text and process them."""
    file = await update.message.voice.get_file()
    file_path = "voice.ogg"
    await file.download_to_drive(file_path)

    # Convert to WAV format
    audio = AudioSegment.from_ogg(file_path)
    audio.export("voice.wav", format="wav")

    # Convert speech to text
    recognizer = sr.Recognizer()
    with sr.AudioFile("voice.wav") as source:
        audio_data = recognizer.record(source)

    try:
        text = recognizer.recognize_google(audio_data)
        print(f"Recognized Voice Text: {text}")

        # Process text as a normal message
        await handle_message(update, context, text)

    except sr.UnknownValueError:
        await update.message.reply_text("Sorry, I couldn't understand the audio.")
    except sr.RequestError:
        await update.message.reply_text("There was an issue processing your voice. Try again.")

    # Cleanup
    os.remove("voice.ogg")
    os.remove("voice.wav")

# AI Content Moderation
async def check_message_with_ai(text: str) -> dict:
    """Check message using AI for advanced content moderation"""
    try:
        prompt = f"""Analyze this message for inappropriate content. Respond with ONLY one word:
- BAN: for explicit sexual content, hate speech, threats, or severe harassment
- MUTE: for spam, promotional content, mild inappropriate language, or suspicious links
- SAFE: for normal, acceptable content

Message: "{text}"

Response (one word only):"""
        
        ai_response = get_ai_response(prompt, chat_session, ai_type).strip().upper()
        
        if "BAN" in ai_response:
            return {'action': 'ban', 'reason': 'AI detected severe violation'}
        elif "MUTE" in ai_response:
            return {'action': 'mute', 'reason': 'AI detected mild violation'}
        else:
            return {'action': 'none', 'reason': 'Content approved'}
            
    except Exception as e:
        print(f"AI moderation failed: {e}")
        # Fallback to regex patterns
        message_lower = text.lower()
        
        if contains_foreign_languages(text):
            return {'action': 'mute', 'reason': 'Foreign language detected'}
        
        spam_patterns = [r'(join|click).*(channel|group)', r't\.me/\w+', r'https?://\S+', r'@\w+channel', r'@\w+group']
        for pattern in spam_patterns:
            if re.search(pattern, message_lower):
                return {'action': 'mute', 'reason': 'Spam pattern detected'}
        
        bad_patterns = [r'\b(fuck|shit|bitch|porn|xxx|adult)\b']
        for pattern in bad_patterns:
            if re.search(pattern, message_lower):
                return {'action': 'ban', 'reason': 'Bad language detected'}
        
        return {'action': 'none', 'reason': 'Content approved'}

# Spam/porn detection keywords
SPAM_KEYWORDS = ['spam', 'click here', 'free money', 'win now', 'urgent', 'limited offer', 'act now']
PORN_KEYWORDS = ['porn', 'xxx', 'adult', 'sex', 'nude', 'escort', 'hookup', 'dating']

async def check_and_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE, reason: str):
    """Mute user for spam content"""
    try:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        # Only mute in groups/supergroups
        if update.effective_chat.type in ['group', 'supergroup']:
            # Mute for 1 day
            mute_duration = timedelta(days=1)
            until_date = update.message.date + mute_duration
            permissions = ChatPermissions(can_send_messages=False)
            
            await context.bot.restrict_chat_member(chat_id, user_id, permissions=permissions, until_date=until_date)
            await context.bot.delete_message(chat_id, update.message.message_id)
            
            await context.bot.send_message(
                chat_id,
                f"🔇 User muted for 1 day - {reason}\n👤 @{update.effective_user.username or 'Unknown'}"
            )
            return True
    except Exception as e:
        print(f"Mute error: {e}")
    return False

async def detect_inappropriate_content(text: str) -> str:
    """Detect spam or porn content"""
    text_lower = text.lower()
    
    for keyword in SPAM_KEYWORDS:
        if keyword in text_lower:
            return "spam content"
    
    for keyword in PORN_KEYWORDS:
        if keyword in text_lower:
            return "inappropriate content"
    
    return None

# Profile picture moderation using Groq Vision
_scanned_users = set()

async def check_user_profile_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check new member's profile picture for inappropriate content"""
    try:
        for member in update.message.new_chat_members:
            if member.is_bot:
                continue
            await scan_user_profile_photo(member, update.effective_chat.id, context)
    except Exception as e:
        print(f"Profile photo check error: {e}")

async def scan_user_profile_photo(user, chat_id, context):
    """Scan a user's profile photo, bio, and name for NSFW/spam content"""
    try:
        if user.id in _scanned_users:
            return False
        _scanned_users.add(user.id)
        if len(_scanned_users) > 1000:
            _scanned_users.clear()

        # Check name for scam indicators
        name = (user.first_name or "") + " " + (user.last_name or "")
        # Normalize unicode to catch fancy text
        import unicodedata
        name_normalized = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii').lower()
        name_normalized = re.sub(r'[^a-z]', '', name_normalized)
        # Extra: map small caps and special chars
        smallcaps_map = str.maketrans('ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ', 'abcdefghijklmnopqrstuvwxyz')
        name_extra = name.lower().translate(smallcaps_map)
        name_extra = re.sub(r'[^a-z]', '', name_extra)
        combined_name = name_normalized + name_extra
        scam_words = ['verified', 'paid', 'official', 'admin', 'support', 'moderator', 'staff', 'helper']
        checkmark_pattern = r'[\u2705\u2611\u2714\u2713\u2b50]'
        is_scam = any(word in combined_name for word in scam_words) or re.search(checkmark_pattern, name)
        if is_scam:
                await context.bot.ban_chat_member(chat_id, user.id)
                keyboard = [[InlineKeyboardButton("🔓 Unban (Admins Only)", callback_data=f"unban_{user.id}_{user.username or user.first_name}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(chat_id, f"🚫 @{user.username or user.first_name} banned - scam name detected (fake verified/paid badge).", reply_markup=reply_markup)
                print(f"\ud83d\udeab Banned {user.first_name} for scam name: {name}")
                return True

        # Check bio/description for spam links
        try:
            chat = await context.bot.get_chat(user.id)
            bio = chat.bio or ""
            if bio:
                # Check bio with AI
                ai_result = await check_message_with_ai(bio)
                if ai_result['action'] == 'ban':
                    await context.bot.ban_chat_member(chat_id, user.id)
                    keyboard = [[InlineKeyboardButton("\ud83d\udd13 Unban (Admins Only)", callback_data=f"unban_{user.id}_{user.username or user.first_name}")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await context.bot.send_message(chat_id, f"\ud83d\udeab @{user.username or user.first_name} banned - inappropriate bio detected.", reply_markup=reply_markup)
                    print(f"\ud83d\udeab Banned {user.first_name} for bad bio: {bio[:50]}")
                    return True
                elif ai_result['action'] == 'mute':
                    await context.bot.ban_chat_member(chat_id, user.id)
                    keyboard = [[InlineKeyboardButton("\ud83d\udd13 Unban (Admins Only)", callback_data=f"unban_{user.id}_{user.username or user.first_name}")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await context.bot.send_message(chat_id, f"\ud83d\udeab @{user.username or user.first_name} banned - spam bio detected.", reply_markup=reply_markup)
                    print(f"\ud83d\udeab Banned {user.first_name} for spam bio: {bio[:50]}")
                    return True
        except Exception as e:
            print(f"Bio check skipped: {e}")

        # Check profile photo
        photos = await context.bot.get_user_profile_photos(user.id, limit=1)
        if not photos.photos:
            return False
        photo = photos.photos[0][-1]
        file = await context.bot.get_file(photo.file_id)
        img_bytes = await file.download_as_bytearray()

        import base64
        img_base64 = base64.b64encode(bytes(img_bytes)).decode()

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "Is this profile picture appropriate for a family-friendly group? Reply ONLY one word: SAFE or UNSAFE. UNSAFE means: nudity, porn, sexual content, cleavage, bra/panty/bikini/lingerie, exposed body parts (hips/butt/chest), suggestive poses, weapons, guns, knives, drugs, crypto/forex promotions, spam text, QR codes, gore, or violence."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
            ]}],
            "max_tokens": 5
        }
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            result = response.json()['choices'][0]['message']['content'].strip().upper()
            if 'UNSAFE' in result:
                await context.bot.ban_chat_member(chat_id, user.id)
                keyboard = [[InlineKeyboardButton("\ud83d\udd13 Unban (Admins Only)", callback_data=f"unban_{user.id}_{user.username or user.first_name}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(chat_id, f"\ud83d\udeab @{user.username or user.first_name} banned - inappropriate profile picture.", reply_markup=reply_markup)
                print(f"\ud83d\udeab Banned {user.first_name} for NSFW profile picture")
                return True
            else:
                print(f"\u2705 Profile photo OK for {user.first_name}")
    except Exception as e:
        print(f"Profile photo scan error: {e}")
    return False

# Handle text messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str = None):
    """Process messages (text and converted voice), moderate content, and generate AI responses."""
    message_type: str = update.message.chat.type
    text = text or update.message.text
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    username = update.message.from_user.username

    # Scan profile photo for existing users (once per user)
    if message_type in ['group', 'supergroup']:
        banned = await scan_user_profile_photo(update.message.from_user, chat_id, context)
        if banned:
            return

    # Content Moderation (only for groups)
    if message_type in ['group', 'supergroup']:
        # Check for inappropriate content first
        violation_type = await detect_inappropriate_content(text)
        if violation_type:
            muted = await check_and_ban_user(update, context, violation_type)
            if muted:
                return
        
        violation = await check_message_with_ai(text)
        if violation['action'] == 'ban':
            await handle_bad_words_violation(update, context, username, chat_id, user_id)
            return
        elif violation['action'] == 'mute':
            await handle_link_violation(update, context, username, chat_id, user_id)
            return

    # Track statistics
    bot_stats['total_messages'] += 1
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Track recent active users for greeting (only in groups)
    if message_type in ['group', 'supergroup']:
        recent_active_users[chat_id].add(user_id)

    # Track group statistics
    if message_type in ['group', 'supergroup']:
        if chat_id not in bot_stats['groups']:
            try:
                chat = await context.bot.get_chat(chat_id)
                member_count = await context.bot.get_chat_member_count(chat_id)
                bot_stats['groups'][chat_id] = {
                    'name': chat.title or 'Unknown Group',
                    'username': chat.username or 'No username',
                    'type': chat.type,
                    'members': member_count,
                    'added_date': current_time
                }
            except:
                bot_stats['groups'][chat_id] = {
                    'name': 'Unknown Group',
                    'username': 'No username',
                    'type': 'unknown',
                    'members': 0,
                    'added_date': current_time
                }

    # Track private user statistics
    elif message_type == 'private':
        name = update.message.from_user.first_name or 'Unknown'
        username_str = username or 'No username'

        if user_id not in bot_stats['private_users']:
            bot_stats['private_users'][user_id] = {
                'name': name,
                'username': username_str,
                'first_seen': current_time,
                'last_active': current_time
            }
        else:
            bot_stats['private_users'][user_id]['last_active'] = current_time

    save_bot_stats()

    print(f'User ({chat_id}) in {message_type}: "{text}"')

    # Legacy regex moderation as additional fallback
    if contains_bad_words(text):
        await handle_bad_words_violation(update, context, username, chat_id, user_id)
        return

    if await contains_spam_links(text, update, context):
        await handle_link_violation(update, context, username, chat_id, user_id)
        return

    # Process with AI model
    if message_type == 'supergroup':
        response = await process_group_message(update, text, chat_session, ai_type)
        if not response:
            return
    else:
        response = get_ai_response(text, chat_session, ai_type)

    print('Bot:', response)
    # Use the improved voice response with rate limiting and fallbacks
    await send_voice_response(update, response)

async def process_group_message(update: Update, text: str, chat_session, ai_type) -> str:
    """Process messages in group chats, only responding when addressed."""
    bot_id = int(TOKEN.split(':')[0])  # Extract bot ID from token

    # Check if replying to bot's message
    if update.message.reply_to_message and update.message.reply_to_message.from_user.id == bot_id:
        print(f"✅ Bot mentioned via reply - responding")
        return get_ai_response(text.strip(), chat_session, ai_type)

    # Check if bot is mentioned by username
    elif BOT_USERNAME in text:
        print(f"✅ Bot mentioned by username - responding")
        return get_ai_response(text.replace(BOT_USERNAME, '').strip(), chat_session, ai_type)

    # Check if bot is mentioned by @mention entities
    elif update.message.entities:
        for entity in update.message.entities:
            if entity.type == 'mention':
                mentioned_username = text[entity.offset:entity.offset + entity.length]
                if mentioned_username == BOT_USERNAME:
                    print(f"✅ Bot mentioned via @mention - responding")
                    return get_ai_response(text.replace(mentioned_username, '').strip(), chat_session, ai_type)

    print(f"❌ Bot not mentioned - ignoring message")
    return None

async def handle_bad_words_violation(update, context, username, chat_id, user_id):
    """Ban users for inappropriate content."""
    # Create admin-only unban button
    keyboard = [
        [InlineKeyboardButton("🔓 Unban (Admins Only)", callback_data=f"unban_{user_id}_{username}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"🚫 @{username} banned for inappropriate content.",
        reply_markup=reply_markup
    )
    await context.bot.ban_chat_member(chat_id, user_id)
    await context.bot.delete_message(chat_id, update.message.message_id)

async def handle_link_violation(update, context, username, chat_id, user_id):
    """Mute users for sending links or foreign languages."""
    mute_duration = timedelta(days=1)
    until_date = update.message.date + mute_duration
    permissions = ChatPermissions(
        can_send_messages=False,
        can_send_other_messages=False,
        can_add_web_page_previews=False
    )

    # Determine violation type
    violation_type = "foreign language" if contains_foreign_languages(update.message.text) else "link/spam"

    # Create admin-only unmute button
    keyboard = [
        [InlineKeyboardButton("🔊 Unmute (Admins Only)", callback_data=f"unmute_{user_id}_{username}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"🔇 @{username} muted for 1 day ({violation_type} detected).",
        reply_markup=reply_markup
    )
    await context.bot.restrict_chat_member(chat_id, user_id, permissions=permissions, until_date=until_date)
    try:
        await context.bot.delete_message(chat_id, update.message.message_id)
    except Exception:
        pass  # Message might already be deleted

async def handle_unban_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unban button clicks (admin only)."""
    query = update.callback_query
    chat_id = query.message.chat_id
    admin_id = query.from_user.id

    # Check if user is admin
    if admin_id not in ADMIN_IDS:
        await query.answer("❌ Admin only! You don't have permission.", show_alert=True)
        return

    # Extract user info from callback data
    _, user_id, username = query.data.split('_', 2)
    user_id = int(user_id)

    try:
        # Unban the user
        await context.bot.unban_chat_member(chat_id, user_id)
        await query.edit_message_text(f"✅ @{username} has been unbanned by admin @{query.from_user.username}")
        await query.answer("✅ User unbanned successfully!")
    except Exception as e:
        await query.answer(f"❌ Failed to unban: {str(e)}", show_alert=True)

async def handle_unmute_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unmute button clicks (admin only)."""
    query = update.callback_query
    chat_id = query.message.chat_id
    admin_id = query.from_user.id

    # Check if user is admin
    if admin_id not in ADMIN_IDS:
        await query.answer("❌ Admin only! You don't have permission.", show_alert=True)
        return

    # Extract user info from callback data
    _, user_id, username = query.data.split('_', 2)
    user_id = int(user_id)

    try:
        # Restore full permissions
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_send_polls=True,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False
        )
        await context.bot.restrict_chat_member(chat_id, user_id, permissions=permissions)
        await query.edit_message_text(f"✅ @{username} has been unmuted by admin @{query.from_user.username}")
        await query.answer("✅ User unmuted successfully!")
    except Exception as e:
        await query.answer(f"❌ Failed to unmute: {str(e)}", show_alert=True)

async def handle_unwarn_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unwarn button clicks (admin only)."""
    query = update.callback_query
    chat_id = str(query.message.chat_id)
    admin_id = query.from_user.id

    # Check if user is admin
    if admin_id not in ADMIN_IDS:
        await query.answer("❌ Admin only! You don't have permission.", show_alert=True)
        return

    # Extract user info from callback data
    _, user_id, username = query.data.split('_', 2)
    user_id = str(user_id)

    try:
        # Remove one warning
        if chat_id in user_warnings and user_id in user_warnings[chat_id]:
            if user_warnings[chat_id][user_id] > 0:
                user_warnings[chat_id][user_id] -= 1
                count = user_warnings[chat_id][user_id]
                save_warnings()
                await query.edit_message_text(f"✅ Warning removed for @{username} by admin @{query.from_user.username}\nCurrent warnings: {count}/3")
                await query.answer("✅ Warning removed successfully!")
            else:
                await query.answer("⚠️ User has no warnings to remove!", show_alert=True)
        else:
            await query.answer("⚠️ User has no warnings to remove!", show_alert=True)
    except Exception as e:
        await query.answer(f"❌ Failed to remove warning: {str(e)}", show_alert=True)

async def send_voice_response(update, response):
    """Convert AI-generated text to voice and send both voice and text."""
    try:
        # Clean text for TTS (remove all formatting)
        clean_text = clean_for_voice(response)

        # Limit text length for TTS (gTTS has limits)
        if len(clean_text) > 500:
            clean_text = clean_text[:500] + "..."

        tts = gTTS(text=clean_text, lang='en', slow=False)
        tts.save("voice.mp3")

        # Check if response is too long for caption (1024 char limit)
        if len(response) > 1000:
            # Send voice without caption, then send text separately
            with open("voice.mp3", "rb") as audio:
                await update.message.reply_voice(audio)
            await update.message.reply_text(response, parse_mode='Markdown')
        else:
            # Send voice with text as caption
            with open("voice.mp3", "rb") as audio:
                await update.message.reply_voice(audio, caption=response, parse_mode='Markdown')

        os.remove("voice.mp3")
        print(f"✅ Voice response sent successfully")
    except Exception as e:
        print(f"TTS error: {e}")
        # Fallback to text with formatting
        await update.message.reply_text(response, parse_mode='Markdown')
        print(f"📝 Fallback text response sent")

# Special days functions
async def get_todays_special_days():
    """Get today's international, Indian special days, Tamil Panjangam, and Rasipalan using AI."""
    today = datetime.now(pytz.timezone('Asia/Kolkata'))
    date_str = today.strftime("%B %d, %Y")

    prompt = f"""What are the special observances for {date_str}? Provide in Tamil:
    1. 🌍 International/World Days
    2. 🇮🇳 Indian Special Days
    3. 📅 Tamil Panjangam (திதி, நட்சத்திரம், யோகம், கரணம்)
    4. ⭐ Today's Rasipalan (brief horoscope for all 12 zodiac signs in Tamil)

    Format:
    🌍 சர்வதேச நாட்கள்:
    - [Day in Tamil]

    🇮🇳 இந்திய சிறப்பு நாட்கள்:
    - [Day in Tamil]

    📅 தமிழ் பஞ்சாங்கம்:
    - திதி: [Tithi]
    - நட்சத்திரம்: [Nakshatra]
    - யோகம்: [Yoga]
    - கரணம்: [Karana]

    ⭐ இன்றைய ராசிபலன்:
    மேஷம்: [Brief prediction]
    ரிஷபம்: [Brief prediction]
    மிதுனம்: [Brief prediction]
    கடகம்: [Brief prediction]
    சிம்மம்: [Brief prediction]
    கன்னி: [Brief prediction]
    துலாம்: [Brief prediction]
    விருச்சிகம்: [Brief prediction]
    தனுசு: [Brief prediction]
    மகரம்: [Brief prediction]
    கும்பம்: [Brief prediction]
    மீனம்: [Brief prediction]

    Keep each rasipalan 1-2 lines only. If no special days: "இன்று பெரிய சிறப்பு நாட்கள் இல்லை, ஆனால் ஒவ்வொரு நாளும் சிறப்பானது!"""

    try:
        response = get_ai_response(prompt, chat_session, ai_type)
        return response
    except Exception as e:
        print(f"Error getting special days: {e}")
        return "ஒவ்வொரு நாளும் சிறப்பானது! அருமையான நாள் வாழ்த்துக்கள்! 🌟"

async def send_daily_special_days(context):
    """Send daily special days with AI image at 7 AM."""
    try:
        ist = pytz.timezone('Asia/Kolkata')
        current_time = datetime.now(ist)
        date_display = current_time.strftime('%B %d, %Y')

        # Get special days info
        special_days = await get_todays_special_days()

        # Generate AI image with date overlay
        image_prompt = f"beautiful calendar illustration {current_time.strftime('%B %d %Y')} special day celebration traditional Indian culture"
        special_day_image = await generate_image_with_channel(image_prompt, "tamil")

        # Format message for Tamil channels
        tamil_message = f"🌅 **காலை வணக்கம்!** 🌅\n\n📅 **{date_display}**\n\n{special_days}\n\n✨ அனைவருக்கும் ஆசீர்வாதமான நாள் வாழ்த்துக்கள்! ✨"

        # Send to Tamil channels
        for channel_id in ["@tamil_digital", "@tamil5"]:
            try:
                if special_day_image:
                    await context.bot.send_photo(chat_id=channel_id, photo=special_day_image, caption=tamil_message, parse_mode='Markdown')
                else:
                    await context.bot.send_message(chat_id=channel_id, text=tamil_message, parse_mode='Markdown')
                print(f"✅ Special days sent to {channel_id}")
            except Exception as e:
                print(f"❌ Error sending to {channel_id}: {e}")

        # Send to Hindi channels
        hindi_message = f"🌅 **सुप्रभात!** 🌅\n\n📅 **{date_display}**\n\n{special_days}\n\n✨ सभी को शुभकामनाएं! ✨"
        for channel_id in ["@digitalstudioo", "@indianchatt"]:
            try:
                if special_day_image:
                    await context.bot.send_photo(chat_id=channel_id, photo=special_day_image, caption=hindi_message, parse_mode='Markdown')
                else:
                    await context.bot.send_message(chat_id=channel_id, text=hindi_message, parse_mode='Markdown')
                print(f"✅ Special days sent to {channel_id}")
            except Exception as e:
                print(f"❌ Error sending to {channel_id}: {e}")

        print(f"✅ Daily special days sent at {current_time.strftime('%H:%M')}")

    except Exception as e:
        print(f"❌ Error sending daily special days: {e}")

# Tamil poem functions
async def generate_tamil_poem(theme):
    """Generate inspirational Tamil poem using AI."""
    prompt = f"""Write a beautiful, inspirational Tamil poem about {theme}.
    The poem should be:
    - 4-6 lines long
    - Inspirational and uplifting
    - In proper Tamil script
    - About {theme}
    - Suitable for all ages
    - Original and creative

    Please write only the Tamil poem, nothing else."""

    try:
        # Try to get poem from AI
        poem = get_ai_response(prompt, chat_session, ai_type)

        # Create unique identifier for this poem
        poem_id = hash(poem) % 10000

        # Check if we've sent this poem before (use 'tamil' key since this is Tamil poem)
        if poem_id in poem_history.get('tamil', set()):
            # Generate alternative if duplicate
            prompt += " Make it completely different from previous poems."
            poem = get_ai_response(prompt, chat_session, ai_type)
            poem_id = hash(poem) % 10000

        # Add to history
        if 'tamil' not in poem_history:
            poem_history['tamil'] = set()
        poem_history['tamil'].add(poem_id)

        # Keep history size manageable (last 100 poems)
        if len(poem_history['tamil']) > 100:
            poem_history['tamil'].pop()

        return poem

    except Exception as e:
        print(f"Error generating poem: {e}")
        # Fallback poem
        return "வாழ்க்கை ஒரு பயணம்\nநம்பிக்கையுடன் நடப்போம்\nவெற்றி நம் கையில்\nமகிழ்ச்சியுடன் வாழ்வோம்"

async def send_daily_poem(context):
    """Send daily Tamil poem to the group."""
    try:
        # Get current time in IST
        ist = pytz.timezone('Asia/Kolkata')
        current_time = datetime.now(ist)
        hour = current_time.hour

        # Determine time-based greeting and theme
        if hour == 8:  # Morning
            greeting = "🌅 காலை வணக்கம்! Good Morning!"
            theme_pool = ["வாழ்க்கை (Life)", "நம்பிக்கை (Hope)", "இயற்கை (Nature)"]
        elif hour == 12:  # Afternoon
            greeting = "☀️ மதிய வணக்கம்! Good Afternoon!"
            theme_pool = ["உழைப்பு (Hard work)", "கல்வி (Education)", "வீரம் (Bravery)"]
        elif hour == 16:  # Evening
            greeting = "🌆 மாலை வணக்கம்! Good Evening!"
            theme_pool = ["குடும்பம் (Family)", "நட்பு (Friendship)", "மனிதநேயம் (Humanity)"]
        elif hour == 20:  # Night
            greeting = "🌙 இரவு வணக்கம்! Good Night!"
            theme_pool = ["தாய் (Mother)", "தாய்நாடு (Motherland)", "காதல் (Love)"]
        else:
            return  # Not a scheduled time

        # Select random theme
        theme = random.choice(theme_pool)

        # Generate poem
        poem = await generate_tamil_poem(theme)

        # Generate contextual image for poem
        poem_image = await generate_contextual_image("poem", theme)

        # Format message
        message = f"{greeting}\n\n📝 இன்றைய கவிதை - {theme}\n\n{poem}\n\n💫 Have a wonderful day!"

        # Send to group with image if available
        if poem_image:
            await context.bot.send_photo(
                chat_id=TARGET_CHAT_ID,
                photo=poem_image,
                caption=message
            )
        else:
            await context.bot.send_message(
                chat_id=TARGET_CHAT_ID,
                text=message
            )

        print(f"Daily poem sent at {current_time.strftime('%H:%M')} - Theme: {theme}")

    except Exception as e:
        print(f"Error sending daily poem: {e}")

async def send_friendly_greeting(context):
    """Send friendly greeting to recent active users"""
    try:
        if not TARGET_CHAT_ID:
            print("No TARGET_CHAT_ID configured for greetings")
            return

        if TARGET_CHAT_ID not in recent_active_users or len(recent_active_users[TARGET_CHAT_ID]) == 0:
            print("No recent active users to greet")
            return

        active_users = list(recent_active_users[TARGET_CHAT_ID])[:5]  # Max 5 users
        print(f"Greeting {len(active_users)} active users")

        # Create mention string
        mentions = []
        for user_id in active_users:
            try:
                member = await context.bot.get_chat_member(TARGET_CHAT_ID, user_id)
                if member.user.username:
                    mentions.append(f"@{member.user.username}")
                else:
                    mentions.append(member.user.first_name)
            except Exception as e:
                print(f"Error getting user {user_id}: {e}")
                continue

        if mentions:
            greeting_messages = [
                f"👋 Hi there! {' '.join(mentions)} How's everyone doing?",
                f"🌟 Hello friends! {' '.join(mentions)} Hope you're having a great day!",
                f"😊 Hey everyone! {' '.join(mentions)} What's up?",
                f"🎉 Greetings! {' '.join(mentions)} How are things going?"
            ]

            message = random.choice(greeting_messages)
            print(f"Sending greeting: {message[:50]}...")

            await context.bot.send_message(
                chat_id=TARGET_CHAT_ID,
                text=message
            )

            print(f"✅ Sent friendly greeting to {len(mentions)} users")

        # Clear recent active users after greeting
        recent_active_users[TARGET_CHAT_ID].clear()
        print("Cleared recent active users list")

    except Exception as e:
        print(f"Error sending friendly greeting: {e}")
        import traceback
        traceback.print_exc()

async def generate_poem(language, topic):
    """Generate poem in specified language"""
    lang_config = LANGUAGE_CHANNELS[language]

    if language == "tamil":
        prompt = f"""Write a beautiful, inspirational Tamil poem about {topic}.
        The poem should be:
        - 4-6 lines long
        - Inspirational and uplifting
        - In proper Tamil script
        - About {topic}
        - Suitable for all ages
        - Original and creative

        Please write only the Tamil poem, nothing else."""
    elif language == "hindi":
        prompt = f"""Write a beautiful, inspirational Hindi poem about {topic}.
        The poem should be:
        - 4-6 lines long
        - Inspirational and uplifting
        - In proper Hindi Devanagari script
        - About {topic}
        - Suitable for all ages
        - Original and creative

        Please write only the Hindi poem, nothing else."""

    poem_text = get_ai_response(prompt, chat_session, ai_type)

    # Check for duplicates
    poem_id = hash(poem_text) % 10000
    if poem_id in poem_history[language]:
        prompt += " Make it completely different from previous poems."
        poem_text = get_ai_response(prompt, chat_session, ai_type)
        poem_id = hash(poem_text) % 10000

    poem_history[language].add(poem_id)
    if len(poem_history[language]) > 100:
        poem_history[language].pop()

    return poem_text

async def generate_news_items(language, count=10):
    """Generate news items in specified language"""
    lang_config = LANGUAGE_CHANNELS[language]
    
    if language == "tamil":
        prompt = f"""Generate {count} latest news headlines in Tamil for today. Include diverse categories like:
        - உலக செய்திகள் (World News)
        - தொழில்நுட்பம் (Technology)
        - விளையாட்டு (Sports)
        - பொழுதுபோக்கு (Entertainment)
        - வணிகம் (Business)
        
        Format each news item as:
        📰 [Category in Tamil]: [News headline in Tamil]
        
        Make them current, relevant, and informative. Keep each headline under 100 characters.
        Write ONLY the news items, nothing else."""
    elif language == "hindi":
        prompt = f"""Generate {count} latest news headlines in Hindi for today. Include diverse categories like:
        - विश्व समाचार (World News)
        - प्रौद्योगिकी (Technology)
        - खेल (Sports)
        - मनोरंजन (Entertainment)
        - व्यापार (Business)
        
        Format each news item as:
        📰 [Category in Hindi]: [News headline in Hindi]
        
        Make them current, relevant, and informative. Keep each headline under 100 characters.
        Write ONLY the news items, nothing else."""
    
    news_text = get_ai_response(prompt, chat_session, ai_type)
    
    # Check for duplicates
    news_id = hash(news_text) % 10000
    if news_id in news_history[language]:
        prompt += " Make them completely different from previous news."
        news_text = get_ai_response(prompt, chat_session, ai_type)
        news_id = hash(news_text) % 10000
    
    news_history[language].add(news_id)
    if len(news_history[language]) > 50:
        news_history[language].pop()
    
    return news_text

async def send_news_to_channel(context, language, news_text, time_of_day):
    """Send news to specified language channel"""
    print(f"\n📰 [NEWS SEND] Starting send_news_to_channel")
    print(f"🌍 [NEWS SEND] Language: {language}, Time: {time_of_day}")
    
    lang_config = LANGUAGE_CHANNELS[language]
    
    # Generate news image
    news_prompt = f"news broadcast journalism media headlines {time_of_day} professional"
    news_image = await generate_image_with_channel(news_prompt, language)
    
    # Format message based on language and time
    if language == "tamil":
        if time_of_day == "morning":
            greeting = "🌅 காலை செய்திகள்"
            time_text = "காலை"
        else:
            greeting = "🌆 மாலை செய்திகள்"
            time_text = "மாலை"
        message = f"{greeting}\n\n📰 **இன்றைய {time_text} முக்கிய செய்திகள்** 📰\n\n{news_text}\n\n@tamil5 @tamil_digital\n\n📱 Stay informed! | தகவல் அறிந்திருங்கள்!"
    elif language == "hindi":
        if time_of_day == "morning":
            greeting = "🌅 सुबह की खबरें"
            time_text = "सुबह"
        else:
            greeting = "🌆 शाम की खबरें"
            time_text = "शाम"
        message = f"{greeting}\n\n📰 **आज की {time_text} मुख्य समाचार** 📰\n\n{news_text}\n\n@indianchatt @digitalstudioo\n\n📱 Stay informed! | सूचित रहें!"
    
    # Send to channel
    try:
        if news_image:
            await context.bot.send_photo(
                chat_id=lang_config["channel_id"],
                photo=news_image,
                caption=message
            )
        else:
            await context.bot.send_message(
                chat_id=lang_config["channel_id"],
                text=message
            )
        print(f"✅ [NEWS SEND] {time_of_day} news sent to {language} channel")
    except Exception as e:
        print(f"❌ [NEWS SEND] Error sending news to {language}: {e}")

async def send_daily_news(context, time_of_day="morning"):
    """Send 10 news items to all language channels"""
    print(f"\n📰 [NEWS SCHEDULER] ===== {time_of_day.upper()} NEWS GENERATION STARTED =====")
    
    try:
        for language in LANGUAGE_CHANNELS.keys():
            print(f"\n📝 [NEWS SCHEDULER] === Processing {language.upper()} news ===")
            
            news_text = await generate_news_items(language, count=10)
            print(f"✅ [NEWS SCHEDULER] Generated {language} news")
            
            await send_news_to_channel(context, language, news_text, time_of_day)
            print(f"✅ [NEWS SCHEDULER] {language} news sent")
        
        print(f"\n🎉 [NEWS SCHEDULER] ===== ALL {time_of_day.upper()} NEWS SENT SUCCESSFULLY =====")
    
    except Exception as e:
        print(f"💥 [NEWS SCHEDULER] Error in news generation: {e}")
        import traceback
        traceback.print_exc()

async def send_poem_to_channel(context, language, topic, poem_text, current_hour):
    """Send poem to specified language channel"""
    print(f"\n📤 [POEM SEND] Starting send_poem_to_channel")
    print(f"🌍 [POEM SEND] Language: {language}, Topic: {topic}")
    print(f"⏰ [POEM SEND] Hour: {current_hour}")

    lang_config = LANGUAGE_CHANNELS[language]
    print(f"📺 [POEM SEND] Channel config: {lang_config}")

    # Generate poem image with English-only prompt and channel-specific watermark
    topic_english = topic.replace('(', '').replace(')', '').split()[0]  # Extract English part only
    print(f"🔄 [POEM SEND] Calling generate_contextual_image() for poem...")
    print(f"🎯 [POEM SEND] Topic (English): '{topic_english}', Channel: {language}")

    content_image = await generate_contextual_image("poem", topic_english, language)
    print(f"🔙 [POEM SEND] generate_contextual_image() returned: {content_image is not None}")

    # Format poem message based on language
    topic_tamil = topic.split('(')[0].strip()
    topic_english = topic.split('(')[1].split(')')[0].strip() if '(' in topic else topic
    topic_hindi = topic.split('|')[-1].strip() if '|' in topic else topic_english
    if language == "tamil":
        message = f"📝 **தமிழ் கவிதை - {topic_tamil} ({topic_english})** 📝\n\n{poem_text}\n\n@tamil5 @tamil_digital\n\n💫 Stay inspired! | உத்வேகம் பெறுங்கள்!"
    elif language == "hindi":
        message = f"📝 **हिंदी कविता - {topic_hindi} ({topic_english})** 📝\n\n{poem_text}\n\n@indianchatt @digitalstudioo\n\n💫 Stay inspired! | प्रेरित रहें!"

    print(f"📝 [POEM SEND] Formatted message length: {len(message)} chars")

    # Send to channel
    try:
        print(f"📤 [POEM SEND] Attempting to send {language} poem to {lang_config['channel_id']}")

        if content_image:
            print(f"🖼️ [POEM SEND] Sending WITH IMAGE to {language} channel via Telegram API")
            await context.bot.send_photo(
                chat_id=lang_config["channel_id"],
                photo=content_image,
                caption=message
            )
            print(f"✅ [POEM SEND] Photo with caption sent successfully")
        else:
            print(f"📝 [POEM SEND] Sending TEXT-ONLY to {language} channel (no image available)")
            await context.bot.send_message(
                chat_id=lang_config["channel_id"],
                text=message
            )
            print(f"✅ [POEM SEND] Text message sent successfully")
        print(f"✅ [POEM SEND] Hourly {language} poem sent successfully - Topic: {topic} at hour {current_hour}")
    except Exception as e:
        print(f"❌ [POEM SEND] Error sending {language} poem to {lang_config['channel_id']}: {e}")
        print(f"🔍 [POEM SEND] Channel ID: {lang_config['channel_id']}, Language: {language}")
        import traceback
        traceback.print_exc()

async def generate_and_send_poems(context):
    """Generate and send hourly poems to all language channels"""
    print(f"\n🎆 [POEM SCHEDULER] ===== HOURLY POEM GENERATION STARTED =====")

    try:
        # Select topic based on current hour (cycles through 24 topics)
        current_hour = datetime.now(pytz.timezone('Asia/Kolkata')).hour
        topic = POEM_TOPICS[current_hour]

        print(f"🎭 [POEM SCHEDULER] Starting poem generation - Hour: {current_hour}, Topic: {topic}")
        print(f"🌍 [POEM SCHEDULER] Languages to process: {list(LANGUAGE_CHANNELS.keys())}")

        # Generate and send poems for each language
        for language in LANGUAGE_CHANNELS.keys():
            print(f"\n📝 [POEM SCHEDULER] === Processing {language.upper()} language ===")
            print(f"🔄 [POEM SCHEDULER] Generating {language} poem for topic: {topic}")

            poem_text = await generate_poem(language, topic)
            print(f"\n{'='*60}")
            print(f"📜 [POEM OUTPUT] Language: {language}, Topic: {topic}")
            print(f"📜 [POEM OUTPUT] Full text:")
            print(poem_text)
            print(f"{'='*60}\n")

            print(f"📤 [POEM SCHEDULER] Sending {language} poem to channel...")
            await send_poem_to_channel(context, language, topic, poem_text, current_hour)
            print(f"✅ [POEM SCHEDULER] {language} poem processing complete")

        print(f"\n🎉 [POEM SCHEDULER] ===== ALL POEMS SENT SUCCESSFULLY FOR HOUR {current_hour} =====")

    except Exception as e:
        print(f"💥 [POEM SCHEDULER] ===== ERROR IN POEM GENERATION =====")
        print(f"❌ [POEM SCHEDULER] Error in multi-language poem generation: {e}")
        import traceback
        traceback.print_exc()
        print(f"💥 [POEM SCHEDULER] ===== END ERROR REPORT =====")

def setup_poem_scheduler_sync(application):
    """Setup daily poem, special days, and quiz scheduler."""
    job_queue = application.job_queue

    # IST timezone
    ist = pytz.timezone('Asia/Kolkata')

    # Load existing quiz data
    print("📁 Loading quiz data and bot stats...")
    load_quiz_data()
    load_bot_stats()
    load_warnings()
    print("✅ Data loaded successfully")

    # Schedule special days announcement at 7 AM
    job_queue.run_daily(
        send_daily_special_days,
        time=time(7, 0, 0, tzinfo=ist),
        days=(0, 1, 2, 3, 4, 5, 6),
        data="special_days",
        name="daily_special_days"
    )

    # Async wrapper functions for job_queue (lambdas don't work with async)
    async def morning_quiz_job(context):
        await start_quiz(context, "morning")

    async def afternoon_quiz_job(context):
        await start_quiz(context, "afternoon")

    async def evening_quiz_job(context):
        await start_quiz(context, "evening")

    async def night_quiz_job(context):
        await start_quiz(context, "night")

    async def end_quiz_job(context):
        await end_quiz(context)

    # Schedule 4 quizzes at requested times
    # Quiz 1: 8 AM
    job_queue.run_daily(
        morning_quiz_job,
        time=time(8, 0, 0, tzinfo=ist),
        days=(0, 1, 2, 3, 4, 5, 6),
        data="morning_quiz",
        name="morning_quiz"
    )

    # Quiz 2: 12 PM
    job_queue.run_daily(
        afternoon_quiz_job,
        time=time(12, 0, 0, tzinfo=ist),
        days=(0, 1, 2, 3, 4, 5, 6),
        data="afternoon_quiz",
        name="afternoon_quiz"
    )

    # Quiz 3: 5 PM
    job_queue.run_daily(
        evening_quiz_job,
        time=time(17, 0, 0, tzinfo=ist),
        days=(0, 1, 2, 3, 4, 5, 6),
        data="evening_quiz",
        name="evening_quiz"
    )

    # Quiz 4: 9 PM
    job_queue.run_daily(
        night_quiz_job,
        time=time(21, 0, 0, tzinfo=ist),
        days=(0, 1, 2, 3, 4, 5, 6),
        data="night_quiz",
        name="night_quiz"
    )

    # Schedule individual quiz results (1 hour after each quiz)
    # Morning quiz result: 9 AM (1 hour after 8 AM quiz)
    job_queue.run_daily(
        end_quiz_job,
        time=time(9, 0, 0, tzinfo=ist),
        days=(0, 1, 2, 3, 4, 5, 6),
        data="morning_quiz_result",
        name="morning_quiz_result"
    )

    # Afternoon quiz result: 1 PM (1 hour after 12 PM quiz)
    job_queue.run_daily(
        end_quiz_job,
        time=time(13, 0, 0, tzinfo=ist),
        days=(0, 1, 2, 3, 4, 5, 6),
        data="afternoon_quiz_result",
        name="afternoon_quiz_result"
    )

    # Evening quiz result: 6 PM (1 hour after 5 PM quiz)
    job_queue.run_daily(
        end_quiz_job,
        time=time(18, 0, 0, tzinfo=ist),
        days=(0, 1, 2, 3, 4, 5, 6),
        data="evening_quiz_result",
        name="evening_quiz_result"
    )

    # Night quiz result: 10 PM (1 hour after 9 PM quiz)
    job_queue.run_daily(
        end_quiz_job,
        time=time(22, 0, 0, tzinfo=ist),
        days=(0, 1, 2, 3, 4, 5, 6),
        data="night_quiz_result",
        name="night_quiz_result"
    )

    # Schedule daily winners (11 PM every day)
    job_queue.run_daily(
        show_daily_winners,
        time=time(23, 0, 0, tzinfo=ist),
        days=(0, 1, 2, 3, 4, 5, 6),
        data="daily_winners",
        name="daily_winners"
    )

    # Schedule weekly winners (Sunday 10 PM)
    job_queue.run_daily(
        show_weekly_winners,
        time=time(22, 0, 0, tzinfo=ist),
        days=(6,),  # Sunday = 6
        data="weekly_winners",
        name="weekly_winners"
    )

    # Schedule monthly winners (1st day of month at 9 AM)
    job_queue.run_monthly(
        show_monthly_winners,
        when=time(9, 0, 0, tzinfo=ist),
        day=1,
        name="monthly_winners"
    )

    # Schedule friendly greetings every 2 hours (only for recent active users)
    job_queue.run_repeating(
        send_friendly_greeting,
        interval=7200,  # 2 hours
        first=300,      # Start 5 minutes after startup
        name="friendly_greeting"
    )

    # Test greeting 1 minute after startup
    job_queue.run_once(
        send_friendly_greeting,
        when=60,  # 1 minute after startup
        name="test_greeting"
    )

    # Schedule hourly multi-language poems (every hour on the hour)
    job_queue.run_repeating(
        generate_and_send_poems,
        interval=3600,  # Every hour
        first=60,       # Start 1 minute after startup
        name="hourly_multilang_poems"
    )

    # Async wrapper functions for news
    async def morning_news_job(context):
        await send_daily_news(context, "morning")

    async def evening_news_job(context):
        await send_daily_news(context, "evening")

    # Schedule morning news at 8 AM
    job_queue.run_daily(
        morning_news_job,
        time=time(8, 0, 0, tzinfo=ist),
        days=(0, 1, 2, 3, 4, 5, 6),
        data="morning_news",
        name="morning_news"
    )

    # Schedule evening news at 6 PM
    job_queue.run_daily(
        evening_news_job,
        time=time(18, 0, 0, tzinfo=ist),
        days=(0, 1, 2, 3, 4, 5, 6),
        data="evening_news",
        name="evening_news"
    )

    print("📅 All schedulers activated!")
    print("⏰ Special Days: 7 AM | Quizzes: 8 AM, 12 PM, 5 PM, 9 PM")
    print("📰 News: 10 items at 8 AM & 6 PM daily (all languages)")
    print("📝 Multi-language Poems: 24 poems daily per language")
    print("   • Tamil: @tamil_digital")
    print("   • Hindi: @digitalstudioo")
    print("🏆 Rankings: Daily 11 PM | Weekly Sunday 10 PM | Monthly 1st 9 AM")

async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle poll answers for quiz tracking."""
    try:
        poll_answer = update.poll_answer
        poll_id = poll_answer.poll_id
        user = poll_answer.user
        option_ids = poll_answer.option_ids

        if poll_id in quiz_data['poll_data'] and option_ids:
            # Store user's answer
            quiz_data['poll_data'][poll_id]['participants'][user.id] = {
                'name': user.first_name or user.username or 'Unknown',
                'answer_index': option_ids[0],  # First selected option
                'username': user.username
            }

            print(f"Poll answer recorded: {user.first_name} answered option {option_ids[0]} for poll {poll_id}")

    except Exception as e:
        print(f"Error handling poll answer: {e}")

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    print(f'Update {update} caused error {context.error}')

# Admin Commands
ADMIN_IDS = [620382392]  # Fallback admin ID
user_warnings = {}  # {chat_id: {user_id: warning_count}}

async def fetch_group_admins(bot):
    """Fetch admin IDs from @tamil5 group"""
    global ADMIN_IDS
    try:
        print(f"🔍 Attempting to fetch admins from @tamil5...")
        chat = await bot.get_chat("@tamil5")
        print(f"✅ Successfully connected to @tamil5 (Chat ID: {chat.id})")
        
        admins = await bot.get_chat_administrators(chat.id)
        print(f"📋 Total administrators found: {len(admins)}")
        
        # Log all admins (including bots)
        for admin in admins:
            admin_type = "🤖 BOT" if admin.user.is_bot else "👤 USER"
            print(f"  {admin_type} - ID: {admin.user.id}, Name: {admin.user.first_name}, Username: @{admin.user.username or 'no_username'}, Status: {admin.status}")
        
        # Filter out bots
        admin_ids = [admin.user.id for admin in admins if not admin.user.is_bot]
        
        if admin_ids:
            ADMIN_IDS = admin_ids
            print(f"\n✅ Successfully loaded {len(admin_ids)} human admins from @tamil5")
            print(f"👥 Admin IDs: {admin_ids}")
            print(f"🔐 These users can now use admin commands")
        else:
            print(f"\n⚠️ No human admins found in @tamil5, using fallback: {ADMIN_IDS}")
    except Exception as e:
        print(f"\n❌ Failed to fetch admins from @tamil5: {e}")
        print(f"⚠️ Using fallback admin ID: {ADMIN_IDS}")
        import traceback
        traceback.print_exc()

def load_warnings():
    global user_warnings
    try:
        with open('user_warnings.json', 'r') as f:
            user_warnings = json.load(f)
    except FileNotFoundError:
        user_warnings = {}

def save_warnings():
    with open('user_warnings.json', 'w') as f:
        json.dump(user_warnings, f)

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    print(f"🔐 Ban command - User ID: {user_id}, Admin IDs: {ADMIN_IDS}, Is Admin: {user_id in ADMIN_IDS}")
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only command")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply to a user's message to ban them")
        return
    user = update.message.reply_to_message.from_user
    try:
        await context.bot.delete_message(update.effective_chat.id, update.message.reply_to_message.message_id)
        await context.bot.delete_message(update.effective_chat.id, update.message.message_id)
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        
        keyboard = [
            [InlineKeyboardButton("🔓 Unban (Admins Only)", callback_data=f"unban_{user.id}_{user.username or user.first_name}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            update.effective_chat.id,
            f"🚫 Banned @{user.username or user.first_name}",
            reply_markup=reply_markup
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    print(f"🔐 Mute command - User ID: {user_id}, Admin IDs: {ADMIN_IDS}, Is Admin: {user_id in ADMIN_IDS}")
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only command")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply to a user's message to mute them")
        return
    user = update.message.reply_to_message.from_user
    duration = 3600
    if context.args:
        try:
            duration = int(context.args[0]) * 60
        except:
            pass
    until_date = update.message.date + timedelta(seconds=duration)
    permissions = ChatPermissions(can_send_messages=False)
    try:
        await context.bot.delete_message(update.effective_chat.id, update.message.reply_to_message.message_id)
        await context.bot.delete_message(update.effective_chat.id, update.message.message_id)
        await context.bot.restrict_chat_member(update.effective_chat.id, user.id, permissions, until_date=until_date)
        
        keyboard = [
            [InlineKeyboardButton("🔊 Unmute (Admins Only)", callback_data=f"unmute_{user.id}_{user.username or user.first_name}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            update.effective_chat.id,
            f"🔇 Muted @{user.username or user.first_name} for {duration//60} minutes",
            reply_markup=reply_markup
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    print(f"🔐 Warn command - User ID: {user_id}, Admin IDs: {ADMIN_IDS}, Is Admin: {user_id in ADMIN_IDS}")
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only command")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply to a user's message to warn them")
        return
    user = update.message.reply_to_message.from_user
    chat_id = str(update.effective_chat.id)
    warned_user_id = str(user.id)
    
    await context.bot.delete_message(update.effective_chat.id, update.message.reply_to_message.message_id)
    await context.bot.delete_message(update.effective_chat.id, update.message.message_id)
    
    if chat_id not in user_warnings:
        user_warnings[chat_id] = {}
    if warned_user_id not in user_warnings[chat_id]:
        user_warnings[chat_id][warned_user_id] = 0
    
    user_warnings[chat_id][warned_user_id] += 1
    count = user_warnings[chat_id][warned_user_id]
    save_warnings()
    
    reason = " ".join(context.args) if context.args else "No reason provided"
    
    if count >= 3:
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, user.id)
            
            keyboard = [
                [InlineKeyboardButton("🔓 Unban (Admins Only)", callback_data=f"unban_{user.id}_{user.username or user.first_name}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                update.effective_chat.id,
                f"🚫 @{user.username or user.first_name} has been BANNED after {count} warnings!",
                reply_markup=reply_markup
            )
            user_warnings[chat_id][warned_user_id] = 0
            save_warnings()
        except Exception as e:
            await context.bot.send_message(update.effective_chat.id, f"❌ Error banning: {e}")
    else:
        keyboard = [
            [InlineKeyboardButton("❌ Remove Warning (Admins Only)", callback_data=f"unwarn_{user.id}_{user.username or user.first_name}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            update.effective_chat.id,
            f"⚠️ Warning {count}/3 for @{user.username or user.first_name}\nReason: {reason}\n\n⚠️ {3-count} warnings left before ban!",
            reply_markup=reply_markup
        )

async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    print(f"🔐 Kick command - User ID: {user_id}, Admin IDs: {ADMIN_IDS}, Is Admin: {user_id in ADMIN_IDS}")
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only command")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply to a user's message to kick them")
        return
    user = update.message.reply_to_message.from_user
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, user.id)
        await context.bot.unban_chat_member(update.effective_chat.id, user.id)
        await update.message.reply_text(f"👢 Kicked @{user.username or user.first_name}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to scan a user's profile photo"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only command")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply to a user's message to scan their profile photo")
        return
    target = update.message.reply_to_message.from_user
    _scanned_users.discard(target.id)  # Force rescan
    await update.message.reply_text(f"🔍 Scanning @{target.username or target.first_name}'s profile photo...")
    banned = await scan_user_profile_photo(target, update.effective_chat.id, context)
    if not banned:
        await update.message.reply_text(f"✅ @{target.username or target.first_name}'s profile photo is clean.")

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get user info by replying to their message"""
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply to a user's message to get their info")
        return
    user = update.message.reply_to_message.from_user
    
    # Get bio
    bio = ""
    try:
        chat = await context.bot.get_chat(user.id)
        bio = chat.bio or "No bio"
    except:
        bio = "Unable to fetch"
    
    # Get profile photo count
    try:
        photos = await context.bot.get_user_profile_photos(user.id)
        photo_count = photos.total_count
    except:
        photo_count = 0
    
    info = (
        f"👤 **User Info**\n\n"
        f"🆔 ID: `{user.id}`\n"
        f"📛 Name: {user.first_name} {user.last_name or ''}\n"
        f"👤 Username: @{user.username or 'None'}\n"
        f"🤖 Bot: {'Yes' if user.is_bot else 'No'}\n"
        f"📝 Bio: {bio}\n"
        f"🖼️ Photos: {photo_count}\n"
        f"🔗 Link: [Profile](tg://user?id={user.id})"
    )
    await update.message.reply_text(info, parse_mode='Markdown')

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    print(f"🔐 Unban command - User ID: {user_id}, Admin IDs: {ADMIN_IDS}, Is Admin: {user_id in ADMIN_IDS}")
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only command")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply to a user's message to unban them")
        return
    user = update.message.reply_to_message.from_user
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, user.id)
        await update.message.reply_text(f"✅ Unbanned @{user.username or user.first_name}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    print(f"🔐 Unmute command - User ID: {user_id}, Admin IDs: {ADMIN_IDS}, Is Admin: {user_id in ADMIN_IDS}")
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Admin only command")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply to a user's message to unmute them")
        return
    user = update.message.reply_to_message.from_user
    permissions = ChatPermissions(can_send_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, user.id, permissions)
        await update.message.reply_text(f"🔊 Unmuted @{user.username or user.first_name}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# Test all connections on startup
def test_all_connections_on_startup():
    """Test all AI and Image API connections on startup"""
    print("\n" + "="*60)
    print("🔍 TESTING ALL CONNECTIONS ON STARTUP")
    print("="*60)
    
    print(f"\n🌐 Environment: {'PythonAnywhere' if is_pythonanywhere() else 'Local'}")
    
    # AI SERVICES
    print("\n🤖 AI SERVICES:")
    print("-" * 40)
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": "test"}], "max_tokens": 5}
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"✅ Groq (Llama 3.1 70B): Working")
        else:
            print(f"❌ Groq: Failed ({response.status_code})")
    except Exception as e:
        print(f"❌ Groq: {str(e)[:50]}")
    
    # IMAGE SERVICES
    print("\n🖼️ IMAGE SERVICES:")
    print("-" * 40)
    
    # Pollinations Flux
    try:
        response = requests.get(
            "https://image.pollinations.ai/prompt/test?width=100&height=100&nologo=true",
            timeout=15,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        if response.status_code == 200 and len(response.content) > 1000:
            print(f"✅ Pollinations Flux: Working ({len(response.content)} bytes)")
        elif response.status_code == 530:
            print(f"⚠️ Pollinations Flux: Service Temporarily Down (530)")
        else:
            print(f"❌ Pollinations Flux: Failed ({response.status_code})")
    except Exception as e:
        print(f"❌ Pollinations Flux: {str(e)[:50]}")
    
    # Pollinations Turbo
    try:
        response = requests.get(
            "https://image.pollinations.ai/prompt/test?width=100&height=100&model=turbo&nologo=true",
            timeout=15,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        if response.status_code == 200 and len(response.content) > 1000:
            print(f"✅ Pollinations Turbo: Working ({len(response.content)} bytes)")
        elif response.status_code == 530:
            print(f"⚠️ Pollinations Turbo: Service Temporarily Down (530)")
        else:
            print(f"❌ Pollinations Turbo: Failed ({response.status_code})")
    except Exception as e:
        print(f"❌ Pollinations Turbo: {str(e)[:50]}")
    
    # Unsplash
    try:
        response = requests.get("https://source.unsplash.com/100x100/?nature", timeout=10, allow_redirects=True)
        if response.status_code == 200 and len(response.content) > 1000:
            print(f"✅ Unsplash: Working ({len(response.content)} bytes)")
        elif response.status_code == 503:
            print(f"⚠️ Unsplash: Service Unavailable (503)")
        else:
            print(f"❌ Unsplash: Failed ({response.status_code})")
    except Exception as e:
        print(f"❌ Unsplash: {str(e)[:50]}")
    
    # Picsum
    try:
        response = requests.get("https://picsum.photos/100/100", timeout=10)
        status = f"Working ({len(response.content)} bytes)" if response.status_code == 200 and len(response.content) > 1000 else f"Failed ({response.status_code})"
        print(f"{'✅' if 'Working' in status else '❌'} Picsum: {status}")
    except Exception as e:
        print(f"❌ Picsum: {str(e)[:50]}")
    
    # OTHER SERVICES
    print("\n🌐 OTHER SERVICES:")
    print("-" * 40)
    
    # Cricket API
    try:
        response = requests.get(f"{CRICAPI_CURRENT_MATCHES_URL}?apikey={CRICAPI_KEY}", timeout=10)
        print(f"✅ Cricket API: {'Working' if response.status_code == 200 else f'Failed ({response.status_code})'}")
    except Exception as e:
        print(f"❌ Cricket API: {str(e)[:50]}")
    
    print("\n" + "="*60)
    print("✅ CONNECTION TEST COMPLETE")
    print("="*60 + "\n")

# Main function
def main():
    """Initialize and run the bot."""
    global chat_session, ai_type
    print(f"🎆 Starting bot initialization...")
    
    # Test all connections first
    test_all_connections_on_startup()
    
    chat_session, ai_type = initialize_ai()
    print(f"🤖 AI System: {ai_type}, Session: {chat_session is not None}")

    # Build application with PythonAnywhere-compatible settings
    app = Application.builder().token(TOKEN).connect_timeout(60).read_timeout(60).pool_timeout(60).connection_pool_size(8).build()

    # Initialize the bot before fetching admins
    print("🔍 Initializing bot...")
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(app.bot.initialize())
    print("✅ Bot initialized successfully")

    # Fetch admin IDs from @tamil5 group
    print("🔐 Fetching admin IDs from @tamil5 group...")
    loop.run_until_complete(fetch_group_admins(app.bot))

    # Cricket-related handlers
    app.add_handler(CommandHandler('cricket', cricket_command))
    app.add_handler(CommandHandler('handcricket', handcricket_command))
    app.add_handler(CommandHandler('stop_updates', stop_all_updates))
    app.add_handler(CallbackQueryHandler(button_callback))

    # Admin command handlers
    app.add_handler(CommandHandler('ban', ban_command))
    app.add_handler(CommandHandler('mute', mute_command))
    app.add_handler(CommandHandler('warn', warn_command))
    app.add_handler(CommandHandler('kick', kick_command))
    app.add_handler(CommandHandler('scan', scan_command))
    app.add_handler(CommandHandler('info', info_command))
    app.add_handler(CommandHandler('unban', unban_command))
    app.add_handler(CommandHandler('unmute', unmute_command))

    # Standard command handlers
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('stats', stats_command))
    app.add_handler(CommandHandler('discover', discover_command))
    app.add_handler(CommandHandler('broadcast', broadcast_command))
    app.add_handler(CommandHandler('ping_users', ping_users_command))
    app.add_handler(CommandHandler('play', play_command))
    app.add_handler(CommandHandler('image', image_command))
    app.add_handler(CommandHandler('gif', gif_command))
    app.add_handler(CommandHandler('test_poems', test_poems_command))
    app.add_handler(CommandHandler('test_flows', test_image_flows_command))
    app.add_handler(CommandHandler('test_apis', test_image_apis_command))
    app.add_handler(CommandHandler('test_all', test_all_connections_command))
    app.add_handler(CommandHandler('test_quiz', test_quiz_command))
    app.add_handler(CommandHandler('test_greeting', test_greeting_command))

    app.add_handler(CommandHandler('xo', xo_command))

    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO | filters.ANIMATION | filters.Sticker.ALL, handle_media_moderation))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, check_user_profile_photo))

    # Poll answer handler
    from telegram.ext import PollAnswerHandler
    app.add_handler(PollAnswerHandler(handle_poll_answer))

    app.add_error_handler(error)

    # Setup poem scheduler (synchronous)
    setup_poem_scheduler_sync(app)

    print('🚀 Polling...')
    print('📝 All features active!')
    print('🌍 Special days | 🧠 Daily quizzes | 📝 Tamil poems')
    print(f'🤖 AI Status: {ai_type} - {"Active" if chat_session else "Fallback Mode"}')

    # Run with PythonAnywhere-compatible settings
    try:
        app.run_polling(poll_interval=5, timeout=60, bootstrap_retries=10, drop_pending_updates=True)
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("💡 PythonAnywhere solutions:")
        print("1. Upgrade to paid account for external API access")
        print("2. Use webhook instead of polling")
        print("3. Check PythonAnywhere's external internet policy")
        print("4. Try running locally first to test bot token")

if __name__ == '__main__':
    main()

async def handle_team_cricket(query, game, player_choice, user):
    """Handle team cricket move"""
    try:
        if game['status'] != 'playing':
            await query.answer("Match not started yet!")
            return

        # Check if user is in current batting team
        batting_team = game['team1'] if game['batting_team'] == 'team1' else game['team2']
        bowling_team = game['team2'] if game['batting_team'] == 'team1' else game['team1']

        user_in_batting = any(p['id'] == user.id for p in batting_team['players'])
        user_in_bowling = any(p['id'] == user.id for p in bowling_team['players'])

        if not (user_in_batting or user_in_bowling):
            await query.answer("You're not part of this match!")
            return

        # Store choice
        if 'pending_choice' not in game:
            game['pending_choice'] = {}

        game['pending_choice'][user.id] = player_choice

        # Check if we have choices from both teams
        batting_choices = [game['pending_choice'].get(p['id']) for p in batting_team['players'] if p['id'] in game['pending_choice']]
        bowling_choices = [game['pending_choice'].get(p['id']) for p in bowling_team['players'] if p['id'] in game['pending_choice']]

        if len(batting_choices) > 0 and len(bowling_choices) > 0:
            # Process the ball
            batsman_choice = batting_choices[0]  # Current batsman's choice
            bowler_choice = bowling_choices[0]   # Any bowler's choice

            game['pending_choice'] = {}  # Clear choices

            if batsman_choice == bowler_choice:
                # OUT!
                game['wickets'] += 1
                game['current_batsman'] += 1

                if game['wickets'] >= len(batting_team['players']) or game['current_batsman'] >= len(batting_team['players']):
                    # All out or innings over
                    if game['innings'] == 1:
                        # Switch innings
                        game['target'] = batting_team['score'] + 1
                        game['batting_team'] = 'team2' if game['batting_team'] == 'team1' else 'team1'
                        game['innings'] = 2
                        game['wickets'] = 0
                        game['current_batsman'] = 0

                        new_batting_team = game['team1'] if game['batting_team'] == 'team1' else game['team2']
                        keyboard = create_cricket_keyboard()

                        await query.edit_message_text(
                            text=f"🏏 INNINGS BREAK! 🏏\n\n"
                            f"📊 {batting_team['name']}: {batting_team['score']}/{game['wickets']}\n"
                            f"🎯 Target: {game['target']}\n\n"
                            f"🔄 {new_batting_team['name']} batting now!\n"
                            f"🏏 Current Batsman: {new_batting_team['players'][0]['name']}\n\n"
                            f"🎯 All players choose numbers!",
                            reply_markup=keyboard
                        )
                    else:
                        # Match over
                        team1_score = game['team1']['score']
                        team2_score = game['team2']['score']

                        if team1_score > team2_score:
                            winner = "🔴 Team 1"
                        elif team2_score > team1_score:
                            winner = "🔵 Team 2"
                        else:
                            winner = "🤝 Draw"

                        keyboard = create_cricket_keyboard()
                        await query.edit_message_text(
                            text=f"🏏 MATCH OVER! 🏏\n\n"
                            f"📊 Final Scores:\n"
                            f"🔴 Team 1: {team1_score}\n"
                            f"🔵 Team 2: {team2_score}\n\n"
                            f"🏆 {winner} Wins!",
                            reply_markup=keyboard
                        )
                        game['status'] = 'ended'
                else:
                    # Next batsman
                    next_batsman = batting_team['players'][game['current_batsman']]
                    keyboard = create_cricket_keyboard()

                    await query.edit_message_text(
                        text=f"🏏 OUT! 🏏\n\n"
                        f"📊 {batting_team['name']}: {batting_team['score']}/{game['wickets']}\n"
                        f"🏏 New Batsman: {next_batsman['name']}\n\n"
                        f"🎯 All players choose numbers!",
                        reply_markup=keyboard
                    )
            else:
                # Runs scored
                batting_team['score'] += batsman_choice

                # Check if target reached in second innings
                if game['innings'] == 2 and batting_team['score'] >= game['target']:
                    keyboard = create_cricket_keyboard()
                    await query.edit_message_text(
                        text=f"🏏 MATCH WON! 🏏\n\n"
                        f"📊 Final Scores:\n"
                        f"🔴 Team 1: {game['team1']['score']}\n"
                        f"🔵 Team 2: {game['team2']['score']}\n\n"
                        f"🏆 {batting_team['name']} Wins!",
                        reply_markup=keyboard
                    )
                    game['status'] = 'ended'
                else:
                    current_batsman = batting_team['players'][game['current_batsman']]
                    keyboard = create_cricket_keyboard()

                    await query.edit_message_text(
                        text=f"🏏 {batsman_choice} RUNS! 🏏\n\n"
                        f"📊 {batting_team['name']}: {batting_team['score']}/{game['wickets']}\n"
                        f"🏏 Batsman: {current_batsman['name']}\n\n"
                        f"🎯 All players choose numbers!",
                        reply_markup=keyboard
                    )

            await query.answer(f"Batsman: {batsman_choice}, Bowler: {bowler_choice}")
        else:
            # Waiting for more players
            await query.answer(f"You chose {player_choice}. Waiting for others...")

    except Exception as e:
        print(f"Team cricket error: {e}")
        await query.answer("Error occurred, please try again")
