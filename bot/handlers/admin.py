from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.settings import get_settings
from repositories.users import get_user_language
from repositories.charges import get_pending_charges, get_charge
from repositories.appsflyer import get_pending_orders, get_order
from bot.render.keyboards import admin_menu, back_home
from bot.render.strings import t
from bot.render.formatters import safe
from services.admin import AdminService
from domain.errors import NotFoundError, InvalidStateTransitionError

service = AdminService()


def _is_admin(user_id: int) -> bool:
    return user_id in get_settings().admin_ids


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
        user_id = update.callback_query.from_user.id
    else:
        user_id = update.effective_user.id
    lang = get_user_language(user_id)
    if not _is_admin(user_id):
        msg = t("admin_only", lang)
        if update.callback_query:
            await update.callback_query.edit_message_text(msg, reply_markup=back_home(lang))
        else:
            await update.effective_message.reply_text(msg, reply_markup=back_home(lang))
        return
    msg = t("admin_panel", lang)
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=admin_menu())
    else:
        await update.effective_message.reply_text(msg, reply_markup=admin_menu())


async def list_pending_charges(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return
    charges = get_pending_charges(limit=10)
    if not charges:
        await query.edit_message_text("لا يوجد طلبات شحن معلقة", reply_markup=admin_menu())
        return
    await query.edit_message_text("📋 طلبات الشحن المعلقة:", reply_markup=admin_menu())
    for row in charges:
        charge_id, user_id, method, amount_usd, status, created_at = row
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=(
                f"💰 <b>Charge #{charge_id}</b>\n"
                f"👤 User: <code>{user_id}</code>\n"
                f"💵 ${amount_usd:.2f} — {method}\n"
                f"🕐 {created_at}"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ تأكيد", callback_data=f"charge:confirm:{charge_id}"),
                InlineKeyboardButton("❌ رفض",   callback_data=f"charge:reject:{charge_id}"),
            ]]),
        )


async def list_pending_af(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return
    orders = get_pending_orders(limit=10)
    if not orders:
        await query.edit_message_text("لا يوجد طلبات AppsFlyer معلقة", reply_markup=admin_menu())
        return
    await query.edit_message_text("🎮 طلبات AppsFlyer المعلقة:", reply_markup=admin_menu())
    for row in orders:
        order_id, user_id, game_name, price_usd, status, created_at = row
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=(
                f"🎮 <b>AF Order #{order_id}</b>\n"
                f"👤 User: <code>{user_id}</code>\n"
                f"🕹 {safe(game_name)}\n"
                f"💵 ${price_usd:.0f}\n"
                f"🕐 {created_at}"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ قبول", callback_data=f"af:accept:{order_id}"),
                InlineKeyboardButton("❌ رفض",  callback_data=f"af:reject:{order_id}"),
            ]]),
        )


async def charge_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = get_user_language(user_id)
    if not _is_admin(user_id):
        await query.edit_message_text("Unauthorized")
        return
    parts = query.data.split(":")
    action, charge_id = parts[1], int(parts[2])
    try:
        if action == "confirm":
            new_bal = service.confirm_charge(str(user_id), charge_id)
            await query.edit_message_text(f"✅ Charge #{charge_id} confirmed — balance ${new_bal:.2f}")
            charge = get_charge(charge_id)
            if charge:
                try:
                    await context.bot.send_message(
                        chat_id=int(charge[1]),
                        text=f"✅ تم تأكيد شحن رصيدك!\n💵 ${charge[3]:.2f} أُضيفت لرصيدك.",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
        else:
            service.reject_charge(str(user_id), charge_id)
            await query.edit_message_text(f"❌ Charge #{charge_id} rejected")
    except (NotFoundError, InvalidStateTransitionError) as exc:
        await query.edit_message_text(str(exc))


async def af_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = get_user_language(user_id)
    if not _is_admin(user_id):
        await query.edit_message_text("Unauthorized")
        return
    parts = query.data.split(":")
    action, order_id = parts[1], int(parts[2])
    try:
        if action == "accept":
            service.accept_appsflyer(str(user_id), order_id)
            await query.edit_message_text(f"✅ AF Order #{order_id} accepted")
            order = get_order(order_id)
            if order:
                try:
                    await context.bot.send_message(
                        chat_id=int(order[1]),
                        text=f"✅ تم قبول طلب AppsFlyer #{order_id}\n🎮 {safe(order[2])}\nسيتم التواصل معك قريباً.",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
        else:
            new_bal = service.reject_appsflyer(str(user_id), order_id)
            await query.edit_message_text(f"❌ AF Order #{order_id} rejected — refunded ${new_bal:.2f}")
            order = get_order(order_id)
            if order:
                try:
                    await context.bot.send_message(
                        chat_id=int(order[1]),
                        text=f"🔴 تم رفض طلب AppsFlyer #{order_id}\n💰 تم إرجاع ${order[3]:.2f} لرصيدك.",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
    except (NotFoundError, InvalidStateTransitionError) as exc:
        await query.edit_message_text(str(exc))
