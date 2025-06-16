import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
from urllib.parse import urlparse, parse_qs, urlencode
import google.generativeai as genai
import os
from discord import Embed, ButtonStyle
from discord.ui import View, Button
import math
import time

TOKEN = ''
INSTANCE_OCID = ''
GOOGLE_API_KEY = ''
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

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
    
from discord import Embed, ButtonStyle
from discord.ui import View, Button
import math

from discord import Embed, ButtonStyle, Interaction
from discord.ui import View, Button
import math
import time

from discord import Embed, ButtonStyle, Interaction
from discord.ui import View, Button
import math
import time
import asyncio

from discord import Embed, ButtonStyle, Interaction
from discord.ui import View, Button
import math
import time
import asyncio

last_embed_message = None  # 이전 임벤드 메시지 저장할 기억자

# ▶️ 음악 재생
@tree.command(name="재생", description="유튜브에서 노래를 재생합니다.")
async def 재생(interaction: discord.Interaction, raw_url: str):
    global last_embed_message
    checking_msg = await interaction.response.send_message(f"🎵 입력 확인 중...")

    url = 정리된_유튜브_URL(raw_url)
    if not url:
        return await interaction.followup.send("❌ 잘못된 유튜브 링크입니다. 전체 URL을 입력해주세요.")

    ytdlp_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'nocheckcertificate': True,
        'no_warnings': True,
        'cookiefile': '/home/ubuntu/bot/youtube_cookies.txt',
        'source_address': '0.0.0.0'
    }

    try:
        with yt_dlp.YoutubeDL(ytdlp_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info['url']
            title = info['title']
            duration = info.get('duration', 0)
            video_id = info.get('id', '')
    except Exception as e:
        return await interaction.followup.send(f"❌ 오류: {str(e)[:150]}")

    vc = interaction.guild.voice_client
    if not vc or not vc.is_playing():
        queue.append((audio_url, title, url, duration, video_id, interaction.user.display_name))
        await start_playback(interaction)
    else:
        queue.append((audio_url, title, url, duration, video_id, interaction.user.display_name))
        await interaction.followup.send(f"🎶 `{title}`(이)가 큐에 추가되었습니다.")

async def start_playback(interaction: discord.Interaction):
    global last_embed_message
    if not queue:
        return

    audio_url, title, url, duration, video_id, requester = queue.pop(0)

    def format_duration(seconds):
        return f"{seconds // 60}:{str(seconds % 60).zfill(2)}"

    total_slots = 20
    thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

    def make_embed(current_sec: int):
        progress = min(math.floor((current_sec / duration) * total_slots), total_slots - 1) if duration else 0
        bar = "━" * progress + "⬤" + "━" * (total_slots - progress - 1)
        embed = Embed(
            title="노래 재생 중 🎵",
            description=f"[{title}]({url})",
            color=0x1DB954
        )
        embed.set_thumbnail(url=thumbnail_url)
        embed.add_field(
            name="⏱️ 재생 상황",
            value=f"({format_duration(current_sec)}) {bar} ({format_duration(duration)})",
            inline=False
        )
        embed.set_footer(text=f"신청자: {requester}")
        return embed

    class MusicControlView(View):
        def __init__(self, vc):
            super().__init__(timeout=None)
            self.vc = vc

        @discord.ui.button(label="⏹️ 정지", style=ButtonStyle.danger, custom_id="stop")
        async def stop_button(self, interaction: Interaction, button: Button):
            if self.vc:
                self.vc.stop()
                queue.clear()
                await interaction.response.send_message("🔚 재생 중지 및 큐 초기화되었습니다.", ephemeral=True)

        @discord.ui.button(label="⏭️ 스킵", style=ButtonStyle.primary, custom_id="skip")
        async def skip_button(self, interaction: Interaction, button: Button):
            if self.vc and self.vc.is_playing():
                self.vc.stop()
                await interaction.response.send_message("⏭️ 스킵되었습니다.", ephemeral=True)

        @discord.ui.button(label="🎶 큐 보기", style=ButtonStyle.secondary, custom_id="show_queue")
        async def queue_button(self, interaction: Interaction, button: Button):
            if not queue:
                await interaction.response.send_message("📍 큐가 비어 있습니다.", ephemeral=True)
            else:
                msg = "\n".join([f"{i+1}. {title}" for i, (_, title, *_ ) in enumerate(queue)])
                await interaction.response.send_message(f"📃 현재 큐:\n{msg}", ephemeral=True)

    voice = interaction.user.voice
    if not voice:
        return await interaction.channel.send("❌ 음성 채널에 먼저 들어가주세요.")

    vc = interaction.guild.voice_client or await voice.channel.connect()
    vc.play(discord.FFmpegPCMAudio(audio_url, before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"))

    view = MusicControlView(vc)

    # 이전 임벤드 메시지 삭제
    if last_embed_message:
        try:
            await last_embed_message.delete()
        except:
            pass

    last_embed_message = await interaction.channel.send(embed=make_embed(0), view=view)

    start_time = time.time()
    while vc.is_playing():
        elapsed = int(time.time() - start_time)
        if elapsed >= duration:
            break
        try:
            await last_embed_message.edit(embed=make_embed(elapsed), view=view)
        except discord.NotFound:
            break
        await asyncio.sleep(2)

    await asyncio.sleep(1)
    await start_playback(interaction)

    # 노래 종료 후 60초 동안 입력이 없으면 채널 나가기
    if vc.is_connected() and not vc.is_playing() and not queue:
        await asyncio.sleep(60)
        if vc.is_connected() and not vc.is_playing() and not queue:
            try:
                if last_embed_message:
                    try:
                        await last_embed_message.delete()
                    except:
                        pass
                await vc.disconnect()
                await interaction.channel.send("📣 1분간 입력이 없어 채널을 나갔습니다.")
            except:
                pass

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

    if vc.is_playing():  # 이미 재생 중이면 중복 재생 방지
        return

    url, title = queue.pop(0)

    def after_playing(error):
        if error:
            print(f"재생 중 오류: {error}")
        fut = asyncio.run_coroutine_threadsafe(
            play_next(interaction) if queue else vc.disconnect(),
            client.loop
        )
        try:
            fut.result()
        except Exception as e:
            print(f"콜백 처리 중 예외 발생: {e}")
#최적화 옵션 삽입
    vc.play(discord.FFmpegPCMAudio(
    url,
    before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"))
    await interaction.channel.send(f"▶️ `{title}` 재생 중입니다.")

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

system_prompt = (
    "너는 '박의 비서'라는 이름의 디스코드 봇이야. "
    "너는 박영현을 보좌하는 비서야. "
    "항상 간결하게, 5줄 이내로 답변해줘."
)

@tree.command(name="채팅", description="'박의 비서'에게 질문을 합니다.")
@app_commands.describe(prompt="물어보고 싶은 내용을 입력하세요.")
async def 채팅(interaction: discord.Interaction, prompt: str):
    await interaction.response.send_message("💬 '박의 비서'에게 물어보는 중입니다...")

    try:
        full_prompt = system_prompt + "\n\n질문: " + prompt
        response = model.generate_content(full_prompt)
        text = response.text.strip()
        if not text:
            text = "⚠️ 대답이 비어있어요. 다시 시도해보세요."
    except Exception as e:
        text = f"❌ 오류 발생: {str(e)[:200]}"

    await (await interaction.original_response()).delete()
    await interaction.followup.send(text)

# 🔥 욕설 감지용 글로벌 변수
욕설_목록 = []
욕설_카운트 = {}

# ✅ 욕설 목록 불러오기
def 욕설_불러오기(path="fwords.txt") -> list[str]:
    try:
        with open(path, encoding="utf-8") as f:
            return [line.strip().lower() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"⚠️ '{path}' 파일이 없습니다.")
        return []

# ✅ 사용자 욕설 카운트 저장
def 욕설_카운트_저장(path="fword_user.txt"):
    with open(path, "w", encoding="utf-8") as f:
        for user_id, count in 욕설_카운트.items():
            f.write(f"{user_id} {count}\n")

# ✅ 사용자 욕설 카운트 불러오기
def 욕설_카운트_불러오기(path="fword_user.txt"):
    global 욕설_카운트
    욕설_카운트 = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 2 and parts[1].isdigit():
                    욕설_카운트[parts[0]] = int(parts[1])

# ✅ 메시지에서 욕설 포함 여부 확인
def 욕설포함(text: str) -> bool:
    lowered = text.lower()
    return any(bad in lowered for bad in 욕설_목록)

def 욕설_횟수세기(text: str) -> int:
    lowered = text.lower()
    return sum(lowered.count(bad) for bad in 욕설_목록)

@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    count = 욕설_횟수세기(message.content)  # ← 실행 결과를 변수에 저장
    if count > 0:
        user_id = str(message.author.id)
        욕설_카운트[user_id] = 욕설_카운트.get(user_id, 0) + count
        욕설_카운트_저장()
        print(f"🤬 {message.author.display_name} 욕설 {count}회 → 총 {욕설_카운트[user_id]}회")

# ✅ 슬래시 명령어로 통계 출력
@tree.command(name="욕통계", description="유저별 욕설 사용 횟수를 확인합니다.")
async def 욕통계(interaction: discord.Interaction):
    if not 욕설_카운트:
        await interaction.response.send_message("✅ 욕설 기록이 없습니다.")
        return

    lines = []
    for user_id, count in 욕설_카운트.items():
        try:
            user = await interaction.guild.fetch_member(int(user_id))
            lines.append(f"👤 {user.display_name} — {count}회")
        except:
            lines.append(f"❓ [알 수 없음] — {count}회")

    sorted_lines = sorted(lines, key=lambda line: -int(line.split()[-1][:-1]))  # 많은 순 정렬
    msg = "\n".join(sorted_lines)
    await interaction.response.send_message(f"# 욕설 통계:\n{msg}")


@tree.command(name="예시", description="풍부한 노래 정보 임베드 메시지 예시")
async def 예시(interaction: discord.Interaction):
    embed = Embed(
        title="노래 재생 중",
        description="[ILLIT (아일릿) 'Magnetic'](https://www.youtube.com/watch?v=dummy)",
        color=0x7289DA
    )
    embed.set_thumbnail(url="https://i.ytimg.com/vi/dummy/hqdefault.jpg")  # 썸네일
    embed.add_field(name="재생 시간", value="2분 전 ———— 40초 후\n(0:00)━━━━━⬤────── (3:09)", inline=False)
    embed.set_footer(text="신청자: 트레이닝 | 남은 확률: 50% | 오늘 오후 8:51")

    view = View()
    view.add_item(Button(label="정지", style=ButtonStyle.danger))
    view.add_item(Button(label="구간 이동", style=ButtonStyle.blurple))
    view.add_item(Button(label="일시정지", style=ButtonStyle.secondary))
    view.add_item(Button(label="▶️ 스킵", style=ButtonStyle.primary))
    view.add_item(Button(label="매일 놀러 음악 추가하기", style=ButtonStyle.success, url="https://example.com"))

    await interaction.response.send_message(embed=embed, view=view)


# ✅ 봇 시작 이벤트
@client.event
async def on_ready():
    global 욕설_목록
    욕설_목록 = 욕설_불러오기()
    욕설_카운트_불러오기()
    await tree.sync()
    print("✅ 봇 준비 완료 및 명령어 동기화됨")

client.run(TOKEN)