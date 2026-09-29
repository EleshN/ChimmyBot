import os

import discord
from discord.ext import commands
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
VERIFIED_ROLE_ID = int(os.getenv("VERIFIED_ROLE_ID"))
VERIFY_CHANNEL_ID = int(os.getenv("VERIFY_CHANNEL_ID"))
RESULTS_CHANNEL_ID = int(os.getenv("RESULTS_CHANNEL_ID"))


class VerificationModal(discord.ui.Modal, title="Alumni Verification"):
    name = discord.ui.TextInput(
        label="Name",
        placeholder="Your first and last name",
        required=True,
        max_length=100,
    )

    email = discord.ui.TextInput(
        label="Email",
        placeholder="Your primary email address",
        required=True,
        max_length=254,
    )

    graduation_year = discord.ui.TextInput(
        label="Cornell Graduation Year",
        placeholder="e.g. 2024",
        required=True,
        min_length=4,
        max_length=4,
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Validate graduation year
        if not self.graduation_year.value.isdigit():
            await interaction.response.send_message(
                "Please enter a valid graduation year.",
                ephemeral=True,
            )
            return

        year = int(self.graduation_year.value)

        if year < 1900 or year > 2100:
            await interaction.response.send_message(
                "Please enter a valid graduation year.",
                ephemeral=True,
            )
            return

        # Find the verified role
        role = interaction.guild.get_role(VERIFIED_ROLE_ID)

        if role is None:
            await interaction.response.send_message(
                "There was a problem finding the verification role. "
                "Please contact an administrator.",
                ephemeral=True,
            )
            return

        # Find the member
        member = interaction.guild.get_member(interaction.user.id)

        if member is None:
            await interaction.response.send_message(
                "There was a problem finding your server membership. "
                "Please contact an administrator.",
                ephemeral=True,
            )
            return

        # Assign the verified role
        try:
            await member.add_roles(role)
        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission to assign the verified role. "
                "Please contact an administrator.",
                ephemeral=True,
            )
            return

        # Find the private verification log channel
        log_channel = interaction.guild.get_channel(
            RESULTS_CHANNEL_ID
        )

        if log_channel is None:
            await interaction.response.send_message(
                "You have been verified, but there was a problem "
                "recording your submission. Please contact an administrator.",
                ephemeral=True,
            )
            return

        # Record the submission
        await log_channel.send(
            f"**New Alumni Verification**\n"
            f"**Name:** {self.name.value}\n"
            f"**Email:** {self.email.value}\n"
            f"**Graduation Year:** {year}\n"
            f"**Discord:** {member.mention} (`{member.id}`)"
        )

        # Confirm privately
        await interaction.response.send_message(
            f"Thanks, {self.name.value}! "
            "You've been verified and can now access the server.",
            ephemeral=True,
        )


class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Verify Me",
        style=discord.ButtonStyle.primary,
        custom_id="alumni_verify_button",
    )
    async def verify_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        # If the user is already verified, don't show the form again.
        role = interaction.guild.get_role(VERIFIED_ROLE_ID)

        if role is not None and role in interaction.user.roles:
            await interaction.response.send_message(
                "You're already verified!",
                ephemeral=True,
            )
            return

        # Open the verification form
        await interaction.response.send_modal(VerificationModal())


class AlumniBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True

        super().__init__(
            command_prefix="!",
            intents=intents,
        )

    async def setup_hook(self):
        # Register the persistent button view.
        self.add_view(VerificationView())

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")

    async def on_member_join(self, member: discord.Member):
        print(f"Member joined: {member} ({member.id})")

        channel = member.guild.get_channel(VERIFY_CHANNEL_ID)

        if channel is None:
            print(
                f"Could not find verification channel "
                f"(ID: {VERIFY_CHANNEL_ID})"
            )
            return

        print(f"Found verification channel: {channel.name}")

        if channel is None:
            print(
                f"Could not find verification channel "
                f"(ID: {VERIFY_CHANNEL_ID})"
            )
            return

        # Don't send a verification message if the user somehow
        # already has the verified role.
        role = member.guild.get_role(VERIFIED_ROLE_ID)

        if role is not None and role in member.roles:
            return

        await channel.send(
            f"Welcome, {member.mention}! 👋\n\n"
            "Welcome to the alumni server! Before you can access "
            "the rest of the server, please complete the verification "
            "form below.",
            view=VerificationView(),
        )

    async def on_socket_raw_receive(self, msg):
        if '"GUILD_MEMBER_ADD"' in msg:
            print("RAW GUILD_MEMBER_ADD RECEIVED!")


bot = AlumniBot()

bot.run(TOKEN)