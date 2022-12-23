import discord
from discord.ext import commands, pages
from discord.commands.context import ApplicationContext
from discord.commands import Option
import aiosqlite
import asyncio
from easy_pil import Canvas, Editor, Font, load_image
import time
import random
from dotenv import load_dotenv, find_dotenv
import os


bot = discord.Bot(intents=discord.Intents.all())
load_dotenv(find_dotenv())


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    setattr(bot, 'db', await aiosqlite.connect("level.db"))
    await asyncio.sleep(3)
    async with bot.db.cursor() as cursor:
        await cursor.execute("""CREATE TABLE IF NOT EXISTS levels
                                (user INT PRIMARY KEY NOT NULL, xp INT, level INT, nextlevel INT, background VARCHAR(30), time INT, total INT, name VARCHAR(50))""")


@bot.slash_command(name="leaderboard", description="Get the xp leaderboard")
async def leaderboard(ctx: ApplicationContext):
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT total, user FROM levels ORDER BY total DESC")
        data = await cursor.fetchall()

        strings = []
        author_string = ""
        pos = 1
        p = 1
        for d in data:
            f_string = f"#{pos}: <@{d[1]}> XP: `{d[0]}`"
            strings.append(f_string)
            if d[1] == ctx.author.id:
                author_string += f"**#{pos}: <@{d[1]}> XP: `{d[0]}`**"
            pos += 1

        chunks = [strings[i: i + 10] for i in range(0, len(strings), 10)]
        embeds = []
        for chunk in chunks:
            texts = []
            for n in chunk:
                texts.append(f"{n}")
            names = "\n".join(texts)
            line = "-"*47
            e = discord.Embed(title=f"**{ctx.guild.name} Leaderboard**",
                              description=f"{names}\n{line}\n{author_string}", color=0x97ce4c)
            e.set_footer(text=f"Page: {p}/{len(chunks)}")
            p += 1
            embeds.append(e)
        paginator = pages.Paginator(
            pages=embeds, timeout=30, disable_on_timeout=True)
        await paginator.respond(ctx.interaction)


@bot.slash_command(name="rank", description="Shows your rank")
async def rank(ctx: ApplicationContext, user: Option(discord.User,
                                                     "Select a user to get the rank from",
                                                     required=False)):
    if user is None:
        user_id = ctx.user.id
        user_name = ctx.user.name
    else:
        user_id = user.id
        user_name = user.name
    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT xp, level, nextlevel, background FROM levels WHERE user =?", (user_id,))
        data = await cursor.fetchone()

    if not data:
        if user is None:
            await ctx.respond("You don't have a rank yet!", ephemeral=True)
        else:
            await ctx.respond("This user doesn't have a rank yet!", ephemeral=True)
    else:
        xp = data[0]
        level = data[1]
        goal = data[2]
        image = data[3]


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    author = message.author
    guild = message.guild

    async with bot.db.cursor() as cursor:
        await cursor.execute("SELECT xp, level, time, total FROM levels WHERE user =?", (author.id,))
        xplevel = await cursor.fetchone()

        if not xplevel:
            await cursor.execute("INSERT INTO levels VALUES (?,?,?,?,?,?,?,?)", (author.id, 0, 0, 100, None, int(time.time() + 60), 0, author.name))
            await bot.db.commit()
            return

        xp = xplevel[0]
        level = xplevel[1]
        level_time = xplevel[2]
        total = xplevel[3]

        if level_time >= int(time.time()):
            return

        num = random.randint(15, 25)
        await cursor.execute("UPDATE levels SET xp =?, total =?, time =?, name =? WHERE user =?", (xp+num, total+num, int(time.time()+60), author.name, author.id,))
        await bot.db.commit()

        await cursor.execute("SELECT level, xp FROM levels WHERE user =?", (author.id,))
        xplevel = await cursor.fetchone()
        level = xplevel[0]
        xp = xplevel[1]

        goal = 5 * (level ** 2) + (50 * level) + 100 - xp

        if goal <= 0:
            g = 5 * ((level + 1) ** 2) + (50 * (level + 1)) + 100
            await cursor.execute("UPDATE levels SET xp =?, level =?, nextlevel =?  WHERE user =?", (0, level+1, g, author.id,))
            channel = bot.get_channel(1003708900148785223)

            await channel.send(f"{author.mention} has leveled up to level **{level+1}**!")
    await bot.db.commit()


bot.run(os.getenv("TOKEN"))
