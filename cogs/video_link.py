import discord
import re
import aiohttp
import asyncio
import io
import yt_dlp
from discord.ext import commands

URL_REGEX = re.compile(r'https?://[^\s<>"\']+')
YOUTUBE_REGEX = re.compile(r'(youtube\.com|youtu\.be)', re.IGNORECASE)

GIF_REGEX = re.compile(
    r'(tenor\.com|giphy\.com|\.gif(\?|$))',
    re.IGNORECASE,
)

VIDEO_EXTENSIONS = ('.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv')

MAX_FILE_SIZE = {
    0: 25 * 1024 * 1024,
    1: 25 * 1024 * 1024,
    2: 50 * 1024 * 1024,
    3: 100 * 1024 * 1024,
}

YDL_OPTS = {
    'format': 'best[filesize<25M]/best[ext=mp4]/best',
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'noplaylist': True,
    'socket_timeout': 15,
}


class VideoLink(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _get_max_size(self, guild: discord.Guild) -> int:
        if guild is None:
            return 25 * 1024 * 1024
        return MAX_FILE_SIZE.get(guild.premium_tier, 25 * 1024 * 1024)

    def _is_youtube(self, url: str) -> bool:
        return bool(YOUTUBE_REGEX.search(url))

    def _is_gif(self, url: str) -> bool:
        return bool(GIF_REGEX.search(url))

    def _is_discord_embeddable(self, url: str) -> bool:
        return bool(DISCORD_EMBEDDABLE_REGEX.search(url))

    def _should_skip(self, url: str) -> bool:
        return self._is_youtube(url) or self._is_gif(url) or self._is_discord_embeddable(url)

    async def _check_direct_video(self, session: aiohttp.ClientSession, url: str) -> bool:
        try:
            async with session.head(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                content_type = resp.headers.get('Content-Type', '')
                if content_type.startswith('video/'):
                    return True
        except Exception:
            pass

        parsed = url.split('?')[0].lower()
        return any(parsed.endswith(ext) for ext in VIDEO_EXTENSIONS)

    async def _download_direct(self, session: aiohttp.ClientSession, url: str, max_size: int) -> bytes | None:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status != 200:
                    return None
                content_length = resp.headers.get('Content-Length')
                if content_length and int(content_length) > max_size:
                    return None
                data = await resp.read()
                if len(data) > max_size:
                    return None
                return data
        except Exception:
            return None

    async def _extract_with_ytdlp(self, url: str, max_size: int) -> dict | None:
        size_mb = max_size // (1024 * 1024)
        opts = {
            **YDL_OPTS,
            'format': f'best[filesize<{size_mb}M][ext=mp4]/best[filesize<{size_mb}M]/best[ext=mp4]/best',
        }

        def _extract():
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if info is None:
                        return None

                    video_url = info.get('url')
                    if not video_url:
                        formats = info.get('formats', [])
                        for f in reversed(formats):
                            if f.get('vcodec', 'none') != 'none' and f.get('url'):
                                fsize = f.get('filesize') or f.get('filesize_approx') or 0
                                if fsize == 0 or fsize <= max_size:
                                    video_url = f['url']
                                    break

                    if not video_url:
                        return None

                    return {
                        'url': video_url,
                        'ext': info.get('ext', 'mp4'),
                        'title': info.get('title', 'video'),
                        'http_headers': info.get('http_headers', {}),
                    }
            except Exception:
                return None

        return await asyncio.get_event_loop().run_in_executor(None, _extract)

    async def _download_video(self, session: aiohttp.ClientSession, url: str, max_size: int, headers: dict = None) -> bytes | None:
        try:
            req_headers = headers or {}
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=120), headers=req_headers) as resp:
                if resp.status != 200:
                    return None
                content_length = resp.headers.get('Content-Length')
                if content_length and int(content_length) > max_size:
                    return None

                chunks = []
                total = 0
                async for chunk in resp.content.iter_chunked(1024 * 1024):
                    total += len(chunk)
                    if total > max_size:
                        return None
                    chunks.append(chunk)
                return b''.join(chunks)
        except Exception:
            return None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        urls = URL_REGEX.findall(message.content)
        if not urls:
            return

        non_yt_urls = [u for u in urls if not self._should_skip(u)]
        if not non_yt_urls:
            return

        max_size = self._get_max_size(message.guild)

        async with message.channel.typing():
            async with aiohttp.ClientSession() as session:
                for url in non_yt_urls[:3]:
                    try:
                        is_direct = await self._check_direct_video(session, url)

                        if is_direct:
                            data = await self._download_direct(session, url, max_size)
                            if data:
                                ext = 'mp4'
                                for e in VIDEO_EXTENSIONS:
                                    if url.split('?')[0].lower().endswith(e):
                                        ext = e.lstrip('.')
                                        break
                                file = discord.File(io.BytesIO(data), filename=f'video.{ext}')
                                await message.reply(file=file, mention_author=False)
                                continue

                        info = await self._extract_with_ytdlp(url, max_size)
                        if info is None:
                            continue

                        data = await self._download_video(
                            session,
                            info['url'],
                            max_size,
                            headers=info.get('http_headers'),
                        )
                        if data is None:
                            continue

                        ext = info.get('ext', 'mp4')
                        file = discord.File(io.BytesIO(data), filename=f'video.{ext}')
                        await message.reply(file=file, mention_author=False)

                    except Exception:
                        continue


async def setup(bot):
    await bot.add_cog(VideoLink(bot))
