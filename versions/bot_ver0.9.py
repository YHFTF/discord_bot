import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp

TOKEN = '' # 여기에 디스코드 봇 토큰을 입력하세요
INSTANCE_OCID = '' # 여기에 Oracle 인스턴스 OCID를 입력하세요

intents = discord.Intents.default()
intents.message_content = True  # 음악 명령어에 필요
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# ▶️ 음악 재생
@tree.command(name="재생", description="유튜브에서 노래를 재생합니다.")
async def 재생(interaction: discord.Interaction, query: str):
    await interaction.response.send_message(f"🔎 `{query}` 검색 중...")

    voice = interaction.user.voice
    if voice is None:
        return await interaction.followup.send("❌ 먼저 음성 채널에 접속해주세요.")

    vc = interaction.guild.voice_client
    if not vc:
        vc = await voice.channel.connect()

    ytdlp_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'cookiefile': '/home/ubuntu/bot/youtube_cookies.txt'
    }

    with yt_dlp.YoutubeDL(ytdlp_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        url = info['url'] if 'url' in info else info['entries'][0]['url']
        title = info['title'] if 'title' in info else info['entries'][0]['title']

    vc.stop()
    vc.play(discord.FFmpegPCMAudio(url, before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"))
    await interaction.followup.send(f"🎵 `{title}` 재생 중입니다.")

# ⏹️ 음악 정지
@tree.command(name="정지", description="재생 중인 음악을 정지합니다.")
async def 정지(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await interaction.response.send_message("⏹️ 음악이 정지되었습니다.")
    else:
        await interaction.response.send_message("❌ 현재 재생 중인 음악이 없습니다.")

# ❌ 음성채널 나가기
@tree.command(name="나가", description="음성 채널에서 나갑니다.")
async def 나가(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        await vc.disconnect()
        await interaction.response.send_message("👋 음성 채널에서 나갔습니다.")
    else:
        await interaction.response.send_message("❌ 음성 채널에 있지 않습니다.")

@tree.command(name="서버켜", description="Oracle 인스턴스를 켭니다.")
async def 서버켜(interaction: discord.Interaction):
    await interaction.response.send_message("🔄 인스턴스를 켜는 중...")
    proc = await asyncio.create_subprocess_exec(
        "oci", "compute", "instance", "action",
        "--instance-id", INSTANCE_OCID,
        "--action", "START",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode == 0:
        await interaction.followup.send("🟢 인스턴스 부팅 시작!")
    else:
        await interaction.followup.send(f"❌ 오류: {stderr.decode()}")

@tree.command(name="서버꺼", description="Oracle 인스턴스를 끕니다.")
async def 서버꺼(interaction: discord.Interaction):
    await interaction.response.send_message("🔻 인스턴스를 끄는 중...")
    proc = await asyncio.create_subprocess_exec(
        "oci", "compute", "instance", "action",
        "--instance-id", INSTANCE_OCID,
        "--action", "STOP",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode == 0:
        await interaction.followup.send("🔴 인스턴스 종료 완료!")
    else:
        await interaction.followup.send(f"❌ 오류: {stderr.decode()}")

@tree.command(name="서버상태", description="Oracle 인스턴스의 현재 상태를 확인합니다.")
async def 서버상태(interaction: discord.Interaction):
    await interaction.response.send_message("📡 인스턴스 상태 확인 중...")
    proc = await asyncio.create_subprocess_exec(
        "oci", "compute", "instance", "get",
        "--instance-id", INSTANCE_OCID,
        "--query", 'data."lifecycle-state"',
        "--raw-output",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode == 0:
        상태 = stdout.decode().strip()
        await interaction.followup.send(f"✅ 현재 인스턴스 상태: `{상태}`")
    else:
        await interaction.followup.send(f"❌ 상태 확인 실패: {stderr.decode()}")

@client.event
async def on_ready():
    await tree.sync()
    print("✅ 봇 준비 완료 및 명령어 동기화")
    
client.run(TOKEN)
