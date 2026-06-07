from __future__ import annotations

import asyncio
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.settings import get_settings
from repositories.users import ensure_user, get_user_language
from repositories.charges import get_pending_charges, count_pending_charges, get_charge
from repositories.appsflyer import (
    get_pending_orders, count_pending_orders,
    get_accepted_orders, count_accepted_orders,
    get_order,
)
from bot.render.keyboards import admin_menu, back_home
from bot.render.strings import t
from bot.render.formatters import safe
from services.admin import AdminService
from domain.errors import NotFoundError, InvalidStateTransitionError

logger = logging.getLogger(__name__)
service = AdminService()
PAGE_SIZE = 5


def _is_admin(user_id: int) -> bool:
    return user_id in get_settings().admin_ids


# ─── Admin Panel ──────────────────────────────────────────────────────────────

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
        user_id = update.callback_query.from_user.id
        username = update.callback_query.from_user.username or ""
        full_name = update.callback_query.from_user.full_name or ""
    else:
        user_id = update.effective_user.id
        username = update.effective_user.username or ""
        full_name = update.effective_user.full_name or ""

    ensure_user(user_id, username, full_name)
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


# ─── Charges with pagination ──────────────────────────────────────────────────

async def list_pending_charges(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    parts = query.data.split(":")
    offset = int(parts[2]) if len(parts) > 2 else 0

    total = count_pending_charges()
    charges = get_pending_charges(limit=PAGE_SIZE, offset=offset)

    if not charges:
        await query.edit_message_text("لا يوجد طلبات شحن معلقة ✅", reply_markup=admin_menu())
        return

    await query.edit_message_text(
        f"📋 طلبات الشحن المعلقة ({offset + 1}–{min(offset + PAGE_SIZE, total)} من {total}):",
        reply_markup=admin_menu(),
    )

    for row in charges:
        charge_id, user_id, method, amount_usd, status, created_at = row
        nav_buttons = _pagination_buttons("admin:charges", offset, total)
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=(
                f"💰 <b>Charge #{charge_id}</b>\n"
                f"👤 User: <code>{user_id}</code>\n"
                f"💵 ${amount_usd:.2f} — {method}\n"
                f"🕐 {created_at}"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ تأكيد", callback_data=f"charge:confirm:{charge_id}"),
                    InlineKeyboardButton("❌ رفض",   callback_data=f"charge:reject:{charge_id}"),
                ],
                nav_buttons,
            ]),
        )
        await asyncio.sleep(0.05)


# ─── AppsFlyer pending orders ─────────────────────────────────────────────────

async def list_pending_af(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    parts = query.data.split(":")
    offset = int(parts[2]) if len(parts) > 2 else 0

    total = count_pending_orders()
    orders = get_pending_orders(limit=PAGE_SIZE, offset=offset)

    if not orders:
        accepted_total = count_accepted_orders()
        if accepted_total:
            await query.edit_message_text(
                f"✅ لا يوجد طلبات معلقة — يوجد {accepted_total} طلب مقبول بانتظار التنفيذ.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 طلبات مقبولة", callback_data="admin:af_accepted:0")],
                    [InlineKeyboardButton("◀️ رجوع", callback_data="admin:panel")],
                ]),
            )
        else:
            await query.edit_message_text("لا يوجد طلبات AppsFlyer معلقة ✅", reply_markup=admin_menu())
        return

    await query.edit_message_text(
        f"🎮 طلبات AppsFlyer المعلقة ({offset + 1}–{min(offset + PAGE_SIZE, total)} من {total}):",
        reply_markup=admin_menu(),
    )

    for row in orders:
        order_id, user_id, game_name, price_usd, status, created_at = row
        nav_buttons = _pagination_buttons("admin:af_orders", offset, total)
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
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ قبول", callback_data=f"af:accept:{order_id}"),
                    InlineKeyboardButton("❌ رفض",  callback_data=f"af:reject:{order_id}"),
                ],
                nav_buttons,
            ]),
        )
        await asyncio.sleep(0.05)


# ─── AppsFlyer accepted orders ────────────────────────────────────────────────

async def list_accepted_af(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    parts = query.data.split(":")
    offset = int(parts[2]) if len(parts) > 2 else 0

    total = count_accepted_orders()
    orders = get_accepted_orders(limit=PAGE_SIZE, offset=offset)

    if not orders:
        await query.edit_message_text("لا يوجد طلبات AppsFlyer مقبولة ✅", reply_markup=admin_menu())
        return

    await query.edit_message_text(
        f"✅ طلبات AppsFlyer المقبولة ({offset + 1}–{min(offset + PAGE_SIZE, total)} من {total}):",
        reply_markup=admin_menu(),
    )

    for row in orders:
        order_id, user_id, game_name, price_usd, status, created_at = row
        nav_buttons = _pagination_buttons("admin:af_accepted", offset, total)
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=(
                f"✅ <b>AF Order #{order_id}</b> — مقبول\n"
                f"👤 User: <code>{user_id}</code>\n"
                f"🕹 {safe(game_name)}\n"
                f"💵 ${price_usd:.0f}\n"
                f"🕐 {created_at}"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🏁 تم التنفيذ", callback_data=f"af:fulfill:{order_id}"),
                    InlineKeyboardButton("❌ رفض",         callback_data=f"af:reject:{order_id}"),
                ],
                nav_buttons,
            ]),
        )
        await asyncio.sleep(0.05)


# ─── Action handlers ──────────────────────────────────────────────────────────

async def charge_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
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
                except Exception as e:
                    logger.warning("Failed to notify user %s: %s", charge[1], e)
        else:
            service.reject_charge(str(user_id), charge_id)
            await query.edit_message_text(f"❌ Charge #{charge_id} rejected")
            charge = get_charge(charge_id)
            if charge:
                try:
                    await context.bot.send_message(
                        chat_id=int(charge[1]),
                        text=f"❌ تم رفض طلب الشحن #{charge_id}.",
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.warning("Failed to notify user %s: %s", charge[1], e)
    except (NotFoundError, InvalidStateTransitionError) as exc:
        await query.edit_message_text(str(exc))


async def af_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not _is_admin(user_id):
        await query.edit_message_text("Unauthorized")
        return

    parts = query.data.split(":")
    action, order_id = parts[1], int(parts[2])
    try:
        if action == "accept":
            service.accept_appsflyer(str(user_id), order_id)
            await query.edit_message_text(f"✅ AF Order #{order_id} accepted — في انتظار التنفيذ")
            order = get_order(order_id)
            if order:
                try:
                    await context.bot.send_message(
                        chat_id=int(order[1]),
                        text=f"✅ تم قبول طلب AppsFlyer #{order_id}\n🎮 {safe(order[2])}\nسيتم التواصل معك قريباً.",
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.warning("Failed to notify user %s: %s", order[1], e)

        elif action == "fulfill":
            service.fulfill_appsflyer(str(user_id), order_id)
            await query.edit_message_text(f"🏁 AF Order #{order_id} fulfilled ✅")
            order = get_order(order_id)
            if order:
                try:
                    await context.bot.send_message(
                        chat_id=int(order[1]),
                        text=f"🏁 تم تنفيذ طلب AppsFlyer #{order_id} بنجاح!\n🎮 {safe(order[2])}",
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.warning("Failed to notify user %s: %s", order[1], e)

        else:  # reject
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
                except Exception as e:
                    logger.warning("Failed to notify user %s: %s", order[1], e)

    except (NotFoundError, InvalidStateTransitionError) as exc:
        await query.edit_message_text(str(exc))


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _pagination_buttons(base: str, offset: int, total: int) -> list:
    buttons = []
    if offset > 0:
        prev_offset = max(0, offset - PAGE_SIZE)
        buttons.append(InlineKeyboardButton("◀️ السابق", callback_data=f"{base}:{prev_offset}"))
    if offset + PAGE_SIZE < total:
        buttons.append(InlineKeyboardButton("التالي ▶️", callback_data=f"{base}:{offset + PAGE_SIZE}"))
    return buttons
