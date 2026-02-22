import os
import json
import asyncio
import time
from datetime import datetime
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError

# ============ 1. 核心配置 ============
API_ID = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"
BOT_TOKEN = "8505048236:AAFHPC3448Gti60whSAC9mak_oKzd7BN1eY"
ADMIN_ID = 6649617045  # 你的原始 ID

# 存储路径
SESSION_PATH = "/app/my_account"
BOT_SESSION_PATH = "/app/bot_control"
DATA_PATH = "/app/bots_data.json"
AUTH_PATH = "/app/authorized_users.json"

# ============ 2. 数据持久化逻辑 ============

def load_data(path, default):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: return default
    return default

def save_data(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 初始加载
SIGN_IN_BOTS = load_data(DATA_PATH, [])
AUTHORIZED_USERS = load_data(AUTH_PATH, [ADMIN_ID])
sign_in_status = {}
login_data = {}

# ============ 3. 核心功能函数 ============

async def sign_in_to_bot(user_client, bot_config):
    try:
        await user_client.send_message(bot_config["bot_username"], bot_config["command"])
        sign_in_status[bot_config["bot_username"]] = {
            "last_time": time.time(), "success": True, "name": bot_config["name"]
        }
        return True
    except Exception as e:
        sign_in_status[bot_config["bot_username"]] = {
            "last_time": time.time(), "success": False, "name": bot_config["name"], "error": str(e)
        }
        return False

# ============ 4. 机器人逻辑 ============

async def main():
    bot = TelegramClient(BOT_SESSION_PATH, API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    
    user_client = TelegramClient(
        SESSION_PATH, API_ID, API_HASH,
        device_model="iPhone 15 Pro",
        system_version="iOS 17.4.1",
        app_version="10.10.1"
    )
    await user_client.connect()

    @bot.on(events.NewMessage)
    async def handler(event):
        global SIGN_IN_BOTS, AUTHORIZED_USERS
        
        # 权限检查
        if event.sender_id not in AUTHORIZED_USERS:
            if event.raw_text.startswith("/"):
                await event.reply("⚠️ **权限不足**\n您不在授权名单中，请联系管理员。")
            return
        
        text = event.raw_text.strip()
        cmd_parts = text.split()
        cmd = cmd_parts[0].lower() if cmd_parts else ""

        # 登录流程处理
        if event.chat_id in login_data:
            state = login_data[event.chat_id]
            if state['step'] == 'phone':
                state['phone'] = text
                try:
                    res = await user_client.send_code_request(text)
                    state['hash'], state['step'] = res.phone_code_hash, 'code'
                    await event.reply("📩 **验证码已发送**\n请查看 Telegram 官方通知并在此回复：")
                except Exception as e:
                    await event.reply(f"❌ 发送失败: {e}"); del login_data[event.chat_id]
            elif state['step'] == 'code':
                try:
                    await user_client.sign_in(state['phone'], text, phone_code_hash=state['hash'])
                    await event.reply("🎉 **登录成功**\n托管账号已接入 iPhone 15 Pro 环境。"); del login_data[event.chat_id]
                except SessionPasswordNeededError:
                    state['step'] = '2fa'; await event.reply("🔐 **二级密码**\n请输入您的两步验证密码：")
                except Exception as e:
                    await event.reply(f"❌ 登录失败: {e}"); del login_data[event.chat_id]
            elif state['step'] == '2fa':
                try:
                    await user_client.sign_in(password=text)
                    await event.reply("🎉 **密码正确，登录成功！**"); del login_data[event.chat_id]
                except Exception as e:
                    await event.reply(f"❌ 密码错误: {e}")
            return

        # --- UI 指令集 ---
        if cmd in ["/start", "/help", "帮助"]:
            help_text = """🤖 **控制中心 (已授权)**

📊 **状态与查询**
/status - 系统运行状态
/list - 查看签到机器人
/myid - 查看你的数字 ID

✨ **签到管理**
/login - 登录托管账号
/sign_now - 立即执行全量签到
/add_bot `[名] [@名] [指令]` - 添加
/del_bot `[@用户名]` - 删除

📝 **手动发信**
/send `[@用户名] [消息]` - 模拟发送

🔑 **管理员权限**
/auth `[用户ID]` - 授权新用户"""
            await event.reply(help_text)

        elif cmd == "/myid":
            await event.reply(f"👤 **你的 ID**: `{event.sender_id}`")

        elif cmd == "/auth":
            if event.sender_id != ADMIN_ID:
                await event.reply("❌ 仅超级管理员可执行授权"); return
            try:
                uid = int(cmd_parts[1])
                if uid not in AUTHORIZED_USERS:
                    AUTHORIZED_USERS.append(uid)
                    save_data(AUTH_PATH, AUTHORIZED_USERS)
                    await event.reply(f"✅ **已添加授权**: `{uid}`")
                else:
                    await event.reply("ℹ️ 该用户已在白名单中。")
            except:
                await event.reply("❌ 格式: `/auth 12345678`")

        elif cmd == "/status":
            auth = await user_client.is_user_authorized()
            res = f"📊 **系统当前状态**\n"
            res += f"━━━━━━━━━━━━━━\n"
            res += f"托管状态: {'🟢 iPhone 15 Pro 在线' if auth else '🔴 离线 (请 /login)'}\n"
            res += f"授权用户: {len(AUTHORIZED_USERS)} 人\n\n"
            if sign_in_status:
                for u, info in sign_in_status.items():
                    icon = "✅" if info["success"] else "❌"
                    res += f"{icon} {info['name']} (@{u})\n"
            else:
                res += "📝 暂无今日签到执行记录。"
            await event.reply(res)

        elif cmd == "/add_bot":
            try:
                name, username, command = cmd_parts[1], cmd_parts[2].replace("@", ""), cmd_parts[3]
                SIGN_IN_BOTS.append({"name": name, "bot_username": username, "command": command})
                save_data(DATA_PATH, SIGN_IN_BOTS)
                await event.reply(f"✅ **添加成功**\n已永久保存机器人: {name}")
            except:
                await event.reply("❌ 格式: `/add_bot 名称 @用户名 命令`")

        elif cmd == "/list":
            if not SIGN_IN_BOTS:
                await event.reply("📭 **列表为空**\n请使用 `/add_bot` 添加签到任务。")
                return
            res = "📋 **永久签到列表**\n━━━━━━━━━━━━━━\n"
            for i, b in enumerate(SIGN_IN_BOTS, 1):
                res += f"{i}. {b['name']} (@{b['bot_username']}) -> `{b['command']}`\n"
            await event.reply(res)

        elif cmd == "/del_bot":
            try:
                username = cmd_parts[1].replace("@", "")
                SIGN_IN_BOTS = [b for b in SIGN_IN_BOTS if b["bot_username"] != username]
                save_data(DATA_PATH, SIGN_IN_BOTS)
                await event.reply(f"🗑️ **已删除**: @{username}")
            except:
                await event.reply("❌ 格式: `/del_bot @用户名`")

        elif cmd == "/login":
            if await user_client.is_user_authorized():
                await event.reply("✅ 账号当前已在线。")
            else:
                await event.reply("📱 **手机号**\n请输入要托管的手机号 (带+86)：")
                login_data[event.chat_id] = {'step': 'phone'}

        elif cmd == "/sign_now":
            if not await user_client.is_user_authorized():
                await event.reply("❌ 请先 /login"); return
            await event.reply("🔄 **执行中**\n全量签到任务已开始...")
            for b in SIGN_IN_BOTS:
                await sign_in_to_bot(user_client, b)
                await asyncio.sleep(5)
            await event.reply("✨ **任务已完成**")

        elif cmd == "/send":
            try:
                target = cmd_parts[1].replace("@", "")
                msg_content = text.split(maxsplit=2)[2]
                await user_client.send_message(target, msg_content)
                await event.reply(f"✅ **已发送**\n目标: @{target}")
            except Exception as e:
                await event.reply(f"❌ 错误: {e}\n用法: `/send @用户名 内容`")

    # 定时器 (00:05 / 12:05)
    async def timer():
        while True:
            now = datetime.utcnow()
            if (now.hour + 8) % 24 in [0, 12] and now.minute == 5:
                current_list = load_data(DATA_PATH, [])
                if await user_client.is_user_authorized():
                    for b in current_list:
                        await sign_in_to_bot(user_client, b)
                        await asyncio.sleep(5)
                await asyncio.sleep(3600)
            await asyncio.sleep(30)

    await asyncio.gather(bot.run_until_disconnected(), timer())

if __name__ == "__main__":
    asyncio.run(main())
