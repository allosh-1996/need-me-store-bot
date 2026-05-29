from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import database as db
import keyboards as kb
from config import USDT_WALLET, SYRIATEL_CASH, ADMIN_ID, PAYMENT_MSG
from lang import t, get_user_lang

WAITING_PROOF = 1

# ═══════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username or "", user.full_name or "")
    lang = get_user_lang(context)
    # شيل الـ ReplyKeyboard القديم بأول رسالة حقيقية
    await update.message.reply_text(
        "👋",
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        t("welcome", lang),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.main_menu(lang)
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_lang(context)
    if lang == "en":
        text = (
            "*Commands*\n\n"
            "`/start` — Home\n"
            "`/products` — Products\n"
            "`/charge` — Top Up\n"
            "`/help` — Help"
        )
    else:
        text = (
            "*الاوامر*\n\n"
            "`/start` — الرئيسية\n"
            "`/products` — المنتجات\n"
            "`/charge` — شحن رصيد\n"
            "`/help` — مساعدة"
        )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ═══════════════════════════════════════
async def toggle_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    current = get_user_lang(context)
    new_lang = "en" if current == "ar" else "ar"
    context.user_data["lang"] = new_lang
    await query.edit_message_text(
        t("welcome", new_lang),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.main_menu(new_lang)
    )

# ═══════════════════════════════════════
async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    lang = get_user_lang(context)

    platform_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("iOS", callback_data="platform_iOS"),
         InlineKeyboardButton("Android", callback_data="platform_Android")],
        [InlineKeyboardButton(t("back", lang), callback_data="back_main")],
    ])

    text = f"*NexVault Shop*\n\n_{t('choose_platform', lang)}_"
    if query:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=platform_kb)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=platform_kb)

async def show_platform_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(context)
    platform = query.data.replace("platform_", "")
    context.user_data['selected_platform'] = platform

    products = db.get_all_products()
    platform_products = [p for p in products if platform in (p.get('platform') or 'iOS')]

    if not platform_products:
        await query.edit_message_text(
            t("no_products_platform", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t("back", lang), callback_data="products")]])
        )
        return

    categories = list(set(p['category'] for p in platform_products if p['category']))
    text = f"*{platform}*\n\n_{t('choose_category', lang)}_"
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=kb.categories_menu(categories, back_cb="products", lang=lang))

async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(context)
    category = query.data.replace("cat_", "")
    platform = context.user_data.get('selected_platform', '')

    EMAIL_CATS = ['Outlook', 'Gmail', 'Hotmail']
    GAME_CATS = ['Coin Master', 'Domino Dream', 'Disney Dream', 'Screw Guru', 'Travel Town', 'Dice Dream']
    if category in EMAIL_CATS:
        context.user_data['cat_source'] = 'emails_menu'
    elif category in GAME_CATS:
        context.user_data['cat_source'] = 'win_appsflyer'
    elif platform == 'Surveys':
        context.user_data['cat_source'] = 'surveys_menu'
    elif platform:
        context.user_data['cat_source'] = f'platform_{platform}'
    else:
        context.user_data['cat_source'] = 'products'

    products = db.get_all_products()
    if platform == 'Surveys':
        cat_products = [p for p in products if p['category'] == category and (p.get('platform') or '') == 'Surveys']
    elif platform and category not in EMAIL_CATS and category not in GAME_CATS:
        cat_products = [p for p in products if p['category'] == category and platform in (p.get('platform') or 'iOS')]
    else:
        cat_products = [p for p in products if p['category'] == category]

    back_cb = context.user_data['cat_source']

    if not cat_products:
        await query.edit_message_text(
            t("no_products_category", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t("back", lang), callback_data=back_cb)]])
        )
        return

    text = f"*{category}*\n\n_{t('choose_product', lang)}_"
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=kb.products_menu(cat_products, lang=lang, back_cb=back_cb))

async def show_product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(context)
    product_id = int(query.data.replace("prod_", ""))

    product = db.get_product(product_id)
    if not product:
        await query.edit_message_text(t("error_not_found", lang))
        return

    stock_count = db.get_stock_count(product_id)
    has_stock = stock_count > 0
    platform = product.get('platform', '') or ''

    stock_line = f"{t('in_stock', lang)} ({stock_count} units)" if has_stock else t('out_of_stock', lang)
    text = (
        f"*{product['name']}*\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{product['description'] or t('no_desc', lang)}\n"
        f"Platform: `{platform}`\n\n"
        f"USD: `${product['price_usd']}`\n"
        f"SYP: `{product['price_syp']:,.0f}`\n\n"
        f"{stock_line}\n"
        f"━━━━━━━━━━━━━━━━"
    )
    back_cb = context.user_data.get('cat_source', 'products')
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=kb.product_detail_menu(product_id, has_stock, lang=lang, back_cb=back_cb))

async def initiate_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(context)
    parts = query.data.split("_")
    product_id = int(parts[1])
    currency = parts[2].upper() if len(parts) > 2 else "USD"
    context.user_data['buy_currency'] = currency

    user = update.effective_user
    product = db.get_product(product_id)

    stock_count = db.get_stock_count(product_id)
    if not product or stock_count == 0:
        await query.edit_message_text(t("no_products_category", lang), parse_mode=ParseMode.MARKDOWN)
        return

    balance = db.get_balance(user.id)
    price = product["price_usd"]
    price_syp = product["price_syp"]
    display_price = f"${price}" if currency == "USD" else f"{price_syp:,.0f}"

    if balance >= price:
        confirm_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{t('buy_from_balance', lang)} — ${price}", callback_data=f"confirm_buy_{product_id}")],
            [InlineKeyboardButton("USDT BEP-20", callback_data=f"pay_{product_id}_{currency}_usdt")],
            [InlineKeyboardButton("Syriatel Cash", callback_data=f"pay_{product_id}_{currency}_syriatel")],
            [InlineKeyboardButton(t("back", lang), callback_data=f"prod_{product_id}")]
        ])
        text = (
            f"*{t('choose_payment', lang)}*\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"{product['name']}\n"
            f"{t('amount', lang)}: `{display_price}`\n"
            f"{t('balance', lang)}: `${balance:.2f}`\n"
            f"━━━━━━━━━━━━━━━━"
        )
    else:
        needed = price - balance
        confirm_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("USDT BEP-20", callback_data=f"pay_{product_id}_{currency}_usdt")],
            [InlineKeyboardButton("Syriatel Cash", callback_data=f"pay_{product_id}_{currency}_syriatel")],
            [InlineKeyboardButton(f"{t('top_up', lang)} — ${needed:.2f}", callback_data="charge_start")],
            [InlineKeyboardButton(t("back", lang), callback_data=f"prod_{product_id}")]
        ])
        text = (
            f"*{product['name']}*\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"{t('amount', lang)}: `{display_price}`\n"
            f"{t('balance', lang)}: `${balance:.2f}`\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"_{t('insufficient_balance', lang)}_"
        )
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=confirm_kb)

async def show_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(context)
    parts = query.data.split("_")
    product_id = int(parts[1])
    currency = parts[2].upper()
    method = parts[3]

    product = db.get_product(product_id)
    user = update.effective_user

    order_id = db.create_order(
        user_id=user.id, username=user.username or "",
        full_name=user.full_name or "", product_id=product_id,
        product_name=product['name'], price_usd=product['price_usd'],
        price_syp=product['price_syp'], currency=currency,
        payment_method=method
    )
    context.user_data['pending_order_id'] = order_id
    price = f"${product['price_usd']}" if currency == "USD" else f"{product['price_syp']:,.0f}"

    if method == "usdt":
        payment_text = (
            f"*USDT Payment*\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"{t('amount', lang)}: `{price}`\n\n"
            f"{t('wallet_address', lang)}:\n`{USDT_WALLET}`\n\n"
            f"*{t('bep20_only', lang)}*\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"{t('send_receipt', lang)}"
        )
    else:
        payment_text = (
            f"*Syriatel Cash*\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"{t('amount', lang)}: `{price}`\n\n"
            f"{t('number', lang)}:\n`{SYRIATEL_CASH}`\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"{t('send_receipt_syriatel', lang)}"
        )

    await query.edit_message_text(
        payment_text + f"\n\n{t('order_id', lang)}: `#{order_id}`",
        parse_mode=ParseMode.MARKDOWN
    )
    return WAITING_PROOF

async def receive_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_lang(context)

    if update.message and update.message.text:
        txt = update.message.text.strip()
        if any(x in txt for x in ["ابدأ", "Start"]):
            return await persistent_start(update, context)

    order_id = context.user_data.get('pending_order_id')
    if not order_id:
        await update.message.reply_text(t("session_expired", lang))
        return ConversationHandler.END

    user = update.effective_user
    order = db.get_order(order_id)

    if update.message.photo:
        proof = update.message.photo[-1].file_id
        proof_type = "photo"
    elif update.message.document:
        proof = update.message.document.file_id
        proof_type = "document"
    else:
        proof = update.message.text
        proof_type = "text"

    db.update_order_proof(order_id, proof)

    admin_text = (
        f"*New Order #{order_id}*\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{user.full_name} (@{user.username or '—'})\n"
        f"`{user.id}`\n"
        f"{order['product_name']}\n"
        f"${order['price_usd']}  |  {order['price_syp']:,.0f}\n"
        f"{order['payment_method'].upper()}\n"
        f"━━━━━━━━━━━━━━━━"
    )

    try:
        if proof_type == "photo":
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=proof,
                caption=admin_text, parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.order_confirm_menu(order_id))
        else:
            await context.bot.send_message(chat_id=ADMIN_ID,
                text=admin_text + f"\nReceipt: `{proof}`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.order_confirm_menu(order_id))
    except Exception as e:
        print(f"Admin notify error: {e}")

    await update.message.reply_text(
        f"*{t('order_received', lang)}*\n\n{t('order_id', lang)}: `#{order_id}`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.main_menu(lang)
    )
    context.user_data.pop('pending_order_id', None)
    return ConversationHandler.END

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    lang = get_user_lang(context)
    user = update.effective_user
    orders = db.get_user_orders(user.id)

    back_kb = InlineKeyboardMarkup([[InlineKeyboardButton(t("back", lang), callback_data="back_main")]])

    if not orders:
        text = f"*{t('my_orders', lang)}*\n\n_{t('no_orders', lang)}_"
        if query:
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_kb)
        else:
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_kb)
        return

    status_map = {
        "pending": t("status_pending", lang),
        "completed": t("status_completed", lang),
        "rejected": t("status_rejected", lang)
    }
    lines = [f"*{t('my_orders', lang)}*\n", "━━━━━━━━━━━━━━━━"]
    for o in orders:
        status = status_map.get(o["status"], "?")
        lines.append(f"{status}  `#{o['id']}` — {o['product_name']}")
    lines.append("━━━━━━━━━━━━━━━━")
    text = "\n".join(lines)

    if query:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_kb)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_kb)

async def payment_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(context)
    text = PAYMENT_MSG.format(usdt_wallet=USDT_WALLET, syriatel_cash=SYRIATEL_CASH)
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb.main_menu(lang))

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(context)
    await query.edit_message_text(
        f"*{t('contact_title', lang)}*\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"@Allosh96ha\n\n"
        f"_{t('contact_reply', lang)}_\n"
        f"━━━━━━━━━━━━━━━━",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.main_menu(lang)
    )

async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(context)
    await query.edit_message_text(
        t("welcome", lang),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.main_menu(lang)
    )

async def persistent_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_lang(context)
    db.upsert_user(user.id, user.username or "", user.full_name or "")
    for k in ['charge_amount','charge_method','charge_display','charge_amount_syp','pending_order_id','buy_currency']:
        context.user_data.pop(k, None)
    await update.message.reply_text(
        t("welcome", lang),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.main_menu(lang)
    )
    return ConversationHandler.END

async def handle_persistent_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    lang = get_user_lang(context)

    if any(x in text for x in ["Start", "ابدأ"]):
        await persistent_start(update, context)

    elif any(x in text for x in ["Support", "دعم"]):
        await update.message.reply_text(
            f"*{t('support_title', lang)}*\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"@Allosh96ha\n\n"
            f"_{t('support_body', lang)}_\n"
            f"━━━━━━━━━━━━━━━━",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.persistent_menu(lang)
        )

    elif any(x in text for x in ["About", "عن المتجر"]):
        await update.message.reply_text(
            f"*{t('about_title', lang)}*\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"{t('about_body', lang)}\n"
            f"━━━━━━━━━━━━━━━━",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.persistent_menu(lang)
        )

async def confirm_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    FIX: يستخدم buy_with_balance() — خصم الرصيد وسحب المنتج في transaction واحدة atomic.
    لا يمكن الحصول على منتج بدون خصم رصيد أو العكس.
    """
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(context)
    product_id = int(query.data.replace("confirm_buy_", ""))

    user = update.effective_user
    product = db.get_product(product_id)

    if not product:
        await query.edit_message_text(t("no_products_category", lang), parse_mode=ParseMode.MARKDOWN)
        return

    price = product['price_usd']

    try:
        # FIX: عملية atomic واحدة — خصم + سحب معاً أو لا شيء
        item, new_balance, remaining = db.buy_with_balance(user.id, product_id, price)
    except ValueError as e:
        err = str(e)
        if err.startswith("insufficient_balance:"):
            balance = float(err.split(":")[1])
            await query.edit_message_text(
                f"*{t('insufficient_balance', lang)}*\n\n"
                f"{t('balance', lang)}: `${balance:.2f}`\n"
                f"{t('amount', lang)}: `${price}`\n\n"
                f"_{t('top_up_first', lang)}_",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(t("top_up", lang), callback_data="charge_start")],
                    [InlineKeyboardButton(t("back", lang), callback_data=f"prod_{product_id}")]
                ])
            )
        else:
            # out_of_stock أو transaction_error
            await query.edit_message_text(t("no_products_category", lang), parse_mode=ParseMode.MARKDOWN)
        return

    order_id = db.create_order(
        user_id=user.id, username=user.username or "",
        full_name=user.full_name or "", product_id=product_id,
        product_name=product['name'], price_usd=price,
        price_syp=product['price_syp'], currency="USD",
        payment_method="balance", delivered_item=item
    )
    db.update_order_status(order_id, 'completed', 'balance')

    done_kb = InlineKeyboardMarkup([[InlineKeyboardButton(t("home", lang), callback_data="back_main")]])
    await query.edit_message_text(
        f"*{t('purchase_success', lang)}*\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{product['name']}\n"
        f"{t('amount', lang)}: `${price}`\n"
        f"{t('balance', lang)}: `${new_balance:.2f}`\n\n"
        f"*{t('product_details', lang)}:*\n`{item}`\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"_{t('thank_you', lang)}_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=done_kb
    )
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"*New Sale #{order_id}*\n{user.full_name}\n{product['name']}\n${price} (Balance)\nStock remaining: {remaining}",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception:
        pass

# ═══════════════════════════════════════
# إيميلات
# ═══════════════════════════════════════
async def emails_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(context)

    kb_emails = InlineKeyboardMarkup([
        [InlineKeyboardButton("Outlook", callback_data="cat_Outlook")],
        [InlineKeyboardButton("Gmail", callback_data="cat_Gmail")],
        [InlineKeyboardButton("Hotmail", callback_data="cat_Hotmail")],
        [InlineKeyboardButton(t("back", lang), callback_data="back_main")],
    ])
    await query.edit_message_text(
        f"*{t('emails_title', lang)}*\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"_{t('choose_type', lang)}_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb_emails
    )



# ═══════════════════════════════════════
# Proxy Menu — رسالة تواصل مباشر
# ═══════════════════════════════════════
async def proxy_menu_simple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(context)

    text = (
        "🌐 *Proxy Service*\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "We offer multiple proxy types:\n\n"
        "• HTTP / HTTPS\n"
        "• SOCKS5\n"
        "• Residential\n"
        "• Mobile 4G / 5G\n"
        "• Modem Private\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "📩 To order, contact the admin directly:\n"
        "👤 @Allosh96ha\n"
        "━━━━━━━━━━━━━━━━"
    )

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 تواصل مع الأدمن", url="https://t.me/Allosh96ha")],
        ])
    )


# ═══════════════════════════════════════
# Surveys
# ═══════════════════════════════════════
async def surveys_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قائمة Surveys — يجيب الفئات من DB تلقائياً (category حيث platform='Surveys')"""
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(context)

    context.user_data['selected_platform'] = 'Surveys'
    context.user_data['cat_source'] = 'surveys_menu'

    products = db.get_all_products()
    survey_products = [p for p in products if (p.get('platform') or '') == 'Surveys']

    if not survey_products:
        await query.edit_message_text(
            f"*Surveys*\n\n_{t('no_surveys', lang)}_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t("back", lang), callback_data="back_main")
            ]])
        )
        return

    # جيب الفئات الفريدة بالترتيب
    categories = list(dict.fromkeys(
        p['category'] for p in survey_products if p.get('category')
    ))

    await query.edit_message_text(
        f"*Surveys*\n\n_{t('choose_survey_category', lang)}_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.categories_menu(categories, back_cb="back_main", lang=lang)
    )

# ═══════════════════════════════════════
# iCloud
# ═══════════════════════════════════════
async def icloud_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يفتح قائمة منتجات iCloud — نفس نظام المنتجات الحالي"""
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(context)

    # حدد platform iOS تلقائياً
    context.user_data['selected_platform'] = 'iOS'
    context.user_data['cat_source'] = 'icloud_menu'

    products = db.get_all_products()
    ios_products = [p for p in products if 'iOS' in (p.get('platform') or 'iOS')]

    if not ios_products:
        await query.edit_message_text(
            t("no_products_platform", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(t("back", lang), callback_data="back_main")
            ]])
        )
        return

    # جيب الفئات
    categories = list(dict.fromkeys(
        p['category'] for p in ios_products if p.get('category')
    ))

    await query.edit_message_text(
        f"*iCloud*\n\n_{t('choose_category', lang)}_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.categories_menu(categories, back_cb="back_main", lang=lang)
    )

# ═══════════════════════════════════════
# Win AppsFlyer
# ═══════════════════════════════════════
async def win_appsflyer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يحول مباشرة لـ handlers_appsflyer.appsflyer_menu"""
    import handlers_appsflyer as haf
    return await haf.appsflyer_menu(update, context)

# ═══════════════════════════════════════
# Commands: /change_language و /support
# ═══════════════════════════════════════
async def change_language_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغيير اللغة مباشرة عبر /change_language"""
    current = get_user_lang(context)
    new_lang = "en" if current == "ar" else "ar"
    context.user_data["lang"] = new_lang
    await update.message.reply_text(
        t("welcome", new_lang),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.main_menu(new_lang)
    )

async def support_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دعم عبر /support"""
    lang = get_user_lang(context)
    await update.message.reply_text(
        f"*{t('support_title', lang)}*\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"@Allosh96ha\n\n"
        f"_{t('support_body', lang)}_\n"
        f"━━━━━━━━━━━━━━━━",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.main_menu(lang)
    )
