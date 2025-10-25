import asyncio
import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream.input_stream import AudioPiped
from pydub import AudioSegment, effects
from config import API_ID, API_HASH, BOT_TOKEN, SESSION_STRING, OWNER_ID, BOOSTED_FILENAME, TMP_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------ Clients ------------------
bot = Client("bass_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
assistant = Client("assistant", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# ------------------ State -------------------
pytg = None
playing_state = {"is_playing": False, "chat_id": None, "file_path": None}


# ------------------ Audio Processing ------------------
async def convert_to_extreme_bass(input_path: str, output_path: str):
    """Convert audio to extreme bass"""
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(2).set_frame_rate(48000)
    low = audio.low_pass_filter(200).apply_gain(+18)
    mid = audio.high_pass_filter(200).apply_gain(+6)
    boosted = low.overlay(mid)
    boosted = effects.normalize(boosted).apply_gain(+8)
    boosted.export(output_path, format="mp3")
    return output_path


# ------------------ Owner Voice Handler ------------------
@bot.on_message(filters.private & filters.user(OWNER_ID) & filters.voice)
async def owner_voice_handler(c: Client, m: Message):
    await m.reply_text("🎵 **Voice received!** Processing for **extreme bass**... 🔊")
    in_path = await bot.download_media(
        m.voice.file_id, file_name=os.path.join(TMP_DIR, "incoming_voice.ogg")
    )
    try:
        out_path = BOOSTED_FILENAME
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: convert_to_extreme_bass(in_path, out_path)
        )
        playing_state['file_path'] = out_path
        await m.reply_text(
            "✅ **Processing complete!**\nSend the **group chat ID** (-100...) to play or `/cancel` to abort."
        )
    except Exception as e:
        logger.exception(e)
        await m.reply_text("⚠️ Failed to process audio.")
    finally:
        try:
            os.remove(in_path)
        except Exception:
            pass


# ------------------ Receive Chat ID ------------------
@bot.on_message(filters.private & filters.user(OWNER_ID) & filters.regex(r'^-?\d+$'))
async def receive_chat_id(c: Client, m: Message):
    chat_id = int(m.text.strip())
    if not playing_state.get('file_path'):
        return await m.reply_text("❌ No processed audio found. Send a voice first.")

    await m.reply_text(f"🔊 Joining **VC of chat {chat_id}**...")

    global pytg
    if pytg is None:
        pytg = PyTgCalls(assistant)
        pytg.start()

    @pytg.on_stream_end()
    async def _(_, update):
        if playing_state['is_playing'] and playing_state['chat_id'] == update.chat_id:
            await pytg.change_stream(update.chat_id, AudioPiped(playing_state['file_path']))

    try:
        playing_state['is_playing'] = True
        playing_state['chat_id'] = chat_id
        await pytg.join_group_call(chat_id, AudioPiped(playing_state['file_path']))
        await m.reply_text("▶️ **Playing now!** Use `/stopdj` to stop.")
    except Exception as e:
        logger.exception(e)
        await m.reply_text(f"❌ Failed to play: {e}")


# ------------------ Stop Handler ------------------
@bot.on_message(filters.private & filters.user(OWNER_ID) & filters.command("stopdj"))
async def stop_handler(c: Client, m: Message):
    if not playing_state['is_playing']:
        return await m.reply_text("⚠️ Nothing is currently playing.")

    try:
        chat_id = playing_state['chat_id']
        playing_state['is_playing'] = False
        if pytg:
            await pytg.leave_group_call(chat_id)
        await m.reply_text("⏹️ **Stopped playback.**")
    except Exception as e:
        logger.exception(e)
        await m.reply_text("⚠️ Could not stop.")


# ------------------ Main ------------------
async def main():
    os.makedirs(TMP_DIR, exist_ok=True)
    await bot.start()
    await assistant.start()
    logger.info("🎧 Bass bot started. Waiting for owner commands...")
    await asyncio.Event().wait()


if __name__ == '__main__':
    asyncio.run(main())


async def main():
    os.makedirs(TMP_DIR, exist_ok=True)
    await bot.start()
    await assistant.start()
    logger.info("🎶 Bass bot started. Waiting for owner's voice…")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
