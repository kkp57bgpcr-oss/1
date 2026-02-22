import os
import json
import asyncio
import time
from datetime import datetime
from telethon import TelegramClient, events

# ============ 1. 核心配置 ============
API_ID = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"
BOT_API_TOKEN = "8505048236:AAFHPC3448Gti60whSAC9mak_oKzd7BN1eY"
ADMIN_ID = 6649617045  # 确保这里是你的数值 ID

# 签到机器人列表
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
    """定时任务：北京时间 12:00 和 00:00"""
    print("⏰ 定时签到轮询已启动...")
    while True:
        try:
            now = datetime.utcnow() 
            hour_bj = (now.hour + 8) % 24
            if hour_bj in [0, 12]:
                for bot in SIGN_IN_BOTS:
                    await sign_in_to_bot(client, bot)
                    await asyncio.sleep(5)
                await asyncio.sleep(3600)
            await asyncio.sleep(60)
        except:
            await asyncio.sleep(60)

# ============ 3. 机器人控制 UI ============

async def start_bot_control(user_client):
    bot_client = TelegramClient("bot_control.session", API_ID, API_HASH)
    await bot_client.start(bot_token=BOT_API_TOKEN)
    print("🤖 机器人控制端已上线!")

    @bot_client.on(events.NewMessage)
    async def bot_handler(event):
        # 必须先声明全局变量，才能在逻辑中修改它
        global SIGN_IN_BOTS
        
        if event.sender_id != ADMIN_ID:
            return
        
        text = event.message.text or ""
        cmd = text.strip().lower()

        if cmd in ["/start", "/help", "帮助"]:
            help_text = """🤖 控制命令:
📋 状态查询:
/status - 查看状态
/list - 查看列表

✨ 签到控制:
/sign_now - 立即签到一次
/add_bot 名称 @用户名 命令
/del_bot @用户名

📝 手动消息:
/send @用户名 消息

🔧 其他:
/help - 查看帮助"""
            await event.reply(help_text)

        elif cmd == "/status":
            res = "📊 当前状态:\n\n"
            for user, info in sign_in_status.items():
                icon = "✅" if info["success"] else "❌"
                t = datetime.fromtimestamp(info["last_sign_in"]).strftime("%H:%M:%S")
                res += f"{icon} {info['name']}: {t}\n"
            await event.reply(res if sign_in_status else "暂无执行记录，请发送 /sign_now 测试")

        elif cmd == "/list":
            res = "📋 列表:\n"
            for i, b in enumerate(SIGN_IN_BOTS, 1):
                res += f"{i}. {b['name']} (@{b['bot_username']})\n"
            await event.reply(res)

        elif cmd == "/sign_now":
            await event.reply("🔄 正在签到...")
            for b in SIGN_IN_BOTS:
                await sign_in_to_bot(user_client, b)
                await asyncio.sleep(2)
            await event.reply("✨ 完成！发送 /status 查看结果")

        elif cmd.startswith("/add_bot"):
            try:
                p = text.split(maxsplit=3)
                SIGN_IN_BOTS.append({"name": p[1], "bot_username": p[2].replace("@",""), "command": p[3]})
                await event.reply(f"✅ 已添加: {p[1]}")
            except:
                await event.reply("格式: /add_bot 名称 @用户名 命令")

        elif cmd.startswith("/del_bot"):
            target_user = text.replace("/del_bot", "").strip().replace("@", "")
            SIGN_IN_BOTS = [b for b in SIGN_IN_BOTS if b["bot_username"] != target_user]
            await event.reply(f"✅ 已删除 @{target_user}")

        elif cmd.startswith("/send"):
            try:
                p = text.split(maxsplit=2)
                await user_client.send_message(p[1].replace("@",""), p[2])
                await event.reply("✅ 已发送")
            except:
                await event.reply("格式: /send @用户名 消息")

    await bot_client.run_until_disconnected()

# ============ 4. 启动入口 ============

async def main():
    # 确保文件夹里有这个 session 文件
    user_client = TelegramClient("my_account.session", API_ID, API_HASH)
    await user_client.connect()

    if not await user_client.is_user_authorized():
        print("❌ 错误：my_account.session 未授权！")
        return

    print("🚀 系统已启动...")
    await asyncio.gather(
        sign_in_loop(user_client),
        start_bot_control(user_client)
    )

if __name__ == "__main__":
    asyncio.run(main())
