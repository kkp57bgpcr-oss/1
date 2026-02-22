import os
import asyncio
import time
from datetime import datetime
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError

# ============ 1. 核心配置 ============
API_ID = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"
BOT_TOKEN = "8505048236:AAFHPC3448Gti60whSAC9mak_oKzd7BN1eY"
ADMIN_ID = 6649617045

# 存储路径（配合 Railway Volume）
SESSION_PATH = "/app/my_account"
BOT_SESSION_PATH = "/app/bot_control"

# 初始签到列表
SIGN_IN_BOTS = [
    {"name": "山东小纸条", "bot_username": "sdxhzbot", "command": "/qd"},
    {"name": "今日社工库", "bot_username": "jrsgk6_bot", "command": "/checkin"},
    {"name": "好望社工库", "bot_username": "haowangshegongkubot", "command": "/sign"},
    {"name": "优享", "bot_username": "youxs520_bot", "command": "/sign"},
    {"name": "云储", "bot_username": "yunchu_bot", "command": "/qd"},
    {"name": "mw社工库", "bot_username": "mwsgkbot", "command": "/qd"}
]

sign_in_status = {}
login_data = {}

# ============ 2. 核心功能 ============

async def sign_in_to_bot(user_client, bot_config):
    """执行单个签到"""
    try:
        await user_client.send_message(bot_config["bot_username"], bot_config["command"])
        sign_in_status[bot_config["bot_username"]] = {
            "last_time": time.time(),
            "success": True,
            "name": bot_config["name"]
        }
        return True
    except Exception as e:
        sign_in_status[bot_config["bot_username"]] = {
            "last_time": time.time(),
            "success": False,
            "name": bot_config["name"],
            "error": str(e)
        }
        return False

# ============ 3. 机器人控制 UI & 指令 ============

async def main():
    # 启动控制端
    bot = TelegramClient(BOT_SESSION_PATH, API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    
    # 启动托管端
    user_client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await user_client.connect()

    print("🚀 铭自动签到系统已就绪...")

    @bot.on(events.NewMessage)
    async def handler(event):
        global SIGN_IN_BOTS
        if event.sender_id != ADMIN_ID: return
        
        text = event.raw_text.strip()
        cmd = text.lower()

        # --- 登录对话流 ---
        if text == "/login":
            if await user_client.is_user_authorized():
                await event.reply("✅ 账号已在线，无需重复登录。")
            else:
                await event.reply("📱 请输入托管手机号 (带国家码，如 +86138...)：")
                login_data[event.chat_id] = {'step': 'phone'}
            return

        if event.chat_id in login_data:
            state = login_data[event.chat_id]
            if state['step'] == 'phone':
                state['phone'] = text
                try:
                    res = await user_client.send_code_request(text)
                    state['hash'], state['step'] = res.phone_code_hash, 'code'
                    await event.reply("📩 验证码已发送，请输入 5 位验证码：")
                except Exception as e:
                    await event.reply(f"❌ 发送失败: {e}"); del login_data[event.chat_id]
            elif state['step'] == 'code':
                try:
                    await user_client.sign_in(state['phone'], text, phone_code_hash=state['hash'])
                    await event.reply("🎉 登录成功！托管账号已激活。"); del login_data[event.chat_id]
                except SessionPasswordNeededError:
                    state['step'] = '2fa'; await event.reply("🔐 请输入两步验证密码：")
                except Exception as e:
                    await event.reply(f"❌ 登录失败: {e}"); del login_data[event.chat_id]
            elif state['step'] == '2fa':
                try:
                    await user_client.sign_in(password=text)
                    await event.reply("🎉 密码正确，登录成功！"); del login_data[event.chat_id]
                except Exception as e:
                    await event.reply(f"❌ 密码错误: {e}")
            return

        # --- 标准控制命令 (你原来的 UI) ---
        if cmd in ["/start", "/help", "帮助"]:
            help_text = """🤖 控制命令:

📋 状态查询:
/status - 查看状态
/list - 查看签到机器人列表

✨ 签到控制:
/login - 登录/切换账号
/sign_now - 立即签到一次
/add_bot 名称 @用户名 命令 - 添加
/del_bot @用户名 - 删除

📝 手动消息:
/send @用户名 消息 - 发送消息

🔧 其他:
/help - 查看帮助"""
            await event.reply(help_text)

        elif cmd == "/status":
            auth = await user_client.is_user_authorized()
            res = f"📊 **系统状态**: {'🟢 在线' if auth else '🔴 离线 (请 /login)'}\n\n"
            if sign_in_status:
                for u, info in sign_in_status.items():
                    icon = "✅" if info["success"] else "❌"
                    t = datetime.fromtimestamp(info["last_time"]).strftime("%H:%M:%S")
                    res += f"{icon} {info['name']} (@{u}): {t}\n"
            else: res += "暂无执行记录。"
            await event.reply(res)

        elif cmd == "/list":
            res = "📋 **签到列表**:\n\n"
            for i, b in enumerate(SIGN_IN_BOTS, 1):
                res += f"{i}. {b['name']} (@{b['bot_username']}) -> `{b['command']}`\n"
            await event.reply(res)

        elif cmd == "/sign_now":
            if not await user_client.is_user_authorized():
                await event.reply("❌ 请先 /login 登录托管账号"); return
            await event.reply("🔄 正在全量签到...")
            for b in SIGN_IN_BOTS:
                await sign_in_to_bot(user_client, b)
                await asyncio.sleep(3)
            await event.reply("✨ 任务完成！")

        elif cmd.startswith("/add_bot"):
            try:
                p = text.split(maxsplit=3)
                SIGN_IN_BOTS.append({"name": p[1], "bot_username": p[2].replace("@",""), "command": p[3]})
                await event.reply(f"✅ 已添加: {p[1]}")
            except: await event.reply("用法: /add_bot 名称 @用户名 命令")

        elif cmd.startswith("/del_bot"):
            user = text.replace("/del_bot", "").strip().replace("@", "")
            SIGN_IN_BOTS = [b for b in SIGN_IN_BOTS if b["bot_username"] != user]
            await event.reply(f"✅ 已删除 @{user}")

        elif cmd.startswith("/send"):
            try:
                p = text.split(maxsplit=2)
                await user_client.send_message(p[1].replace("@",""), p[2])
                await event.reply(f"✅ 消息已发送至 @{p[1]}")
            except Exception as e: await event.reply(f"❌ 发送失败: {e}")

    # 定时循环 (UTC+8 00:05 和 12:05)
    async def timer():
        while True:
            now = datetime.utcnow()
            hour_bj = (now.hour + 8) % 24
            if hour_bj in [0, 12] and now.minute == 5:
                if await user_client.is_user_authorized():
                    for b in SIGN_IN_BOTS:
                        await sign_in_to_bot(user_client, b)
                        await asyncio.sleep(5)
                await asyncio.sleep(3600)
            await asyncio.sleep(30)

    await asyncio.gather(bot.run_until_disconnected(), timer())

if __name__ == "__main__":
    asyncio.run(main())
