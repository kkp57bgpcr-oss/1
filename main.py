import os
import json
import asyncio
import time
from datetime import datetime
from telethon import TelegramClient, events

# ============ 1. 核心配置 ============
# 建议在 Railway 的 Variables 中设置，或者直接填在这里
API_ID = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"
BOT_API_TOKEN = "8417331227:AAESrsOPgEDMeu7NHgLMgoZrynkxoafBLBY"
ADMIN_ID = 6649617045  # 确保这里是你的数值 ID

# 签到机器人列表（初始默认）
SIGN_IN_BOTS = [
    {"name": "山东小纸条", "bot_username": "sdxhzbot", "command": "/qd"},
    {"name": "今日社工库", "bot_username": "jrsgk6_bot", "command": "/checkin"},
    {"name": "好望社工库", "bot_username": "haowangshegongkubot", "command": "/sign"},
    {"name": "优享", "bot_username": "youxs520_bot", "command": "/sign"},
    {"name": "云储", "bot_username": "yunchu_bot", "command": "/qd"},
    {"name": "mw社工库", "bot_username": "mwsgkbot", "command": "/qd"}
]

# 状态记录
sign_in_status = {}

# ============ 2. 核心业务逻辑 ============

async def sign_in_to_bot(client, bot_config):
    """发送签到指令"""
    try:
        await client.send_message(bot_config["bot_username"], bot_config["command"])
        sign_in_status[bot_config["bot_username"]] = {
            "last_sign_in": time.time(),
            "success": True,
            "name": bot_config["name"]
        }
        return True
    except Exception as e:
        sign_in_status[bot_config["bot_username"]] = {
            "last_sign_in": time.time(),
            "success": False,
            "name": bot_config["name"],
            "error": str(e)
        }
        return False

async def sign_in_loop(client):
    """定时任务：每天北京时间 12:00 和 00:00 (UTC+8)"""
    while True:
        try:
            # 获取当前北京时间 (假设服务器是 UTC)
            now = datetime.utcnow() 
            hour_bj = (now.hour + 8) % 24
            
            if hour_bj in [0, 12]:
                print(f"[{datetime.now()}] 执行定时签到...")
                for bot in SIGN_IN_BOTS:
                    await sign_in_to_bot(client, bot)
                    await asyncio.sleep(5)
                await asyncio.sleep(3600) # 防止同一小时重复触发
            await asyncio.sleep(60)
        except Exception as e:
            await asyncio.sleep(60)

# ============ 3. 机器人控制 UI (你原来的界面) ============

async def start_bot_control(user_client):
    # 为控制机器人使用独立的 session 避免冲突
    bot_client = TelegramClient("bot_control.session", API_ID, API_HASH)
    await bot_client.start(bot_token=BOT_API_TOKEN)
    
    @bot_client.on(events.NewMessage)
    async def bot_handler(event):
        if event.sender_id != ADMIN_ID: return
        
        text = event.message.text or ""
        cmd = text.strip().lower()

        if cmd in ["/start", "/help", "帮助"]:
            help_text = """🤖 控制命令:

📋 状态查询:
/status - 查看状态
/list - 查看签到机器人列表

✨ 签到控制:
/sign_now - 立即签到一次
/add_bot 名称 @用户名 命令 - 添加签到机器人
/del_bot @用户名 - 删除签到机器人

📝 手动消息:
/send @用户名 消息 - 发送消息

🔧 其他:
/help - 查看帮助"""
            await event.reply(help_text)

        elif cmd == "/status":
            res = "📊 当前状态:\n\n"
            res += f"签到库数量: {len(SIGN_IN_BOTS)}\n\n记录:\n"
            for user, info in sign_in_status.items():
                icon = "✅" if info["success"] else "❌"
                t = datetime.fromtimestamp(info["last_sign_in"]).strftime("%H:%M:%S")
                res += f"{icon} {info['name']} (@{user}): {t}\n"
            await event.reply(res or "暂无执行记录")

        elif cmd == "/list":
            res = "📋 签到机器人列表:\n\n"
            for i, b in enumerate(SIGN_IN_BOTS, 1):
                res += f"{i}. {b['name']}\n   @{b['bot_username']} {b['command']}\n"
            await event.reply(res)

        elif cmd == "/sign_now":
            await event.reply("🔄 正在执行全量签到...")
            for b in SIGN_IN_BOTS:
                await sign_in_to_bot(user_client, b)
                await asyncio.sleep(3)
            await event.reply("✨ 签到任务执行完毕，发送 /status 查看结果")

        elif cmd.startswith("/add_bot"):
            try:
                p = text.split(maxsplit=3)
                SIGN_IN_BOTS.append({"name": p[1], "bot_username": p[2].replace("@",""), "command": p[3]})
                await event.reply(f"✅ 已添加: {p[1]}")
            except: await event.reply("格式: /add_bot 名称 @用户名 命令")

        elif cmd.startswith("/del_bot"):
            user = text.replace("/del_bot", "").strip().replace("@", "")
            global SIGN_IN_BOTS
            SIGN_IN_BOTS = [b for b in SIGN_IN_BOTS if b["bot_username"] != user]
            await event.reply(f"✅ 已删除 @{user}")

        elif cmd.startswith("/send"):
            try:
                p = text.split(maxsplit=2)
                target = p[1].replace("@", "")
                await user_client.send_message(target, p[2])
                await event.reply(f"✅ 消息已发给 @{target}")
            except: await event.reply("格式: /send @用户名 消息")

    await bot_client.run_until_disconnected()

# ============ 4. 启动入口 ============

async def main():
    # 自动加载上传的 session 文件
    user_client = TelegramClient("my_account.session", API_ID, API_HASH)
    await user_client.connect()

    if not await user_client.is_user_authorized():
        print("❌ 错误：请在本地生成 my_account.session 并上传！")
        return

    print("🚀 铭自动签到系统已在 Railway 启动")
    await asyncio.gather(
        sign_in_loop(user_client),
        start_bot_control(user_client)
    )

if __name__ == "__main__":
    asyncio.run(main())
