from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import database as db
import keyboards as kb
from config import ADMIN_ID, USDT_WALLET

WAITING_METHOD, WAITING_AMOUNT, WAITING_TXHASH = range(20, 23)

async def charge_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    user = update.effective_user
    balance = db.get_balance(user.id)

    method_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙 USDT BEP-20  (دولار  |  USD)", callback_data="chg_method_usdt")],
        [InlineKeyboardButton("📱 Syriatel Cash  (ليرة سورية  |  SYP)", callback_data="chg_method_syriatel")],
        [InlineKeyboardButton("🔙 Back  |  رجوع", callback_data="back_main")]
    ])

    text = (
        f"⚡ *Top Up  |  شحن الرصيد*\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"💰 Current Balance  |  رصيدك: `${balance:.2f}`\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"_اختر طريقة الشحن  |  Choose payment method:_"
    )

    if query:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=method_kb)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=method_kb)

    return WAITING_METHOD

async def charge_method_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data.replace("chg_method_", "")
    context.user_data["charge_method"] = method

    if method == "usdt":
        text = (
            f"🪙 *USDT BEP-20 Top Up*\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📋 Wallet Address  |  عنوان المحفظة:\n"
            f"`{USDT_WALLET}`\n\n"
            f"⚠️ *BEP-20 Network Only*\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💵 كم دولار تريد تشحن؟ \n"
            f"_How much USD to top up? _"
        )
    else:
        from config import SYRIATEL_CASH
        text = (
            f"📱 *Syriatel Cash Top Up*\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📞 Number  |  الرقم:\n"
            f"`{SYRIATEL_CASH}`\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💴 كم ليرة تريد تشحن؟ \n"
            f"_How much SYP? _"
        )

    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
    return WAITING_AMOUNT

async def charge_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    method = context.user_data.get("charge_method", "usdt")
    raw = update.message.text.strip().replace("$", "").replace(",", "").replace("،", "")

    try:
        amount = float(raw)
    except ValueError:
        await update.message.reply_text("🔴 أرسل رقم فقط  |  Send a number only (e.g. 5 or 50000)")
        return WAITING_AMOUNT

    if method == "usdt":
        if amount > 10000:
            await update.message.reply_text("🔴 الحد الأقصى $10,000  |  Maximum $10,000")
            return WAITING_AMOUNT
        display = f"${amount}"
    else:
        display = f"{amount:,.0f} ل.س"

    context.user_data["charge_amount"] = amount
    context.user_data["charge_display"] = display

    cancel_kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel  |  إلغاء", callback_data="back_main")]])
    await update.message.reply_text(
        f"✅ Amount  |  المبلغ: `{display}`\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📸 أرسل صورة الإيصال أو TXID 👇\n"
        f"_Send receipt screenshot or transaction ID_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=cancel_kb
    )
    return WAITING_TXHASH

async def charge_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    amount = context.user_data.get("charge_amount", 0)
    method = context.user_data.get("charge_method", "usdt")
    display = context.user_data.get("charge_display", f"${amount}")
    method_label = "USDT BEP-20" if method == "usdt" else "Syriatel Cash"

    if not amount:
        await update.message.reply_text(
            "🔴 انتهت الجلسة  |  Session expired. Start again.",
            reply_markup=kb.persistent_menu()
        )
        return ConversationHandler.END

    if update.message.photo:
        proof = update.message.photo[-1].file_id
        proof_type = "photo"
        tx_hash = update.message.caption or "photo"
    elif update.message.document:
        proof = update.message.document.file_id
        proof_type = "document"
        tx_hash = update.message.caption or "file"
    else:
        proof = update.message.text or ""
        proof_type = "text"
        tx_hash = proof

    try:
        req_id = db.create_charge_request(user_id=user.id, username=user.username or "",
            full_name=user.full_name or "", amount_usd=amount, tx_hash=tx_hash, method=method)
        db.update_charge_proof(req_id, proof)
    except Exception as e:
        print(f"DB Error: {e}")
        await update.message.reply_text("🔴 خطأ في الحفظ  |  Save error, try again.")
        return ConversationHandler.END

    admin_text = (
        f"💰 *Top Up Request  |  طلب شحن* `#{req_id}`\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👤 {user.full_name} (@{user.username or '—'})\n"
        f"🆔 `{user.id}`\n"
        f"💵 Amount: `{display}`\n"
        f"💳 Method: `{method_label}`\n"
        f"🔗 TXID: `{tx_hash[:60]}`\n"
        f"━━━━━━━━━━━━━━━━"
    )

    admin_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"✅ Confirm {display}", callback_data=f"chg_confirm_{req_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"chg_reject_{req_id}")
    ]])

    try:
        if proof_type == "photo":
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=proof,
                caption=admin_text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_kb)
        elif proof_type == "document":
            await context.bot.send_document(chat_id=ADMIN_ID, document=proof,
                caption=admin_text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_kb)
        else:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text,
                parse_mode=ParseMode.MARKDOWN, reply_markup=admin_kb)
    except Exception as e:
        print(f"Admin notify error: {e}")

    done_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Home  |  الرئيسية", callback_data="back_main")]])
    await update.message.reply_text(
        f"✅ *Top Up Request Sent!  |  تم إرسال طلب الشحن!*\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🔖 Request ID: `#{req_id}`\n"
        f"💵 Amount: `{display}`\n"
        f"💳 Method: {method_label}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"⏳ _سيتم مراجعة التحويل وإضافة الرصيد قريباً_\n"
        f"_Balance will be added after review_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=done_kb
    )

    for k in ["charge_amount", "charge_method", "charge_display"]:
        context.user_data.pop(k, None)
    return ConversationHandler.END

async def charge_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop('charge_amount', None)
    await update.message.reply_text("❌ Cancelled  |  تم الإلغاء", reply_markup=kb.persistent_menu())
    return ConversationHandler.END

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    user = update.effective_user
    balance = db.get_balance(user.id)

    conn = db.get_conn()
    c = conn.cursor()
    c.execute("SELECT total_charged, total_spent FROM balances WHERE user_id=?", (user.id,))
    row = c.fetchone()
    conn.close()

    total_charged = row['total_charged'] if row else 0
    total_spent = row['total_spent'] if row else 0

    bal_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Top Up  |  شحن رصيد", callback_data="charge_start")],
        [InlineKeyboardButton("🔙 Back  |  رجوع", callback_data="back_main")]
    ])

    text = (
        f"💰 *My Balance  |  رصيدي*\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"💵 Balance: `${balance:.2f}`\n"
        f"📥 Total Charged: `${total_charged:.2f}`\n"
        f"📤 Total Spent: `${total_spent:.2f}`\n"
        f"━━━━━━━━━━━━━━━━"
    )

    if query:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=bal_kb)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=bal_kb)

async def admin_confirm_charge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return

    req_id = int(query.data.replace("chg_confirm_", ""))
    req = db.get_charge_request(req_id)

    if not req:
        try:
            await query.edit_message_caption("🔴 الطلب غير موجود  |  Not found")
        except:
            await query.edit_message_text("🔴 Not found")
        return

    # ✅ بس غير الحالة لـ pending_manual — بدون ما يضيف رصيد
    db.reject_charge(req_id)  # نغلق الطلب
    # نعيد فتحه بحالة جديدة
    conn = db.get_conn()
    c = conn.cursor()
    c.execute("UPDATE charge_requests SET status='accepted' WHERE id=?", (req_id,))
    conn.commit()
    conn.close()

    # إشعار المستخدم إن الطلب قُبل وبانتظار الإضافة
    try:
        await context.bot.send_message(
            chat_id=req['user_id'],
            text=(
                f"✅ *Request Accepted!  |  تم قبول طلبك!*\n\n"
                f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                f"💵 Amount: `${req['amount_usd']}`\n\n"
                f"⏳ _سيتم إضافة الرصيد قريباً_\n"
                f"_Balance will be added shortly_ 🚀\n"
                f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.main_menu()
        )
    except Exception as e:
        print(f"Notify error: {e}")

    try:
        await query.edit_message_caption(
            f"✅ Accepted #{req_id} — ${req['amount_usd']} for {req['full_name']}\n"
            f"⚠️ أضف الرصيد يدوياً من الداشبورد → المستخدمين"
        )
    except:
        await query.edit_message_text(
            f"✅ Accepted `#{req_id}` — `${req['amount_usd']}` for {req['full_name']}\n"
            f"⚠️ أضف الرصيد يدوياً من الداشبورد → المستخدمين",
            parse_mode=ParseMode.MARKDOWN
        )

async def admin_reject_charge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return

    req_id = int(query.data.replace("chg_reject_", ""))
    req = db.get_charge_request(req_id)
    db.reject_charge(req_id)

    try:
        await context.bot.send_message(
            chat_id=req['user_id'],
            text=(
                f"🔴 *Top Up Rejected  |  تم رفض طلب الشحن*\n\n"
                f"🔖 Request ID: `#{req_id}`\n\n"
                f"_للاستفسار تواصل مع الأدمن_\n"
                f"_Contact admin for more info_"
            ),
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        pass

    try:
        await query.edit_message_caption(f"🔴 Rejected #{req_id}")
    except:
        await query.edit_message_text(f"🔴 Rejected `#{req_id}`", parse_mode=ParseMode.MARKDOWN)
