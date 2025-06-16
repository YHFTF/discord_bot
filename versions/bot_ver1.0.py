import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
from urllib.parse import urlparse, parse_qs, urlencode

TOKEN = ''
INSTANCE_OCID = ''

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

queue = []

def 정리된_유튜브_URL(raw_input: str) -> str | None:
    """사용자가 입력한 유튜브 링크를 yt-dlp가 처리 가능한 형태로 보정"""
    try:
        parsed = urlparse(raw_input)

        if "youtu.be" in parsed.netloc:
            # 단축 링크 → watch 형식으로 변환
            video_id = parsed.path.lstrip("/")
            if len(video_id) == 11:
                return f"https://www.youtube.com/watch?v={video_id}"
            else:
                return None

        elif "youtube.com" in parsed.netloc:
            query = parse_qs(parsed.query)
            video_id = query.get("v", [None])[0]
            if video_id and len(video_id) == 11:
                return f"https://www.youtube.com/watch?v={video_id}"
            else:
                return None

        else:
            return None
    except:
        return None
    
# ▶️ 음악 재생
@tree.command(name="재생", description="유튜브에서 노래를 재생합니다.")
async def 재생(interaction: discord.Interaction, raw_url: str):
    await interaction.response.send_message(f"🎵 입력 확인 중...")

    url = 정리된_유튜브_URL(raw_url)
    if not url:
        return await interaction.followup.send("❌ 잘못된 유튜브 링크입니다. 전체 URL을 입력해주세요.")

    # 아래는 기존 yt_dlp 처리 부분 그대로/최적화 옵션 추가
    ytdlp_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'nocheckcertificate': True,
    'no_warnings': True,
    'cookiefile': '/home/ubuntu/bot/youtube_cookies.txt',
    'extract_flat': True,  # 검색일 경우만
    'source_address': '0.0.0.0'  # IPv6 오류 방지
    }

    try:
        with yt_dlp.YoutubeDL(ytdlp_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info['url']
            title = info['title']
    except Exception as e:
        return await interaction.followup.send(f"❌ 오류: {str(e)[:150]}")

    queue.append((audio_url, title))
    await interaction.followup.send(f"✅ `{title}`(이)가 큐에 추가되었습니다.")

    vc = interaction.guild.voice_client
    if not vc or not vc.is_playing():
        await play_next(interaction)

# 다음 곡 재생
async def play_next(interaction: discord.Interaction):
    if not queue:
        return

    vc = interaction.guild.voice_client
    if not vc:
        voice = interaction.user.voice
        if voice:
            vc = await voice.channel.connect()
        else:
            return await interaction.channel.send("❌ 음성 채널에 먼저 들어가주세요.")

    url, title = queue.pop(0)

    def after_playing(error):
        if error:
            print(f"재생 중 오류: {error}")
        if not queue:
            asyncio.run_coroutine_threadsafe(vc.disconnect(), client.loop)
        else:
            asyncio.run_coroutine_threadsafe(play_next(interaction), client.loop)
#최적화 옵션 삽입
    vc.play(discord.FFmpegPCMAudio(
    url,
    before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"))
    await interaction.channel.send(f"▶️ `{title}` 재생 중입니다.")

# ⏭️ 스킵
@tree.command(name="스킵", description="현재 음악을 스킵합니다.")
async def 스킵(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await interaction.response.send_message("⏭️ 다음 곡으로 넘어갑니다.")
        await asyncio.sleep(1)  # ffmpeg가 완전히 종료될 시간을 줌
        await play_next(interaction)  # 다음 곡 재생
    else:
        await interaction.response.send_message("❌ 현재 재생 중인 곡이 없습니다.")

# ⏹️ 정지
@tree.command(name="정지", description="음악을 정지하고 큐를 초기화합니다.")
async def 정지(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        vc.stop()
        queue.clear()
        await interaction.response.send_message("⏹️ 정지 및 큐 초기화 완료")
    else:
        await interaction.response.send_message("❌ 재생 중인 음악이 없습니다.")

# 📋 큐 보기
@tree.command(name="큐", description="현재 음악 큐를 확인합니다.")
async def 큐보기(interaction: discord.Interaction):
    if not queue:
        await interaction.response.send_message("📭 큐가 비어 있습니다.")
    else:
        msg = "\n".join([f"{i+1}. {title}" for i, (_, title) in enumerate(queue)])
        await interaction.response.send_message(f"📃 현재 큐 목록:\n{msg}")

# ❌ 음성채널 나가기
@tree.command(name="나가", description="음성 채널에서 나갑니다.")
async def 나가(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        await vc.disconnect()
        await interaction.response.send_message("👋 음성 채널에서 나갔습니다.")
    else:
        await interaction.response.send_message("❌ 음성 채널에 있지 않습니다.")

# Oracle 인스턴스 켜기
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

# Oracle 인스턴스 끄기
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

# Oracle 인스턴스 상태 확인
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

# ✅ 봇 시작 이벤트
@client.event
async def on_ready():
    await tree.sync()
    print("✅ 봇 준비 완료 및 명령어 동기화됨")

client.run(TOKEN)