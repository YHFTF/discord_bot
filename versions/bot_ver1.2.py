import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
from urllib.parse import urlparse, parse_qs, urlencode
import google.generativeai as genai
import os

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


# ✅ 봇 시작 이벤트
@client.event
async def on_ready():
    global 욕설_목록
    욕설_목록 = 욕설_불러오기()
    욕설_카운트_불러오기()
    await tree.sync()
    print("✅ 봇 준비 완료 및 명령어 동기화됨")

client.run(TOKEN)