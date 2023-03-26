import disnake
from disnake.ext import commands
import psycopg2
import asyncio
import pytz
from PIL import Image
import sqlite3
import scipy.stats as sps

bot = commands.Bot(
    command_prefix='!',
    test_guilds=[482012169911664640, 192460940409700352],
    sync_commands_debug=True
)

with open('stats_pass.txt', 'r') as t:
    stats_pass = t.read()

conn_game = psycopg2.connect(
    host="104.153.105.63",
    database="utstats",
    user="utstats",
    password=stats_pass,
    port=5432)

c2 = conn_game.cursor()

with open('token.txt', 'r') as t:
    discordtoken = t.read()


def update_colors():
    conn = sqlite3.connect("C:/Users/poiso/PycharmProjects/elo2color/Mods.db")
    c = conn.cursor()

    filepath = "spectrum.png"
    img = Image.open(filepath)
    rgb_im = img.convert('RGB')

    width = img.width

    # return names and elo of players
    c.execute("SELECT ID, Elo FROM EliminationStats ORDER BY Elo DESC")
    name_elo = c.fetchall()
    name_elo_list = list(name_elo)

    # return list of just elo
    c.execute("SELECT Elo FROM EliminationStats ORDER BY Elo DESC")
    elo = c.fetchall()
    elo_list = [i[0] for i in elo]

    # iterates through list of names and elos
    # inserts percentile of elo per player
    # calculates percentage of spectrum image to pull color from and inserts rgb value

    for x in range(len(name_elo)):
        percentile = sps.percentileofscore(elo_list, name_elo[x][1])
        name_elo_list[x] += (percentile,)
        name_elo_list[x] += (percentile * (width / 100) - 1,)
        r, g, b = rgb_im.getpixel((name_elo_list[x][3], 1))
        name_elo_list[x] += ((r, g, b),)

    name_color = [[] for i in range(len(name_elo_list))]

    # Appends just name and R G B values to a new list

    for x in range(len(name_elo_list)):
        name_color[x].append(name_elo_list[x][0])
        name_color[x].append(name_elo_list[x][4][0])
        name_color[x].append(name_elo_list[x][4][1])
        name_color[x].append(name_elo_list[x][4][2])

    # Updates R G B values in EliminationColor table.

    c.executemany("insert or replace into EliminationColors(ID, R, G, B)"
                  "values(?,?,?,?);", name_color)

    conn.commit()
    conn.close()

    print('Color table updated with ', c.rowcount, 'records.')


# List players in more attractive format

def parse_players(list_to_parse):
    parsed_players = ""

    for i in range(len(list_to_parse)):

        if i < (len(list_to_parse) - 1):
            parsed_players += list_to_parse[i][0] + " :small_orange_diamond: "
        else:
            parsed_players += list_to_parse[i][0]

    return parsed_players


@bot.slash_command(description="Show last game from server")
async def update(inter, gametype: str = ''):
    await inter.send('Live updates enabled')
    asyncio.create_task(background_code())


async def background_code():
    match_id_2 = None

    while True:

        c2.execute("SELECT matchid "
                   "FROM utstats_match "
                   "WHERE servername LIKE '%UTPugs%' "
                   "ORDER BY matchid DESC LIMIT 1")

        match_id_1 = c2.fetchone()

        if match_id_2:
            if match_id_1[0] != match_id_2[0]:
                print("SQL UPDATED!")
                c2.execute("SELECT servername, gamemode, redteamscore, blueteamscore, date, matchid, gamemap "
                           "FROM utstats_match "
                           "WHERE servername LIKE '%UTPugs%' AND gamemode iLIKE '%%' "
                           "ORDER BY matchid DESC LIMIT 10")

                data = c2.fetchall()

                server_name = data[0][0]
                game_mode = data[0][1]
                red_team_score = data[0][2]
                blue_team_score = data[0][3]
                date = data[0][4]
                match_id = data[0][5]
                map_name = data[0][6]

                est = pytz.timezone('US/Eastern')
                date = date.astimezone(est).strftime("%b %d, %Y %I:%M%p %Z")

                if game_mode == "UTCTFGameMode":
                    game_mode = "CTF"
                elif game_mode == "Elimination_113_C":
                    game_mode = "Elimination"
                elif game_mode == "UTFlagRunGame":
                    game_mode = "Blitz"
                elif game_mode == "UTDuelGame":
                    game_mode = "Duel"

                c2.execute("SELECT p.playername "
                           "FROM utstats_matchstats m, utstats_player p "
                           "WHERE p.playerid = m.playerid_id AND m.matchid_id = '" + str(
                    match_id) + "' AND m.team = 'Red'")

                red_team_players = c2.fetchall()
                red_team_players = parse_players(red_team_players)

                c2.execute("SELECT p.playername "
                           "FROM utstats_matchstats m, utstats_player p "
                           "WHERE p.playerid = m.playerid_id "
                           "AND m.matchid_id = '" + str(match_id) + "' AND m.team = 'Blue'")

                blue_team_players = c2.fetchall()
                blue_team_players = parse_players(blue_team_players)

                embed = disnake.Embed(
                    title="Latest " + str(game_mode) + " on " + str(server_name),
                    url="https://ut4stats.com/match_summary/" + str(match_id) + "",
                    description="Date: " + str(date) + "\n Map: " + map_name + "",
                    colour=0xF0C43F,
                )
                embed.add_field(name="Red Team Score: " + str(red_team_score) + "", value=str(red_team_players),
                                inline=True)
                embed.add_field(name="Blue Team Score: " + str(blue_team_score) + "", value=str(blue_team_players),
                                inline=False)

                channel = bot.get_channel(1088637359299510353)

                if game_mode == "CTF" or game_mode == "Elimination":
                    update_colors()
                    await channel.send(embed=embed)

        await asyncio.sleep(60)

        c2.execute("SELECT matchid "
                   "FROM utstats_match "
                   "WHERE servername LIKE '%UTPugs%' "
                   "ORDER BY matchid DESC LIMIT 1")

        match_id_2 = c2.fetchone()

        if match_id_1[0] != match_id_2[0]:
            print("SQL UPDATED!")
            c2.execute("SELECT servername, gamemode, redteamscore, blueteamscore, date, matchid, gamemap "
                       "FROM utstats_match "
                       "WHERE servername LIKE '%UTPugs%' AND gamemode iLIKE '%%' "
                       "ORDER BY matchid DESC LIMIT 10")

            data = c2.fetchall()

            server_name = data[0][0]
            game_mode = data[0][1]
            red_team_score = data[0][2]
            blue_team_score = data[0][3]
            date = data[0][4]
            match_id = data[0][5]
            map_name = data[0][6]

            est = pytz.timezone('US/Eastern')
            date = date.astimezone(est).strftime("%b %d, %Y %I:%M%p %Z")

            if game_mode == "UTCTFGameMode":
                game_mode = "CTF"
            elif game_mode == "UTDuelGame":
                game_mode = "Duel"
            elif game_mode == "Elimination_113_C":
                game_mode = "Elimination"
            elif game_mode == "UTFlagRunGame":
                game_mode = "Blitz"

            c2.execute("SELECT p.playername "
                       "FROM utstats_matchstats m, utstats_player p "
                       "WHERE p.playerid = m.playerid_id AND m.matchid_id = '" + str(match_id) + "' AND m.team = 'Red'")

            red_team_players = c2.fetchall()
            red_team_players = parse_players(red_team_players)

            c2.execute("SELECT p.playername "
                       "FROM utstats_matchstats m, utstats_player p "
                       "WHERE p.playerid = m.playerid_id "
                       "AND m.matchid_id = '" + str(match_id) + "' AND m.team = 'Blue'")

            blue_team_players = c2.fetchall()
            blue_team_players = parse_players(blue_team_players)

            embed = disnake.Embed(
                title="Latest " + str(game_mode) + " on " + str(server_name),
                url="https://ut4stats.com/match_summary/" + str(match_id) + "",
                description="Date: " + str(date) + "\n Map: " + map_name + "",
                colour=0xF0C43F,
            )
            embed.add_field(name="Red Team Score: " + str(red_team_score) + "", value=str(red_team_players),
                            inline=True)
            embed.add_field(name="Blue Team Score: " + str(blue_team_score) + "", value=str(blue_team_players),
                            inline=False)

            channel = bot.get_channel(1088637359299510353)

            if game_mode == "CTF" or game_mode == "Elimination":
                update_colors()
                await channel.send(embed=embed)

        await asyncio.sleep(60)


bot.run(str(discordtoken))
