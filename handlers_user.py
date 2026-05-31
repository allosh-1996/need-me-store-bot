from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

import database as db
import keyboards as kb
from config import ADMIN_IDS
from lang import t, get_user_lang
from utils import rate_limit


# ─────────────────────────────────────────
# Start / Home
# ─────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.username or "", user.full_name or "")
    lang = get_user_lang(context, user.id)
    await update.message.reply_text(
        t("welcome", lang), parse_mode=ParseMode.MARKDOWN, reply_markup=kb.main_menu(lang)
    )


async def persistent_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """back_main callback + fallback /start inside conversations."""
    query = update.callback_query
    if query:
        await query.answer()
    user = update.effective_user
    db.upsert_user(user.id, user.username or "", user.full_name or "")
    lang = get_user_lang(context, user.id)
    # clear navigation state on going home
    context.user_data.pop("back_context", None)
    context.user_data.pop("category", None)
    if query:
        await query.edit_message_text(
            t("welcome", lang), parse_mode=ParseMode.MARKDOWN, reply_markup=kb.main_menu(lang)
        )
    else:
        await update.message.reply_text(
            t("welcome", lang), parse_mode=ParseMode.MARKDOWN, reply_markup=kb.main_menu(lang)
        )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_lang(context, update.effective_user.id)
    if lang == "en":
        text = "*Commands*\n\n`/start` — Home\n`/products` — Products\n`/charge` — Top Up\n`/help` — Help"
    else:
        text = "*الاوامر*\n\n`/start` — الرئيسية\n`/products` — المنتجات\n`/charge` — شحن رصيد\n`/help` — مساعدة"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def support_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_user_lang(context, update.effective_user.id)
    await update.message.reply_text(
        f"🛟 *{t('support_title', lang)}*\n\n—————————————————\n\n"
        f"👤 @Allosh96ha\n\n_{t('support_body', lang)}_\n\n—————————————————\n",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.main_menu(lang),
    )


# ─────────────────────────────────────────
# Language
# ─────────────────────────────────────────

async def change_language_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user     = update.effective_user
    current  = get_user_lang(context, user.id)
    new_lang = "en" if current == "ar" else "ar"
    context.user_data["lang"] = new_lang
    db.set_user_lang(user.id, new_lang)
    await update.message.reply_text(
        t("welcome", new_lang), parse_mode=ParseMode.MARKDOWN, reply_markup=kb.main_menu(new_lang)
    )


@rate_limit(seconds=2)
async def toggle_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    user     = query.from_user
    current  = get_user_lang(context, user.id)
    new_lang = "en" if current == "ar" else "ar"
    context.user_data["lang"] = new_lang
    db.set_user_lang(user.id, new_lang)
    await query.edit_message_text(
        t("welcome", new_lang), parse_mode=ParseMode.MARKDOWN, reply_markup=kb.main_menu(new_lang)
    )


# ─────────────────────────────────────────
# Products — platform / category / detail
# ─────────────────────────────────────────

@rate_limit(seconds=2)
async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    lang = get_user_lang(context, update.effective_user.id)
    keyboard = [
        [InlineKeyboardButton("🍏 iOS",     callback_data="platform_iOS"),
         InlineKeyboardButton("🤖 Android", callback_data="platform_Android")],
        [InlineKeyboardButton(t("back", lang), callback_data="back_main")],
    ]
    text = f"*{t('choose_platform', lang)}*"
    if query:
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                      reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN,
                                        reply_markup=InlineKeyboardMarkup(keyboard))


async def products_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_products(update, context)


@rate_limit(seconds=2)
async def show_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    platform = query.data.replace("platform_", "")
    lang     = get_user_lang(context, update.effective_user.id)
    context.user_data["platform"]     = platform
    context.user_data["back_context"] = "products"
    context.user_data.pop("category", None)
    categories = db.get_categories(platform)
    if not categories:
        await query.edit_message_text(
            t("no_products_platform", lang), parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t("back", lang), callback_data="products")]])
        )
        return
    await query.edit_message_text(
        f"*{t('choose_category', lang)}*", parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.categories_menu(categories, back_cb="products", lang=lang)
    )


@rate_limit(seconds=2)
async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await query.answer()
    category = query.data.replace("cat_", "")
    lang     = get_user_lang(context, update.effective_user.id)
    context.user_data["category"] = category
    back_ctx = context.user_data.get("back_context", "products")
    products = db.get_products_by_category(category)
    if not products:
        await query.edit_message_text(
            t("no_products_category", lang), parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t("back", lang), callback_data=back_ctx)]])
        )
        return
    await query.edit_message_text(
        f"*{t('choose_product', lang)}*", parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.products_menu(products, lang=lang, back_cb=back_ctx)
    )


@rate_limit(seconds=2)
async def show_product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query      = update.callback_query
    await query.answer()
    product_id = int(query.data.replace("prod_", ""))
    lang       = get_user_lang(context, update.effective_user.id)
    product    = db.get_product(product_id)
    if not product:
        await query.edit_message_text(t("error_not_found", lang))
        return
    has_stock  = product["stock_count"] > 0
    stock_text = t("in_stock", lang) if has_stock else t("out_of_stock", lang)
    text = (
        f"*{product['name']}*\n\n—————————————————\n\n"
        f"📝 {product['description'] or t('no_desc', lang)}\n\n"
        f"💵 ${product['price_usd']}\n📦 {stock_text}\n\n—————————————————\n"
    )
    # back goes to the category list we came from
    category = context.user_data.get("category", "")
    back_ctx  = context.user_data.get("back_context", "products")
    back_cb   = f"cat_{category}" if category else back_ctx
    await query.edit_message_text(
        text, parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.product_detail_menu(product_id, has_stock=has_stock, lang=lang, back_cb=back_cb)
    )


@rate_limit(seconds=5)
async def buy_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query      = update.callback_query
    await query.answer()
    parts      = query.data.split("_")
    product_id = int(parts[1])
    currency   = parts[2] if len(parts) > 2 else "USD"
    user       = query.from_user
    lang       = get_user_lang(context, user.id)
    product    = db.get_product(product_id)
    if not product:
        await query.edit_message_text(t("error_not_found", lang))
        return
    price_usd = float(product["price_usd"] or 0)
    price_syp = float(product["price_syp"] or 0)
    balance   = db.get_balance(user.id)
    if balance < price_usd:
        await query.edit_message_text(
            f"❌ *{t('insufficient_balance', lang)}*\n\n"
            f"💰 {t('current_balance', lang)}: `${balance:.2f}`\n"
            f"💵 {t('price', lang)}: `${price_usd}`\n\n_{t('top_up_first', lang)}_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(t("top_up_title", lang), callback_data="charge_start")],
                [InlineKeyboardButton(t("back", lang),         callback_data=f"prod_{product_id}")],
            ])
        )
        return
    if product["stock_count"] == 0:
        await query.edit_message_text(
            f"❌ *{t('out_of_stock', lang)}*", parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t("back", lang), callback_data=f"prod_{product_id}")]])
        )
        return
    try:
        order_id = db.create_order_atomic(
            user_id=user.id, username=user.username or "", full_name=user.full_name or "",
            product_id=product_id, product_name=product["name"],
            price_usd=price_usd, price_syp=price_syp, currency=currency,
        )
    except ValueError:
        await query.edit_message_text(
            f"❌ *{t('insufficient_balance', lang)}*", parse_mode=ParseMode.MARKDOWN,
        )
        return
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"🛍️ *طلب جديد | New Order*\n\n—————————————————\n\n"
                    f"🔖 Order ID: `#{order_id}`\n👤 {user.full_name} (@{user.username or '—'})\n"
                    f"🆔 `{user.id}`\n📦 {product['name']}\n💵 ${price_usd}\n\n—————————————————"
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass
    await query.edit_message_text(
        f"✅ *{t('order_placed', lang)}*\n\n—————————————————\n\n"
        f"🔖 Order ID: `#{order_id}`\n📦 {product['name']}\n💵 ${price_usd}\n\n"
        f"_{t('order_processing', lang)}_\n\n—————————————————\n",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t("home", lang), callback_data="back_main")]])
    )


# ─────────────────────────────────────────
# Balance
# ─────────────────────────────────────────

@rate_limit(seconds=3)
async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user    = query.from_user
    lang    = get_user_lang(context, user.id)
    balance = db.get_balance(user.id)
    await query.edit_message_text(
        f"💰 *{t('balance_title', lang)}*\n\n—————————————————\n\n"
        f"💵 *${balance:.2f}*\n\n—————————————————\n",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(t("top_up_title", lang), callback_data="charge_start")],
            [InlineKeyboardButton(t("back", lang),         callback_data="back_main")],
        ])
    )


# ─────────────────────────────────────────
# Contact
# ─────────────────────────────────────────

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang  = get_user_lang(context, update.effective_user.id)
    await query.edit_message_text(
        f"🛟 *{t('support_title', lang)}*\n\n—————————————————\n\n"
        f"👤 @Allosh96ha\n\n_{t('support_body', lang)}_\n\n—————————————————\n",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t("back", lang), callback_data="back_main")]])
    )


# ─────────────────────────────────────────
# Proxy
# ─────────────────────────────────────────

@rate_limit(seconds=3)
async def proxy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang  = get_user_lang(context, update.effective_user.id)
    from config import PROXY_TYPES
    keyboard = [[InlineKeyboardButton(label, callback_data=f"proxy_type_{key}")]
                for key, label in PROXY_TYPES.items()]
    keyboard.append([InlineKeyboardButton(t("back", lang), callback_data="back_main")])
    await query.edit_message_text(
        "🌐 *Proxy*\n\n—————————————————\n\nاختر نوع البروكسي:\n_Choose proxy type:_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


@rate_limit(seconds=3)
async def proxy_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query      = update.callback_query
    await query.answer()
    proxy_type = query.data.replace("proxy_type_", "")
    user       = query.from_user
    lang       = get_user_lang(context, user.id)
    from config import PROXY_TYPES
    label = PROXY_TYPES.get(proxy_type, proxy_type)
    context.user_data["proxy_type"]            = proxy_type
    context.user_data["proxy_type_label"]      = label
    context.user_data["waiting_proxy_details"] = True
    await query.edit_message_text(
        f"🌐 *{label}*\n\n—————————————————\n\n"
        f"أرسل تفاصيل طلبك:\n• الكمية\n• الدولة\n• أي ملاحظات\n\n"
        f"_Send your order details:_\n_- Quantity, Country, Notes_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t("back", lang), callback_data="proxy_menu")]])
    )


async def proxy_details_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_proxy_details"):
        return
    user       = update.effective_user
    lang       = get_user_lang(context, user.id)
    proxy_type = context.user_data.get("proxy_type", "")
    label      = context.user_data.get("proxy_type_label", "")
    details    = update.message.text.strip()[:500]
    order_id   = db.create_proxy_order(
        user_id=user.id, username=user.username or "", full_name=user.full_name or "",
        proxy_type=proxy_type, proxy_type_label=label,
        quantity=1, country="—", notes=details,
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"🌐 *طلب بروكسي جديد*\n\n—————————————————\n\n"
                    f"🔖 ID: `#{order_id}`\n👤 {user.full_name} (@{user.username or '—'})\n"
                    f"🆔 `{user.id}`\n📦 {label}\n📝 {details}\n\n—————————————————"
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass
    context.user_data["waiting_proxy_details"] = False
    await update.message.reply_text(
        f"✅ *تم إرسال طلبك*\n\n🔖 Order ID: `#{order_id}`\n📦 {label}\n\n_سيتم التواصل معك قريباً_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.main_menu(lang)
    )


# ─────────────────────────────────────────
# Section menus — Emails / iCloud / Surveys
# ─────────────────────────────────────────

@rate_limit(seconds=2)
async def icloud_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang  = get_user_lang(context, update.effective_user.id)
    context.user_data["back_context"] = "icloud_menu"
    context.user_data.pop("category", None)
    products = db.get_products_by_category("Apple iCloud") or db.get_products_by_platform("iOS")
    if not products:
        await query.edit_message_text(
            t("no_products_platform", lang),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t("back", lang), callback_data="back_main")]])
        )
        return
    await query.edit_message_text(
        f"🍏 *iCloud*\n\n{t('choose_product', lang)}", parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.products_menu(products, lang=lang, back_cb="back_main")
    )


@rate_limit(seconds=2)
async def emails_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang  = get_user_lang(context, update.effective_user.id)
    context.user_data["back_context"] = "emails_menu"
    context.user_data.pop("category", None)
    # try to find email-related categories
    categories = [c for c in db.get_categories()
                  if any(x in c.lower() for x in ["email", "outlook", "gmail", "hotmail", "mail"])]
    if categories:
        await query.edit_message_text(
            f"📧 *{t('btn_emails', lang)}*\n\n{t('choose_category', lang)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.categories_menu(categories, back_cb="back_main", lang=lang)
        )
        return
    # fallback: show all products in Emails category
    products = db.get_products_by_category("Emails")
    if products:
        await query.edit_message_text(
            f"📧 *{t('btn_emails', lang)}*\n\n{t('choose_product', lang)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.products_menu(products, lang=lang, back_cb="back_main")
        )
        return
    await query.edit_message_text(
        t("no_products_platform", lang),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t("back", lang), callback_data="back_main")]])
    )


@rate_limit(seconds=3)
async def surveys_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang  = get_user_lang(context, update.effective_user.id)
    context.user_data["back_context"] = "surveys_menu"
    context.user_data.pop("category", None)
    products = db.get_products_by_category("Survey Accounts")
    if not products:
        await query.edit_message_text(
            t("no_products_category", lang),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t("back", lang), callback_data="back_main")]])
        )
        return
    await query.edit_message_text(
        f"📊 *Surveys*\n\n{t('choose_product', lang)}", parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.products_menu(products, lang=lang, back_cb="back_main")
    )


# ─────────────────────────────────────────
# Universal cancel — /start inside any conversation
# ─────────────────────────────────────────

async def universal_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يلغي أي conversation مفتوح ويرجع للرئيسية — يُستخدم كـ fallback لـ /start."""
    context.user_data.clear()
    user = update.effective_user
    db.upsert_user(user.id, user.username or "", user.full_name or "")
    lang = get_user_lang(context, user.id)
    await update.message.reply_text(
        t("welcome", lang), parse_mode=ParseMode.MARKDOWN, reply_markup=kb.main_menu(lang)
    )
    return ConversationHandler.END
