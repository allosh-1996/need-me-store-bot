from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import database as db
import keyboards as kb
from config import ADMIN_ID
from lang import t, get_user_lang


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username or "", user.full_name or "")
    lang = get_user_lang(context)
    await update.message.reply_text("👋", reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text(
        t("welcome", lang),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.main_menu(lang)
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_lang(context)
    if lang == "en":
        text = "*Commands*\n\n`/start` — Home\n`/products` — Products\n`/charge` — Top Up\n`/help` — Help"
    else:
        text = "*الاوامر*\n\n`/start` — الرئيسية\n`/products` — المنتجات\n`/charge` — شحن رصيد\n`/help` — مساعدة"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def change_language_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current = get_user_lang(context)
    new_lang = "en" if current == "ar" else "ar"
    context.user_data["lang"] = new_lang
    await update.message.reply_text(
        t("welcome", new_lang),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.main_menu(new_lang)
    )


async def support_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    lang = get_user_lang(context)

    products = db.get_all_products()
    categories = list(dict.fromkeys(p['category'] for p in products if p.get('category')))

    text = f"*NexVault Shop*\n\n_{t('choose_category', lang)}_"
    if query:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                      reply_markup=kb.categories_menu(categories, back_cb="back_main", lang=lang))
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN,
                                        reply_markup=kb.categories_menu(categories, back_cb="back_main", lang=lang))


async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(context)
    category = query.data.replace("cat_", "")

    products = db.get_all_products()
    cat_products = [p for p in products if p['category'] == category]

    back_cb = context.user_data.get('cat_source', 'products')

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
    stock_line = f"{t('in_stock', lang)} ({stock_count} units)" if has_stock else t('out_of_stock', lang)

    text = (
        f"*{product['name']}*\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{product['description'] or t('no_desc', lang)}\n\n"
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
    product_id = int(query.data.split("_")[1])

    user = update.effective_user
    product = db.get_product(product_id)

    if not product or db.get_stock_count(product_id) == 0:
        await query.edit_message_text(t("no_products_category", lang), parse_mode=ParseMode.MARKDOWN)
        return

    balance = db.get_balance(user.id)
    price = product["price_usd"]

    if balance >= price:
        confirm_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"✅ {t('buy_from_balance', lang)} — ${price}", callback_data=f"confirm_buy_{product_id}")],
            [InlineKeyboardButton(t("back", lang), callback_data=f"prod_{product_id}")]
        ])
        text = (
            f"*{product['name']}*\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"{t('amount', lang)}: `${price}`\n"
            f"{t('balance', lang)}: `${balance:.2f}`\n"
            f"━━━━━━━━━━━━━━━━"
        )
    else:
        needed = price - balance
        confirm_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"💳 {t('top_up', lang)} — ${needed:.2f}", callback_data="charge_start")],
            [InlineKeyboardButton(t("back", lang), callback_data=f"prod_{product_id}")]
        ])
        text = (
            f"*{product['name']}*\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"{t('amount', lang)}: `${price}`\n"
            f"{t('balance', lang)}: `${balance:.2f}`\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"_{t('insufficient_balance', lang)}_"
        )
    await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=confirm_kb)


async def confirm_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t("home", lang), callback_data="back_main")]])
    )
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"*New Sale #{order_id}*\n{user.full_name}\n{product['name']}\n${price} (Balance)\nStock remaining: {remaining}",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception:
        pass


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
        "pending":   t("status_pending", lang),
        "completed": t("status_completed", lang),
        "rejected":  t("status_rejected", lang)
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
    for k in ['charge_amount', 'charge_method', 'charge_display', 'charge_amount_syp', 'pending_order_id', 'buy_currency']:
        context.user_data.pop(k, None)
    await update.message.reply_text(
        t("welcome", lang),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.main_menu(lang)
    )
    return ConversationHandler.END


async def icloud_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(context)

    context.user_data['cat_source'] = 'back_main'

    products = db.get_all_products()
    icloud_products = [p for p in products if p.get('category') == 'Apple iCloud']

    if not icloud_products:
        await query.edit_message_text(
            t("no_products_category", lang),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t("back", lang), callback_data="back_main")]])
        )
        return

    await query.edit_message_text(
        f"*iCloud*\n\n_{t('choose_product', lang)}_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.products_menu(icloud_products, lang=lang, back_cb="back_main")
    )


async def emails_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(context)

    context.user_data['cat_source'] = 'emails_menu'

    await query.edit_message_text(
        f"*{t('emails_title', lang)}*\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"_{t('choose_type', lang)}_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Outlook", callback_data="cat_Outlook")],
            [InlineKeyboardButton("Gmail",   callback_data="cat_Gmail")],
            [InlineKeyboardButton("Hotmail", callback_data="cat_Hotmail")],
            [InlineKeyboardButton(t("back", lang), callback_data="back_main")],
        ])
    )


async def surveys_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = get_user_lang(context)

    context.user_data['cat_source'] = 'surveys_menu'

    products = db.get_all_products()
    survey_products = [p for p in products if p.get('category', '').lower().startswith('survey')]

    if not survey_products:
        await query.edit_message_text(
            f"*Surveys*\n\n_{t('no_surveys', lang)}_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t("back", lang), callback_data="back_main")]])
        )
        return

    categories = list(dict.fromkeys(p['category'] for p in survey_products if p.get('category')))
    await query.edit_message_text(
        f"*Surveys*\n\n_{t('choose_survey_category', lang)}_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.categories_menu(categories, back_cb="back_main", lang=lang)
    )


async def proxy_menu_simple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🌐 *Proxy Service*\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "• HTTP / HTTPS\n"
        "• SOCKS5\n"
        "• Residential\n"
        "• Mobile 4G / 5G\n"
        "• Modem Private\n\n"
        "━━━━━━━━━━━━━━━━\n"
        "📩 للطلب تواصل مع الأدمن مباشرة:\n"
        "👤 @Allosh96ha\n"
        "━━━━━━━━━━━━━━━━",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 تواصل مع الأدمن", url="https://t.me/Allosh96ha")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
        ])
    )
