import logging
import asyncio
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
)
from config.settings import BOT_TOKEN, ADMIN_IDS
from handlers import start, hunt, market, home, museum, weapons, inventory, profile, leaderboard
from admin import dashboard, manage_content, economy, players, events, transactions, bot_settings, logs, roles
from handlers.conversations import universal_text_handler
from database.db import init_db

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def handle_noop(update, context):
    """Handle noop callbacks silently"""
    if update.callback_query:
        await update.callback_query.answer()

async def handle_lb(update, context):
    """Handle leaderboard callbacks"""
    query = update.callback_query
    await query.answer()
    lb_type = query.data.replace("lb_", "")
    await leaderboard.show_leaderboard(update, context, lb_type)

async def handle_player_detail(update, context):
    """Handle player detail from admin"""
    query = update.callback_query
    await query.answer()
    player_id = int(query.data.replace("player_detail_", ""))
    await players.show_player_detail(query, player_id)

async def handle_home_eat(update, context):
    query = update.callback_query
    await query.answer()
    await home.show_food_menu(query, update.effective_user.id, "food")

async def handle_home_drink(update, context):
    query = update.callback_query
    await query.answer()
    await home.show_food_menu(query, update.effective_user.id, "drink")

async def handle_home_rest(update, context):
    query = update.callback_query
    await query.answer()
    query.data = "rest_"
    await home.rest(update, context)

async def handle_home_craft(update, context):
    query = update.callback_query
    await query.answer()
    query.data = "craft_"
    await home.craft_food(update, context)

async def handle_upgrade_home_confirm(update, context):
    query = update.callback_query
    await query.answer()
    query.data = "upgrade_home_confirm"
    await home.upgrade_home(update, context)

async def handle_spawn_select(update, context):
    """Handle boss spawn selection"""
    query = update.callback_query
    await query.answer()
    animal_id = query.data.replace("spawn_select_", "")
    
    context.user_data['admin_action'] = 'spawn_boss'
    context.user_data['spawn_animal'] = animal_id
    
    await query.edit_message_text(
        f"👹 <b>Spawn Boss: {animal_id}</b>\n\n"
        f"Kirim format:\n<code>map_id|hp|reward_koin</code>\n\n"
        f"Contoh: <code>forest|50000|25000</code>",
        parse_mode="HTML",
        reply_markup=None
    )

async def handle_topup_select(update, context):
    """Handle topup package selection"""
    query = update.callback_query
    await query.answer()
    pkg_id = query.data.replace("topup_select_", "")
    
    from database.queries import get_topup_packages, get_setting
    packages = await get_topup_packages()
    pkg = next((p for p in packages if p['id'] == pkg_id), None)
    
    if not pkg:
        await query.answer("❌ Paket tidak ditemukan!", show_alert=True)
        return
    
    from utils.helpers import format_number
    actual_coins = int(pkg['coins'] * (1 + pkg['bonus_percent'] / 100))
    payment_info = await get_setting("payment_info") or "Hubungi admin"
    
    context.user_data['topup_pkg_id'] = pkg_id
    context.user_data['topup_amount'] = pkg['price']
    context.user_data['waiting_for'] = 'topup_proof'
    
    await query.edit_message_text(
        f"💎 <b>Top-Up: {pkg['name']}</b>\n\n"
        f"💰 Koin: {format_number(actual_coins)}\n"
        f"💵 Harga: Rp {format_number(pkg['price'])}\n\n"
        f"📋 <b>Cara Bayar:</b>\n{payment_info}\n\n"
        f"📸 Setelah transfer, kirim foto bukti bayar ke bot ini!\n"
        f"Bot akan otomatis meneruskan ke admin.",
        parse_mode="HTML",
        reply_markup=None
    )

async def handle_proof_photo(update, context):
    """Handle payment proof photo from players"""
    user = update.effective_user
    
    if context.user_data.get('waiting_for') == 'topup_proof':
        photo = update.message.photo[-1]
        pkg_id = context.user_data.get('topup_pkg_id')
        amount = context.user_data.get('topup_amount', 0)
        
        from database.queries import get_topup_packages, create_transaction, get_player, create_player
        player = await get_player(user.id)
        if not player:
            player = await create_player(user.id, user.username or "", user.first_name)
        
        packages = await get_topup_packages()
        pkg = next((p for p in packages if p['id'] == pkg_id), None)
        pkg_name = pkg['name'] if pkg else pkg_id
        
        txn_id = await create_transaction(
            user.id, 'topup', amount,
            f"Top-Up {pkg_name}",
            photo.file_id
        )
        
        # Notify admins
        bot = context.bot
        name = user.username or user.first_name
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_photo(
                    admin_id,
                    photo=photo.file_id,
                    caption=(
                        f"📩 <b>Bukti Top-Up Baru!</b>\n\n"
                        f"👤 Player: {name} (ID: {user.id})\n"
                        f"💎 Paket: {pkg_name}\n"
                        f"💵 Rp {from_utils_format(amount)}\n"
                        f"🔖 Txn ID: #{txn_id}\n\n"
                        f"Gunakan /admin untuk verifikasi."
                    ),
                    parse_mode="HTML"
                )
            except Exception:
                pass
        
        context.user_data.pop('waiting_for', None)
        context.user_data.pop('topup_pkg_id', None)
        context.user_data.pop('topup_amount', None)
        
        await update.message.reply_text(
            f"✅ <b>Bukti Diterima!</b>\n\n"
            f"ID Transaksi: <b>#{txn_id}</b>\n"
            f"Admin akan memverifikasi dalam 1x24 jam.\n\n"
            f"Terima kasih! 🦌",
            parse_mode="HTML"
        )
        return
    
    # Pass to admin photo handler
    if user.id in ADMIN_IDS:
        await manage_content.handle_photo_upload(update, context)

def from_utils_format(n):
    return f"{int(n):,}".replace(",", ".")

async def main():
    await init_db()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # ── USER COMMANDS ──────────────────────────────────────────
    app.add_handler(CommandHandler("start", start.cmd_start))
    app.add_handler(CommandHandler("help", start.cmd_help))
    app.add_handler(CommandHandler("admin", dashboard.admin_panel))
    
    # ── MAIN MENU ──────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(start.main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(handle_noop, pattern="^noop$"))
    
    # ── HUNT ───────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(hunt.menu_hunt, pattern="^menu_hunt$"))
    app.add_handler(CallbackQueryHandler(hunt.select_map, pattern="^map_[^_]+$"))
    app.add_handler(CallbackQueryHandler(hunt.select_animal, pattern="^hunt_animal_"))
    app.add_handler(CallbackQueryHandler(hunt.do_hunt, pattern="^do_hunt_"))
    app.add_handler(CallbackQueryHandler(hunt.filter_rarity, pattern="^filter_rarity_"))
    app.add_handler(CallbackQueryHandler(hunt.search_animal, pattern="^search_animal$"))
    
    # ── MARKET ─────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(market.menu_market, pattern="^menu_market$"))
    app.add_handler(CallbackQueryHandler(market.sell_inventory, pattern="^market_sell$"))
    app.add_handler(CallbackQueryHandler(market.sell_item, pattern="^sell_item_"))
    app.add_handler(CallbackQueryHandler(market.sell_item, pattern="^sell_all$"))
    app.add_handler(CallbackQueryHandler(market.check_prices, pattern="^market_prices$"))
    app.add_handler(CallbackQueryHandler(market.p2p_market, pattern="^market_p2p$"))
    app.add_handler(CallbackQueryHandler(market.p2p_list, pattern="^p2p_list$"))
    app.add_handler(CallbackQueryHandler(market.p2p_buy, pattern="^p2p_buy_"))
    app.add_handler(CallbackQueryHandler(market.p2p_create, pattern="^p2p_create$"))
    app.add_handler(CallbackQueryHandler(market.menu_topup, pattern="^market_topup$"))
    app.add_handler(CallbackQueryHandler(handle_topup_select, pattern="^topup_select_"))
    
    # ── HOME ───────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(home.menu_home, pattern="^menu_home$"))
    app.add_handler(CallbackQueryHandler(handle_home_eat, pattern="^home_eat$"))
    app.add_handler(CallbackQueryHandler(handle_home_drink, pattern="^home_drink$"))
    app.add_handler(CallbackQueryHandler(handle_home_rest, pattern="^home_rest$"))
    app.add_handler(CallbackQueryHandler(handle_home_craft, pattern="^home_craft$"))
    app.add_handler(CallbackQueryHandler(home.eat_food, pattern="^eat_"))
    app.add_handler(CallbackQueryHandler(home.drink_water, pattern="^drink_"))
    app.add_handler(CallbackQueryHandler(home.rest, pattern="^rest_"))
    app.add_handler(CallbackQueryHandler(home.craft_food, pattern="^craft_"))
    app.add_handler(CallbackQueryHandler(home.upgrade_home, pattern="^upgrade_home$"))
    app.add_handler(CallbackQueryHandler(handle_upgrade_home_confirm, pattern="^upgrade_home_confirm$"))
    
    # ── MUSEUM ─────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(museum.menu_museum, pattern="^menu_museum$"))
    app.add_handler(CallbackQueryHandler(museum.view_trophies, pattern="^museum_trophies$"))
    app.add_handler(CallbackQueryHandler(museum.add_trophy, pattern="^add_trophy_"))
    app.add_handler(CallbackQueryHandler(museum.museum_leaderboard, pattern="^museum_lb$"))
    app.add_handler(CallbackQueryHandler(museum.achievements, pattern="^achievements$"))
    
    # ── WEAPONS & INVENTORY ────────────────────────────────────
    app.add_handler(CallbackQueryHandler(weapons.menu_weapons, pattern="^menu_weapons$"))
    app.add_handler(CallbackQueryHandler(weapons.buy_weapon, pattern="^buy_weapon_"))
    app.add_handler(CallbackQueryHandler(weapons.equip_weapon, pattern="^equip_weapon_"))
    app.add_handler(CallbackQueryHandler(inventory.menu_inventory, pattern="^menu_inventory$"))
    app.add_handler(CallbackQueryHandler(inventory.view_items, pattern="^inv_items$"))
    app.add_handler(CallbackQueryHandler(inventory.view_animals, pattern="^inv_animals$"))
    app.add_handler(CallbackQueryHandler(inventory.use_item, pattern="^use_item_"))
    
    # ── PROFILE & LEADERBOARD ──────────────────────────────────
    app.add_handler(CallbackQueryHandler(profile.menu_profile, pattern="^menu_profile$"))
    app.add_handler(CallbackQueryHandler(leaderboard.menu_leaderboard, pattern="^menu_leaderboard$"))
    app.add_handler(CallbackQueryHandler(handle_lb, pattern="^lb_"))
    
    # ── ADMIN PANEL ────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(dashboard.admin_dashboard, pattern="^admin_dashboard$"))
    app.add_handler(CallbackQueryHandler(manage_content.menu, pattern="^admin_content$"))
    app.add_handler(CallbackQueryHandler(economy.menu, pattern="^admin_economy$"))
    app.add_handler(CallbackQueryHandler(players.menu, pattern="^admin_players$"))
    app.add_handler(CallbackQueryHandler(events.menu, pattern="^admin_events$"))
    app.add_handler(CallbackQueryHandler(transactions.menu, pattern="^admin_transactions$"))
    app.add_handler(CallbackQueryHandler(bot_settings.menu, pattern="^admin_settings$"))
    app.add_handler(CallbackQueryHandler(logs.menu, pattern="^admin_logs$"))
    app.add_handler(CallbackQueryHandler(roles.menu, pattern="^admin_roles$"))
    
    # ── ADMIN CONTENT ──────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(manage_content.manage_animals, pattern="^content_animals$"))
    app.add_handler(CallbackQueryHandler(manage_content.add_animal, pattern="^add_animal$"))
    app.add_handler(CallbackQueryHandler(manage_content.edit_animal, pattern="^edit_animal_"))
    app.add_handler(CallbackQueryHandler(manage_content.delete_animal, pattern="^del_animal_"))
    app.add_handler(CallbackQueryHandler(manage_content.manage_weapons, pattern="^content_weapons$"))
    app.add_handler(CallbackQueryHandler(manage_content.add_weapon, pattern="^add_weapon$"))
    app.add_handler(CallbackQueryHandler(manage_content.edit_weapon, pattern="^edit_weapon_"))
    app.add_handler(CallbackQueryHandler(manage_content.manage_items, pattern="^content_items$"))
    app.add_handler(CallbackQueryHandler(manage_content.manage_maps, pattern="^content_maps$"))
    app.add_handler(CallbackQueryHandler(manage_content.toggle_map, pattern="^toggle_map_"))
    app.add_handler(CallbackQueryHandler(manage_content.manage_homes, pattern="^content_homes$"))
    app.add_handler(CallbackQueryHandler(manage_content.manage_museum, pattern="^content_museum$"))
    
    # ── ADMIN ECONOMY ──────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(economy.set_prices, pattern="^eco_prices$"))
    app.add_handler(CallbackQueryHandler(economy.topup_packages, pattern="^eco_topup$"))
    app.add_handler(CallbackQueryHandler(economy.rarity_multiplier, pattern="^eco_rarity$"))
    app.add_handler(CallbackQueryHandler(economy.toggle_event, pattern="^eco_event_"))
    app.add_handler(CallbackQueryHandler(economy.set_payment_info, pattern="^eco_payment$"))
    
    # ── ADMIN PLAYERS ──────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(players.search_player, pattern="^player_search$"))
    app.add_handler(CallbackQueryHandler(handle_player_detail, pattern="^player_detail_"))
    app.add_handler(CallbackQueryHandler(players.give_coins, pattern="^player_give_coin_"))
    app.add_handler(CallbackQueryHandler(players.give_coins, pattern="^player_take_coin_"))
    app.add_handler(CallbackQueryHandler(players.give_coins, pattern="^player_coins_"))
    app.add_handler(CallbackQueryHandler(players.give_item, pattern="^player_item_"))
    app.add_handler(CallbackQueryHandler(players.set_level, pattern="^player_level_"))
    app.add_handler(CallbackQueryHandler(players.ban_player, pattern="^player_ban_"))
    app.add_handler(CallbackQueryHandler(players.broadcast, pattern="^player_broadcast$"))
    
    # ── ADMIN EVENTS ───────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(events.spawn_boss_menu, pattern="^event_boss$"))
    app.add_handler(CallbackQueryHandler(events.active_bosses, pattern="^event_active$"))
    app.add_handler(CallbackQueryHandler(events.create_event, pattern="^event_create$"))
    app.add_handler(CallbackQueryHandler(handle_spawn_select, pattern="^spawn_select_"))
    
    # ── ADMIN TRANSACTIONS ─────────────────────────────────────
    app.add_handler(CallbackQueryHandler(transactions.verify_topup, pattern="^txn_verify$"))
    app.add_handler(CallbackQueryHandler(transactions.approve_topup, pattern="^approve_txn_"))
    app.add_handler(CallbackQueryHandler(transactions.reject_topup, pattern="^reject_txn_"))
    app.add_handler(CallbackQueryHandler(transactions.history, pattern="^txn_history$"))
    app.add_handler(CallbackQueryHandler(transactions.export_csv, pattern="^txn_export$"))
    
    # ── ADMIN SETTINGS ─────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(bot_settings.set_photo, pattern="^setting_photos$"))
    app.add_handler(CallbackQueryHandler(bot_settings.set_photo, pattern="^setting_photo_"))
    app.add_handler(CallbackQueryHandler(bot_settings.game_params, pattern="^setting_params$"))
    app.add_handler(CallbackQueryHandler(bot_settings.toggle_feature, pattern="^setting_toggles$"))
    app.add_handler(CallbackQueryHandler(bot_settings.toggle_feature, pattern="^setting_toggle_"))
    
    # ── ADMIN LOGS ─────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(logs.realtime_log, pattern="^log_realtime$"))
    app.add_handler(CallbackQueryHandler(logs.realtime_log, pattern="^log_critical$"))
    app.add_handler(CallbackQueryHandler(logs.realtime_log, pattern="^log_warning$"))
    app.add_handler(CallbackQueryHandler(logs.cheat_detection, pattern="^log_cheat$"))
    
    # ── ADMIN ROLES ────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(roles.add_admin, pattern="^role_add$"))
    app.add_handler(CallbackQueryHandler(roles.edit_role, pattern="^role_list_edit$"))
    app.add_handler(CallbackQueryHandler(roles.edit_role, pattern="^role_edit_"))
    app.add_handler(CallbackQueryHandler(roles.remove_admin, pattern="^role_list_remove$"))
    app.add_handler(CallbackQueryHandler(roles.remove_admin, pattern="^role_remove_"))
    app.add_handler(CallbackQueryHandler(roles.set_role_handler, pattern="^set_role_"))
    
    # ── PHOTO HANDLER ──────────────────────────────────────────
    app.add_handler(MessageHandler(filters.PHOTO, handle_proof_photo))
    
    # ── UNIVERSAL TEXT HANDLER (must be last) ──────────────────
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, universal_text_handler))
    
    logger.info("🦌 HuntGame Bot starting...")
    print("🦌 HuntGame Bot is running!")
    await app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    asyncio.run(main())
