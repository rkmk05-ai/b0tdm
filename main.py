import discord
from discord import app_commands
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
intents.moderation = True

OWNER_ID = 716983514565705749
warnings = {}
punishment_id = 0
PUNISH_LOG_CHANNEL = 1494088216003870830
THREAD_LOG_CHANNEL = 1494088651146264656

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

async def log_punishment(punishment_type, user, moderator, length, reason):
    global punishment_id
    punishment_id += 1
    pid = punishment_id

    log_channel = client.get_channel(PUNISH_LOG_CHANNEL)
    thread_channel = client.get_channel(THREAD_LOG_CHANNEL)

    log_msg = (
        f"*{punishment_type} #{pid}*\n"
        f"**Username** `{user}`\n"
        f"**User ID:** `{user.id}`\n"
        f"**Moderator Username:** `{moderator}`\n"
        f"**Punishment Type:** `{punishment_type}`\n"
        f"**Length:** `{length}`\n"
        f"**Reason:** `{reason}`"
    )

    thread_body = (
        f"**Username** `{user}`\n"
        f"**User ID:** `{user.id}`\n"
        f"**Length:** `{length}`\n"
        f"**Reason:** `{reason}`\n"
        f"**Proof:**"
    )

    try:
        if log_channel:
            await log_channel.send(log_msg)
        if thread_channel:
            thread_name = f"#{punishment_type} #{pid} - {user}"
            seed_msg = await thread_channel.send(thread_name)
            thread = await seed_msg.create_thread(
                name=thread_name[:100],
                auto_archive_duration=10080
            )
            await thread.send(thread_body)
    except Exception as e:
        print(f"Logging error: {e}")

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

manual_mode = False
ai_mode = False
intelligence_mode = False
intelligence_start_time = None
captured_messages = []

@client.event
async def on_ready():
    await tree.sync()
    print(f'Logged in as {client.user}')
    print(f'Listening to channel ID: {SOURCE_CHANNEL_ID}')
    print(f'Forwarding to channel ID: {TARGET_CHANNEL_ID}')
    print('Bot is ready! Slash commands synced.')
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

COMMANDS_INFO = {
    "/ban": "Ban a member from the server",
    "/kick": "Kick a member from the server",
    "/warn": "Warn a member (sends them a DM)",
    "/timeout": "Timeout a member for X minutes",
    "/warnings": "View all warnings for a member",
    "!manual": "Toggle manual forwarding mode",
    "!ai": "Toggle AI auto-reply mode",
    "!view": "View last 10 messages from source channel",
    "!forward": "Manually forward a message (manual mode only)",
    "!intelligence": "Start/stop capturing messages and export to HTML",
    "!exportall": "Export ALL server messages to an HTML file",
}

class CommandSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=cmd, description=desc[:100])
            for cmd, desc in COMMANDS_INFO.items()
        ]
        super().__init__(placeholder="Select a command to learn more...", options=options)

    async def callback(self, interaction: discord.Interaction):
        cmd = self.values[0]
        desc = COMMANDS_INFO[cmd]
        embed = discord.Embed(title=cmd, description=desc, color=0x7289da)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class CommandView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(CommandSelect())

@tree.command(name="commands", description="View all available bot commands")
async def commands_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Bot Commands",
        description="Select a command from the dropdown to learn more.",
        color=0x7289da
    )
    for cmd, desc in COMMANDS_INFO.items():
        embed.add_field(name=cmd, value=desc, inline=False)
    await interaction.response.send_message(embed=embed, view=CommandView(), ephemeral=True)

@tree.command(name="ban", description="Ban a member from the server")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        await member.ban(reason=reason)
        await interaction.followup.send(f"Banned **{member}** — Reason: {reason}", ephemeral=True)
        await log_punishment("Ban", member, interaction.user, "N/A", reason)
    except discord.Forbidden:
        await interaction.followup.send("I don't have permission to ban that member.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Error: {e}", ephemeral=True)

@tree.command(name="kick", description="Kick a member from the server")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        await member.kick(reason=reason)
        await interaction.followup.send(f"Kicked **{member}** — Reason: {reason}", ephemeral=True)
        await log_punishment("Kick", member, interaction.user, "N/A", reason)
    except discord.Forbidden:
        await interaction.followup.send("I don't have permission to kick that member.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Error: {e}", ephemeral=True)

@tree.command(name="warn", description="Warn a member")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return
    if member.id not in warnings:
        warnings[member.id] = []
    warnings[member.id].append(reason)
    count = len(warnings[member.id])
    await interaction.response.send_message(f"Warned **{member}** (Warning #{count}) — Reason: {reason}", ephemeral=True)
    await log_punishment("Warn", member, interaction.user, "N/A", reason)
    try:
        await member.send(f"You have been warned in **{interaction.guild.name}**.\nReason: {reason}\nTotal warnings: {count}")
    except Exception:
        pass

@tree.command(name="timeout", description="Timeout a member (leave all blank for max 28 days)")
async def timeout(interaction: discord.Interaction, member: discord.Member, days: int = 0, hours: int = 0, minutes: int = 0, reason: str = "No reason provided"):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        total_minutes = days * 1440 + hours * 60 + minutes
        if total_minutes == 0:
            total_minutes = 40320
        capped = min(total_minutes, 40320)
        until = discord.utils.utcnow() + timedelta(minutes=capped)
        await member.timeout(until, reason=reason)
        unix_ts = int(until.timestamp())
        length_ts = f"<t:{unix_ts}:F> (<t:{unix_ts}:R>)"
        if capped == 40320 and total_minutes >= 40320:
            duration_text = "28 days (maximum)"
        else:
            parts = []
            if days: parts.append(f"{days}d")
            if hours: parts.append(f"{hours}h")
            if minutes: parts.append(f"{minutes}m")
            duration_text = " ".join(parts) if parts else f"{capped} minutes"
        await interaction.followup.send(f"Timed out **{member}** for {duration_text} — Reason: {reason}", ephemeral=True)
        await log_punishment("Timeout", member, interaction.user, length_ts, reason)
    except discord.Forbidden:
        await interaction.followup.send("I don't have permission to timeout that member.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Error: {e}", ephemeral=True)

@tree.command(name="warnings", description="View warnings for a member")
async def view_warnings(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return
    user_warnings = warnings.get(member.id, [])
    if not user_warnings:
        await interaction.response.send_message(f"**{member}** has no warnings.", ephemeral=True)
    else:
        warning_list = "\n".join([f"{i+1}. {w}" for i, w in enumerate(user_warnings)])
        await interaction.response.send_message(f"**{member}** has {len(user_warnings)} warning(s):\n{warning_list}", ephemeral=True)

@client.event
async def on_audit_log_entry_create(entry: discord.AuditLogEntry):
    mod = entry.user
    target = entry.target
    reason = entry.reason or "No reason provided"

    if entry.action == discord.AuditLogAction.ban:
        if mod and not mod.bot:
            await log_punishment("Ban", target, mod, "N/A", reason)

    elif entry.action == discord.AuditLogAction.unban:
        if mod and not mod.bot:
            await log_punishment("Unban", target, mod, "N/A", reason)

    elif entry.action == discord.AuditLogAction.kick:
        if mod and not mod.bot:
            await log_punishment("Kick", target, mod, "N/A", reason)

    elif entry.action == discord.AuditLogAction.member_update:
        after = entry.after
        before = entry.before
        if hasattr(after, 'timed_out_until') and hasattr(before, 'timed_out_until'):
            if mod and not mod.bot:
                if after.timed_out_until is not None and (before.timed_out_until is None or before.timed_out_until < after.timed_out_until):
                    unix_ts = int(after.timed_out_until.timestamp())
                    length_ts = f"<t:{unix_ts}:F> (<t:{unix_ts}:R>)"
                    await log_punishment("Timeout", target, mod, length_ts, reason)
                elif after.timed_out_until is None and before.timed_out_until is not None:
                    await log_punishment("Untimeout", target, mod, "N/A", reason)

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
    if not TOKEN:
        print("Error: No Discord token found. Please add DISCORD_TOKEN to Secrets.")
    elif not os.getenv("GROQ_API_KEY"):
        print("Error: No Groq API key found. Please add GROQ_API_KEY to Secrets.")
    else:
        print("Starting bot...")
        client.run(TOKEN)
             
