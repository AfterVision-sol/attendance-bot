import os
import discord
from discord.ext import tasks, commands
from datetime import datetime, time
import pytz
import asyncio
from flask import Flask
from threading import Thread

# === Keep-alive server (for Render Web Service ping) ===
app = Flask(__name__)

@app.route('/')
def home():
    return "Attendance Bot is alive!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# === Environment Variables ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
ATTENDANCE_CHANNEL_ID = int(os.getenv("ATTENDANCE_CHANNEL_ID"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")

# === Discord Bot Setup ===
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# === In-memory tracker ===
attendance_message_id = None

@bot.event
async def on_ready():
    print(f"{bot.user} is now running.")
    post_attendance_message.start()
    check_attendance.start()

@tasks.loop(time=time(10, 0))  # 10:00 AM
async def post_attendance_message():
    global attendance_message_id
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    date_str = now.strftime("%B %d, %Y")

    channel = bot.get_channel(ATTENDANCE_CHANNEL_ID)
    if not channel:
        print("Attendance channel not found.")
        return

    embed = discord.Embed(
        title="✅ Mark Your Attendance",
        description=f"React with ✅ to check in for **{date_str}**.\n\nMake sure to react before 5:00 PM IST.",
        color=0x9ef01a
    )
    embed.set_footer(text="VisionBot by AfterVision")

    msg = await channel.send(embed=embed)
    await msg.add_reaction("✅")
    attendance_message_id = msg.id

@tasks.loop(time=time(17, 0))  # 5:00 PM
async def check_attendance():
    global attendance_message_id
    if attendance_message_id is None:
        print("No attendance message ID found.")
        return

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    date_str = now.strftime("%B %d, %Y")

    attendance_channel = bot.get_channel(ATTENDANCE_CHANNEL_ID)
    log_channel = bot.get_channel(LOG_CHANNEL_ID)

    try:
        msg = await attendance_channel.fetch_message(attendance_message_id)
        for reaction in msg.reactions:
            if str(reaction.emoji) == "✅":
                users = await reaction.users().flatten()
                attendees = [user.mention for user in users if not user.bot]

                description = (
                    f"✅ **{len(attendees)}** member(s) checked in:\n\n" + "\n".join(attendees)
                    if attendees else "❌ No one checked in today."
                )

                embed = discord.Embed(
                    title=f"📈 Attendance Log – {date_str}",
                    description=description,
                    color=0x9ef01a
                )
                embed.set_footer(text="Auto-logged by VisionBot")

                await log_channel.send(embed=embed)
                break

    except Exception as e:
        print(f"Error checking attendance: {e}")

# === Start everything ===
keep_alive()          # Start Flask server for uptime pings
bot.run(BOT_TOKEN)    # Start Discord bot
