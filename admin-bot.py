from telegram.ext import (
    CommandHandler, MessageHandler, filters, 
    ConversationHandler, Application, CallbackQueryHandler
)
from telegram import Update
from config import get_token
import handlears
import asyncio

async def setup_scheduler(app: Application):
    """Bot ishga tushgandan keyin scheduler start qilinadi"""
    handlears.scheduler.start()
    
    await handlears.restart_active_signals(app)

def main():
    TOKEN = get_token()

    dp = Application.builder().token(TOKEN).post_init(setup_scheduler).build()

    dp.add_handler(CommandHandler('start', handlears.start))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("airwaystart", handlears.airway_start)],
        states={
            handlears.FROM_CITY: [CallbackQueryHandler(handlears.from_city_selected)],
            handlears.TO_CITY: [CallbackQueryHandler(handlears.to_city_selected)],
            handlears.DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlears.get_filghts_selected)],
            handlears.FL_NUM: [CallbackQueryHandler(handlears.select_class)],

            handlears.SELECT: [
                CallbackQueryHandler(handlears.select_class, pattern=r'^toggle_class:'),
                CallbackQueryHandler(handlears.select_class, pattern='^confirm_classes$'),
            ],

            handlears.ADD_COMMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlears.add_comment_signal)
            ],
        },
        fallbacks=[CommandHandler("cancel", handlears.cancel)],
        per_message=False,
        allow_reentry=True
    )

    admin_handler = ConversationHandler(
        entry_points=[CommandHandler('addadmin', handlears.admin_start)],
        states={
            handlears.ACCOUNT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlears.admin_name)],
            handlears.ID_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlears.insert_admin)]
        },
        fallbacks=[CommandHandler("cancel", handlears.cancel)],
        allow_reentry=True
    )
    remove_handler = ConversationHandler(
        entry_points=[CommandHandler('remove_admin', handlears.remove_start)],
        states={
            handlears.REMOVE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlears.remove_admin)],
        },
        fallbacks=[CommandHandler("cancel", handlears.cancel)],
        allow_reentry=True
    )
    edit_comment_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handlears.ask_new_comment, pattern='edit_comment')],
        states={
            handlears.EDIT_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handlears.save_new_comment)]
        },
        fallbacks=[CommandHandler("cancel", handlears.cancel)],
        allow_reentry=True
    )

    dp.add_handler(edit_comment_conv)
    dp.add_handler(conv_handler)
    dp.add_handler(admin_handler)
    dp.add_handler(remove_handler)
    dp.add_handler(CommandHandler('viewadmins', handlears.view_all_admin))
    dp.add_handler(CommandHandler('viewactives', handlears.view_actives))
    dp.add_handler(CommandHandler('clsviewactives', handlears.view_actives_by_classes))
    dp.add_handler(CommandHandler('stopallactives', handlears.stop_all_byid))
    dp.add_handler(CallbackQueryHandler(handlears.stop_signal, pattern="stop_signal"))
    dp.add_handler(CallbackQueryHandler(handlears.stop_signal_by_classes, pattern="byclasses_stopsignal"))


    dp.run_polling(allowed_updates=Update.ALL_TYPES, timeout=30)

if __name__ == '__main__':
    main()
