import discord
import os
import time
from datetime import datetime, timedelta
from openai import OpenAI

# Get token from environment variables like in your original code
TOKEN = os.getenv("DISCORD_TOKEN")  
SOURCE_CHANNEL_ID = 1493360277755003061 # Source channel ID
TARGET_CHANNEL_ID = 1479997892231036970 # Target channel ID
groq_client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY")
)

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True

OWNER_ID = 716983514565705749
warnings = {}  # {user_id: [list of warning reasons]}

async def forward_message(message, target_id):
    try:
        target_channel = client.get_channel(target_id)
        if target_channel:
            await target_channel.send(f"||@here ||** **{message.content}")
            for attachment in message.attachments:
                await target_channel.send(attachment.url)
        else:
            print(f"Error: Target channel with ID {target_id} not found.")
    except Exception as e:
        print(f"Error forwarding message: {e}")

client = discord.Client(intents=intents)

manual_mode = False
ai_mode = False
intelligence_mode = False
intelligence_start_time = None
captured_messages = []

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    print(f'Listening to channel ID: {SOURCE_CHANNEL_ID}')
    print(f'Forwarding to channel ID: {TARGET_CHANNEL_ID}')
    print('Bot is ready!')
    print('Commands:')
    print('!manual - Toggle manual mode')
    print('!ai - Toggle AI mode')
    print('!view - View last 10 messages from source channel')
    print('!forward - Forward message manually (when in manual mode)')
    print('!intelligence - Start/stop capturing messages and export to HTML')
    print('!exportall - Export ALL messages from the server to HTML')

def generate_html(messages_list):
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Discord Messages Export</title>
    <style>
        body { font-family: Arial, sans-serif; background: #36393f; color: #dcddde; padding: 20px; }
        .message { padding: 10px; margin: 5px 0; background: #40444b; border-radius: 5px; }
        .author { color: #7289da; font-weight: bold; }
        .timestamp { color: #72767d; font-size: 12px; margin-left: 10px; }
        .content { margin-top: 5px; }
        h1 { color: #fff; }
    </style>
</head>
<body>
    <h1>Discord Messages Export</h1>
"""
    for msg in messages_list:
        channel_info = f" in #{msg.get('channel', 'unknown')}" if 'channel' in msg else ""
        html += f"""    <div class="message">
        <span class="author">{msg['author']}</span>
        <span class="timestamp">{msg['timestamp']}{channel_info}</span>
        <div class="content">{msg['content']}</div>
    </div>
"""
    html += """</body>
</html>"""
    return html

def owner_only(interaction: discord.Interaction) -> bool:
    return interaction.user.id == OWNER_ID

@tree.command(name="ban", description="Ban a member from the server")
@app_commands.check(owner_only)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    try:
        await member.ban(reason=reason)
        await interaction.response.send_message(f"Banned **{member}** — Reason: {reason}", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to ban that member.", ephemeral=True)

@tree.command(name="kick", description="Kick a member from the server")
@app_commands.check(owner_only)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"Kicked **{member}** — Reason: {reason}", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to kick that member.", ephemeral=True)

@tree.command(name="warn", description="Warn a member")
@app_commands.check(owner_only)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if member.id not in warnings:
        warnings[member.id] = []
    warnings[member.id].append(reason)
    count = len(warnings[member.id])
    await interaction.response.send_message(f"Warned **{member}** (Warning #{count}) — Reason: {reason}", ephemeral=True)
    try:
        await member.send(f"You have been warned in **{interaction.guild.name}**.\nReason: {reason}\nTotal warnings: {count}")
    except Exception:
        pass

@tree.command(name="timeout", description="Timeout a member")
@app_commands.check(owner_only)
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided"):
    try:
        until = discord.utils.utcnow() + timedelta(minutes=minutes)
        await member.timeout(until, reason=reason)
        await interaction.response.send_message(f"Timed out **{member}** for {minutes} minute(s) — Reason: {reason}", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to timeout that member.", ephemeral=True)

@tree.command(name="warnings", description="View warnings for a member")
@app_commands.check(owner_only)
async def view_warnings(interaction: discord.Interaction, member: discord.Member):
    user_warnings = warnings.get(member.id, [])
    if not user_warnings:
        await interaction.response.send_message(f"**{member}** has no warnings.", ephemeral=True)
    else:
        warning_list = "\n".join([f"{i+1}. {w}" for i, w in enumerate(user_warnings)])
        await interaction.response.send_message(f"**{member}** has {len(user_warnings)} warning(s):\n{warning_list}", ephemeral=True)

@ban.error
@kick.error
@warn.error
@timeout.error
@view_warnings.error
async def mod_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)

@client.event
async def on_message(message):
    global manual_mode, ai_mode, intelligence_mode, intelligence_start_time, captured_messages

    # Ignore messages from the bot itself
    if message.author.bot:
        return

    # Capture messages when intelligence mode is active
    if intelligence_mode and not message.content.startswith('!intelligence'):
        captured_messages.append({
            'author': message.author.name,
            'content': message.content,
            'timestamp': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'channel': message.channel.name if hasattr(message.channel, 'name') else 'DM'
        })

    if message.content.startswith('!exportall'):
        await message.channel.send("Exporting all messages from the server... This may take a while.")
        all_messages = []
        for channel in message.guild.text_channels:
            try:
                async for msg in channel.history(limit=None):
                    if not msg.author.bot:
                        all_messages.append({
                            'author': msg.author.name,
                            'content': msg.content,
                            'timestamp': msg.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                            'channel': channel.name
                        })
            except Exception as e:
                print(f"Could not access channel {channel.name}: {e}")
        all_messages.sort(key=lambda x: x['timestamp'])
        if all_messages:
            html_content = generate_html(all_messages)
            filename = f"all_messages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            with open(filename, 'w') as f:
                f.write(html_content)
            await message.channel.send(f"Exported {len(all_messages)} messages.", file=discord.File(filename))
            os.remove(filename)
        else:
            await message.channel.send("No messages found to export.")
        return

    if message.content.startswith('!intelligence'):
        if not intelligence_mode:
            intelligence_mode = True
            intelligence_start_time = datetime.now()
            captured_messages = []
            await message.channel.send("Intelligence mode activated. Now capturing all messages. Use `!intelligence` again to stop and get HTML.")
        else:
            intelligence_mode = False
            if captured_messages:
                html_content = generate_html(captured_messages)
                filename = f"messages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                with open(filename, 'w') as f:
                    f.write(html_content)
                await message.channel.send(f"Intelligence mode deactivated. Captured {len(captured_messages)} messages.", file=discord.File(filename))
                os.remove(filename)
            else:
                await message.channel.send("Intelligence mode deactivated. No messages were captured.")
            captured_messages = []
        return

    if message.content.startswith('!manual'):
        manual_mode = not manual_mode
        await message.channel.send(f"Manual mode {'enabled' if manual_mode else 'disabled'}")
        return

    if message.content.startswith('!ai'): # Added AI mode toggle
        ai_mode = not ai_mode
        await message.channel.send(f"AI mode {'enabled' if ai_mode else 'disabled'}")
        return

    if message.content.startswith('!view'):
        source_channel = client.get_channel(SOURCE_CHANNEL_ID)
        messages = [msg async for msg in source_channel.history(limit=10)]
        messages.reverse()
        response = "Last 10 messages:\n"
        for msg in messages:
            response += f"{msg.author.name}: {msg.content}\n"
        await message.channel.send(response)
        return

    if message.channel.id == SOURCE_CHANNEL_ID:
        if manual_mode:
            if message.content.startswith('!forward'):
                async for msg in message.channel.history(limit=10):
                    if not msg.content.startswith('!'):
                        message = msg
                        await forward_message(message, TARGET_CHANNEL_ID)
                        break
            return
        print(f"Message in source channel: {message.content}")
        if not manual_mode:
            await forward_message(message, TARGET_CHANNEL_ID)

    # Handle AI responses when AI mode is enabled
    if ai_mode and message.channel.id == TARGET_CHANNEL_ID:
            try:
                response = groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": message.content}],
                    max_tokens=500
                )
                ai_response = response.choices[0].message.content
                await message.channel.send(f"🤖 {ai_response}")
            except Exception as e:
                print(f"AI Error: {e}")
                await message.channel.send("Sorry, I couldn't generate a response.")


if __name__ == "__main__":
    while True:
        try:
            if not TOKEN:
                print("Error: No Discord token found. Please add your bot token to the Secrets tab with the key 'DISCORD_TOKEN'")
                print("Retrying in 60 seconds...")
                time.sleep(60)
                continue
            if not os.getenv("GROQ_API_KEY"):
                print("Error: No Groq API key found. Please add your Groq API key to the Secrets tab with the key 'GROQ_API_KEY'")
                print("Retrying in 60 seconds...")
                time.sleep(60)
                continue
            print("Starting bot...")
            client.run(TOKEN)
        except discord.errors.LoginFailure as e:
            print(f"Login error: {e}. Check your token in Secrets.")
            print("Retrying in 60 seconds...")
            time.sleep(60)
        except Exception as e:
            print(f"An error occurred: {e}")
            print("Restarting bot in 10 seconds...")
            time.sleep(10)
             
