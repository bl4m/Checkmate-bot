from logging import getLogger
from os import getenv

from discord.ext import commands
from discord.embeds import Embed
import discord
from views.utils import create_failure_embed, create_success_embed

logger = getLogger(__name__)

# --- CTF question template ---------------------------------------------------
# Copy this block for every new question: rename the constants, rename the
# command, and point FLAG at a new env var. Keep the flag out of the source so
# it never lands in the repo.
TEST123_FLAG = getenv("TEST123_FLAG", "somnium{replace_me}")
TEST123_TITLE = "🧩 Question 1 — <name of the question>"
TEST123_PROMPT = (
    "<Put the question text here.>\n\n"
    "Wrap your answer in `somnium{...}` when you submit it."
)
TEST123_HINT = "<Optional hint. Delete this field if the question has no hint.>"
# Role given on a correct answer. Set to None to skip the reward entirely.
TEST123_SOLVE_ROLE = None
# -----------------------------------------------------------------------------

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="rules")
    
    async def rules(self, ctx: commands.Context):
        """
        Rules for Somnium Event
        """
        await ctx.send(embed=create_success_embed("rules message", "Rules"))

    @commands.hybrid_command(name="links")
    async def links(self, ctx: commands.Context): 
        """
            Important Links
        """
        await ctx.send(embed=create_success_embed("[Somnium](https://somnium.ccstiet.com)\n[CCS](https://www.instagram.com/ccs_tiet/)", "Links"))

    @commands.hybrid_command(name="test123")
    @commands.dm_only()
    @commands.cooldown(rate=5, per=60.0, type=commands.BucketType.user)
    async def test123(self, ctx: commands.Context, *, answer: str | None = None):
        """
        CTF question — works only in a DM with the bot.

        Run it with no argument to read the question, or pass your flag to submit.
        """
        # No answer given: hand out the question.
        if answer is None:
            embed = discord.Embed(
                title=TEST123_TITLE,
                description=TEST123_PROMPT,
                color=discord.Color.from_rgb(153, 102, 255),
            )
            if TEST123_HINT:
                embed.add_field(name="Hint", value=TEST123_HINT, inline=False)
            embed.add_field(
                name="How to answer",
                value=f"Send `{ctx.clean_prefix}test123 <your flag>` right here in this DM.",
                inline=False,
            )
            embed.set_footer(text="Somnium • Keep your flag to yourself")
            await ctx.send(embed=embed)
            return

        submitted = answer.strip().strip("`")

        if submitted.casefold() == TEST123_FLAG.casefold():
            logger.info("test123 solved by %s (%s)", ctx.author, ctx.author.id)
            await ctx.send(
                embed=create_success_embed(
                    "That's the right flag. On to the next memory.",
                    title="✅ Correct",
                )
            )
            await self._grant_solve_role(ctx.author, TEST123_SOLVE_ROLE)
            return

        logger.info("test123 wrong answer from %s (%s)", ctx.author, ctx.author.id)
        await ctx.send(
            embed=create_failure_embed(
                "That isn't it. Read the question again and try once more.",
                title="❌ Not quite",
            )
        )

    @test123.error
    async def test123_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.PrivateMessageOnly):
            await ctx.send(
                embed=create_failure_embed(
                    "`test123` only works in a DM with me — send it there so nobody sees your flag.",
                    title="DM only",
                ),
                ephemeral=True,
                delete_after=10,
            )
            return

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                embed=create_failure_embed(
                    f"Too many attempts. Try again in {error.retry_after:.0f}s.",
                    title="Slow down",
                ),
                ephemeral=True,
                delete_after=10,
            )
            return

        logger.error("Unhandled error in test123", exc_info=error)

    async def _grant_solve_role(self, user: discord.User | discord.Member, role_name: str | None):
        """Give the solver a role back in the guild. No-op when role_name is None."""
        if not role_name or not self.bot.guilds:
            return

        guild = self.bot.guilds[0]
        member = guild.get_member(user.id)
        if member is None:
            logger.warning("Solver %s is not in the guild; skipping role.", user.id)
            return

        role = discord.utils.get(guild.roles, name=role_name)
        if role is None:
            try:
                role = await guild.create_role(name=role_name, reason="CTF solve reward")
            except discord.HTTPException:
                logger.exception("Could not create solve role %s", role_name)
                return

        if role not in member.roles:
            try:
                await member.add_roles(role, reason="Solved test123")
            except discord.HTTPException:
                logger.exception("Could not grant solve role to %s", user.id)


async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
